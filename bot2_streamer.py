import os
import re
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8946650986:AAGy6rYE-C42f7jcgeyS8Xl4-j9UAyIEwEk")

# ==================== CHUNK CONFIGURATION ====================
# Minimum Chunk Size set to 200 KB for fast loading on low networks
MIN_STREAM_CHUNK_SIZE = 200 * 1024        # 200 KB Minimum
MAX_STREAM_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB Maximum
DEFAULT_CHUNK_SIZE = 2 * 1024 * 1024      # 2 MB Standard Chunk

pyro_client = None

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
    print("🚀 Starting Bot 2 (Video Streaming Engine)...")

    pyro_client = Client(
        "bot2_streamer_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    await pyro_client.start()
    print("✅ Bot 2 Pyrogram Engine Active!")
    yield
    await pyro_client.stop()

app = FastAPI(title="Bot 2 - Streamer Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Content-Length", "Accept-Ranges", "Content-Type", "Content-Disposition"],
)

# ==================== STREAMING CORE ENGINE ====================
async def get_stream_response(
    chat_id: str,
    message_id: str,
    request: Request,
    range_header: str
):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*"})

    msg_id_clean = int(str(message_id).replace(".mp4", "").replace(".mkv", ""))

    if not pyro_client:
        return Response(content=b"", media_type="video/mp4", status_code=503)

    try:
        target_id = int(chat_id) if (chat_id.startswith("-") or chat_id.isdigit()) else (chat_id if chat_id.startswith("@") else f"@{chat_id}")
        msg = await pyro_client.get_messages(target_id, msg_id_clean)
    except Exception as e:
        return Response(content=b"", media_type="video/mp4", status_code=404)

    if not is_video_message(msg):
        return Response(content=b"", media_type="video/mp4", status_code=400)

    media = msg.video or msg.document
    file_size = media.file_size

    from_bytes = 0
    until_bytes = file_size - 1

    # Range Header Parsing
    if range_header:
        range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = range_match.group(1)
            end = range_match.group(2)
            from_bytes = int(start) if start else 0
            if end:
                until_bytes = int(end)
            else:
                until_bytes = from_bytes + DEFAULT_CHUNK_SIZE - 1
    else:
        until_bytes = from_bytes + DEFAULT_CHUNK_SIZE - 1

    # Enforce Minimum 200 KB and Maximum 10 MB per chunk response
    requested_length = until_bytes - from_bytes + 1

    if requested_length > MAX_STREAM_CHUNK_SIZE:
        until_bytes = from_bytes + MAX_STREAM_CHUNK_SIZE - 1
    elif requested_length < MIN_STREAM_CHUNK_SIZE and (file_size - from_bytes) >= MIN_STREAM_CHUNK_SIZE:
        until_bytes = from_bytes + MIN_STREAM_CHUNK_SIZE - 1

    until_bytes = min(until_bytes, file_size - 1)
    chunk_length = (until_bytes - from_bytes) + 1

    headers = {
        "Content-Type": "video/mp4",
        "Content-Disposition": f"inline; filename=\"{msg_id_clean}.mp4\"",
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
        "Content-Length": str(chunk_length),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges, Content-Type, Content-Disposition",
        "Cache-Control": "no-cache",
    }

    if request.method == "HEAD":
        return Response(status_code=206 if range_header else 200, headers=headers)

    # Pyrogram Stream Offset Logic (Pyrogram works in 1MB internal chunks)
    PYRO_BLOCK_SIZE = 1024 * 1024
    start_chunk = from_bytes // PYRO_BLOCK_SIZE
    end_chunk = until_bytes // PYRO_BLOCK_SIZE
    chunks_to_fetch = (end_chunk - start_chunk) + 1
    skip_bytes = from_bytes % PYRO_BLOCK_SIZE

    async def media_streamer():
        bytes_sent = 0
        current_skipped = 0
        try:
            async for chunk in pyro_client.stream_media(
                msg, 
                offset=start_chunk, 
                limit=chunks_to_fetch
            ):
                if current_skipped < skip_bytes:
                    if current_skipped + len(chunk) <= skip_bytes:
                        current_skipped += len(chunk)
                        continue
                    else:
                        needed = skip_bytes - current_skipped
                        chunk = chunk[needed:]
                        current_skipped = skip_bytes

                remaining = chunk_length - bytes_sent
                if remaining <= 0:
                    break

                if len(chunk) >= remaining:
                    yield chunk[:remaining]
                    bytes_sent += remaining
                    break

                yield chunk
                bytes_sent += len(chunk)
        except (asyncio.CancelledError, Exception):
            pass

    return StreamingResponse(media_streamer(), status_code=206, headers=headers)

# ==================== ENDPOINTS ====================
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Bot 2 Video Streamer Engine Active 🚀"}

@app.api_route("/stream/{chat_id}/{message_id}", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/stream/{chat_id}/{message_id}.mp4", methods=["GET", "HEAD", "OPTIONS"])
async def stream_video(chat_id: str, message_id: str, request: Request, range: str = Header(None)):
    return await get_stream_response(chat_id, message_id, request, range)
      
