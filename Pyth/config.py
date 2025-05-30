import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Yandex Cloud
FOLDER_ID = os.getenv("FOLDER_ID")
SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
YANDEX_PRIVATE_KEY_PATH = os.getenv("YANDEX_PRIVATE_KEY_PATH")

# ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL")

# Прочее
TRIAL_PRICE = int(os.getenv("TRIAL_PRICE", 99))        # по умолчанию 99 ₽
MONTHLY_PRICE = int(os.getenv("MONTHLY_PRICE", 689))