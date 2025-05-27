
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = "8128014975:AAHwYRzNnFPoUuaYbCf9vhqTz01HwUfCngQ"

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

class SleepLog(StatesGroup):
    sleep_time = State()
    wake_time = State()
    feeling = State()
    comment = State()

def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials_info = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)
    client = authorize(creds)
    sheet = client.open("SleepLog").worksheet("Лист1")
    return sheet

@dp.message(F.text.lower() == "/start")
async def start(message: Message, state: FSMContext):
    await message.answer("🛏️ Во сколько ты лёг?")
    await state.set_state(SleepLog.sleep_time)

@dp.message(SleepLog.sleep_time)
async def handle_sleep_time(message: Message, state: FSMContext):
    await state.update_data(sleep_time=message.text)
    await message.answer("🌞 Во сколько ты проснулся?")
    await state.set_state(SleepLog.wake_time)

@dp.message(SleepLog.wake_time)
async def handle_wake_time(message: Message, state: FSMContext):
    await state.update_data(wake_time=message.text)
    await message.answer("😊 Как ты себя чувствуешь от 1 до 10?")
    await state.set_state(SleepLog.feeling)

@dp.message(SleepLog.feeling)
async def handle_feeling(message: Message, state: FSMContext):
    await state.update_data(feeling=message.text)
    await message.answer("💬 Будет какой-то комментарий?")
    await state.set_state(SleepLog.comment)

@dp.message(SleepLog.comment)
async def handle_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    data = await state.get_data()

    now = datetime.now().strftime("%Y-%m-%d")
    row = [now, data['sleep_time'], data['wake_time'], data['feeling'], data['comment']]
    try:
        sheet = get_sheet()
        sheet.append_row(row)
        await message.answer("✅ Спасибо! Я записал это в таблицу.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при записи в таблицу: {e}")

    await state.clear()

async def ask_questions():
    await bot.send_message(chat_id="8128014975", text="🛏️ Во сколько ты лёг?")
    # будет триггериться обычный flow дальше через FSM

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ask_questions, CronTrigger(hour=9, minute=0))  # В 9:00 по UTC
    scheduler.start()

if __name__ == "__main__":
    import asyncio
    from aiogram import executor

    async def main():
        setup_scheduler()
        await dp.start_polling(bot)

    asyncio.run(main())
