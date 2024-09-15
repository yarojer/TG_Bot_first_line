from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Создаем роутер
router = Router()

# Основной хендлер для команды /start
@router.message(Command('start'))
async def start(message: types.Message):
    # Создаем кнопки для инлайн-клавиатуры
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ФА", callback_data='fa')],
            [InlineKeyboardButton(text="Хранение", callback_data='storage')],
            [InlineKeyboardButton(text="ФА API", callback_data='apifa')],
            [InlineKeyboardButton(text="Рекламные расходы", callback_data='rkexp')]
        ]
    )

    # Отправляем сообщение с инлайн-клавиатурой
    await message.answer(
        text="Выберите, что вы хотите проанализировать:",
        reply_markup=keyboard
    )


