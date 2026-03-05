import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Импортируем наши модули
from database import init_db, get_user, save_user
from states import Form

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатуры
gender_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
        [KeyboardButton(text="Другой")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

age_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="18–24", callback_data="age_18")],
    [InlineKeyboardButton(text="25–30", callback_data="age_25")],
    [InlineKeyboardButton(text="31–35", callback_data="age_31")],
    [InlineKeyboardButton(text="36–40", callback_data="age_36")],
    [InlineKeyboardButton(text="40+", callback_data="age_40")]
])

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        text = f"Привет снова! Твоя анкета:\nПол: {user['gender']}\nВозраст: {user['age']}\n\nНажми 'Найти чат' чтобы начать."
        await message.answer(text)
    else:
        await message.answer(
            "Привет! Это анонимный чат для знакомств 18+.\nСначала заполни анкету.\nВыбери пол:",
            reply_markup=gender_kb
        )
        await state.set_state(Form.gender)

# Пока базовая версия — дальше добавим обработку пола, возраста, поиск чата и VIP
# (когда этот запустится, добавим остальное)

async def main():
    await init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
