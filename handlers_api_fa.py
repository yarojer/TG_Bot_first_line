import logging
import os
import pandas as pd
from aiogram import Bot, types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from calculator_API import fetch_data_from_api
from datetime import datetime
from aiogram.types import FSInputFile
from calculator_API import generate_and_save_report
# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для управления процессом
class APIFAStates(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_analysis_choice = State()
    waiting_for_brand = State()
    waiting_for_analysis_period = State()

# Хранение данных пользователей
user_data = {}

# Создаем роутер
router = Router()

# Обработка команды начала процесса API FA
@router.message(Command('apifa'))
async def handle_apifa(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data[user_id] = {'current_state': 'waiting_for_api_key'}
    
    await message.answer(
        "Пожалуйста, введите ваш API ключ с методом Статистика."
    )
    await state.set_state(APIFAStates.waiting_for_api_key)

# Обработка нажатия кнопки ФА API
@router.callback_query(lambda callback_query: callback_query.data == "apifa")  # Исправлен оператор сравнения
async def button_click_apifa(callback_query: types.CallbackQuery, state: FSMContext):  # Добавлено двоеточие
    user_id = callback_query.from_user.id

    await state.update_data(files=[], analysis_type='apifa')
    await state.set_state(APIFAStates.waiting_for_api_key)

    await callback_query.message.answer(
        "Пожалуйста, введите ваш API ключ с методом Статистика."
    )
    logger.info(f"Состояние пользователя {user_id} установлено на waiting_for_api_key")
    
    await callback_query.answer()  # Исправлен вызов метода

# Обработка ввода API ключа
@router.message(StateFilter(APIFAStates.waiting_for_api_key))
async def handle_apifa_api_key(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    api_key = message.text

    # Сохранение API ключа
    os.environ["API_FA_KEY"] = api_key
    user_data[user_id]['api_key'] = api_key  # Сохраняем ключ в user_data

    # Запрос на выбор типа анализа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Весь отчет", callback_data='full_report')],
            [InlineKeyboardButton(text="Анализ бренда", callback_data='brand_analysis')]
        ]
    )
    await message.answer("Что именно анализируем?", reply_markup=keyboard)
    await state.set_state(APIFAStates.waiting_for_analysis_choice)

# Обработка выбора типа анализа (callback handler)
@router.callback_query(F.data.in_(['full_report', 'brand_analysis']), StateFilter(APIFAStates.waiting_for_analysis_choice))
async def button_click_fa(query: types.CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    choice = query.data

    logger.info(f"Пользователь {user_id} выбрал опцию: {choice}")
    
    if choice == 'full_report':
        # Если выбран полный отчет, запрашиваем период анализа
        await state.update_data(analysis_type='full_report')
        await query.message.answer("Пожалуйста, укажите период анализа в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
        await state.set_state(APIFAStates.waiting_for_analysis_period)
    elif choice == 'brand_analysis':
        # Если выбран анализ бренда, запрашиваем название бренда
        await state.update_data(analysis_type='brand_analysis')
        await query.message.answer("Пожалуйста, укажите название бренда.")
        await state.set_state(APIFAStates.waiting_for_brand)
    else:
        logger.error(f"Неизвестный тип анализа: {choice}")
    
    await query.answer()

# Обработка ввода названия бренда
@router.message(StateFilter(APIFAStates.waiting_for_brand))
async def handle_brand_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    brand_name = message.text.strip()
    logger.info(f"Пользователь {user_id} ввел название бренда: {brand_name}")

    # Сохраняем название бренда в состоянии
    await state.update_data(brand_name=brand_name)

    # Запрашиваем период анализа
    await message.reply("Пожалуйста, укажите период анализа в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    await state.set_state(APIFAStates.waiting_for_analysis_period)

# Обработка ввода периода анализа
@router.message(StateFilter(APIFAStates.waiting_for_analysis_period))
async def handle_analysis_period(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    analysis_period = message.text
    data = await state.get_data()

    try:
        start_date_str, end_date_str = analysis_period.split('-')
        start_date = pd.to_datetime(start_date_str, format='%d.%m.%Y')
        end_date = pd.to_datetime(end_date_str, format='%d.%m.%Y')

        user_data[user_id]['analysis_start_date'] = start_date
        user_data[user_id]['analysis_end_date'] = end_date

        api_key = user_data[user_id]['api_key']
        analysis_type = data.get('analysis_type')
        brand_name = data.get('brand_name', None)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        df = fetch_data_from_api(api_key, start_date_str, end_date_str, user_id, timestamp)

        if 'Дата заказа покупателем' in df.columns:
            df['Дата заказа покупателем'] = df['Дата заказа покупателем'].dt.tz_localize(None)

        # Передаем brand_name в generate_and_save_report, если анализ типа brand_analysis
        filename = generate_and_save_report(df, start_date, end_date, user_id, brand_name if analysis_type == 'brand_analysis' else None)

        # Отправка файла пользователю
        await send_file_to_user(bot, message, filename)

        await state.clear()

    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, укажите период в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        await message.answer("Произошла ошибка при обработке данных. Пожалуйста, повторите попытку.")
        
async def send_file_to_user(bot: Bot, message: types.Message, file_path: str):
    """
    Отправляет файл пользователю по известному пути.
    :param bot: Объект бота.
    :param message: Сообщение пользователя.
    :param file_path: Путь к файлу для отправки.
    """
    # Проверяем существование файла
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не найден.")
        await message.reply("Файл не найден.")
        return

    try:
        # Используем FSInputFile для передачи файла по его пути
        document = FSInputFile(file_path)
        await bot.send_document(chat_id=message.chat.id, document=document)
        logger.info(f"Файл {file_path} успешно отправлен.")
    except Exception as e:
        logger.error(f"Ошибка при отправке файла {file_path}: {e}")
        await message.reply("Ошибка при отправке файла.")
