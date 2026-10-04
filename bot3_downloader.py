import os
import re
import asyncio
import urllib.parse
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from pyrogram import Client
from pyrogram.errors import RPCError, FloodWait

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT3_TOKEN") or os.getenv("BOT_TOKEN", "8646261177:AAGmVPIzmduiLhZ5AJbiJGMb0kh4vbn7n6E")

pyro_client: Optional[Client] = None

# ==================== HELPER FUNCTIONS ====================
def is_video_message(message) -> bool:
    if not message or message.empty:
        return False
    if message.video:
        return True
    if message.document:
        mime = (message.document.mime_type or "").lower()
        fname = (message.document.file_name or "").lower()
        if mime.startswith("video/") or fname.endswith((".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v")):
            return True
    return False

def extract_filename(message, default_id: int, custom_name: Optional[str] = None) -> str:
    if custom_name:
        return re.sub(r'[\r\n"]', '', custom_name).strip()

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

    return re.sub(r'[\r\n"]', '', filename)

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
        in_memory=True,  # Prevents SQLite DB locks on cloud hosts like Render
        max_concurrent_transmissions=10  # Telegram Speed Boost for chunk downloading
    )

    await pyro_client.start()
    print("✅ Bot 3 Pyrogram Engine Active & Ready!")
    yield
    if pyro_client and pyro_client.is_connected:
        await pyro_client.stop()
        print("🛑 Bot 3 Engine Stopped Cleanly.")

app = FastAPI(title="Bot 3 - Downloader Engine", lifespan=lifespan)

# Enable Full CORS for Web Downloads & Multi-threaded Managers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type", "Content-Range", "Accept-Ranges"],
)

# ==================== DOWNLOAD CORE ENGINE ====================
async def handle_download_request(
    chat_id: str, 
    message_id: str, 
    request: Request, 
    range_header: Optional[str] = None,
    filename_override: Optional[str] = None
):
    if request.method == "OPTIONS":
        return Response(
            status_code=200, 
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Length, Content-Type, Content-Range, Accept-Ranges",
            }
        )

    # Clean URL parameters and extensions
    chat_id_clean = urllib.parse.unquote(str(chat_id)).strip()
    msg_str_clean = urllib.parse.unquote(str(message_id)).strip()
    clean_msg_str = re.sub(r"\.\w+$", "", msg_str_clean)

    try:
        msg_id_clean = int(clean_msg_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Message ID format")

    if not pyro_client or not pyro_client.is_connected:
        raise HTTPException(status_code=503, detail="Downloader client engine initializing...")

    try:
        cid_str = chat_id_clean
        if cid_str.lstrip('-').isdigit():
            target_id = int(cid_str)
        else:
            target_id = cid_str if cid_str.startswith("@") else f"@{cid_str}"

        msg = await pyro_client.get_messages(target_id, msg_id_clean)
    except FloodWait as e:
        return Response(
            content=f"Rate limited by Telegram. Retry after {e.value} seconds.", 
            status_code=429, 
            headers={"Retry-After": str(e.value)}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File message not found in Telegram")

    if not is_video_message(msg):
        raise HTTPException(status_code=400, detail="Target message is not a valid video/media file")

    media = msg.video or msg.document
    file_size = media.file_size
    file_name = extract_filename(msg, msg_id_clean, filename_override)

    # Safe Header Encoding (Fixes Latin-1 Uvicorn header crashes)
    ascii_filename = file_name.encode('ascii', 'ignore').decode('ascii').strip() or f"7anime_Episode_{msg_id_clean}.mp4"
    ascii_filename = re.sub(r'[\r\n"]', '', ascii_filename)
    encoded_filename = urllib.parse.quote(file_name)

    # Range Header Handling for Resumable Downloads (1DM / ADM / Chrome)
    if not range_header:
        range_header = request.headers.get("range") or request.headers.get("Range")

    from_bytes = 0
    until_bytes = file_size - 1

    if range_header:
        range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = range_match.group(1)
            end = range_match.group(2)
            from_bytes = int(start) if start else 0
            if end:
                until_bytes = int(end)

    # 416 Range Not Satisfiable check
    if from_bytes >= file_size:
        return Response(
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Access-Control-Allow-Origin": "*",
            }
        )

    until_bytes = min(until_bytes, file_size - 1)
    chunk_length = (until_bytes - from_bytes) + 1

    headers = {
        "Content-Type": getattr(media, "mime_type", "video/mp4") or "video/mp4",
        "Content-Disposition": f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}',
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
        "Content-Length": str(chunk_length),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Disposition, Content-Length, Content-Type, Content-Range, Accept-Ranges",
        "Cache-Control": "no-cache",
    }

    if request.method == "HEAD":
        return Response(status_code=206 if range_header else 200, headers=headers)

    # Pyrogram Block Calculation (1MB Chunking)
    PYRO_BLOCK_SIZE = 1024 * 1024
    start_chunk = from_bytes // PYRO_BLOCK_SIZE
    end_chunk = until_bytes // PYRO_BLOCK_SIZE
    chunks_to_fetch = (end_chunk - start_chunk) + 1
    skip_bytes = from_bytes % PYRO_BLOCK_SIZE

    async def file_downloader():
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

    return StreamingResponse(
        file_downloader(), 
        status_code=206 if range_header else 200, 
        headers=headers
    )

# ==================== ENDPOINTS ====================
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Bot 3 Downloader Engine Active 🚀", "service": "7anime Direct Downloader"}

@app.get("/health")
def health_check():
    return {"status": "ok", "connected": pyro_client.is_connected if pyro_client else False}

# Standard Download Endpoints
@app.api_route("/download/{chat_id}/{message_id}", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/download/{chat_id}/{message_id}.mp4", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/download/{chat_id}/{message_id}.mkv", methods=["GET", "HEAD", "OPTIONS"])
async def download_file(
    chat_id: str, 
    message_id: str, 
    request: Request, 
    range: Optional[str] = Header(None),
    name: Optional[str] = Query(None)
):
    return await handle_download_request(chat_id, message_id, request, range, name)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
    
