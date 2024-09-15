import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Проверка загруженной переменной
BOT_TOKEN = os.getenv("BOT_TOKEN")
print(f"BOT_TOKEN: {BOT_TOKEN}")  # Добавьте эту строку для отладки

