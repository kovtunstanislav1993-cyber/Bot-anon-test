import aiosqlite
import time

DB_FILE = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                gender TEXT,
                age INTEGER,
                is_vip INTEGER DEFAULT 0,
                vip_until INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                user1_id INTEGER,
                user2_id INTEGER,
                PRIMARY KEY (user1_id, user2_id)
            )
        ''')
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT gender, age, is_vip, vip_until FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return {"gender": row[0], "age": row[1], "is_vip": row[2], "vip_until": row[3]}
        return None

async def save_user(user_id: int, gender: str, age: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, gender, age) VALUES (?, ?, ?)",
            (user_id, gender, age)
        )
        await db.commit()

async def set_vip(user_id: int, days: int = 1):
    until = int(time.time()) + days * 86400
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "UPDATE users SET is_vip = 1, vip_until = ? WHERE user_id = ?",
            (until, user_id)
        )
        await db.commit()

async def is_vip_user(user_id: int) -> bool:
    user = await get_user(user_id)
    if user and user['is_vip']:
        if user['vip_until'] > int(time.time()):
            return True
        # Сброс, если истёк
        await db.execute("UPDATE users SET is_vip = 0, vip_until = 0 WHERE user_id = ?", (user_id,))
        await db.commit()
    return False
