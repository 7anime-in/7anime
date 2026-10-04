import os
import re
import json
import base64
import asyncio
import urllib.request
import urllib.error
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

# GITHUB SYNC SETTINGS
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "7anime-in/7anime")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH", "sitevideo_data.json")

DATA_FILE = "sitevideo_data.json"
anime_database: Dict[str, Any] = {}

# Fast Lookups
msg_index: Set[Tuple[str, int]] = set()
msg_lookup: Dict[Tuple[str, int], Tuple[str, str, int]] = {}

pyro_client: Client = None
scanner_task: asyncio.Task = None

active_context: Dict[str, Any] = {
    "anime": None,
    "season": None,
    "type": None,
    "auto_ep": 1
}

# ==================== PRE-COMPILED REGEX PATTERNS ====================
RE_UNOFFICIAL_DUB = re.compile(r"\b(unofficial|fandub|fan_dub|fan-dub|fan dub)\b", re.IGNORECASE)
RE_OFFICIAL_DUB = re.compile(r"\b(official|offical|officialdub|official_dub)\b", re.IGNORECASE)

RE_SE_COMBINED = re.compile(r"\bS(\d{1,2})[\s\.\-_]*E(\d{1,3})\b", re.IGNORECASE)
RE_SEASON_ONLY = re.compile(r"\b(?:Season|S)[\s\-\_]*0*(\d+)\b", re.IGNORECASE)
RE_EPISODE_ONLY = re.compile(r"\b(?:Episode|Ep|E)[\s\-\_]*0*(\d+)\b", re.IGNORECASE)
RE_CLEAN_NOISE_EP = re.compile(r"\b(1080p|720p|480p|360p|2160p|x264|x265|hevc|2023|2024|2025|2026)\b", re.IGNORECASE)
RE_EP_FALLBACK = re.compile(r"(?:[\s\-\_\[\vert{}^])0*(\d{1,3})(?:[\s\-\_\]]|$|\.mp4|\.mkv)")

RE_FN_SE = re.compile(r"(?:[_\s\.\-]|\b)[sS](\d{1,2})[_\s\.\-]*[eE](\d{1,3})\b")
RE_FN_S = re.compile(r"(?:[_\s\.\-]|\b)[sS]0*(\d{1,2})\b")
RE_FN_E = re.compile(r"(?:[_\s\.\-]|\b)[eE]0*(\d{1,3})\b")

RE_EXPLICIT_TAG = re.compile(r"(?:Anime\s*Name|Anime|Title|Name)\s*[:\-]\s*([^\n\r]+)", re.IGNORECASE)
RE_NON_GENERIC_LINE = re.compile(r"^(Episode|Season|Language|Quality|Main Channel|Powered By|http|https|@)", re.IGNORECASE)
RE_GENERIC_FORWARD = re.compile(r"(official|community|animez|channel|network|main)", re.IGNORECASE)

RE_CLEAN_TITLE_TAGS = re.compile(
    r"(?i)\b(in|hindi|dubbed|dub|sub|official|offical|unofficial|fandub|1080p|720p|480p|fhd|hd|hevc|x264|x265|language|quality|main channel|community|animez)\b"
)
RE_CODEC_HEVC = re.compile(r"\b(x265|hevc|h265|h\.265|265)\b", re.IGNORECASE)
RE_CODEC_AAC = re.compile(r"\b(aac|aac2\.0)\b", re.IGNORECASE)
RE_CODEC_OPUS = re.compile(r"\b(opus|ac3|eac3|dts)\b", re.IGNORECASE)

# ==================== FORMAT & CODEC DETECTOR ====================
def detect_video_format(caption: str = "", filename: str = "") -> str:
    combined = f"{caption} {filename}".lower()
    
    v_codec = "H.265 / HEVC" if RE_CODEC_HEVC.search(combined) else "H.264 / AVC"
    
    if RE_CODEC_AAC.search(combined):
        a_codec = "AAC"
    elif RE_CODEC_OPUS.search(combined):
        a_codec = "Opus/AC3"
    else:
        a_codec = "AAC"

    return f"{v_codec} ({a_codec})"

# ==================== GITHUB API SYNC & LOCAL PERSISTENCE ====================
def sync_to_github_sync(json_str: str) -> bool:
    if not GITHUB_TOKEN:
        print("⚠ GITHUB_TOKEN missing! Skipping GitHub commit.")
        return False

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "7anime-Bot1"
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        sha = None
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    sha = data.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"⚠️ GitHub GET SHA Error: {e}")

        encoded_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        payload = {
            "message": "Auto-update sitevideo_data.json via Bot 1",
            "content": encoded_content,
            "branch": GITHUB_BRANCH
        }
        if sha:
            payload["sha"] = sha

        data_bytes = json.dumps(payload).encode("utf-8")
        put_req = urllib.request.Request(url, data=data_bytes, headers=headers, method="PUT")
        put_req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(put_req) as resp:
            if resp.status in (200, 201):
                print("✅ Successfully updated sitevideo_data.json on GitHub!")
                return True
    except Exception as e:
        print(f"⚠️ GitHub Sync Exception: {e}")

    return False

def _write_file_sync(data_str: str):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(data_str)

async def save_database_to_file():
    json_str = json.dumps(anime_database, indent=2, ensure_ascii=False)
    try:
        await asyncio.to_thread(_write_file_sync, json_str)
    except Exception as e:
        print(f"⚠️ Error saving locally: {e}")

    await asyncio.to_thread(sync_to_github_sync, json_str)

def rebuild_msg_index():
    global msg_index, msg_lookup
    msg_index.clear()
    msg_lookup.clear()
    
    for slug, anime_data in anime_database.items():
        for season, ep_list in anime_data.get("seasons", {}).items():
            for idx, ep_item in enumerate(ep_list):
                chat = ep_item.get("chat_id")
                msg = ep_item.get("msg_id")
                if chat and msg is not None:
                    try:
                        key = (str(chat), int(msg))
                        msg_index.add(key)
                        msg_lookup[key] = (slug, str(season), idx)
                    except ValueError:
                        continue

def load_database_from_file():
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

def parse_anime_info(caption: str, forward_title: str = "", filename: str = "", use_context: bool = True) -> Tuple[str, str, int, str]:
    global active_context

    caption_text = caption or ""
    file_text = filename or ""

    # 1. AUDIO / DUB TYPE EXTRACTION
    dub_type = None

    if RE_UNOFFICIAL_DUB.search(caption_text) or "#unofficial" in caption_text.lower() or "#fandub" in caption_text.lower():
        dub_type = "unofficial"
    elif RE_OFFICIAL_DUB.search(caption_text) or "#official" in caption_text.lower():
        dub_type = "official"

    if not dub_type and file_text:
        if RE_UNOFFICIAL_DUB.search(file_text):
            dub_type = "unofficial"
        elif RE_OFFICIAL_DUB.search(file_text):
            dub_type = "official"

    if not dub_type:
        dub_type = active_context.get("type") if (use_context and active_context.get("type")) else "official"

    # 2. SEASON & EPISODE EXTRACTION
    season = None
    episode = None

    # Priority 1: Caption Text
    se_match = RE_SE_COMBINED.search(caption_text)
    if se_match:
        season = str(int(se_match.group(1)))
        episode = int(se_match.group(2))
    else:
        season_match = RE_SEASON_ONLY.search(caption_text)
        if season_match:
            season = str(int(season_match.group(1)))

        ep_match = RE_EPISODE_ONLY.search(caption_text)
        if not ep_match:
            clean_text = RE_CLEAN_NOISE_EP.sub("", caption_text)
            ep_match = RE_EP_FALLBACK.search(clean_text)

        if ep_match:
            episode = int(ep_match.group(1))

    # Priority 2: Video File Name
    if (season is None or episode is None) and file_text:
        fn_se_match = RE_FN_SE.search(file_text)
        if fn_se_match:
            if season is None:
                season = str(int(fn_se_match.group(1)))
            if episode is None:
                episode = int(fn_se_match.group(2))
        else:
            if season is None:
                fn_s = RE_FN_S.search(file_text)
                if fn_s:
                    season = str(int(fn_s.group(1)))
            if episode is None:
                fn_e = RE_FN_E.search(file_text)
                if fn_e:
                    episode = int(fn_e.group(1))

    # Context Fallbacks for Season & Episode
    if season is None:
        season = str(active_context["season"]) if (use_context and active_context.get("season")) else "1"

    if episode is None:
        if use_context and active_context.get("auto_ep"):
            episode = active_context["auto_ep"]
            active_context["auto_ep"] += 1
        else:
            episode = 1
    else:
        if use_context and active_context.get("anime"):
            active_context["auto_ep"] = episode + 1

    # 3. ANIME NAME EXTRACTION
    raw_title = None

    # Priority A: Caption Tag "Anime name: XYZ", "Anime: XYZ", "Title: XYZ"
    explicit_match = RE_EXPLICIT_TAG.search(caption_text)
    if explicit_match:
        raw_title = explicit_match.group(1).strip()
        raw_title = re.sub(r"[\)\}\]]+$", "", raw_title).strip()

    # Priority B: Video File Name Extraction
    elif file_text and not re.search(r"^(video|file|doc|\d+$)", file_text, re.IGNORECASE):
        fn_clean = re.sub(r"\.(mp4|mkv|webm|avi|mov)$", "", file_text, flags=re.IGNORECASE)
        fn_clean = re.sub(r"(?i)[_\s\.\-]*[sS]\d{1,2}[_\s\.\-]*[eE]\d{1,3}\b", "", fn_clean)
        fn_clean = re.sub(r"(?i)[_\s\.\-]*[sS]\d{1,2}\b", "", fn_clean)
        fn_clean = re.sub(r"(?i)[_\s\.\-]*[eE]\d{1,3}\b", "", fn_clean)
        fn_clean = RE_CLEAN_TITLE_TAGS.sub("", fn_clean)
        fn_clean = re.sub(r"[_\.\-]", " ", fn_clean).strip()
        if len(fn_clean) > 2:
            raw_title = fn_clean

    # Priority C: Active Context
    elif use_context and active_context.get("anime"):
        raw_title = active_context["anime"]

    # Priority D: First Non-Generic Line in Caption
    else:
        lines = [l.strip() for l in caption_text.split("\n") if l.strip()]
        for line in lines:
            if not RE_NON_GENERIC_LINE.search(line):
                raw_title = line
                break

    # Priority E: Forward Title Fallback
    if not raw_title and forward_title:
        if not RE_GENERIC_FORWARD.search(forward_title):
            raw_title = forward_title

    if not raw_title:
        raw_title = "Unknown Anime"

    # Final Cleaning of Title
    clean_title = re.sub(r"(?i)\bS\d{1,2}[\s\.\-_]*E\d{1,3}\b", "", raw_title)
    clean_title = re.sub(r"(?i)\b(Episode|Season)\s*\d+", "", clean_title)
    clean_title = RE_CLEAN_TITLE_TAGS.sub("", clean_title)
    clean_title = re.sub(r"[^\w\s]", " ", clean_title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip().title()

    if not clean_title or len(clean_title) < 2:
        clean_title = "Unknown Anime"

    return clean_title, season, episode, dub_type

async def add_to_database(chat_id: str, msg_id: int, caption: str, forward_title: str, filename: str = "", use_context: bool = True, auto_save: bool = True) -> Tuple[str, str, int, str, str]:
    formatted_chat = str(chat_id).replace("@", "")
    key = (formatted_chat, int(msg_id))

    anime_name, season_num, ep_num, dub_type = parse_anime_info(caption, forward_title, filename, use_context=use_context)
    slug_key = re.sub(r'[^a-zA-Z0-9]+', '_', anime_name.lower()).strip('_')
    video_format = detect_video_format(caption, filename)

    # Fast O(1) Update if message already indexed
    if key in msg_index and key in msg_lookup:
        slug, season, idx = msg_lookup[key]
        try:
            ep_item = anime_database[slug]["seasons"][season][idx]
            ep_item["stream_url"] = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{formatted_chat}/{msg_id}.mp4"
            ep_item["download_url"] = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{formatted_chat}/{msg_id}"
            ep_item["embed_url"] = f"https://t.me/{formatted_chat}/{msg_id}?embed=1"
            ep_item["tg_url"] = f"https://t.me/{formatted_chat}/{msg_id}"
            ep_item["format"] = video_format
            if auto_save:
                await save_database_to_file()
            return anime_database[slug]["title"], season, ep_item["ep"], ep_item.get("type", dub_type), video_format
        except (KeyError, IndexError):
            pass

    if slug_key not in anime_database:
        anime_database[slug_key] = {"title": anime_name, "seasons": {}}

    anime_database[slug_key]["title"] = anime_name

    if season_num not in anime_database[slug_key]["seasons"]:
        anime_database[slug_key]["seasons"][season_num] = []

    ep_list = anime_database[slug_key]["seasons"][season_num]

    ep_entry = {
        "ep": ep_num,
        "chat_id": formatted_chat,
        "msg_id": int(msg_id),
        "type": dub_type,
        "format": video_format,
        "stream_url": f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{formatted_chat}/{msg_id}.mp4",
        "download_url": f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{formatted_chat}/{msg_id}",
        "embed_url": f"https://t.me/{formatted_chat}/{msg_id}?embed=1",
        "tg_url": f"https://t.me/{formatted_chat}/{msg_id}"
    }

    existing_ep = next((item for item in ep_list if item["ep"] == ep_num and item.get("type", "official") == dub_type), None)

    if existing_ep:
        existing_ep.update(ep_entry)
    else:
        ep_list.append(ep_entry)
        ep_list.sort(key=lambda x: x["ep"])

    msg_index.add(key)
    msg_lookup[key] = (slug_key, season_num, len(ep_list) - 1)

    if auto_save:
        await save_database_to_file()

    return anime_name, season_num, ep_num, dub_type, video_format

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
                                fname = getattr(message.video or message.document, "file_name", "") or ""
                                forward_title = (
                                    message.forward_from_chat.title
                                    if message.forward_from_chat
                                    else (message.forward_sender_name or "")
                                )
                                await add_to_database(str(target_chat), message.id, caption, forward_title, filename=fname, use_context=False, auto_save=False)

                    if not has_media:
                        empty_count += 1
                    else:
                        empty_count = 0

                    current_id += chunk_size
                    await asyncio.sleep(1)

                except Exception:
                    current_id += chunk_size
                    await asyncio.sleep(1)

            await save_database_to_file()
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
            "• `/rescan` - Reset DB & fresh scan channels\n\n"
            "📊 **System:**\n"
            "• `/stats` - View total indexed anime & episode count"
        )
        await message.reply_text(start_text, quote=True)

    @pyro_client.on_message(filters.command("setcontext"))
    async def set_context_cmd(client: Client, message: Message):
        global active_context
        args = message.text.split(maxsplit=1)
        if len(args) < 2 or "|" not in args[1]:
            return await message.reply_text("❌ Usage: `/setcontext Anime Name | Season | Audio`", quote=True)

        parts = [p.strip() for p in args[1].split("|")]
        anime_name = parts[0]
        season_num = parts[1] if len(parts) > 1 else "1"
        dub_type = parts[2].lower() if len(parts) > 2 else "official"

        active_context = {"anime": anime_name, "season": season_num, "type": dub_type, "auto_ep": 1}
        await message.reply_text(f"🎯 **Bulk Context Active!**\n• **Anime:** `{anime_name}`\n• **Season:** `{season_num}`\n• **Audio:** `{dub_type.upper()}`", quote=True)

    @pyro_client.on_message(filters.command("clearcontext"))
    async def clear_context_cmd(client: Client, message: Message):
        global active_context
        active_context = {"anime": None, "season": None, "type": None, "auto_ep": 1}
        await message.reply_text("🧹 **Bulk Context Cleared!**", quote=True)

    @pyro_client.on_message(filters.command("stats"))
    async def stats_cmd(client: Client, message: Message):
        total_anime = len(anime_database)
        total_eps = sum(len(ep_list) for anime in anime_database.values() for ep_list in anime.get("seasons", {}).values())
        ctx_status = f"`{active_context['anime']}` (S{active_context['season']})" if active_context["anime"] else "None"
        await message.reply_text(f"📊 **Total Anime:** `{total_anime}` | **Total Episodes:** `{total_eps}`\n🎯 **Active Context:** {ctx_status}\n🌐 **GitHub Sync Repo:** `{GITHUB_REPO}`", quote=True)

    @pyro_client.on_message(filters.command("rescan"))
    async def rescan_cmd(client: Client, message: Message):
        anime_database.clear()
        msg_index.clear()
        msg_lookup.clear()
        await save_database_to_file()
        await message.reply_text("🔄 **Database Reset! Rescanning channels...**", quote=True)
        asyncio.create_task(auto_scan_channels())

    # AUTO LIVE FORWARD & UPLOAD HANDLER
    @pyro_client.on_message((filters.video | filters.document) & ~filters.command(["start", "stats", "rescan", "ping", "add", "delete", "rename", "addchannel", "listchannels", "setcontext", "clearcontext"]))
    async def auto_index_media(client: Client, message: Message):
        if not is_video_message(message):
            return

        chat = message.chat
        chat_identifier = f"@{chat.username}" if chat.username else str(chat.id)
        msg_id = message.id

        combined_text = ""
        if message.reply_to_message:
            combined_text += (message.reply_to_message.text or message.reply_to_message.caption or "") + "\n"

        caption = message.caption or getattr(message.video or message.document, "file_name", "") or ""
        combined_text += caption

        fname = getattr(message.video or message.document, "file_name", "") or ""
        forward_title = message.forward_from_chat.title if message.forward_from_chat else (message.forward_sender_name or "")

        anime_name, season_num, ep_num, dub_type, video_format = await add_to_database(chat_identifier, msg_id, combined_text, forward_title, filename=fname, use_context=True, auto_save=True)
        
        reply_text = (
            f"✅ **Video Indexed Automatically!**\n\n"
            f"🎬 **Anime:** `{anime_name}`\n"
            f"🍂 **Season:** `{season_num}` | 📺 **Episode:** `{ep_num}`\n"
            f"🎙️ **Audio:** `{dub_type.upper()}`\n"
            f"🎞️ **Format:** `{video_format}`\n\n"
            f"📁 Synced to GitHub (`sitevideo_data.json`)"
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
    msg_lookup.clear()
    await save_database_to_file()
    asyncio.create_task(auto_scan_channels())
    return {"status": "Rescan initiated"}
