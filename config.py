import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    GEMINI_KEY = os.getenv("GEMINI_KEY")
    GM_FLASH = os.getenv("GM_FLASH")
    GM_FLASH2 = os.getenv("GM_FLASH2")
    SESSION_TYPE = "filesystem"