import asyncio
import sqlite3
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# ---------- ENV ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not found in .env file")

# ---------- BOT ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# ---------- DATABASE ----------
conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    remind_at TEXT,
    done INTEGER DEFAULT 0
)
""")
conn.commit()


# ---------- REMINDER ----------
async def send_reminder(user_id: int, text: str):
    await bot.send_message(user_id, f"⏰ Напоминание:\n{text}")


def schedule_reminder(task_id, user_id, text, remind_at):
    run_date = datetime.fromisoformat(remind_at)
    scheduler.add_job(
        send_reminder,
        "date",
        run_date=run_date,
        args=[user_id, text],
        id=str(task_id)
    )


# ---------- COMMANDS ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я To-Do Reminder Bot\n\n"
        "/add Задача | YYYY-MM-DD HH:MM\n"
        "/list — список задач\n"
        "/done ID — завершить\n"
        "/delete ID — удалить"
    )


@dp.message(Command("add"))
async def add_task(message: types.Message):
    try:
        data = message.text.replace("/add", "").strip()
        text, time_str = data.split("|")
        remind_at = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M")

        cursor.execute(
            "INSERT INTO tasks (user_id, text, remind_at) VALUES (?, ?, ?)",
            (message.from_user.id, text.strip(), remind_at.isoformat())
        )
        conn.commit()

        task_id = cursor.lastrowid
        schedule_reminder(
            task_id,
            message.from_user.id,
            text.strip(),
            remind_at.isoformat()
        )

        await message.answer("✅ Задача добавлена")
    except Exception:
        await message.answer("❌ Формат:\n/add Текст | 2026-01-05 18:30")


@dp.message(Command("list"))
async def list_tasks(message: types.Message):
    cursor.execute(
        "SELECT id, text, remind_at, done FROM tasks WHERE user_id=?",
        (message.from_user.id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("📭 Задач нет")
        return

    reply = "📋 Твои задачи:\n\n"
    for task in rows:
        status = "✅" if task[3] else "⏳"
        reply += f"{task[0]}. {task[1]} ({task[2]}) {status}\n"

    await message.answer(reply)


@dp.message(Command("done"))
async def done_task(message: types.Message):
    task_id = message.text.replace("/done", "").strip()
    cursor.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
    conn.commit()
    await message.answer("✅ Задача выполнена")


@dp.message(Command("delete"))
async def delete_task(message: types.Message):
    task_id = message.text.replace("/delete", "").strip()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()

    try:
        scheduler.remove_job(task_id)
    except:
        pass

    await message.answer("🗑 Задача удалена")


# ---------- START ----------
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
