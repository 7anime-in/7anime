import os
import re
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client, filters
from pyrogram.errors import FloodWait, ChannelPrivate, ChatAdminRequired, PeerIdInvalid

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8517895964:AAEx3rrj9dGS-EdFX5X20ehXmHRafqJlSrM")

BOT2_STREAM_BASE = os.getenv("BOT2_STREAM_BASE", "https://7anime-bot2-streamer.onrender.com")
BOT3_DOWNLOAD_BASE = os.getenv("BOT3_DOWNLOAD_BASE", "https://7anime-bot3-downloader.onrender.com")

CHANNEL_INPUT = os.getenv("CHANNEL_ID", "sevenanime_ch1")
CHANNEL_IDS = [ch.strip() for ch in CHANNEL_INPUT.split(",") if ch.strip()]

anime_database: Dict[str, Any] = {}
scanner_task: asyncio.Task = None

# Top-level Pyrogram Client Initialization
pyro_client = Client(
    "bot1_scanner_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ==================== HELPER FUNCTIONS ====================
def is_video_message(message) -> bool:
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

def parse_anime_info(caption: str, forward_title: str = ""):
    text = caption or ""

    dub_type = "official"
    if re.search(r"\b(unofficial|fandub|fan_dub|fan-dub|fan dub)\b", text, re.IGNORECASE) or "#unofficial" in text.lower() or "#fandub" in text.lower():
        dub_type = "unofficial"
    elif "#official" in text.lower():
        dub_type = "official"

    season_match = re.search(r"(?:Season|S)[\s\-\_]*0*(\d+)", text, re.IGNORECASE)
    season = season_match.group(1) if season_match else "1"

    ep_match = re.search(r"(?:Episode|Ep|E)[\s\-\_]*0*(\d+)", text, re.IGNORECASE)
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

    clean_title = re.sub(
        r"(?i)\b(in|hindi|dubbed|dub|sub|official|unofficial|fandub|1080p|720p|480p|fhd|hd|hevc|x264|x265|episode|season|language|quality|main channel)\b",
        "",
        raw_title,
    )
    clean_title = re.sub(r"[^\w\s]", " ", clean_title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip().title()

    if not clean_title or len(clean_title) < 2:
        clean_title = "Unknown Anime"

    return clean_title, str(int(season)), episode, dub_type

def add_to_database(chat_id: str, msg_id: int, caption: str, forward_title: str):
    anime_name, season_num, ep_num, dub_type = parse_anime_info(caption, forward_title)
    slug_key = re.sub(r'[^a-zA-Z0-9]', '_', anime_name.lower()).strip('_')

    if slug_key not in anime_database:
        anime_database[slug_key] = {"title": anime_name, "seasons": {}}

    anime_database[slug_key]["title"] = anime_name

    if season_num not in anime_database[slug_key]["seasons"]:
        anime_database[slug_key]["seasons"][season_num] = []

    ep_list = anime_database[slug_key]["seasons"][season_num]
    existing_ep = next((item for item in ep_list if item["ep"] == ep_num and item.get("type", "official") == dub_type), None)

    formatted_chat = str(chat_id).replace("@", "")
    stream_url = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{formatted_chat}/{msg_id}.mp4"
    download_url = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{formatted_chat}/{msg_id}"

    if existing_ep:
        existing_ep["chat_id"] = formatted_chat
        existing_ep["msg_id"] = msg_id
        existing_ep["stream_url"] = stream_url
        existing_ep["download_url"] = download_url
    else:
        ep_list.append({
            "ep": ep_num,
            "chat_id": formatted_chat,
            "msg_id": msg_id,
            "type": dub_type,
            "stream_url": stream_url,
            "download_url": download_url
        })
        ep_list.sort(key=lambda x: x["ep"])

# ==================== CHANNEL AUTO SCANNER ====================
async def auto_scan_channels():
    if not CHANNEL_IDS:
        print("ℹ No CHANNEL_ID set. Skipping channel scan.")
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
            scanned_count = 0

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
                                add_to_database(str(target_chat), message.id, caption, forward_title)
                                scanned_count += 1

                    if not has_media:
                        empty_count += 1
                    else:
                        empty_count = 0

                    current_id += chunk_size
                    await asyncio.sleep(0.05)

                except FloodWait as e:
                    print(f"⚠️ Telegram Rate Limit: waiting {e.value}s...")
                    await asyncio.sleep(e.value + 1)
                except (ChannelPrivate, ChatAdminRequired, PeerIdInvalid) as e:
                    print(f"❌ Channel Access Error [{ch_id}]: {e}")
                    break
                except Exception:
                    current_id += chunk_size

            print(f"✅ Channel '{target_chat}' scanned completely! Total videos indexed: {scanned_count}")
        except Exception as e:
            print(f"⚠️ Error scanning channel {ch_id}: {e}")

async def channel_scanner_loop():
    while True:
        await auto_scan_channels()
        await asyncio.sleep(600)

# ==================== TELEGRAM HANDLERS ====================
@pyro_client.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        "🤖 **Bot 1: Scanner & Master Router Bot Active!**\n\n"
        "• `/stats` - Total indexed anime count\n"
        "• `/rescan` - Rescan channels completely",
        quote=True,
    )

@pyro_client.on_message(filters.command("stats"))
async def stats_cmd(client, message):
    total_anime = len(anime_database)
    total_eps = sum(
        len(ep_list)
        for anime in anime_database.values()
        for ep_list in anime.get("seasons", {}).values()
    )
    await message.reply_text(f"📊 **Total Anime:** `{total_anime}` | **Total Episodes:** `{total_eps}`", quote=True)

@pyro_client.on_message(filters.command("rescan"))
async def rescan_cmd(client, message):
    anime_database.clear()
    await message.reply_text("🔄 **Database Reset! Rescanning channels...**", quote=True)
    asyncio.create_task(auto_scan_channels())

@pyro_client.on_message((filters.video | filters.document) & ~filters.command(["start", "stats", "rescan"]))
async def auto_index_media(client, message):
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

    add_to_database(chat_identifier, msg_id, caption, forward_title)
    clean_chat = chat_identifier.replace("@", "")

    stream_url = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{clean_chat}/{msg_id}.mp4"
    download_url = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{clean_chat}/{msg_id}"

    await message.reply_text(
        f"✅ **Video Indexed & Routed Successfully!**\n\n"
        f"📺 **Bot 2 Stream Link:** `{stream_url}`\n"
        f"📥 **Bot 3 Download Link:** `{download_url}`",
        quote=True
    )

# ==================== LIFECYCLE ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scanner_task
    print("🚀 Starting Pyrogram Client...")
    pyro_started = False
    try:
        await pyro_client.start()
        pyro_started = True
        print("✅ Telegram Client Started Successfully!")
        scanner_task = asyncio.create_task(channel_scanner_loop())
    except Exception as e:
        print(f"❌ Pyrogram Start Error: {e}")
        print("⚠️ FastAPI will continue running to keep Render port active.")

    yield

    print("🛑 Shutting down Bot 1...")
    if scanner_task:
        scanner_task.cancel()
    if pyro_started and pyro_client.is_connected:
        await pyro_client.stop()

app = FastAPI(title="Bot 1 - Scanner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== REST API ENDPOINTS ====================
@app.get("/")
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
    return list(anime_database.values())[0] if anime_database else {"title": default_title, "seasons": {"1": []}}

@app.get("/api/rescan")
async def rescan_api():
    anime_database.clear()
    asyncio.create_task(auto_scan_channels())
    return {"status": "Rescan initiated"}
    
