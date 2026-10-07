import os
import re
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client
from pyrogram.errors import FloodWait

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT2_TOKEN") or os.getenv("BOT_TOKEN", "8946650986:AAGy6rYE-C42f7jcgeyS8Xl4-j9UAyIEwEk")

pyro_client: Optional[Client] = None

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

# ==================== LIFECYCLE HANDLER ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pyro_client
    print("🚀 Starting Bot 2 Direct Telegram 302 Redirect Streaming Engine...")

    pyro_client = Client(
        "bot2_streamer_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
    )

    await pyro_client.start()
    print("✅ Bot 2 Pyrogram Engine Active & Ready!")
    yield
    if pyro_client and pyro_client.is_connected:
        await pyro_client.stop()
        print("🛑 Bot 2 Engine Stopped Cleanly.")

app = FastAPI(title="Bot 2 - Streamer Engine (302 Redirect)", lifespan=lifespan)

# Enable Full CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Content-Length", "Accept-Ranges", "Content-Type", "Content-Disposition"],
)

# ==================== ENDPOINTS ====================
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Bot 2 Direct 302 Streamer Engine Active 🚀", "service": "7anime Engine"}

@app.get("/health")
def health_check():
    return {"status": "ok", "connected": pyro_client.is_connected if pyro_client else False}

@app.api_route("/stream/{chat_id}/{message_id}", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/stream/{chat_id}/{message_id}.mp4", methods=["GET", "HEAD", "OPTIONS"])
async def stream_video(chat_id: str, message_id: str, request: Request):
    if request.method == "OPTIONS":
        return Response(
            status_code=200, 
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )

    clean_msg_str = re.sub(r"\.\w+$", "", str(message_id))
    try:
        msg_id_clean = int(clean_msg_str)
    except ValueError:
        return Response(content=b"Invalid Message ID", media_type="text/plain", status_code=400)

    if not pyro_client or not pyro_client.is_connected:
        return Response(content=b"Streamer Engine Initializing...", media_type="text/plain", status_code=503)

    try:
        cid_str = str(chat_id).strip()
        if cid_str.lstrip('-').isdigit():
            target_id = int(cid_str)
        else:
            target_id = cid_str if cid_str.startswith("@") else f"@{cid_str}"

        msg = await pyro_client.get_messages(target_id, msg_id_clean)
    except FloodWait as e:
        return Response(
            content=b"Rate limited by Telegram", 
            status_code=429, 
            headers={"Retry-Address": str(e.value)}
        )
    except Exception as e:
        print(f"Error fetching message: {e}")
        return Response(content=b"Video Message Not Found", media_type="text/plain", status_code=404)

    if not is_video_message(msg):
        return Response(content=b"Target message is not a valid video file", media_type="text/plain", status_code=400)

    media = msg.video or msg.document

    try:
        file_info = await pyro_client.get_file(media.file_id)
        if file_info and file_info.file_path:
            telegram_cdn_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            return RedirectResponse(url=telegram_cdn_url, status_code=302)
        else:
            return Response(content=b"Failed to fetch Telegram file path", media_type="text/plain", status_code=500)
            
    except Exception as e:
        print(f"Redirect error: {e}")
        return Response(content=f"Stream Redirect Error: {str(e)}".encode(), media_type="text/plain", status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("bot2_streamer:app", host="0.0.0.0", port=port, reload=False)
    
