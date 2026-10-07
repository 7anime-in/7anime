import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pyrogram import Client

app = FastAPI()

API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8696088856:AAFiYCKSyXzPCGgWGqypO6kBTlsOFmngAI8")

bot = Client(
    "7anime_serverless_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

async def start_bot():
    if not bot.is_connected:
        await bot.start()

@app.get("/stream/{chat_id}/{msg_id}.mp4")
async def stream_telegram_video(chat_id: str, msg_id: int, request: Request):
    await start_bot()
    try:
        target_chat = chat_id
        if not chat_id.startswith("-100") and not chat_id.startswith("@"):
            target_chat = f"@{chat_id}"

        message = await bot.get_messages(target_chat, msg_id)
        if not message or not message.video:
            raise HTTPException(status_code=404, detail="Video not found on Telegram channel.")

        file_size = message.video.file_size
        
        async def generate():
            async for chunk in bot.stream_media(message):
                yield chunk

        return StreamingResponse(generate(), media_type="video/mp4")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def home():
    return {"status": "7anime Vercel FastAPI Streamer Active"}
  
