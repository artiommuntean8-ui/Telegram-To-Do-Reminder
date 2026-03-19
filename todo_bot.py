import asyncio
import sqlite3
import os
from datetime import datetime
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

# Set up logging
logging.basicConfig(level=logging.INFO)

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
async def send_reminder(user_id: int, text: str, task_id: int):
    # Add an inline button to mark the task as done immediately
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task_id}")]
    ])
    await bot.send_message(user_id, f"⏰ Напоминание:\n{text}", reply_markup=keyboard)


def schedule_reminder(task_id: int, user_id: int, text: str, remind_at: str):
    run_date = datetime.fromisoformat(remind_at)
    scheduler.add_job(
        send_reminder,
        "date",
        run_date=run_date,
        args=[user_id, text, task_id],
        id=str(task_id),
        misfire_grace_time=3600  # Run job even if bot was down, up to 1 hour late
    )


async def load_and_schedule_tasks():
    """Loads pending tasks from DB and schedules them on bot startup."""
    print("Loading and scheduling tasks on startup...")
    now = datetime.now()
    cursor.execute("SELECT id, user_id, text, remind_at FROM tasks WHERE done = 0")
    tasks = cursor.fetchall()
    scheduled_count = 0
    for task in tasks:
        task_id, user_id, text, remind_at_str = task
        remind_at = datetime.fromisoformat(remind_at_str)
        if remind_at > now:
            schedule_reminder(task_id, user_id, text, remind_at_str)
            scheduled_count += 1
    print(f"Scheduled {scheduled_count} future tasks.")


# ---------- COMMANDS ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я To-Do Reminder Bot\n\n"
        "Я помогу тебе не забыть о важных делах.\n\n"
        "<b>Команды:</b>\n"
        "/add <code>Задача | ГГГГ-ММ-ДД ЧЧ:ММ</code> - добавить задачу\n"
        "/list - показать активные задачи\n"
        "/done <code>ID</code> - отметить задачу как выполненную\n"
        "/delete <code>ID</code> - удалить задачу\n\n"
        "Используй /list чтобы увидеть ID своих задач.",
        parse_mode="HTML"
    )


@dp.message(Command("add"))
async def add_task(message: types.Message):
    try:
        command_args = message.text.replace("/add", "").strip()

        if "|" not in command_args:
            await message.answer("❌ Ошибка: отсутствует разделитель '|'.\nФормат: /add Текст | Дата")
            return

        text, time_str = command_args.split("|", 1)
        text = text.strip()
        time_str = time_str.strip()

        if not text:
            await message.answer("❌ Ошибка: текст задачи не может быть пустым.")
            return

        try:
            # Try parsing full date and time
            remind_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            # If that fails, try parsing just the time (assuming today)
            time_val = datetime.strptime(time_str, "%H:%M").time()
            remind_at = datetime.combine(datetime.now().date(), time_val)

        if remind_at < datetime.now():
            await message.answer("🤔 Дата напоминания в прошлом, но я все равно добавил задачу.")

        cursor.execute(
            "INSERT INTO tasks (user_id, text, remind_at) VALUES (?, ?, ?)",
            (message.from_user.id, text, remind_at.isoformat())
        )
        conn.commit()

        task_id = cursor.lastrowid
        schedule_reminder(
            task_id,
            message.from_user.id,
            text,
            remind_at.isoformat()
        )

        await message.answer("✅ Задача добавлена")
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ или просто ЧЧ:ММ (сегодня)\n"
            "Пример: /add Сделать отчет | 2024-12-31 23:59"
        )


@dp.message(Command("list"))
async def list_tasks(message: types.Message):
    cursor.execute(
        "SELECT id, text, remind_at FROM tasks WHERE user_id=? AND done=0 ORDER BY remind_at",
        (message.from_user.id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("🎉 У вас нет активных задач!")
        return

    reply = "📋 Ваши активные задачи:\n\n"
    for task in rows:
        # task is (id, text, remind_at)
        remind_time = datetime.fromisoformat(task[2]).strftime("%Y-%m-%d %H:%M")
        reply += f"<b>{task[0]}</b>. {task[1]} (<i>{remind_time}</i>)\n"

    await message.answer(reply, parse_mode="HTML")


@dp.message(Command("done"))
async def done_task(message: types.Message):
    try:
        task_id = int(message.text.replace("/done", "").strip())
    except ValueError:
        await message.answer("❌ Укажите корректный ID задачи.\nПример: /done 123")
        return

    cursor.execute(
        "UPDATE tasks SET done=1 WHERE id=? AND user_id=?",
        (task_id, message.from_user.id)
    )
    conn.commit()

    if cursor.rowcount == 0:
        await message.answer("🤔 Задача с таким ID не найдена или она вам не принадлежит.")
    else:
        try:
            scheduler.remove_job(str(task_id))
        except Exception:  # JobLookupError
            pass  # Job was already triggered or never existed, which is fine
        await message.answer("✅ Задача отмечена как выполненная.")


@dp.callback_query(F.data.startswith("done_"))
async def process_done_callback(callback: CallbackQuery):
    """Handles the 'Done' button click on reminder messages."""
    task_id = int(callback.data.split("_")[1])

    cursor.execute(
        "UPDATE tasks SET done=1 WHERE id=?",
        (task_id,)
    )
    conn.commit()

    await callback.answer("Задача выполнена!")
    await callback.message.edit_text(callback.message.text + "\n\n✅ Задача выполнена!", reply_markup=None)


@dp.message(Command("delete"))
async def delete_task(message: types.Message):
    try:
        task_id = int(message.text.replace("/delete", "").strip())
    except ValueError:
        await message.answer("❌ Укажите корректный ID задачи.\nПример: /delete 123")
        return

    cursor.execute(
        "DELETE FROM tasks WHERE id=? AND user_id=?",
        (task_id, message.from_user.id)
    )
    conn.commit()

    if cursor.rowcount == 0:
        await message.answer("🤔 Задача с таким ID не найдена или она вам не принадлежит.")
        return

    try:
        scheduler.remove_job(str(task_id))
    except Exception:  # JobLookupError
        pass

    await message.answer("🗑 Задача удалена.")


# ---------- START ----------
async def main():
    scheduler.start()
    await load_and_schedule_tasks()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
