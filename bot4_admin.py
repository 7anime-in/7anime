import os
import re
import json
import base64
import asyncio
import urllib.request
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT4_TOKEN") or os.getenv("BOT_TOKEN")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
DATA_FILE_PATH = "site_data.json"

DEFAULT_SITE_DATA = {
    "banner": {
        "title": "Solo Leveling",
        "image": "https://m.media-amazon.com/images/M/MV5BODlhM2RmM2ItM2FkYi00ZGY2LTg2NzAtNjg4NTgwOGVhMDFkXkEyXkFqcGdeQXVyMTI1NDEyNTM5._V1_.jpg",
        "description": "10 Years ago, after the Gate connected the real world with the monster world, Sung Jinwoo became the weakest hunter.",
        "play_slug": "solo_leveling"
    },
    "cards": {
        "solo_leveling": {
            "title": "Solo Leveling",
            "image": "https://m.media-amazon.com/images/M/MV5BODlhM2RmM2ItM2FkYi00ZGY2LTg2NzAtNjg4NTgwOGVhMDFkXkEyXkFqcGdeQXVyMTI1NDEyNTM5._V1_.jpg",
            "genres": "Action, Fantasy",
            "rating": "9.2",
            "slug": "solo_leveling"
        }
    }
}

site_data: Dict[str, Any] = DEFAULT_SITE_DATA.copy()

# ==================== PYROGRAM CLIENT SETUP ====================
pyro_client = Client(
    "bot4_admin_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ==================== GITHUB AUTO-COMMIT LOGIC ====================
def fetch_from_github():
    global site_data
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("⚠️ GITHUB_TOKEN or GITHUB_REPO not set.", flush=True)
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Bot4-Admin"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            content = base64.b64decode(data["content"]).decode("utf-8")
            site_data = json.loads(content)
            print("✅ Sync site_data.json from GitHub successful!", flush=True)
    except Exception as e:
        print(f"⚠️ Could not fetch site_data.json from GitHub: {e}", flush=True)

def save_to_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Bot4-Admin"
    }

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as res:
            sha = json.loads(res.read().decode("utf-8")).get("sha")
    except Exception:
        pass

    content_str = json.dumps(site_data, indent=4)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "🤖 Auto-update site_data.json via Bot 4",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(req) as res:
            print("🚀 site_data.json saved to GitHub Repo!", flush=True)
    except Exception as e:
        print(f"❌ Error committing to GitHub: {e}", flush=True)

# ==================== TELEGRAM COMMAND HANDLERS ====================
@pyro_client.on_message(filters.private)
async def debug_all_private_messages(client: Client, message: Message):
    print(f"📩 Incoming Message in Private: {message.text}", flush=True)

    if message.text and message.text.startswith("/start"):
        help_text = (
            "👑 **Bot 4: Website Content Manager Active!**\n\n"
            "🔹 `/addcard Title | Image_URL | Genres | Rating`\n"
            "🔹 `/removecard slug`\n"
            "🔹 `/setbanner Title | Image_URL | Description | Play_Slug`\n"
            "🔹 `/listcards` - Active cards list\n"
            "🔹 `/getbanner` - Current banner info"
        )
        await message.reply_text(help_text, quote=True)

    elif message.text and message.text.startswith("/addcard"):
        raw_text = message.text.replace("/addcard", "").strip()
        parts = [p.strip() for p in raw_text.split("|")]
        if len(parts) < 4:
            await message.reply_text("⚠️ Usage: `/addcard Title | Image_URL | Genres | Rating`", quote=True)
            return

        title, img_url, genres, rating = parts[0], parts[1], parts[2], parts[3]
        slug = re.sub(r'[^a-zA-Z0-9]', '_', title.lower()).strip('_')

        if "cards" not in site_data or not isinstance(site_data["cards"], dict):
            site_data["cards"] = {}

        site_data["cards"][slug] = {
            "title": title,
            "image": img_url,
            "genres": genres,
            "rating": rating,
            "slug": slug
        }
        asyncio.create_task(asyncio.to_thread(save_to_github))
        await message.reply_text(f"✅ **Card Added & Saved to GitHub!**\n📌 **Title:** {title}\n🔗 **Slug:** `{slug}`", quote=True)

    elif message.text and message.text.startswith("/removecard"):
        slug = message.text.replace("/removecard", "").strip().lower()
        cards = site_data.get("cards", {})
        if slug in cards:
            deleted = cards.pop(slug)
            asyncio.create_task(asyncio.to_thread(save_to_github))
            await message.reply_text(f"🗑️ Card **{deleted['title']}** removed!", quote=True)
        else:
            await message.reply_text(f"⚠️ Slug `{slug}` not found!", quote=True)

    elif message.text and message.text.startswith("/setbanner"):
        raw_text = message.text.replace("/setbanner", "").strip()
        parts = [p.strip() for p in raw_text.split("|")]
        if len(parts) < 4:
            await message.reply_text("⚠️ Usage: `/setbanner Title | Image_URL | Description | Play_Slug`", quote=True)
            return

        site_data["banner"] = {
            "title": parts[0],
            "image": parts[1],
            "description": parts[2],
            "play_slug": parts[3]
        }
        asyncio.create_task(asyncio.to_thread(save_to_github))
        await message.reply_text("🎨 **Hero Banner Updated & Saved to GitHub!**", quote=True)

    elif message.text and message.text.startswith("/listcards"):
        cards = site_data.get("cards", {})
        if not cards:
            await message.reply_text("📭 No cards listed.", quote=True)
            return
        msg = "📜 **Current Anime Cards:\n\n"
        for slug, card in cards.items():
            msg += f"• ** | Slug: `{slug}`\n"
        await message.reply_text(msg, quote=True)

    elif message.text and message.text.startswith("/getbanner"):
        b = site_data.get("banner", {})
        if not b:
            await message.reply_text("📭 No banner set.", quote=True)
            return
        await message.reply_text(f"🖼️ **Hero Banner:** {b.get('title')}\n🔗 **Play Slug:** `{b.get('play_slug')}`", quote=True)

# ==================== LIFECYCLE ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Bot 4 (Admin Content Manager)...", flush=True)
    fetch_from_github()
    await pyro_client.start()
    print("✅ Bot 4 Active & Listening!", flush=True)
    yield
    if pyro_client and pyro_client.is_connected:
        await pyro_client.stop()

app = FastAPI(title="Bot 4 - Admin Content Manager API", lifespan=lifespan)

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
    return {"status": "Bot 4 Admin API Active 🚀"}

@app.get("/api/site-data")
def get_site_data():
    return {
        "banner": site_data.get("banner", DEFAULT_SITE_DATA["banner"]),
        "cards": list(site_data.get("cards", {}).values())
    }
    
