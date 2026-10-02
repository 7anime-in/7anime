import os
import re
import json
import asyncio
from typing import Dict, Any, Tuple, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8517895964:AAEx3rrj9dGS-EdFX5X20ehXmHRafqJlSrM")

BOT2_STREAM_BASE = os.getenv("BOT2_STREAM_BASE", "https://7anime-bot2-streamer.onrender.com")
BOT3_DOWNLOAD_BASE = os.getenv("BOT3_DOWNLOAD_BASE", "https://7anime-bot3-downloader.onrender.com")

CHANNEL_INPUT = os.getenv("CHANNEL_ID", "sevenanime_ch1")
CHANNEL_IDS = [ch.strip() for ch in CHANNEL_INPUT.split(",") if ch.strip()]

# FILE NAME FOR JSON STORAGE
DATA_FILE = "sitevideo_data.json"
anime_database: Dict[str, Any] = {}
# Fast O(1) Duplicate Lookup Index: set of tuples (chat_id, msg_id)
msg_index: Set[Tuple[str, int]] = set()

pyro_client: Client = None
scanner_task: asyncio.Task = None

# BULK FORWARDING CONTEXT MEMORY
active_context: Dict[str, Any] = {
    "anime": None,
    "season": None,
    "type": None,
    "auto_ep": 1
}

# ==================== PERSISTENT JSON STORAGE ====================
def rebuild_msg_index():
    """Builds O(1) lookup index in memory for fast duplicate checks."""
    global msg_index
    msg_index.clear()
    for slug, anime_data in anime_database.items():
        for season, ep_list in anime_data.get("seasons", {}).items():
            for ep_item in ep_list:
                chat = ep_item.get("chat_id")
                msg = ep_item.get("msg_id")
                if chat and msg is not None:
                    try:
                        msg_index.add((str(chat), int(msg)))
                    except ValueError:
                        continue

def load_database_from_file():
    """Bot restart hone par local sitevideo_data.json load karta hai."""
    global anime_database
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                anime_database = json.load(f)
            rebuild_msg_index()
            print(f"✅ Loaded existing data from {DATA_FILE}! Total Anime: {len(anime_database)}")
        except Exception as e:
            print(f"⚠️ Error reading {DATA_FILE}: {e}")
            anime_database = {}
            rebuild_msg_index()
    else:
        anime_database = {}
        rebuild_msg_index()

def save_database_to_file():
    """JSON file me current DB update karta hai."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(anime_database, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving to {DATA_FILE}: {e}")

# ==================== HELPER FUNCTIONS ====================
def is_video_message(message: Message) -> bool:
    if not message or message.empty:
        return False
    if message.video:
        return True
    if message.document:
        mime = (message.document.mime_type or "").lower()
        fname = (message.document.file_name or "").lower()
        if mime.startswith("video/") or fname.endswith((".mp4", ".mkv", ".webm", ".avi", ".mov")):
            return True
    return False

# ENHANCED CAPTION & CONTEXT PARSER (FIXED FOR S02E04 FORMAT)
def parse_anime_info(caption: str, forward_title: str = "", use_context: bool = True) -> Tuple[str, str, int, str]:
    global active_context

    # 1. BULK CONTEXT MODE
    if use_context and active_context.get("anime"):
        anime_name = active_context["anime"]
        season = str(active_context["season"])
        dub_type = active_context["type"]

        se_match = re.search(r"\bS(\d{1,2})[\s\.\-_]*E(\d{1,3})\b", caption or "", re.IGNORECASE)
        if se_match:
            episode = int(se_match.group(2))
            active_context["auto_ep"] = episode + 1
            return anime_name, season, episode, dub_type

        ep_match = re.search(r"(?:Episode|Ep|E)[\s\-\_]*0*(\d+)", caption or "", re.IGNORECASE)
        if not ep_match:
            clean_text = re.sub(r"\b(1080p|720p|480p|360p|2160p|x264|x265|hevc)\b", "", caption or "", flags=re.IGNORECASE)
            ep_match = re.search(r"(?:[\s\-\_\[\vert{}^])0*(\d{1,3})(?:[\s\-\_\]]|$|\.mp4|\.mkv)", clean_text)

        if ep_match:
            episode = int(ep_match.group(1))
            active_context["auto_ep"] = episode + 1
        else:
            episode = active_context["auto_ep"]
            active_context["auto_ep"] += 1

        return anime_name, season, episode, dub_type

    # 2. STANDARD CAPTION PARSING
    text = caption or ""

    dub_type = "official"
    if re.search(r"\b(unofficial|fandub|fan_dub|fan-dub|fan dub)\b", text, re.IGNORECASE) or "#unofficial" in text.lower() or "#fandub" in text.lower():
        dub_type = "unofficial"
    elif re.search(r"\b(official|officialdub|official_dub)\b", text, re.IGNORECASE) or "#official" in text.lower():
        dub_type = "official"

    # Check combined S01E01 / S02E04 pattern first
    se_match = re.search(r"\bS(\d{1,2})[\s\.\-_]*E(\d{1,3})\b", text, re.IGNORECASE)
    if se_match:
        season = str(int(se_match.group(1)))
        episode = int(se_match.group(2))
    else:
        season_match = re.search(r"\b(?:Season|S)[\s\-\_]*0*(\d+)\b", text, re.IGNORECASE)
        season = str(int(season_match.group(1))) if season_match else "1"

        ep_match = re.search(r"\b(?:Episode|Ep|E)[\s\-\_]*0*(\d+)\b", text, re.IGNORECASE)
        if not ep_match:
            clean_text = re.sub(r"\b(1080p|720p|480p|360p|2160p|x264|x265|hevc|2023|2024|2025|2026)\b", "", text, flags=re.IGNORECASE)
            ep_match = re.search(r"(?:[\s\-\_\[\vert{}^])0*(\d{1,3})(?:[\s\-\_\]]|$|\.mp4|\.mkv)", clean_text)

        episode = int(ep_match.group(1)) if ep_match else 1

    explicit_name = re.search(r"(?:Anime|Title|Name)\s*:\s*([^\n\r\t|]+)", text, re.IGNORECASE)

    if explicit_name:
        raw_title = explicit_name.group(1).strip()
    elif forward_title:
        raw_title = forward_title
    else:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        raw_title = lines[0] if lines else "Unknown Anime"

    clean_title = re.sub(r"(?i)\bS\d{1,2}[\s\.\-_]*E\d{1,3}\b", "", raw_title)
    clean_title = re.sub(
        r"(?i)\b(in|hindi|dubbed|dub|sub|official|unofficial|fandub|1080p|720p|480p|fhd|hd|hevc|x264|x265|episode|season|language|quality|main channel)\b",
        "",
        clean_title,
    )
    clean_title = re.sub(r"[^\w\s]", " ", clean_title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip().title()

    if not clean_title or len(clean_title) < 2:
        clean_title = "Unknown Anime"

    return clean_title, season, episode, dub_type

# OPTIMIZED ADD TO DATABASE WITH O(1) LOOKUP & TYPE SAFETY
def add_to_database(chat_id: str, msg_id: int, caption: str, forward_title: str, use_context: bool = True, auto_save: bool = True) -> Tuple[str, str, int, str]:
    formatted_chat = str(chat_id).replace("@", "")

    anime_name, season_num, ep_num, dub_type = parse_anime_info(caption, forward_title, use_context=use_context)
    slug_key = re.sub(r'[^a-zA-Z0-9]+', '_', anime_name.lower()).strip('_')

    # Fast O(1) Duplicate Check
    if (formatted_chat, int(msg_id)) in msg_index:
        for slug, anime_data in anime_database.items():
            for season, ep_list in anime_data.get("seasons", {}).items():
                for ep_item in ep_list:
                    if str(ep_item.get("chat_id")) == formatted_chat and int(ep_item.get("msg_id", 0)) == int(msg_id):
                        ep_item["stream_url"] = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{formatted_chat}/{msg_id}.mp4"
                        ep_item["download_url"] = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{formatted_chat}/{msg_id}"
                        ep_item["embed_url"] = f"https://t.me/{formatted_chat}/{msg_id}?embed=1"
                        ep_item["tg_url"] = f"https://t.me/{formatted_chat}/{msg_id}"
                        if auto_save:
                            save_database_to_file()
                        return anime_name, season_num, ep_num, dub_type

    if slug_key not in anime_database:
        anime_database[slug_key] = {"title": anime_name, "seasons": {}}

    anime_database[slug_key]["title"] = anime_name

    if season_num not in anime_database[slug_key]["seasons"]:
        anime_database[slug_key]["seasons"][season_num] = []

    ep_list = anime_database[slug_key]["seasons"][season_num]

    stream_url = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{formatted_chat}/{msg_id}.mp4"
    download_url = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{formatted_chat}/{msg_id}"
    embed_url = f"https://t.me/{formatted_chat}/{msg_id}?embed=1"
    tg_url = f"https://t.me/{formatted_chat}/{msg_id}"

    ep_entry = {
        "ep": ep_num,
        "chat_id": formatted_chat,
        "msg_id": int(msg_id),
        "type": dub_type,
        "stream_url": stream_url,
        "download_url": download_url,
        "embed_url": embed_url,
        "tg_url": tg_url
    }

    existing_ep = next((item for item in ep_list if item["ep"] == ep_num and item.get("type", "official") == dub_type), None)

    if existing_ep:
        existing_ep.update(ep_entry)
    else:
        ep_list.append(ep_entry)
        ep_list.sort(key=lambda x: x["ep"])

    msg_index.add((formatted_chat, int(msg_id)))

    if auto_save:
        save_database_to_file()

    return anime_name, season_num, ep_num, dub_type

# ==================== CHANNEL AUTO SCANNER ====================
async def auto_scan_channels():
    global pyro_client
    if not CHANNEL_IDS or not pyro_client or not pyro_client.is_connected:
        return

    print("🔍 Bot 1 Scanning Telegram Channels...")

    for ch_id in CHANNEL_IDS:
        if not ch_id:
            continue
        try:
            if ch_id.startswith("-100") or ch_id.startswith("-"):
                target_chat = int(ch_id)
            elif ch_id.isdigit():
                target_chat = int(f"-100{ch_id}")
            else:
                target_chat = ch_id if ch_id.startswith("@") else f"@{ch_id}"
            
            chunk_size = 100
            current_id = 1
            empty_count = 0

            while empty_count < 10:
                msg_ids = list(range(current_id, current_id + chunk_size))
                try:
                    messages = await pyro_client.get_messages(target_chat, msg_ids)
                    has_media = False

                    if messages:
                        for message in messages:
                            if is_video_message(message):
                                has_media = True
                                caption = message.caption or getattr(message.video or message.document, "file_name", "") or ""
                                forward_title = (
                                    message.forward_from_chat.title
                                    if message.forward_from_chat
                                    else (message.forward_sender_name or "")
                                )
                                add_to_database(str(target_chat), message.id, caption, forward_title, use_context=False, auto_save=False)

                    if not has_media:
                        empty_count += 1
                    else:
                        empty_count = 0

                    current_id += chunk_size
                    await asyncio.sleep(1)

                except Exception:
                    current_id += chunk_size
                    await asyncio.sleep(1)

            save_database_to_file()
            print(f"✅ Channel '{target_chat}' scan sync completed!")
        except Exception as e:
            print(f"⚠️ Error scanning channel {ch_id}: {e}")

async def channel_scanner_loop():
    await asyncio.sleep(10)
    while True:
        await auto_scan_channels()
        await asyncio.sleep(600)

# ==================== LIFECYCLE & TELEGRAM BOT COMMANDS ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pyro_client, scanner_task
    print("🚀 Starting Bot 1 (Master Scanner API)...")

    load_database_from_file()

    pyro_client = Client(
        "bot1_scanner_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )

    @pyro_client.on_message(filters.command(["start", "ping"]))
    async def start_cmd(client: Client, message: Message):
        start_text = (
            "🤖 **7anime Bot 1: Master Scanner & Indexer Bot**\n\n"
            "📌 **Commands & Usage Guide:**\n\n"
            "🎯 **Bulk Forwarding:**\n"
            "• `/setcontext <Anime> | <Season> | <Audio>`\n"
            "  _Example:_ `/setcontext Solo Leveling | 2 | official`\n"
            "• `/clearcontext` - Clear active bulk context\n\n"
            "📺 **Channel Management:**\n"
            "• `/listchannels` - View all monitored channels\n"
            "• `/addchannel <@username>` - Add new channel\n"
            "  _Example:_ `/addchannel @sevenanime_ch2`\n"
            "• `/rescan` - Reset DB & fresh scan channels\n\n"
            "🛠️ **Manual Database Edits:**\n"
            "• `/add <channel> <msg_id> <slug> <season> <ep> [official/unofficial]`\n"
            "  _Example:_ `/add sevenanime_ch1 248 solo_leveling 2 1 official`\n"
            "• `/delete <slug> <season> <ep>`\n"
            "  _Example:_ `/delete solo_leveling 2 1`\n"
            "• `/rename <slug> <New Title>`\n"
            "  _Example:_ `/rename solo_leveling Solo Leveling: Arise`\n\n"
            "📊 **System:**\n"
            "• `/stats` - View total indexed anime & episode count\n"
            "• `/start` or `/ping` - Show this full help menu"
        )
        await message.reply_text(start_text, quote=True)

    @pyro_client.on_message(filters.command("setcontext"))
    async def set_context_cmd(client: Client, message: Message):
        global active_context
        args = message.text.split(maxsplit=1)
        if len(args) < 2 or "|" not in args[1]:
            return await message.reply_text(
                "❌ Usage: `/setcontext Anime Name | Season | Audio`\n\n"
                "Example: `/setcontext Solo Leveling | 2 | official`\n"
                "Example: `/setcontext Naruto | 1 | unofficial`", 
                quote=True
            )

        parts = [p.strip() for p in args[1].split("|")]
        anime_name = parts[0]
        season_num = parts[1] if len(parts) > 1 else "1"
        dub_type = parts[2].lower() if len(parts) > 2 else "official"

        active_context = {
            "anime": anime_name,
            "season": season_num,
            "type": dub_type,
            "auto_ep": 1
        }

        await message.reply_text(
            f"🎯 **Bulk Context Active!**\n\n"
            f"• **Anime:** `{anime_name}`\n"
            f"• **Season:** `{season_num}`\n"
            f"• **Audio:** `{dub_type.upper()}`\n\n"
            f"Ab is season ki saari videos ek sath forward kar do! Auto-indexing start ho gayi hai.\n"
            f"Forward karne ke baad `/clearcontext` bhej dena.",
            quote=True
        )

    @pyro_client.on_message(filters.command("clearcontext"))
    async def clear_context_cmd(client: Client, message: Message):
        global active_context
        active_context = {"anime": None, "season": None, "type": None, "auto_ep": 1}
        await message.reply_text("🧹 **Bulk Context Cleared!** Standard caption parsing active.", quote=True)

    @pyro_client.on_message(filters.command("stats"))
    async def stats_cmd(client: Client, message: Message):
        total_anime = len(anime_database)
        total_eps = sum(
            len(ep_list)
            for anime in anime_database.values()
            for ep_list in anime.get("seasons", {}).values()
        )
        ctx_status = f"`{active_context['anime']}` (S{active_context['season']})" if active_context["anime"] else "None"
        await message.reply_text(
            f"📊 **Total Anime:** `{total_anime}` | **Total Episodes:** `{total_eps}`\n"
            f"📁 **Data File:** `sitevideo_data.json`\n"
            f"🎯 **Active Context:** {ctx_status}",
            quote=True
        )

    @pyro_client.on_message(filters.command("rescan"))
    async def rescan_cmd(client: Client, message: Message):
        anime_database.clear()
        msg_index.clear()
        save_database_to_file()
        await message.reply_text("🔄 **Database Reset! Rescanning channels...**", quote=True)
        asyncio.create_task(auto_scan_channels())

    @pyro_client.on_message(filters.command("addchannel"))
    async def add_channel_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return await message.reply_text("❌ Usage: `/addchannel @channel_username`", quote=True)
        
        new_ch = args[1].strip()
        if new_ch not in CHANNEL_IDS:
            CHANNEL_IDS.append(new_ch)
            await message.reply_text(f"✅ **Channel Added:** `{new_ch}`\nStarting scan...", quote=True)
            asyncio.create_task(auto_scan_channels())
        else:
            await message.reply_text(f"⚠️ Channel `{new_ch}` is already monitored.", quote=True)

    @pyro_client.on_message(filters.command("listchannels"))
    async def list_channels_cmd(client: Client, message: Message):
        channels_str = "\n".join([f"• `{ch}`" for ch in CHANNEL_IDS])
        await message.reply_text(f"📺 **Monitored Channels:**\n{channels_str}", quote=True)

    @pyro_client.on_message(filters.command("add"))
    async def manual_add_cmd(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 6:
            return await message.reply_text("❌ Usage: `/add <channel> <msg_id> <anime_slug> <season> <ep> [official/unofficial]`", quote=True)

        chat_id = args[1].replace("@", "")
        msg_id = int(args[2])
        slug_key = args[3].lower()
        season_num = str(args[4])
        ep_num = int(args[5])
        dub_type = args[6].lower() if len(args) > 6 else "official"

        if slug_key not in anime_database:
            anime_database[slug_key] = {"title": slug_key.replace("_", " ").title(), "seasons": {}}

        if season_num not in anime_database[slug_key]["seasons"]:
            anime_database[slug_key]["seasons"][season_num] = []

        ep_list = anime_database[slug_key]["seasons"][season_num]
        
        ep_entry = {
            "ep": ep_num,
            "chat_id": chat_id,
            "msg_id": msg_id,
            "type": dub_type,
            "stream_url": f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{chat_id}/{msg_id}.mp4",
            "download_url": f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{chat_id}/{msg_id}",
            "embed_url": f"https://t.me/{chat_id}/{msg_id}?embed=1",
            "tg_url": f"https://t.me/{chat_id}/{msg_id}"
        }

        existing_ep = next((i for i in ep_list if i["ep"] == ep_num and i.get("type") == dub_type), None)
        if existing_ep:
            existing_ep.update(ep_entry)
        else:
            ep_list.append(ep_entry)
            ep_list.sort(key=lambda x: x["ep"])

        msg_index.add((chat_id, msg_id))
        save_database_to_file()
        await message.reply_text(f"✅ Episode added manually to `{slug_key}` (S{season_num}E{ep_num})!", quote=True)

    @pyro_client.on_message(filters.command("delete"))
    async def delete_ep_cmd(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 4:
            return await message.reply_text("❌ Usage: `/delete <anime_slug> <season> <ep>`", quote=True)

        slug_key, season_num, ep_num = args[1].lower(), str(args[2]), int(args[3])

        if slug_key in anime_database and season_num in anime_database[slug_key]["seasons"]:
            ep_list = anime_database[slug_key]["seasons"][season_num]
            anime_database[slug_key]["seasons"][season_num] = [i for i in ep_list if i["ep"] != ep_num]
            rebuild_msg_index()
            save_database_to_file()
            return await message.reply_text(f"🗑️ Deleted S{season_num}E{ep_num} from `{slug_key}`.", quote=True)

        await message.reply_text("❌ Episode not found in database.", quote=True)

    @pyro_client.on_message(filters.command("rename"))
    async def rename_anime_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            return await message.reply_text("❌ Usage: `/rename <anime_slug> <New Anime Title>`", quote=True)

        slug_key, new_title = args[1].lower(), args[2].strip()
        if slug_key in anime_database:
            anime_database[slug_key]["title"] = new_title
            save_database_to_file()
            return await message.reply_text(f"✏️ Title updated to **{new_title}**!", quote=True)

        await message.reply_text("❌ Anime slug not found.", quote=True)

    # AUTO LIVE FORWARD & UPLOAD HANDLER
    @pyro_client.on_message((filters.video | filters.document) & ~filters.command(["start", "stats", "rescan", "ping", "add", "delete", "rename", "addchannel", "listchannels", "setcontext", "clearcontext"]))
    async def auto_index_media(client: Client, message: Message):
        if not is_video_message(message):
            return

        chat = message.chat
        chat_identifier = f"@{chat.username}" if chat.username else str(chat.id)
        msg_id = message.id

        caption = message.caption or getattr(message.video or message.document, "file_name", "") or ""
        forward_title = (
            message.forward_from_chat.title
            if message.forward_from_chat
            else (message.forward_sender_name or "")
        )

        anime_name, season_num, ep_num, dub_type = add_to_database(chat_identifier, msg_id, caption, forward_title, use_context=True, auto_save=True)
        
        reply_text = (
            f"✅ **Video Indexed Automatically!**\n\n"
            f"🎬 **Anime:** `{anime_name}`\n"
            f"🍂 **Season:** `{season_num}` | 📺 **Episode:** `{ep_num}`\n"
            f"🎙️ **Audio:** `{dub_type.upper()}`\n\n"
            f"📁 Saved to `sitevideo_data.json`"
        )
        await message.reply_text(reply_text, quote=True)

    asyncio.create_task(pyro_client.start())
    print("✅ Bot 1 Active & Ready!")

    scanner_task = asyncio.create_task(channel_scanner_loop())

    yield

    if scanner_task:
        scanner_task.cancel()
    if pyro_client and pyro_client.is_connected:
        await pyro_client.stop()

app = FastAPI(title="Bot 1 - Master Scanner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== REST API ENDPOINTS ====================
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Bot 1 Scanner Engine Active 🚀", "total_anime": len(anime_database)}

@app.get("/api/all-anime")
def get_all_anime():
    return anime_database

@app.get("/api/episodes/{anime_slug}")
def get_anime_episodes(anime_slug: str):
    clean_query = re.sub(r'[^a-zA-Z0-9]', '', anime_slug.lower())

    if not anime_database:
        return {"title": anime_slug.replace("_", " ").title(), "seasons": {"1": []}}

    if anime_slug.lower() in anime_database:
        return anime_database[anime_slug.lower()]

    for key in anime_database:
        clean_key = re.sub(r'[^a-zA-Z0-9]', '', key.lower())
        if clean_query in clean_key or clean_key in clean_query:
            return anime_database[key]

    default_title = anime_slug.replace("_", " ").title()
    return {"title": default_title, "seasons": {"1": []}}

@app.get("/api/rescan")
async def rescan_api():
    anime_database.clear()
    msg_index.clear()
    save_database_to_file()
    asyncio.create_task(auto_scan_channels())
    return {"status": "Rescan initiated"}
