import os
import logging
import json
from datetime import datetime
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Конфигурация
TOKEN = "8128014975:AAHwYRzNnFPoUuaYbCf9vhqTz01HwUfCngQ"
OWNER_ID = int(os.getenv("OWNER_ID"))
SPREADSHEET_NAME = "SleepLog"
SHEET_NAME = "Лист1"

class SleepLogStates(StatesGroup):
    waiting_bedtime = State()
    waiting_waketime = State()
    waiting_feeling = State()
    waiting_comment = State()

def get_sheet():
    credentials_json = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

# Инициализация бота с правильным parse_mode
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

@dp.message(SleepLogStates.waiting_bedtime)
async def bedtime_handler(message: Message, state: FSMContext):
    await state.update_data(bedtime=message.text)
    await message.answer("🌞 Во сколько ты проснулся?")
    await state.set_state(SleepLogStates.waiting_waketime)

@dp.message(SleepLogStates.waiting_waketime)
async def waketime_handler(message: Message, state: FSMContext):
    await state.update_data(waketime=message.text)
    await message.answer("😊 Как ты себя чувствуешь от 1 до 10?")
    await state.set_state(SleepLogStates.waiting_feeling)

@dp.message(SleepLogStates.waiting_feeling)
async def feeling_handler(message: Message, state: FSMContext):
    await state.update_data(feeling=message.text)
    await message.answer("✍️ Хочешь оставить комментарий?")
    await state.set_state(SleepLogStates.waiting_comment)

@dp.message(SleepLogStates.waiting_comment)
async def comment_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text
    sheet = get_sheet()
    row = [
        datetime.now().strftime("%d.%m.%Y"),
        data["bedtime"],
        data["waketime"],
        data["feeling"],
        comment
    ]
    sheet.append_row(row)
    await message.answer("✅ Спасибо! Я записал это в таблицу.")
    await state.clear()

@dp.message()
async def start_conversation(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return await message.answer("⛔️ У тебя нет доступа.")
    await message.answer("🛏 Во сколько ты лёг?")
    await state.set_state(SleepLogStates.waiting_bedtime)

async def ask_questions():
    await bot.send_message(OWNER_ID, "🛏 Во сколько ты лёг?")

async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler.add_job(ask_questions, CronTrigger(hour=9, minute=0))
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
