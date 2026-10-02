import os
import re
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Header
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

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
    print("🚀 Starting Bot 2 High-Speed Video Streaming Engine...")

    pyro_client = Client(
        "bot2_streamer_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,  # Prevents SQLite DB locks on cloud hosts like Render
        max_concurrent_transmissions=10  # Telegram Speed Boost for concurrent chunking
    )

    await pyro_client.start()
    print("✅ Bot 2 Pyrogram Engine Active & Ready!")
    yield
    if pyro_client and pyro_client.is_connected:
        await pyro_client.stop()
        print("🛑 Bot 2 Engine Stopped Cleanly.")

app = FastAPI(title="Bot 2 - Streamer Engine", lifespan=lifespan)

# Enable Full CORS for Web Player & P2P WebRTC Compatibility
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
    range_header: Optional[str] = None
):
    # Fallback to fetch Range header directly from request headers
    if not range_header:
        range_header = request.headers.get("range") or request.headers.get("Range")

    # Fast Return for Pre-flight OPTIONS Request (P2P Handshake)
    if request.method == "OPTIONS":
        return Response(
            status_code=200, 
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges, Content-Type",
            }
        )

    # Clean extension if passed in URL (.mp4, .mkv, .webm, etc.)
    clean_msg_str = re.sub(r"\.\w+$", "", str(message_id))
    try:
        msg_id_clean = int(clean_msg_str)
    except ValueError:
        return Response(content=b"Invalid Message ID", media_type="text/plain", status_code=400)

    if not pyro_client or not pyro_client.is_connected:
        return Response(content=b"Streamer Engine Initializing...", media_type="text/plain", status_code=503)

    try:
        # Channel ID Formatting Fix (-100... or @channel)
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
            headers={"Retry-After": str(e.value)}
        )
    except Exception as e:
        print(f"Error fetching message: {e}")
        return Response(content=b"Video Message Not Found", media_type="text/plain", status_code=404)

    if not is_video_message(msg):
        return Response(content=b"Target message is not a valid video file", media_type="text/plain", status_code=400)

    media = msg.video or msg.document
    file_size = media.file_size
    file_name = getattr(media, "file_name", f"{msg_id_clean}.mp4") or f"{msg_id_clean}.mp4"
    mime_type = getattr(media, "mime_type", "video/mp4") or "video/mp4"

    from_bytes = 0
    until_bytes = file_size - 1

    # Exact Range Header Handling for SwarmCloud P2P Chunking
    if range_header:
        range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = range_match.group(1)
            end = range_match.group(2)
            from_bytes = int(start) if start else 0
            if end:
                until_bytes = int(end)

    until_bytes = min(until_bytes, file_size - 1)
    chunk_length = (until_bytes - from_bytes) + 1

    headers = {
        "Content-Type": mime_type,
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
        "Content-Length": str(chunk_length),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges, Content-Type, Content-Disposition",
        "Cache-Control": "public, max-age=3600",
    }

    # HEAD Request (SwarmCloud P2P Chunk Probing)
    if request.method == "HEAD":
        return Response(status_code=206 if range_header else 200, headers=headers)

    # Pyrogram 1 MB Block Calculation
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
            # Gracefully handle player seek or tab closed events
            pass

    return StreamingResponse(
        media_streamer(), 
        status_code=206 if range_header else 200, 
        headers=headers
    )

# ==================== ENDPOINTS ====================
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Bot 2 Video Streamer Engine Active 🚀", "service": "7anime Engine"}

@app.get("/health")
def health_check():
    return {"status": "ok", "connected": pyro_client.is_connected if pyro_client else False}

@app.api_route("/stream/{chat_id}/{message_id}", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/stream/{chat_id}/{message_id}.mp4", methods=["GET", "HEAD", "OPTIONS"])
async def stream_video(chat_id: str, message_id: str, request: Request, range: str = Header(None)):
    return await get_stream_response(chat_id, message_id, request, range)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("bot2_streamer:app", host="0.0.0.0", port=port, reload=False)
    
