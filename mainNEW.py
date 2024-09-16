import logging
import asyncio
from aiogram import Bot, types, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from handlers_faNEW import router as fa_router  # FSM для анализа файлов (FA)
from handlers_storageNEW import router as storage_router  # FSM для анализа данных хранения
from handlers_api_fa import router as apifa_router  # FSM для анализа FA API
from handlers import start
from config import BOT_TOKEN

# Логирование
logging.basicConfig(level=logging.INFO)

# Основная функция
async def main():
    # Создание экземпляра бота
    bot = Bot(token=BOT_TOKEN)

    # Создание хранилища для состояний
    storage = MemoryStorage()

    # Создание диспетчера
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров для модулей FA, Storage и API FA
    dp.include_router(fa_router)
    dp.include_router(storage_router)
    dp.include_router(apifa_router)  # Подключаем роутер для анализа FA API

    # Добавляем обработчик для команды /start
    @dp.message(Command('start'))
    async def handle_start(message: Message):
        await start(message)

    # Запуск polling
    await dp.start_polling(bot)

# Запуск основного цикла программы
if __name__ == "__main__":
    asyncio.run(main())
