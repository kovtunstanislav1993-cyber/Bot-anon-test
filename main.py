import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from database import init_db, get_user, save_user, is_vip_user
from states import Form

print("=== BOT STARTED ===")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.info("Бот запущен | DEBUG включён")

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.critical("BOT_TOKEN НЕ НАЙДЕН!")
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

queue = []
active_chats = {}
blocked = set()
matchmaking_task = None

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

async def matchmaking_loop():
    logging.debug("matchmaking_loop запущена")
    while True:
        await asyncio.sleep(2)  # чаще проверяем — 2 секунды
        logging.debug(f"Цикл проверки | В очереди: {len(queue)} | {queue}")
        if len(queue) >= 2:
            logging.info(f"Найдено минимум 2 человека в очереди: {queue}")
            try:
                u1 = queue.pop(0)
                u2 = queue.pop(0)
                active_chats[u1] = u2
                active_chats[u2] = u1
                logging.info(f"ПАРА СОЕДИНЕНА: {u1} ↔ {u2}")
                await bot.send_message(u1, "✅ ПАРА НАЙДЕНА! Общайтесь анонимно 🔥\nСообщения теперь будут пересылаться.", reply_markup=chat_kb)
                await bot.send_message(u2, "✅ ПАРА НАЙДЕНА! Общайтесь анонимно 🔥\nСообщения теперь будут пересылаться.", reply_markup=chat_kb)
            except Exception as e:
                logging.error(f"Ошибка при соединении пары: {e}")
        else:
            logging.debug("Очередь меньше 2 — ждём")

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    logging.info(f"/start от {message.from_user.id}")
    await state.clear()
    user = await get_user(message.from_user.id)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Найти собеседника")]], resize_keyboard=True)
    if user:
        await message.answer("Анкета готова. Нажми 'Найти собеседника'", reply_markup=kb)
    else:
        await message.answer("Заполни анкету. Пол:", reply_markup=gender_kb)
        await state.set_state(Form.gender)

@dp.message(Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender = message.text.strip()
    if gender not in ["Мужчина", "Женщина", "Другой"]:
        await message.answer("Выбери из кнопок.")
        return
    await state.update_data(gender=gender)
    await message.answer("Возраст:", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Выбери:", reply_markup=age_kb)
    await state.set_state(Form.age)

@dp.callback_query(Form.age)
async def process_age(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    age_str = callback.data.split("_")[1]
    age = {"18": 18, "25": 25, "31": 31, "36": 36, "40": 40}.get(age_str, 25)
    await save_user(callback.from_user.id, data["gender"], age)
    await callback.message.edit_text(f"Анкета сохранена! Пол: {data['gender']}, Возраст: {age_str}+")
    await state.clear()
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Найти собеседника")]], resize_keyboard=True)
    await callback.message.answer("Готов! Нажми кнопку.", reply_markup=kb)

@dp.message(F.text == "Найти собеседника")
async def find_partner(message: types.Message):
    user_id = message.from_user.id
    logging.info(f"Кнопка 'Найти собеседника' нажата {user_id}")
    await message.answer(f"DEBUG: Добавляю в очередь. Было: {len(queue)}, стало: {len(queue)+1}")

    if user_id in blocked:
        await message.answer("Ты заблокирован.")
        return
    if user_id in active_chats:
        await message.answer("Ты уже в чате.")
        return
    if user_id in queue:
        await message.answer("Ты уже ждёшь...")
        return

    queue.append(user_id)
    logging.info(f"Добавлен {user_id} в очередь → {queue}")
    await message.answer(f"Ищем... В очереди: {len(queue)} (DEBUG)")

    global matchmaking_task
    if matchmaking_task is None or matchmaking_task.done():
        matchmaking_task = asyncio.create_task(matchmaking_loop())
        logging.info("Задача matchmaking запущена заново")

@dp.message()
async def catch_all(message: types.Message):
    logging.info(f"Поймано сообщение: '{message.text}' от {message.from_user.id}")
    await message.answer("Нажми 'Найти собеседника' или /start")

async def main():
    logging.info("main() запущен")
    await init_db()
    logging.info("База готова")
    global matchmaking_task
    matchmaking_task = asyncio.create_task(matchmaking_loop())
    logging.info("matchmaking запущен при старте")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
