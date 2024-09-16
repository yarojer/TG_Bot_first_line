import logging
import os
import pandas as pd
import io
from datetime import datetime
from aiogram import Bot, types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.types import FSInputFile
from calculator import calculate_all_combinations
from calculator import save_to_excel as calculator_save_to_excel

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для управления процессом анализа
class FAStates(StatesGroup):
    waiting_for_files = State()
    waiting_for_analysis_type = State()
    waiting_for_brand = State()
    waiting_for_period = State()

# Путь для сохранения файлов
BASE_DOWNLOAD_PATH = r"X:\TG_Bot_FAavto\project_folder _V1\downloads"

# Создаем роутер
router = Router()

# Старт процесса анализа FA
@router.message(Command('fa'))
async def fa_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал процесс FA. Ожидание загрузки файлов.")
    
    await message.answer(
        "Добро пожаловать! Пожалуйста, отправьте все отчеты в формате Excel. "
        "После загрузки всех отчетов отправьте команду /analyze."
    )
    
    await state.set_state(FAStates.waiting_for_files)
    logger.info(f"Состояние пользователя {user_id} установлено на WAITING_FOR_FILES")

# Обработка нажатий кнопrb ФА
@router.callback_query(lambda callback_query: callback_query.data == 'fa')
async def button_click_apifa(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Очищаем и обновляем данные пользователя
    await state.update_data(files=[], analysis_type='fa')
    await state.set_state(FAStates.waiting_for_files)

    # Запрашиваем файлы
    await callback_query.message.answer(
        "Добро пожаловать! Пожалуйста, отправьте все отчеты в формате Excel. "
        "После загрузки всех отчетов отправьте команду /analyze."
    )
    logger.info(f"Состояние пользователя {user_id} установлено на WAITING_FOR_FILES через кнопку")
    await callback_query.answer()

# Обработка получения файла (используем фильтр StateFilter для фильтрации по состоянию)
@router.message(F.document, StateFilter(FAStates.waiting_for_files))
async def file_received(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    logger.info(f"Начало выполнения file_received для пользователя {user_id}")
    
    # Получаем документ из сообщения
    file = message.document
    file_name = file.file_name
    logger.info(f"Файл получен от пользователя {user_id}: {file_name}")
    
    # Создание папки для файлов
    user_folder = os.path.join(BASE_DOWNLOAD_PATH, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, file_name)

    # Загрузка файла
    try:
        # Получение объекта файла с помощью API
        file_obj = await bot.get_file(file.file_id)
        
        # Скачивание файла напрямую с помощью file_obj.download()
        await bot.download_file(file_obj.file_path, file_path)
        logger.info(f"Файл успешно загружен: {file_path}")
        
        # Сохраняем пути загруженных файлов в состоянии пользователя
        data = await state.get_data()
        files = data.get('files', [])
        files.append(file_path)
        await state.update_data(files=files)
        
        await message.reply(f"Файл '{file_name}' загружен. Отправьте команду /analyze, когда загрузите все отчеты.")
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}")
        await message.reply("Произошла ошибка при загрузке файла. Пожалуйста, попробуйте еще раз.")


# Обработка команды анализа
@router.message(Command('analyze'), StateFilter(FAStates.waiting_for_files))
async def analyze(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил анализ данных.")

    # Получение данных состояния
    data = await state.get_data()

    if 'files' not in data or not data['files']:
        await message.reply("Пожалуйста, загрузите отчеты перед запуском анализа.")
        return
    
    # Кнопки для выбора анализа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Весь отчет", callback_data='full_report')],
            [InlineKeyboardButton(text="Анализ бренда", callback_data='brand_analysis')]
        ]
    )
    await message.reply("Что именно анализируем?", reply_markup=keyboard)
    await state.set_state(FAStates.waiting_for_analysis_type)

# Обработка пользовательского ввода периода анализа
@router.message(StateFilter(FAStates.waiting_for_period))
async def handle_period_input(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_text = message.text
    logger.info(f"Пользователь {user_id} ввел период: {user_text}")

    try:
        # Парсим дату
        start_date_str, end_date_str = map(str.strip, user_text.split('-'))
        start_date = pd.to_datetime(start_date_str, format='%d.%m.%Y')
        end_date = pd.to_datetime(end_date_str, format='%d.%m.%Y')

        # Сохраняем данные о периоде в состоянии пользователя
        await state.update_data(start_date=start_date, end_date=end_date)

        # Получение данных о типе анализа
        data = await state.get_data()
        analysis_type = data.get('analysis_type')

        logger.info(f"Тип анализа для пользователя {user_id}: {analysis_type}")

        if analysis_type == 'full_report':
            logger.info(f"Пользователь {user_id} запустил анализ полного отчета.")
            result_file = calculate_and_send_report(user_id, (start_date, end_date))

            # Вызов функции отправки файла
            await send_file_to_user(bot, message, result_file)
        
        elif analysis_type == 'brand_analysis':
            # Логика для анализа по бренду
            brand_name = data.get('brand_name')
            logger.info(f"Пользователь {user_id} запустил анализ по бренду: {brand_name}.")
            result_file = calculate_and_send_report(user_id, (start_date, end_date), brand_name)

            # Вызов функции отправки файла
            await send_file_to_user(bot, message, result_file)
        
        else:
            logger.error(f"Неизвестный тип анализа: {analysis_type}")
            await message.reply("Неизвестный тип анализа.")
    
    except ValueError:
        logger.error(f"Некорректный формат периода: {user_text}")
        await message.reply("Некорректный формат периода. Пожалуйста, используйте формат ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    
    # Завершение состояния
    await state.clear()

# Обработка ввода названия бренда
@router.message(StateFilter(FAStates.waiting_for_brand))
async def handle_brand_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    brand_name = message.text.strip()
    logger.info(f"Пользователь {user_id} ввел название бренда: {brand_name}")

    # Сохраняем название бренда в состоянии
    await state.update_data(brand_name=brand_name)

    # Запрашиваем период анализа
    await message.reply("Пожалуйста, укажите период анализа в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    await state.set_state(FAStates.waiting_for_period)


# Обработка выбора типа анализа (callback handler)
@router.callback_query(F.data.in_(['full_report', 'brand_analysis']), StateFilter(FAStates.waiting_for_analysis_type))
async def button_click_fa(query: types.CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    choice = query.data

    logger.info(f"Пользователь {user_id} выбрал опцию: {choice}")
    
    if choice == 'full_report':
        await state.update_data(analysis_type='full_report')
        await query.message.answer("Пожалуйста, укажите период анализа в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
        await state.set_state(FAStates.waiting_for_period)
    elif choice == 'brand_analysis':
        await state.update_data(analysis_type='brand_analysis')
        await query.message.answer("Пожалуйста, укажите название бренда.")
        await state.set_state(FAStates.waiting_for_brand)
    else:
        logger.error(f"Неизвестный тип анализа: {choice}")
    
    await query.answer()

# Функция для расчета и отправки отчета
def calculate_and_send_report(user_id, period, brand_name=None):
    user_folder = f"downloads/{user_id}"
    file_list = os.listdir(user_folder)
    df_list = [pd.read_excel(f"{user_folder}/{file}") for file in file_list]
    df = pd.concat(df_list, ignore_index=True)

    logger.info(f"Объединенный DataFrame для пользователя {user_id}: {df.shape}")

    start_date, end_date = period

    try:
        filtered_df = filter_data_by_date(df, start_date, end_date, user_id)
        result_df = calculate_all_combinations(filtered_df, start_date, end_date, brand_name=brand_name)
    except Exception as e:
        logger.error(f"Ошибка при анализе данных для пользователя {user_id}: {e}")
        raise

    results_folder = "results"
    os.makedirs(results_folder, exist_ok=True)
    user_folder = os.path.join(results_folder, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = os.path.join(user_folder, f"result_{timestamp}.xlsx")

    save_to_excel(result_df, start_date, end_date, result_file)
    logger.info(f"Отчет для пользователя {user_id} сохранен в файл: {result_file}")
    
    return result_file

# Фильтрация данных по дате
def filter_data_by_date(df, start_date, end_date, user_id):
    if 'Дата заказа покупателем' not in df.columns:
        logger.error("Столбец 'Дата заказа покупателем' отсутствует в данных.")
        raise ValueError("Отсутствует столбец 'Дата заказа покупателем' в данных.")

    df['Дата заказа покупателем'] = pd.to_datetime(df['Дата заказа покупателем'], infer_datetime_format=True)
    logger.info(f"Фильтрация данных для периода с {start_date} по {end_date}")
    
    filtered_df = df[(df['Дата заказа покупателем'] >= start_date) & (df['Дата заказа покупателем'] <= end_date)]
    
    if filtered_df.empty:
        logger.warning(f"Пустой DataFrame после фильтрации для пользователя {user_id}.")
    
    return filtered_df

def save_to_excel(df, start_date, end_date, filename):
    # Используем функцию save_to_excel из calculator.py
    calculator_save_to_excel(df, start_date, end_date, filename)

# Функция отправки файла пользователю
async def send_file_to_user(bot: Bot, message: types.Message, file_path: str):
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