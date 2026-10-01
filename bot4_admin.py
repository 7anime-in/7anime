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

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")

BOT_TOKEN = "8854095839:AAFKUKA8Bd8Hk-3_DzRKLdKdEvLR4awz5Fw"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()
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
            "type": "series",
            "slug": "solo_leveling"
        }
    }
}

site_data: Dict[str, Any] = DEFAULT_SITE_DATA.copy()
pyro_client: Client = None

# ==================== GITHUB AUTO-COMMIT LOGIC ====================
def fetch_from_github():
    global site_data
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("⚠️ GITHUB_TOKEN or GITHUB_REPO not set. Using default site_data.", flush=True)
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
            print("✅ site_data.json fetched successfully from GitHub!", flush=True)
    except Exception as e:
        print(f"⚠️ GitHub fetch warning: {e}. Using default site_data.", flush=True)

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

# ==================== LIFECYCLE & COMMAND HANDLERS ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pyro_client
    print("🚀 Starting Bot 4 (Admin Content Manager)...", flush=True)

    fetch_from_github()

    pyro_client = Client(
        "bot4_admin_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )

    # Detailed /start & /help Command Guide
    @pyro_client.on_message(filters.command(["start", "help"]))
    async def start_cmd(client: Client, message: Message):
        help_text = (
            "👑 **Bot 4: Website Content Manager - Full Command Guide** 🚀\n\n"
            "Is bot ka use karke tum website (`site_data.json`) ke cards aur banner ko Telegram se hi manage kar sakte ho.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **CARD MANAGEMENT COMMANDS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ **/addcard** - Naya Anime Card Add Karein\n"
            "• **Syntax:** `/addcard Title | Image_URL | Genres | Rating | [Type]`\n"
            "• **Type Options:** `series`, `movie`, `hentai` (Default: `series`)\n"
            "• **Examples:**\n"
            "  - *Series:* `/addcard Solo Leveling | https://link.com/img.jpg | Action, Fantasy | 9.2 | series`\n"
            "  - *Movie:* `/addcard Your Name | https://link.com/img.jpg | Romance, Drama | 9.0 | movie`\n"
            "  - *Hentai (18+):* `/addcard Overflow | https://link.com/img.jpg | Romance | 8.5 | hentai`\n\n"

            "2️⃣ **/editcard** - Pehle Se Bane Card Ko Update Karein\n"
            "• **Syntax:** `/editcard Slug | Title | Image_URL | Genres | Rating | [Type]`\n"
            "• **Example:**\n"
            "  `/editcard solo_leveling | Solo Leveling Season 2 | https://link.com/new.jpg | Action | 9.5 | series`\n\n"

            "3️⃣ **/removecard** - Kisi Card Ko Delete Karein\n"
            "• **Syntax:** `/removecard Slug`\n"
            "• **Example:** `/removecard solo_leveling`\n\n"

            "4️⃣ **/listcards** - Website Ke Sabhi Active Cards Ki List Dekhein\n"
            "• **Command:** `/listcards`\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🖼️ **HERO BANNER COMMANDS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "5️⃣ **/setbanner** ya **/editbanner** - Website Ka Main Banner Update Karein\n"
            "• **Syntax:** `/setbanner Title | Image_URL | Description | Play_Slug`\n"
            "• **Example:**\n"
            "  `/setbanner Solo Leveling | https://link.com/banner.jpg | 10 years ago gates opened... | solo_leveling`\n\n"

            "6️⃣ **/removebanner** - Current Banner Ko Hatao/Clear Karein\n"
            "• **Command:** `/removebanner`\n\n"

            "7️⃣ **/getbanner** - Current Set Banner Ki Information Dekhein\n"
            "• **Command:** `/getbanner`"
        )
        await message.reply_text(help_text, quote=True)

    # /addcard (With Category Badge Support)
    @pyro_client.on_message(filters.command("addcard"))
    async def add_card_cmd(client: Client, message: Message):
        split_text = message.text.split(maxsplit=1)
        if len(split_text) < 2:
            await message.reply_text("⚠️ Usage: `/addcard Title | Image_URL | Genres | Rating | [Type]`", quote=True)
            return

        parts = [p.strip() for p in split_text[1].split("|")]
        if len(parts) < 4:
            await message.reply_text("⚠️ Usage: `/addcard Title | Image_URL | Genres | Rating | [Type]`", quote=True)
            return

        title, img_url, genres, rating = parts[0], parts[1], parts[2], parts[3]
        card_type = parts[4].lower() if len(parts) >= 5 and parts[4].strip() else "series"

        if card_type not in ["series", "movie", "hentai"]:
            card_type = "series"

        slug = re.sub(r'[^a-z0-9_]+', '_', title.lower()).strip('_')

        if "cards" not in site_data or not isinstance(site_data["cards"], dict):
            site_data["cards"] = {}

        site_data["cards"][slug] = {
            "title": title,
            "image": img_url,
            "genres": genres,
            "rating": rating,
            "type": card_type,
            "slug": slug
        }
        asyncio.create_task(asyncio.to_thread(save_to_github))
        await message.reply_text(
            f"✅ **Card Added & Saved!**\n"
            f"📌 **Title:** {title}\n"
            f"🏷️ **Type:** `{card_type.upper()}`\n"
            f"🔗 **Slug:** `{slug}`", 
            quote=True
        )

    # /editcard
    @pyro_client.on_message(filters.command("editcard"))
    async def edit_card_cmd(client: Client, message: Message):
        split_text = message.text.split(maxsplit=1)
        if len(split_text) < 2:
            await message.reply_text("⚠️ Usage: `/editcard Slug | Title | Image_URL | Genres | Rating | [Type]`", quote=True)
            return

        parts = [p.strip() for p in split_text[1].split("|")]
        if len(parts) < 5:
            await message.reply_text("⚠️ Usage: `/editcard Slug | Title | Image_URL | Genres | Rating | [Type]`", quote=True)
            return

        target_slug = parts[0].lower().strip()
        cards = site_data.get("cards", {})

        if target_slug not in cards:
            await message.reply_text(f"❌ Card with slug `{target_slug}` not found!", quote=True)
            return

        title, img_url, genres, rating = parts[1], parts[2], parts[3], parts[4]
        card_type = parts[5].lower() if len(parts) >= 6 and parts[5].strip() else cards[target_slug].get("type", "series")

        if card_type not in ["series", "movie", "hentai"]:
            card_type = "series"

        cards[target_slug].update({
            "title": title,
            "image": img_url,
            "genres": genres,
            "rating": rating,
            "type": card_type
        })

        asyncio.create_task(asyncio.to_thread(save_to_github))
        await message.reply_text(f"✏️ **Card Updated & Saved!**\n📌 **Slug:** `{target_slug}`\n🏷️ **Type:** `{card_type.upper()}`", quote=True)

    # /removecard
    @pyro_client.on_message(filters.command("removecard"))
    async def remove_card_cmd(client: Client, message: Message):
        split_text = message.text.split(maxsplit=1)
        if len(split_text) < 2:
            await message.reply_text("⚠️ Usage: `/removecard slug`", quote=True)
            return

        raw_slug = split_text[1].strip().lower()
        slug = re.sub(r'[^a-z0-9_]+', '_', raw_slug).strip('_')

        cards = site_data.get("cards", {})
        if isinstance(cards, dict) and slug in cards:
            deleted = cards.pop(slug)
            asyncio.create_task(asyncio.to_thread(save_to_github))
            await message.reply_text(f"🗑️ Card **{deleted['title']}** removed!", quote=True)
        else:
            await message.reply_text(f"⚠️ Slug `{slug}` not found!", quote=True)

    # /setbanner & /editbanner
    @pyro_client.on_message(filters.command(["setbanner", "editbanner"]))
    async def set_banner_cmd(client: Client, message: Message):
        split_text = message.text.split(maxsplit=1)
        if len(split_text) < 2:
            await message.reply_text("⚠️ Usage: `/setbanner Title | Image_URL | Description | Play_Slug`", quote=True)
            return

        parts = [p.strip() for p in split_text[1].split("|")]
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
        await message.reply_text(f"🎨 **Hero Banner Updated & Saved!**\n📌 **Title:** {parts[0]}", quote=True)

    # /removebanner
    @pyro_client.on_message(filters.command("removebanner"))
    async def remove_banner_cmd(client: Client, message: Message):
        site_data["banner"] = {}
        asyncio.create_task(asyncio.to_thread(save_to_github))
        await message.reply_text("🗑️ **Hero Banner Removed & Saved!**", quote=True)

    # /listcards
    @pyro_client.on_message(filters.command("listcards"))
    async def list_cards_cmd(client: Client, message: Message):
        cards = site_data.get("cards", {})
        if not isinstance(cards, dict) or not cards:
            await message.reply_text("📭 No cards listed.", quote=True)
            return
        msg = "📜 **Current Anime Cards:**\n\n"
        for slug, card in cards.items():
            card_type = card.get('type', 'series').upper()
            msg += f"• **{card.get('title', 'N/A')}** `[{card_type}]` | Slug: `{slug}`\n"
        await message.reply_text(msg, quote=True)

    # /getbanner
    @pyro_client.on_message(filters.command("getbanner"))
    async def get_banner_cmd(client: Client, message: Message):
        b = site_data.get("banner", {})
        if not isinstance(b, dict) or not b:
            await message.reply_text("📭 No active banner set.", quote=True)
            return
        await message.reply_text(f"🖼️ **Hero Banner:** {b.get('title')}\n🔗 **Play Slug:** `{b.get('play_slug')}`", quote=True)

    # Non-blocking startup
    asyncio.create_task(pyro_client.start())
    print("✅ Bot 4 Connected & Listening!", flush=True)

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
    raw_cards = site_data.get("cards", {})
    cards_list = list(raw_cards.values()) if isinstance(raw_cards, dict) else []
    
    raw_banner = site_data.get("banner", {})
    banner_data = raw_banner if isinstance(raw_banner, dict) else DEFAULT_SITE_DATA["banner"]

    return {
        "banner": banner_data,
        "cards": cards_list
    }
    
