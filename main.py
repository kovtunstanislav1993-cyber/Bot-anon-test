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
    raise ValueError("BOT_TOKEN не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Глобальные структуры (в памяти — потеряются при рестарте, но для теста ок)
queue = []              # список ждущих: [user_id, ...]
active_chats = {}       # user_id -> partner_id
blocked = set()         # глобальный бан (можно per-user)

gender_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
        [KeyboardButton(text="Другой")]
    ],
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
    keyboard=[
        [KeyboardButton(text="Следующий"), KeyboardButton(text="Стоп")],
        [KeyboardButton(text="Заблокировать"), KeyboardButton(text="Купить VIP")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton("Найти собеседника")]], resize_keyboard=True)
        await message.answer(f"Привет! Анкета готова (пол: {user['gender']}, возраст ~{user['age']}+).\nНажми ниже, чтобы найти пару.", reply_markup=kb)
    else:
        await message.answer("Привет! Заполни анкету для знакомств 18+.\nВыбери пол:", reply_markup=gender_kb)
        await state.set_state(Form.gender)

@dp.message(Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender = message.text.strip()
    if gender not in ["Мужчина", "Женщина", "Другой"]:
        await message.answer("Выбери из кнопок.")
        return
    await state.update_data(gender=gender)
    await message.answer("Теперь возраст:", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Выбери категорию:", reply_markup=age_kb)
    await state.set_state(Form.age)

@dp.callback_query(Form.age)
async def process_age(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    age_str = callback.data.split("_")[1]
    age_map = {"18": 18, "25": 25, "31": 31, "36": 36, "40": 40}
    age = age_map.get(age_str, 25)

    await save_user(callback.from_user.id, data["gender"], age)

    await callback.message.edit_text(f"Анкета сохранена!\nПол: {data['gender']}\nВозраст: {age_str}+")
    await state.clear()

    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton("Найти собеседника")]], resize_keyboard=True)
    await callback.message.answer("Готов! Нажми кнопку ниже.", reply_markup=kb)

@dp.message(lambda m: m.text == "Найти собеседника")
async def find_partner(message: types.Message):
    user_id = message.from_user.id
    if user_id in blocked:
        await message.answer("Ты заблокирован в системе.")
        return
    if user_id in active_chats:
        await message.answer("Ты уже в чате! Напиши /stop или используй кнопки.")
        return

    queue.append(user_id)
    await message.answer("Ищем собеседника... ⏳ (может занять время)")

    # Проверяем очередь каждые 2 секунды (простой polling)
    while len(queue) >= 2 and user_id in queue:
        try:
            partner_id = queue.pop(0) if queue[0] != user_id else queue.pop(1)
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id

            await bot.send_message(user_id, "Пара найдена! Общайтесь анонимно 🔥\nИспользуй кнопки ниже.", reply_markup=chat_kb)
            await bot.send_message(partner_id, "Пара найдена! Общайтесь анонимно 🔥\nИспользуй кнопки ниже.", reply_markup=chat_kb)
            break
        except:
            await asyncio.sleep(2)

@dp.message(lambda m: m.text in ["Следующий", "Стоп", "Заблокировать", "Купить VIP"])
async def chat_controls(message: types.Message):
    user_id = message.from_user.id
    if user_id not in active_chats:
        return

    partner = active_chats.get(user_id)
    cmd = message.text

    if cmd == "Стоп":
        del active_chats[user_id]
        if partner in active_chats:
            del active_chats[partner]
        await message.answer("Чат завершён. /start или 'Найти собеседника'.")
        if partner:
            await bot.send_message(partner, "Собеседник завершил чат.")

    elif cmd == "Следующий":
        # Стоп + сразу новый поиск
        del active_chats[user_id]
        if partner in active_chats:
            del active_chats[partner]
        if partner:
            await bot.send_message(partner, "Собеседник ищет нового...")
        await find_partner(message)

    elif cmd == "Заблокировать":
        blocked.add(partner)
        await message.answer("Пользователь заблокирован.")
        if partner:
            await bot.send_message(partner, "Ты был заблокирован собеседником.")

    elif cmd == "Купить VIP":
        await message.answer("VIP пока в разработке. Скоро добавим оплату за отправку фото и приоритет!")

@dp.message()
async def forward_message(message: types.Message):
    user_id = message.from_user.id
    if user_id not in active_chats:
        return

    partner = active_chats[user_id]

    if message.photo or message.document or message.video:
        if await is_vip_user(user_id):
            await message.copy_to(partner)
            await message.reply("Фото/файл отправлен!")
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Купить VIP (скоро)", callback_data="vip")]
            ])
            await message.reply("Фото/видео только для VIP. Купить?", reply_markup=kb)
    else:
        await message.copy_to(partner)

async def main():
    await init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
