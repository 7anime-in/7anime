import os

# ==================== TELEGRAM API CREDENTIALS ====================
API_ID = int(os.getenv("API_ID", "31169133"))
API_HASH = os.getenv("API_HASH", "b836f4b836df4cf83c2d475a5ad3b285")

# ==================== BOT TOKENS ====================
BOT1_TOKEN = os.getenv("BOT1_TOKEN", "8517895964:AAHQlTU8BBM2HBRCatn5qh45jW-KeP67q3o")
BOT2_TOKEN = os.getenv("BOT2_TOKEN", "8946650986:AAGy6rYE-C42f7jcgeyS8Xl4-j9UAyIEwEk")
BOT3_TOKEN = os.getenv("BOT3_TOKEN", "8646261177:AAGmVPIzmduiLhZ5AJbiJGMb0kh4vbn7n6E")
BOT4_TOKEN = os.getenv("BOT4_TOKEN", "8854095839:AAH8pFz3ZszE7Gyp0AY1if7JY2NoC18bNJg")

# ==================== RENDER WEB SERVICE BASE URLS ====================
# In URLs ko apni Render Web Services deploy hone ke baad update kar sakte ho
BOT1_BASE_URL = os.getenv("BOT1_BASE_URL", "https://7anime-bot1-scanner.onrender.com")
BOT2_STREAM_BASE = os.getenv("BOT2_STREAM_BASE", "https://7anime-bot2-streamer.onrender.com")
BOT3_DOWNLOAD_BASE = os.getenv("BOT3_DOWNLOAD_BASE", "https://7anime-bot3-downloader.onrender.com")
BOT4_ADMIN_BASE = os.getenv("BOT4_ADMIN_BASE", "https://7anime-bot4-admin.onrender.com")

# ==================== TARGET TELEGRAM CHANNELS ====================
CHANNEL_INPUT = os.getenv("CHANNEL_ID", "-1004315586873,-1004409520918,sevenanime_ch1")
CHANNEL_IDS = [ch.strip() for ch in CHANNEL_INPUT.split(",") if ch.strip()]

# ==================== STREAMING & CHUNK CONFIGURATION ====================
MIN_STREAM_CHUNK_SIZE = 200 * 1024        # 200 KB Minimum Chunk (Fast Start)
MAX_STREAM_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB Maximum Chunk Limit
DEFAULT_CHUNK_SIZE = 2 * 1024 * 1024      # 2 MB Default Chunk
DOWNLOAD_CHUNK_SIZE = 2 * 1024 * 1024     # 2 MB High-Speed Download Chunk
