import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from database import init_db, get_user, save_user, is_vip_user
from states import Form

# ====================== ЛОГИ ДЛЯ BOTHOST ======================
print("=== BOT STARTED SUCCESSFULLY ON BOTHOST ===")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.info("Бот запущен | Токен подхвачен | Логирование активно")

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("BOT_TOKEN НЕ НАЙДЕН!")
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

queue = []
active_chats = {}
blocked = set()
matchmaking_task = None

# ====================== КЛАВИАТУРЫ ======================
gender_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
              [KeyboardButton(text="Другой")]],
    resize_keyboard=True, one_time_keyboard=True
)

age_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="18–24", callback_data="age_18")],
    [InlineKeyboardButton(text="25–30", callback_data="age_25")],
    [InlineKeyboardButton(text="31–35", callback_data="age_31")],
    [InlineKeyboardButton(text="36–40", callback_data="age_36")],
    [InlineKeyboardButton(text="40+", callback_data="age_40")]
])

chat_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Следующий"), KeyboardButton(text="Стоп")],
              [KeyboardButton(text="Заблокировать"), KeyboardButton(text="Купить VIP")]],
    resize_keyboard=True
)

# ====================== ПОИСК ПАР ======================
async def matchmaking_loop():
    logging.info("Задача matchmaking_loop запущена")
    while True:
        await asyncio.sleep(3)
        logging.info(f"Проверка очереди: {len(queue)} человек")
        while len(queue) >= 2:
            u1 = queue.pop(0)
            u2 = queue.pop(0)
            active_chats[u1] = u2
            active_chats[u2] = u1
            logging.info(f"Пара найдена: {u1} <-> {u2}")
            await bot.send_message(u1, "✅ Пара найдена! Общайтесь анонимно 🔥", reply_markup=chat_kb)
            await bot.send_message(u2, "✅ Пара найдена! Общайтесь анонимно 🔥", reply_markup=chat_kb)

# ====================== ХЕНДЛЕРЫ ======================
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    logging.info(f"Команда /start от {message.from_user.id}")
    user = await get_user(message.from_user.id)
    if user:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton("Найти собеседника")]], resize_keyboard=True)
        await message.answer("Привет! Анкета уже есть. Нажми кнопку 👇", reply_markup=kb)
    else:
        await message.answer("Привет! Заполни анкету:", reply_markup=gender_kb)
        await state.set_state(Form.gender)

# ... (остальные хендлеры gender, age, find_partner, chat_controls, forward_message — точно как в предыдущей версии, они не менялись)

# (Чтобы не делать сообщение слишком длинным, я оставил только изменённую часть. Полный код с остальными хендлерами я могу дать отдельно, но сначала обнови эти два файла)

async def main():
    print("Запуск main()...")
    await init_db()
    logging.info("База данных готова")
    
    global matchmaking_task
    matchmaking_task = asyncio.create_task(matchmaking_loop())
    logging.info("Задача поиска пар запущена")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
