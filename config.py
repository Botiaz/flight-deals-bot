import os
from dotenv import load_dotenv

load_dotenv()

# Kiwi Tequila API — registre-se gratuitamente em https://tequila.kiwi.com
KIWI_API_KEY = os.getenv("KIWI_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
