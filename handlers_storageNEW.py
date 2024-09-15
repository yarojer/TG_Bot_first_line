import os
import logging
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from datetime import datetime
import pandas as pd
from aiogram.types import FSInputFile  # Импортируем правильный класс для работы с файлами
from storage import fetch_and_save_data
import random
from aiogram.types import FSInputFile

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Определение состояний FSM
class StorageStates(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_period = State()

# Создаем роутер
router = Router()

# Обработка команды /storage (начало диалога)
@router.message(Command("storage"))
async def storage_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Уведомляем пользователя о запросе API-ключа
    await message.answer("Пожалуйста, предоставьте ваш API ключ с методом Аналитика.")
    
    # Устанавливаем состояние ожидания API-ключа
    await state.set_state(StorageStates.waiting_for_api_key)

# Обработка пользовательского ввода API-ключа
@router.message(StateFilter(StorageStates.waiting_for_api_key))
async def handle_api_key(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text

    # Сохраняем API-ключ в переменные окружения
    os.environ["WB_API_TOKEN"] = user_text
    logger.info(f"API-ключ получен от пользователя {user_id}.")

    # Сохраняем API-ключ в состояние
    await state.update_data(api_key=user_text)
    
    # Запрашиваем период анализа
    await message.answer("API ключ сохранен. Пожалуйста, укажите период анализа в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    await state.set_state(StorageStates.waiting_for_period)

# Обработка пользовательского ввода периода анализа
@router.message(StateFilter(StorageStates.waiting_for_period))
async def handle_period(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text
    logger.info(f"Пользователь {user_id} ввел период: {user_text}")

    try:
        # Парсинг периода анализа
        start_date_str, end_date_str = map(str.strip, user_text.split('-'))
        start_date = pd.to_datetime(start_date_str, format='%d.%m.%Y', errors='raise')
        end_date = pd.to_datetime(end_date_str, format='%d.%m.%Y', errors='raise')

        logger.info(f"Период корректно распознан: с {start_date} по {end_date}")

        # Расчет количества дней в периоде
        period_days = (end_date - start_date).days + 1  # Добавляем 1, чтобы включить последний день
        # Расчет времени ожидания: 1 минута на каждый день + 10 секунд фиксированное время
        wait_time_minutes = period_days  # 1 минута на каждый день

        # Добавляем рандомные секунды от 5 до 15
        random_extra_seconds = random.randint(5, 12)
        wait_time_seconds = wait_time_minutes * 60 + random_extra_seconds  # Перевод в секунды и добавление рандомных секунд

        # Форматируем время ожидания в виде "X минут Y секунд"
        wait_minutes = wait_time_seconds // 60
        wait_seconds = wait_time_seconds % 60
        wait_time_str = f"{wait_minutes} минут(ы) {wait_seconds} секунд(ы)"

        # Путь к GIF файлу
        gif_path = r"X:\TG_Bot_FAavto\project_folder _V1\mem\mr-bean-mrbean.mp4"

        # Проверяем доступность файла перед отправкой
        if not os.path.exists(gif_path):
            await message.answer("Ошибка: файл не найден по указанному пути.")
            logger.error(f"Файл не найден по пути: {gif_path}")
            return

        # Отправка GIF пользователю с использованием FSInputFile
        await message.answer(f"Пожалуйста, ожидайте. Примерное время формирования отчета: {wait_time_str}.")
        gif_file = FSInputFile(gif_path)  # Создаем объект FSInputFile для отправки
        await message.answer_animation(animation=gif_file)  # Отправляем GIF

        # Получаем сохраненные данные из состояния
        data = await state.get_data()
        api_key = data.get("api_key")

        if not api_key:
            raise ValueError("API ключ не найден в данных состояния.")

        logger.info(f"Запрос к fetch_and_save_data с user_id: {user_id}, start_date: {start_date}, end_date: {end_date}, api_key: {api_key}")

        # Получение данных и сохранение их в файл
        file_name = fetch_and_save_data(user_id, start_date, end_date, api_key)

        if not file_name:
            await message.answer("Произошла ошибка при получении или сохранении данных.")
            return

        absolute_file_path = os.path.abspath(file_name)
        await message.answer("Данные успешно получены и сохранены в файле.")

        # Проверка существования файла и отправка пользователю
        if os.path.exists(absolute_file_path):
            try:
                # Проверка размера файла
                file_size = os.path.getsize(absolute_file_path)
                max_size = 50 * 1024 * 1024  # 50 MB - ограничение Telegram

                if file_size > max_size:
                    await message.answer("Файл слишком большой для отправки через Telegram обратитесь к Максиму.")
                    logger.error(f"Файл {absolute_file_path} превышает максимальный размер для отправки.")
                    return

                # Создаем FSInputFile для отправки файла
                document = FSInputFile(absolute_file_path)
                await message.answer_document(document=document, caption=os.path.basename(absolute_file_path))

                logger.info(f"Файл '{absolute_file_path}' успешно отправлен пользователю {user_id}.")
            
            except Exception as send_error:
                logger.error(f"Ошибка при отправке файла {absolute_file_path}: {send_error}")
                await message.answer("Ошибка при отправке файла. Пожалуйста, попробуйте еще раз.")
        else:
            logger.error(f"Файл не найден по пути: {absolute_file_path}")
            await message.answer(f"Ошибка: файл не найден по пути {absolute_file_path}.")

    except ValueError as ve:
        # Если ошибка связана с датами
        logger.error(f"Ошибка формата даты для пользователя {user_id}: {ve}")
        await message.answer("Некорректный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    
    except Exception as e:
        # Обработка всех других ошибок
        await message.answer("Произошла ошибка при обработке данных.")
        logger.error(f"Неожиданная ошибка для пользователя {user_id}: {e}")
    
    # Завершение диалога, сброс состояний
    await state.clear()

# Обработка нажатий кнопок для выбора анализа
@router.callback_query(lambda callback_query: callback_query.data == 'storage')
async def button_click_storage(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Очищаем и обновляем данные пользователя
    await state.update_data(files=[], analysis_type='storage')
    await state.set_state(StorageStates.waiting_for_api_key)

    # Запрашиваем API ключ
    await callback_query.message.answer("Пожалуйста, предоставьте ваш API ключ c методом Аналитика.")
    logger.info(f"User {user_id} selected Storage. Waiting for API key.")
    await callback_query.answer()

# Регистрация роутера
def register_storage_handlers(dp: Router):
    dp.include_router(router)
