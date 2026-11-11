import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
BASE_URL = "https://api.deepseek.com"

if not DEEPSEEK_API_KEY:
    raise RuntimeError(
        "Не задан DEEPSEEK_API_KEY. Установите переменную окружения "
    )
