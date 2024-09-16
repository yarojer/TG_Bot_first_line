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
from rk_sum import get_advert_ids

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class APIRKStates(StatesGroup):
    waiting_for_rkapi_key = State()
    waiting_for_rkanalysis_choice = State()
    waiting_for_rkanalysis_period = State()

user_data = {}

router = Router()

# Обработчик команды
@router.message(Command('rkexp'))
async def handle_rkexp(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data[user_id] = {'current_state': 'waiting_for_rkapi_key'}

    await message.answer(
        "Пожалуйста, введите ваш API ключ с методом Продвижения."
    )
    await state.set_state(APIRKStates.waiting_for_rkapi_key)

# Обработчик нажатия кнопки
@router.callback_query(lambda callback_query: callback_query.data == "rkexp")  
async def button_click_RKexp(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    await state.update_data(analysis_type='rkexp')
    await state.set_state(APIRKStates.waiting_for_rkapi_key)

    await callback_query.message.answer(
        "Пожалуйста, введите ваш API ключ с методом Продвижения."
    )
    logger.info(f"Состояние пользователя {user_id} установлено на waiting_for_rkapi_key")
    
    await callback_query.answer()

# Обработка ввода API ключа
@router.message(StateFilter(APIRKStates.waiting_for_rkapi_key))
async def handle_apifa_api_key(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    api_key = message.text

    # Сохранение API ключа
    os.environ["API_RK_KEY"] = api_key
    user_data[user_id]['api_key'] = api_key  # Сохраняем ключ в user_data

    # Запрос на выбор типа анализа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Все РК", callback_data='fullrk_report')],
        ]
    )
    await message.answer("Что именно анализируем?", reply_markup=keyboard)
    await state.set_state(APIRKStates.waiting_for_rkanalysis_choice)

# Обработка выбора типа анализа 
@router.callback_query(F.data.in_(['fullrk_report']), StateFilter(APIRKStates.waiting_for_rkanalysis_choice))
async def button_click_rk(query: types.CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    choice = query.data

    logger.info(f"Пользователь {user_id} выбрал опцию: {choice}")
    
    if choice == 'fullrk_report':
        # Если выбран полный отчет, запрашиваем период анализа
        await state.update_data(analysis_type='fullrk_report')
        await query.message.answer("Пожалуйста, укажите период анализа в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
        await state.set_state(APIRKStates.waiting_for_rkanalysis_period)

# Обработка ввода периода анализа
@router.message(StateFilter(APIRKStates.waiting_for_rkanalysis_period))
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

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        ##df = (api_key, start_date_str, end_date_str, user_id, timestamp)
        get_advert_ids(api_key)


        # Отправка файла пользователю
        await (bot, message)

        await state.clear()

    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, укажите период в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        await message.answer("Произошла ошибка при обработке данных. Пожалуйста, повторите попытку.")