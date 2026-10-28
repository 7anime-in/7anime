import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pyrogram import Client

API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
SESSION_STRING = os.getenv("SESSION_STRING") or ""
BOT_TOKEN = os.getenv("BOT_TOKEN") or ""

userbot: Client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global userbot
    print("Starting Pyrogram Client on Render...", flush=True)
    
    if not API_ID or not API_HASH or not SESSION_STRING or not BOT_TOKEN:
        print("CRITICAL ERROR: API_ID, API_HASH, SESSION_STRING, ya BOT_TOKEN missing hain Render Environment Variables mein!", flush=True)
        raise RuntimeError("Missing Telegram Secrets!")
    
    try:
        userbot = Client(
            "7anime_userbot",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=SESSION_STRING,
            in_memory=True
        )
        await userbot.start()
        print("Pyrogram Userbot successfully connected!", flush=True)
    except Exception as e:
        print(f"Telegram start failed: {e}", flush=True)
        raise e
        
    yield
    
    if userbot and userbot.is_connected:
        await userbot.stop()
        print("Pyrogram Userbot stopped.", flush=True)

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "online", "platform": "Render Zero Bandwidth Redirect"}

@app.get("/download/{chat_id}/{message_id}")
async def direct_download(chat_id: str, message_id: int):
    if not userbot or not userbot.is_connected:
        raise HTTPException(status_code=503, detail="Telegram client is not connected")

    try:
        target_chat = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
        
        # 1. Fetch message metadata from Telegram (0 bandwidth)
        msg = await userbot.get_messages(target_chat, message_id)
        if not msg or msg.empty:
            raise HTTPException(status_code=404, detail="Message delete ho gaya hai ya mil nahi raha!")
            
        media = msg.document or msg.video or msg.audio
        if not media:
            raise HTTPException(status_code=404, detail="Is message mein koi media file nahi hai!")

        # 2. Get direct file path reference from Telegram CDN
        file_info = await userbot.get_file(media.file_id)
        if not file_info or not file_info.file_path:
            raise HTTPException(status_code=500, detail="Telegram se file path fetch nahi ho paya!")

        # 3. Build official Telegram CDN download URL
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        # 4. 302 Redirect (0 Server Bandwidth)
        return RedirectResponse(url=download_url, status_code=302)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redirect Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Render dynamically assigns a port via os.getenv("PORT")
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
  
