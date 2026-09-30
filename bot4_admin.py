import os
import re
import asyncio
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8854095839:AAH8pFz3ZszE7Gyp0AY1if7JY2NoC18bNJg")

pyro_client = None

# Default Site Data (Memory Database for index.html)
site_data: Dict[str, Any] = {
    "banner": {
        "title": "Solo Leveling",
        "image": "https://m.media-amazon.com/images/M/MV5BODlhM2RmM2ItM2FkYi00ZGY2LTg2NzAtNjg4NTgwOGVhMDFkXkEyXkFqcGdeQXVyMTI1NDEyNTM5._V1_.jpg",
        "description": "10 Years ago, after the Gate that connected the real world with the monster world opened, Sung Jinwoo became the weakest hunter.",
        "play_slug": "solo_leveling"
    },
    "cards": {
        "solo_leveling": {
            "title": "Solo Leveling",
            "image": "https://m.media-amazon.com/images/M/MV5BODlhM2RmM2ItM2FkYi00ZGY2LTg2NzAtNjg4NTgwOGVhMDFkXkEyXkFqcGdeQXVyMTI1NDEyNTM5._V1_.jpg",
            "genres": "Action, Fantasy, Supernatural",
            "rating": "9.2",
            "slug": "solo_leveling"
        }
    }
}

# ==================== LIFECYCLE & BOT COMMANDS ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pyro_client
    print("🚀 Starting Bot 4 (Admin Content Manager)...")

    pyro_client = Client(
        "bot4_admin_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    # /start Command
    @pyro_client.on_message(filters.command("start"))
    async def start_cmd(client: Client, message: Message):
        help_text = (
            "👑 **Bot 4: Website Content & Admin Manager Active!**\n\n"
            "**Telegram Commands for index.html:**\n\n"
            "🔹 `/addcard Title | Image_URL | Genres | Rating`\n"
            "└ Add new anime card to index grid\n\n"
            "🔹 `/removecard slug`\n"
            "└ Remove anime card from index page\n\n"
            "🔹 `/setbanner Title | Image_URL | Description | Play_Slug`\n"
            "└ Change Hero Banner on top of index page\n\n"
            "🔹 `/listcards` - Show list of active cards\n"
            "🔹 `/getbanner` - Show current hero banner info"
        )
        await message.reply_text(help_text, quote=True)

    # /addcard Title | Image_URL | Genres | Rating
    @pyro_client.on_message(filters.command("addcard"))
    async def add_card_cmd(client: Client, message: Message):
        raw_text = message.text.replace("/addcard", "").strip()
        if not raw_text or "|" not in raw_text:
            await message.reply_text(
                "❌ **Format Error!**\n\nUse: `/addcard Title | Image_URL | Genres | Rating`",
                quote=True
            )
            return

        parts = [p.strip() for p in raw_text.split("|")]
        if len(parts) < 4:
            await message.reply_text(
                "⚠️ **4 Parameters Required!**\nExample: `/addcard Solo Leveling | https://img.jpg | Action, Fantasy | 9.2`",
                quote=True
            )
            return

        title, img_url, genres, rating = parts[0], parts[1], parts[2], parts[3]
        slug = re.sub(r'[^a-zA-Z0-9]', '_', title.lower()).strip('_')

        site_data["cards"][slug] = {
            "title": title,
            "image": img_url,
            "genres": genres,
            "rating": rating,
            "slug": slug
        }

        await message.reply_text(
            f"✅ **Card Added to index.html Grid!**\n\n"
            f"📌 **Title:** {title}\n"
            f"🔗 **Slug:** `{slug}`\n"
            f"⭐ **Rating:** {rating}\n"
            f"🏷️ **Genres:** {genres}",
            quote=True
        )

    # /removecard [slug]
    @pyro_client.on_message(filters.command("removecard"))
    async def remove_card_cmd(client: Client, message: Message):
        slug = message.text.replace("/removecard", "").strip().lower()
        if not slug:
            await message.reply_text("❌ Usage: `/removecard solo_leveling`", quote=True)
            return

        if slug in site_data["cards"]:
            deleted = site_data["cards"].pop(slug)
            await message.reply_text(f"🗑️ Card **{deleted['title']}** (`{slug}`) removed from website!", quote=True)
        else:
            await message.reply_text(f"⚠️ Card with slug `{slug}` not found!", quote=True)

    # /setbanner Title | Image_URL | Description | Play_Slug
    @pyro_client.on_message(filters.command("setbanner"))
    async def set_banner_cmd(client: Client, message: Message):
        raw_text = message.text.replace("/setbanner", "").strip()
        if not raw_text or "|" not in raw_text:
            await message.reply_text(
                "❌ **Format Error!**\n\nUse: `/setbanner Title | Image_URL | Description | Play_Slug`",
                quote=True
            )
            return

        parts = [p.strip() for p in raw_text.split("|")]
        if len(parts) < 4:
            await message.reply_text("⚠️ Provide all 4 parameters separated by `|`", quote=True)
            return

        title, img_url, desc, play_slug = parts[0], parts[1], parts[2], parts[3]

        site_data["banner"] = {
            "title": title,
            "image": img_url,
            "description": desc,
            "play_slug": play_slug
        }

        await message.reply_text(
            f"🎨 **Hero Banner Updated!**\n\n"
            f"🎬 **Title:** {title}\n"
            f"📝 **Description:** {desc[:80]}...\n"
            f"▶️ **Target Slug:** `{play_slug}`",
            quote=True
        )

    # /listcards
    @pyro_client.on_message(filters.command("listcards"))
    async def list_cards_cmd(client: Client, message: Message):
        if not site_data["cards"]:
            await message.reply_text("📭 No cards currently listed.", quote=True)
            return

        msg = "📜 **Current Website Anime Cards:\n\n"
        for slug, card in site_data["cards"].items():
            msg += f"• ** | Slug: `{slug}` | ⭐ {card['rating']}\n"

        await message.reply_text(msg, quote=True)

    # /getbanner
    @pyro_client.on_message(filters.command("getbanner"))
    async def get_banner_cmd(client: Client, message: Message):
        b = site_data["banner"]
        await message.reply_text(
            f"🖼️ **Active Hero Banner:**\n\n"
            f"📌 **Title:** {b['title']}\n"
            f"🖼️ **Image:** {b['image']}\n"
            f"📝 **Description:** {b['description']}\n"
            f"🔗 **Play Slug:** `{b['play_slug']}`",
            quote=True
        )

    await pyro_client.start()
    print("✅ Bot 4 Active & Ready!")
    yield
    await pyro_client.stop()

app = FastAPI(title="Bot 4 - Admin Content Manager API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API ENDPOINTS FOR FRONTEND ====================
@app.get("/")
def home():
    return {"status": "Bot 4 Admin API Active 🚀"}

@app.get("/api/site-data")
def get_site_data():
    """Returns Hero Banner & Anime Cards for index.html rendering"""
    return {
        "banner": site_data["banner"],
        "cards": list(site_data["cards"].values())
    }

@app.get("/api/banner")
def get_banner():
    return site_data["banner"]

@app.get("/api/cards")
def get_cards():
    return list(site_data["cards"].values())
