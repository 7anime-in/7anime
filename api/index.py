import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pyrogram import Client

app = FastAPI()

API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
SESSION_STRING = os.getenv("SESSION_STRING") or ""

# Helper to get active Pyrogram client (Initialized per request for Serverless)
async def get_userbot():
    if not API_ID or not API_HASH or not SESSION_STRING:
        raise RuntimeError("Telegram credentials missing in Vercel Environment Variables!")
    
    client = Client(
        "vercel_7anime_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )
    await client.start()
    return client

@app.get("/")
async def root():
    return {"status": "online", "platform": "Vercel Serverless Telegram Proxy"}

@app.get("/download/{chat_id}/{message_id}")
async def proxy_download(request: Request, chat_id: str, message_id: int):
    client = None
    try:
        # Handle chat ID format (Username vs Numeric ID)
        if chat_id.lstrip("-").isdigit():
            target_chat = int(chat_id)
        else:
            target_chat = chat_id if chat_id.startswith("@") else f"@{chat_id}"

        client = await get_userbot()

        # Fetch message from Telegram
        msg = await client.get_messages(target_chat, message_id)
        if not msg or msg.empty:
            raise HTTPException(status_code=404, detail="Telegram message not found!")

        media = msg.document or msg.video or msg.audio
        if not media:
            raise HTTPException(status_code=404, detail="No media found in this message!")

        file_size = media.file_size
        file_name = getattr(media, "file_name", "anime_video.mp4")
        mime_type = getattr(media, "mime_type", "video/mp4")

        # Handle HTTP Range Headers (Crucial for 20MB chunking & video seeking)
        range_header = request.headers.get("range")
        start = 0
        end = file_size - 1

        if range_header:
            try:
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0])
                if len(byte_range) > 1 and byte_range[1]:
                    end = int(byte_range[1])
            except ValueError:
                pass

        # Stream generator for chunks
        async def chunk_generator():
            try:
                async for chunk in client.stream_media(msg, offset=start, limit=end - start + 1):
                    yield chunk
            except GeneratorExit:
                pass
            finally:
                if client and client.is_connected:
                    await client.stop()

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": mime_type,
            "Content-Disposition": f'inline; filename="{file_name}"',
        }

        return StreamingResponse(
            chunk_generator(),
            status_code=206 if range_header else 200,
            headers=headers
        )

    except Exception as e:
        if client and client.is_connected:
            await client.stop()
        raise HTTPException(status_code=500, detail=str(e))
