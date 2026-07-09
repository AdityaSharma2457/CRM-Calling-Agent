from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    MCUBE_API_KEY = os.getenv("MCUBE_API_KEY")
    MCUBE_EXE_NUMBER = os.getenv("MCUBE_EXE_NUMBER")
    MCUBE_OUTBOUND_API_URL = os.getenv("MCUBE_OUTBOUND_API_URL", "https://api.mcube.com/Restmcube-api/outbound-calls")

    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    HF_API_KEY = os.getenv("HF_API_KEY", "")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "backend/app/db/chroma")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "university_info")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    MCUBE_WEBSOCKET_URL = os.getenv("MCUBE_WEBSOCKET_URL", "ws://localhost:8000/ws/voice")


settings = Settings()