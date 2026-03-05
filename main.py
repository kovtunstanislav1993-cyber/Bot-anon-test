import asyncio
import logging
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from database import init_db, get_user, save_user, is_vip_user, set_vip
from states import Form

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Глобальные переменные
queue = []                    # очередь поиска
active_chats = {}             # user_id -> partner_id
blocked = set()               # заблокированные пользователи
matchmaking_task = None       # задача поиска пар

# ==================== КЛАВИАТУРЫ ====================
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

chat_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Следующий"), KeyboardButton(text="Стоп")],
        [KeyboardButton(text="Заблокировать"), KeyboardButton(text="Купить VIP")]
    ],
    resize_keyboard=True
)

# ==================== ЗАДАЧА ПОИСКА ПАР ====================
async def matchmaking_loop():
    while True:
        await asyncio.sleep(3)  # проверяем каждые 3 секунды
        while len(queue) >= 2:
            try:
                u1 = queue.pop(0)
                u2 = queue.pop(0)

                active_chats[u1] = u2
                active_chats[u2] = u1

                await bot.send_message(u1, "✅ Собеседник найден! Общайтесь анонимно 🔥\nИспользуй кнопки ниже.", reply_markup=chat_kb)
                await bot.send_message(u2, "✅ Собеседник найден! Общайтесь анонимно 🔥\nИспользуй кнопки ниже.", reply_markup=chat_kb)
            except Exception as e:
                logging.error(f"Ошибка в matchmaking: {e}")

# ==================== ХЕНДЛЕРЫ ====================
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Найти собеседника")]], resize_keyboard=True)
        await message.answer(f"Привет снова!\nПол: {user['gender']}\nВозраст: {user['age']}+\n\nНажми кнопку ниже 👇", reply_markup=kb)
    else:
        await message.answer("Привет! Это анонимный чат знакомств 18+.\nСначала заполни анкету.\nВыбери пол:", reply_markup=gender_kb)
        await state.set_state(Form.gender)

@dp.message(Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender = message.text.strip()
    if gender not in ["Мужчина", "Женщина", "Другой"]:
        await message.answer("Пожалуйста, выбери из кнопок.")
        return
    await state.update_data(gender=gender)
    await message.answer("Теперь выбери возраст:", reply_markup=types.ReplyKeyboardRemove())
    await message.answer
