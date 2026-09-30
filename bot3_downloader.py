import os
import re
import asyncio
import urllib.parse
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client
from pyrogram.errors import RPCError, FloodWait

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8646261177:AAGmVPIzmduiLhZ5AJbiJGMb0kh4vbn7n6E")

# Download chunk size (2MB per chunk for high-speed file transfer)
DOWNLOAD_CHUNK_SIZE = 2 * 1024 * 1024

pyro_client = None

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

def extract_filename(message, default_id: int) -> str:
    filename = None
    if message.video and message.video.file_name:
        filename = message.video.file_name
    elif message.document and message.document.file_name:
        filename = message.document.file_name

    if not filename:
        caption = message.caption or ""
        first_line = caption.split("\n")[0] if caption else ""
        if first_line:
            clean_name = re.sub(r'[^\w\s\.-]', '', first_line).strip()
            if clean_name:
                filename = f"{clean_name}.mp4"

    if not filename:
        filename = f"7anime_Episode_{default_id}.mp4"

    # Sanitize filename for headers
    filename = re.sub(r'[\r\n]', '', filename)
    return filename

# ==================== LIFECYCLE HANDLER ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pyro_client
    print("🚀 Starting Bot 3 (Direct Downloader Engine)...")

    pyro_client = Client(
        "bot3_downloader_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    await pyro_client.start()
    print("✅ Bot 3 Pyrogram Engine Active!")
    yield
    await pyro_client.stop()

app = FastAPI(title="Bot 3 - Downloader Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type"],
)

# ==================== DOWNLOAD CORE ENGINE ====================
@app.api_route("/download/{chat_id}/{message_id}", methods=["GET", "HEAD", "OPTIONS"])
async def download_file(chat_id: str, message_id: str, request: Request):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*"})

    msg_id_clean = int(str(message_id).replace(".mp4", "").replace(".mkv", ""))

    if not pyro_client:
        raise HTTPException(status_code=503, detail="Downloader client unavailable")

    try:
        target_id = int(chat_id) if (chat_id.startswith("-") or chat_id.isdigit()) else (chat_id if chat_id.startswith("@") else f"@{chat_id}")
        msg = await pyro_client.get_messages(target_id, msg_id_clean)
    except Exception as e:
        raise HTTPException(status_code=404, detail="File message not found")

    if not is_video_message(msg):
        raise HTTPException(status_code=400, detail="Invalid media message")

    media = msg.video or msg.document
    file_size = media.file_size
    file_name = extract_filename(msg, msg_id_clean)

    # Safe URL Encoding for Filenames containing Special/Hindi Characters
    encoded_filename = urllib.parse.quote(file_name)

    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": f"attachment; filename=\"{file_name}\"; filename*=UTF-8''{encoded_filename}",
        "Content-Length": str(file_size),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Disposition, Content-Length, Content-Type",
        "Cache-Control": "no-cache",
    }

    if request.method == "HEAD":
        return Response(status_code=200, headers=headers)

    # Pyrogram Stream Generator
    async def file_downloader():
        try:
            async for chunk in pyro_client.stream_media(msg):
                yield chunk
        except (asyncio.CancelledError, Exception):
            pass

    return StreamingResponse(file_downloader(), status_code=200, headers=headers)

# ==================== ENDPOINTS ====================
@app.get("/")
def home():
    return {"status": "Bot 3 Downloader Engine Active 🚀"}
