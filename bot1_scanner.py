import os
import re
import asyncio
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))[span_4](start_span)[span_4](end_span)
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")[span_5](start_span)[span_5](end_span)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8517895964:AAHQlTU8BBM2HBRCatn5qh45jW-KeP67q3o")

# Bot 2 aur Bot 3 ke Render Web Service URLs (Inhe Render env variables me update kar sakte ho)
BOT2_STREAM_BASE = os.getenv("BOT2_STREAM_BASE", "https://7anime-bot2-streamer.onrender.com")
BOT3_DOWNLOAD_BASE = os.getenv("BOT3_DOWNLOAD_BASE", "https://7anime-bot3-downloader.onrender.com")

CHANNEL_INPUT = os.getenv("CHANNEL_ID", "-1004315586873,-1004409520918,sevenanime_ch1")[span_6](start_span)[span_6](end_span)
CHANNEL_IDS = [ch.strip() for ch in CHANNEL_INPUT.split(",") if ch.strip()][span_7](start_span)[span_7](end_span)

pyro_client = None
anime_database: Dict[str, Any] = {}

# ==================== HELPER FUNCTIONS ====================
def is_video_message(message) -> bool:[span_8](start_span)[span_8](end_span)
    if not message or message.empty:[span_9](start_span)[span_9](end_span)
        return False[span_10](start_span)[span_10](end_span)
    if message.video:[span_11](start_span)[span_11](end_span)
        return True[span_12](start_span)[span_12](end_span)
    if message.document:[span_13](start_span)[span_13](end_span)
        mime = (message.document.mime_type or "").lower()[span_14](start_span)[span_14](end_span)
        fname = (message.document.file_name or "").lower()[span_15](start_span)[span_15](end_span)
        if mime.startswith("video/") or fname.endswith((".mp4", ".mkv", ".webm", ".avi", ".mov")):[span_16](start_span)[span_16](end_span)
            return True[span_17](start_span)[span_17](end_span)
    return False[span_18](start_span)[span_18](end_span)

def parse_anime_info(caption: str, forward_title: str = ""):[span_19](start_span)[span_19](end_span)
    text = caption or "[span_20](start_span)"[span_20](end_span)

    dub_type = "official[span_21](start_span)"[span_21](end_span)
    if re.search(r"\b(unofficial|fandub|fan_dub|fan-dub|fan dub)\b", text, re.IGNORECASE) or "#unofficial" in text.lower() or "#fandub" in text.lower():[span_22](start_span)[span_22](end_span)
        dub_type = "unofficial[span_23](start_span)"[span_23](end_span)
    elif "#official" in text.lower():[span_24](start_span)[span_24](end_span)
        dub_type = "official[span_25](start_span)"[span_25](end_span)

    season_match = re.search(r"(?:Season|S)[\s\-\_]*0*(\d+)", text, re.IGNORECASE)[span_26](start_span)[span_26](end_span)
    season = season_match.group(1) if season_match else "1[span_27](start_span)"[span_27](end_span)

    ep_match = re.search(r"(?:Episode|Ep|E)[\s\-\_]*0*(\d+)", text, re.IGNORECASE)[span_28](start_span)[span_28](end_span)
    if not ep_match:[span_29](start_span)[span_29](end_span)
        clean_text = re.sub(r"\b(1080p|720p|480p|360p|2160p|x264|x265|hevc|2023|2024|2025|2026)\b", "", text, flags=re.IGNORECASE)[span_30](start_span)[span_30](end_span)
        ep_match = re.search(r"(?:[\s\-\_\[\vert{}^])0*(\d{1,3})(?:[\s\-\_\]]|$|\.mp4|\.mkv)", clean_text)[span_31](start_span)[span_31](end_span)

    episode = int(ep_match.group(1)) if ep_match else 1[span_32](start_span)[span_32](end_span)

    explicit_name = re.search(r"(?:Anime|Title|Name)\s*:\s*([^\n\r\t|]+)", text, re.IGNORECASE)[span_33](start_span)[span_33](end_span)

    if explicit_name:[span_34](start_span)[span_34](end_span)
        raw_title = explicit_name.group(1).strip()[span_35](start_span)[span_35](end_span)
    elif forward_title:[span_36](start_span)[span_36](end_span)
        raw_title = forward_title[span_37](start_span)[span_37](end_span)
    else:
        lines = [l.strip() for l in text.split("\n") if l.strip()][span_38](start_span)[span_38](end_span)
        raw_title = lines[0] if lines else "Unknown Anime[span_39](start_span)"[span_39](end_span)

    clean_title = re.sub([span_40](start_span)[span_40](end_span)
        r"(?i)\b(in|hindi|dubbed|dub|sub|official|unofficial|fandub|1080p|720p|480p|fhd|hd|hevc|x264|x265|episode|season|language|quality|main channel)\b",[span_41](start_span)[span_41](end_span)
        "",[span_42](start_span)[span_42](end_span)
        raw_title,[span_43](start_span)[span_43](end_span)
    )
    clean_title = re.sub(r"[^\w\s]", " ", clean_title)[span_44](start_span)[span_44](end_span)
    clean_title = re.sub(r"\s+", " ", clean_title).strip().title()[span_45](start_span)[span_45](end_span)

    if not clean_title or len(clean_title) < 2:[span_46](start_span)[span_46](end_span)
        clean_title = "Unknown Anime[span_47](start_span)"[span_47](end_span)

    return clean_title, str(int(season)), episode, dub_type[span_48](start_span)[span_48](end_span)

def add_to_database(chat_id: str, msg_id: int, caption: str, forward_title: str):[span_49](start_span)[span_49](end_span)
    anime_name, season_num, ep_num, dub_type = parse_anime_info(caption, forward_title)[span_50](start_span)[span_50](end_span)
    slug_key = re.sub(r'[^a-zA-Z0-9]', '_', anime_name.lower()).strip('_')[span_51](start_span)[span_51](end_span)

    if slug_key not in anime_database:[span_52](start_span)[span_52](end_span)
        anime_database[slug_key] = {"title": anime_name, "seasons": {}}[span_53](start_span)[span_53](end_span)

    anime_database[slug_key]["title"] = anime_name[span_54](start_span)[span_54](end_span)

    if season_num not in anime_database[slug_key]["seasons"]:[span_55](start_span)[span_55](end_span)
        anime_database[slug_key]["seasons"][season_num] = [][span_56](start_span)[span_56](end_span)

    ep_list = anime_database[slug_key]["seasons"][season_num][span_57](start_span)[span_57](end_span)
    existing_ep = next((item for item in ep_list if item["ep"] == ep_num and item.get("type", "official") == dub_type), None)[span_58](start_span)[span_58](end_span)

    formatted_chat = str(chat_id).replace("@", "")
    stream_url = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{formatted_chat}/{msg_id}.mp4"
    download_url = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{formatted_chat}/{msg_id}"

    if existing_ep:
        existing_ep["chat_id"] = formatted_chat[span_59](start_span)[span_59](end_span)
        existing_ep["msg_id"] = msg_id[span_60](start_span)[span_60](end_span)
        existing_ep["stream_url"] = stream_url
        existing_ep["download_url"] = download_url
    else:
        ep_list.append({
            "ep": ep_num,
            "chat_id": formatted_chat,[span_61](start_span)[span_61](end_span)
            "msg_id": msg_id,[span_62](start_span)[span_62](end_span)
            "type": dub_type,[span_63](start_span)[span_63](end_span)
            "stream_url": stream_url,
            "download_url": download_url
        })
        ep_list.sort(key=lambda x: x["ep"])[span_64](start_span)[span_64](end_span)

# ==================== CHANNEL AUTO SCANNER ====================
async def auto_scan_channels():[span_65](start_span)[span_65](end_span)
    if not CHANNEL_IDS:[span_66](start_span)[span_66](end_span)
        print("ℹ️ No CHANNEL_ID set. Skipping channel scan.")[span_67](start_span)[span_67](end_span)
        return

    print("🔍 Bot 1 Scanning Telegram Channels...")[span_68](start_span)[span_68](end_span)

    for ch_id in CHANNEL_IDS:[span_69](start_span)[span_69](end_span)
        if not ch_id:[span_70](start_span)[span_70](end_span)
            continue
        try:
            target_chat = int(ch_id) if (ch_id.startswith("-") or ch_id.isdigit()) else (ch_id if ch_id.startswith("@") else f"@{ch_id}")[span_71](start_span)[span_71](end_span)
            
            chunk_size = 100[span_72](start_span)[span_72](end_span)
            current_id = 1[span_73](start_span)[span_73](end_span)
            empty_count = 0[span_74](start_span)[span_74](end_span)
            scanned_count = 0[span_75](start_span)[span_75](end_span)

            while empty_count < 10:[span_76](start_span)[span_76](end_span)
                msg_ids = list(range(current_id, current_id + chunk_size))[span_77](start_span)[span_77](end_span)
                try:
                    messages = await pyro_client.get_messages(target_chat, msg_ids)[span_78](start_span)[span_78](end_span)
                    has_media = False

                    if messages:
                        for message in messages:[span_79](start_span)[span_79](end_span)
                            if is_video_message(message):[span_80](start_span)[span_80](end_span)
                                has_media = True
                                caption = message.caption or getattr(message.video or message.document, "file_name", "") or "[span_81](start_span)"[span_81](end_span)
                                forward_title = ([span_82](start_span)[span_82](end_span)
                                    message.forward_from_chat.title[span_83](start_span)[span_83](end_span)
                                    if message.forward_from_chat[span_84](start_span)[span_84](end_span)
                                    else (message.forward_sender_name or "")[span_85](start_span)[span_85](end_span)
                                )
                                add_to_database(str(target_chat), message.id, caption, forward_title)[span_86](start_span)[span_86](end_span)
                                scanned_count += 1[span_87](start_span)[span_87](end_span)

                    if not has_media:
                        empty_count += 1[span_88](start_span)[span_88](end_span)
                    else:
                        empty_count = 0[span_89](start_span)[span_89](end_span)

                    current_id += chunk_size[span_90](start_span)[span_90](end_span)
                    await asyncio.sleep(0.05)[span_91](start_span)[span_91](end_span)

                except FloodWait as e:[span_92](start_span)[span_92](end_span)
                    print(f"⚠️ Telegram Rate Limit: waiting {e.value}s...")[span_93](start_span)[span_93](end_span)
                    await asyncio.sleep(e.value + 1)[span_94](start_span)[span_94](end_span)
                except Exception as e:
                    current_id += chunk_size[span_95](start_span)[span_95](end_span)

            print(f"✅ Channel '{target_chat}' scanned completely! Total videos indexed: {scanned_count}")[span_96](start_span)[span_96](end_span)
        except Exception as e:
            print(f"⚠️ Error scanning channel {ch_id}: {e}")[span_97](start_span)[span_97](end_span)

# ==================== LIFECYCLE & HANDLERS ====================
@asynccontextmanager
async def lifespan(app: FastAPI):[span_98](start_span)[span_98](end_span)
    global pyro_client
    print("Starting Bot 1 (Scanner Engine)...")

    pyro_client = Client([span_99](start_span)[span_99](end_span)
        "bot1_scanner_session",
        api_id=API_ID,[span_100](start_span)[span_100](end_span)
        api_hash=API_HASH,[span_101](start_span)[span_101](end_span)
        bot_token=BOT_TOKEN,[span_102](start_span)[span_102](end_span)
    )

    @pyro_client.on_message(filters.command("start"))[span_103](start_span)[span_103](end_span)
    async def start_cmd(client, message):[span_104](start_span)[span_104](end_span)
        await message.reply_text([span_105](start_span)[span_105](end_span)
            "🤖 **Bot 1: Scanner & Master Router Bot Active!**\n\n"
            "• `/stats` - Total indexed anime count\n"
            "• `/rescan` - Rescan channels completely",
            quote=True,[span_106](start_span)[span_106](end_span)
        )

    @pyro_client.on_message(filters.command("stats"))[span_107](start_span)[span_107](end_span)
    async def stats_cmd(client, message):[span_108](start_span)[span_108](end_span)
        total_anime = len(anime_database)[span_109](start_span)[span_109](end_span)
        total_eps = sum([span_110](start_span)[span_110](end_span)
            len(ep_list)[span_111](start_span)[span_111](end_span)
            for anime in anime_database.values()[span_112](start_span)[span_112](end_span)
            for ep_list in anime.get("seasons", {}).values()[span_113](start_span)[span_113](end_span)
        )
        await message.reply_text(f"📊 **Total Anime:** `{total_anime}` | **Total Episodes:** `{total_eps}`", quote=True)[span_114](start_span)[span_114](end_span)

    @pyro_client.on_message(filters.command("rescan"))[span_115](start_span)[span_115](end_span)
    async def rescan_cmd(client, message):[span_116](start_span)[span_116](end_span)
        anime_database.clear()[span_117](start_span)[span_117](end_span)
        await message.reply_text("🔄 **Database Reset! Rescanning channels...**", quote=True)[span_118](start_span)[span_118](end_span)
        asyncio.create_task(auto_scan_channels())[span_119](start_span)[span_119](end_span)

    @pyro_client.on_message((filters.video | filters.document) & ~filters.command(["start", "stats", "rescan"]))[span_120](start_span)[span_120](end_span)
    async def auto_index_media(client, message):
        if not is_video_message(message):[span_121](start_span)[span_121](end_span)
            return

        chat = message.chat[span_122](start_span)[span_122](end_span)
        chat_identifier = f"@{chat.username}" if chat.username else str(chat.id)[span_123](start_span)[span_123](end_span)
        msg_id = message.id[span_124](start_span)[span_124](end_span)

        caption = message.caption or getattr(message.video or message.document, "file_name", "") or "[span_125](start_span)"[span_125](end_span)
        forward_title = ([span_126](start_span)[span_126](end_span)
            message.forward_from_chat.title[span_127](start_span)[span_127](end_span)
            if message.forward_from_chat[span_128](start_span)[span_128](end_span)
            else (message.forward_sender_name or "")[span_129](start_span)[span_129](end_span)
        )

        add_to_database(chat_identifier, msg_id, caption, forward_title)[span_130](start_span)[span_130](end_span)
        clean_chat = chat_identifier.replace("@", "")

        stream_url = f"{BOT2_STREAM_BASE.rstrip('/')}/stream/{clean_chat}/{msg_id}.mp4"
        download_url = f"{BOT3_DOWNLOAD_BASE.rstrip('/')}/download/{clean_chat}/{msg_id}"

        await message.reply_text(
            f"✅ **Video Indexed & Routed Successfully!**\n\n"
            f"📺 **Bot 2 Stream Link:** `{stream_url}`\n"
            f"📥 **Bot 3 Download Link:** `{download_url}`",
            quote=True
        )

    await pyro_client.start()[span_131](start_span)[span_131](end_span)
    asyncio.create_task(auto_scan_channels())[span_132](start_span)[span_132](end_span)
    yield
    await pyro_client.stop()[span_133](start_span)[span_133](end_span)

app = FastAPI(title="Bot 1 - Scanner API", lifespan=lifespan)[span_134](start_span)[span_134](end_span)

app.add_middleware([span_135](start_span)[span_135](end_span)
    CORSMiddleware,[span_136](start_span)[span_136](end_span)
    allow_origins=["*"],[span_137](start_span)[span_137](end_span)
    allow_credentials=True,[span_138](start_span)[span_138](end_span)
    allow_methods=["*"],[span_139](start_span)[span_139](end_span)
    allow_headers=["*"],[span_140](start_span)[span_140](end_span)
)

# ==================== REST API ENDPOINTS ====================
@app.get("/")
def home():
    return {"status": "Bot 1 Scanner Engine Active 🚀"}

@app.get("/api/all-anime")[span_141](start_span)[span_141](end_span)
def get_all_anime():[span_142](start_span)[span_142](end_span)
    return anime_database[span_143](start_span)[span_143](end_span)

@app.get("/api/episodes/{anime_slug}")[span_144](start_span)[span_144](end_span)
def get_anime_episodes(anime_slug: str):[span_145](start_span)[span_145](end_span)
    clean_query = re.sub(r'[^a-zA-Z0-9]', '', anime_slug.lower())[span_146](start_span)[span_146](end_span)

    if not anime_database:[span_147](start_span)[span_147](end_span)
        return {"title": anime_slug.replace("_", " ").title(), "seasons": {"1": []}}[span_148](start_span)[span_148](end_span)

    if anime_slug.lower() in anime_database:[span_149](start_span)[span_149](end_span)
        return anime_database[anime_slug.lower()][span_150](start_span)[span_150](end_span)

    for key in anime_database:[span_151](start_span)[span_151](end_span)
        clean_key = re.sub(r'[^a-zA-Z0-9]', '', key.lower())[span_152](start_span)[span_152](end_span)
        if clean_query in clean_key or clean_key in clean_query:[span_153](start_span)[span_153](end_span)
            return anime_database[key][span_154](start_span)[span_154](end_span)

    return list(anime_database.values())[0][span_155](start_span)[span_155](end_span)

@app.get("/api/rescan")
def rescan_api():
    anime_database.clear()
    asyncio.create_task(auto_scan_channels())
    return {"status": "Rescan initiated"}
