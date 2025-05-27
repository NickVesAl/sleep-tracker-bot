import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- НАСТРОЙКИ ---
TOKEN = "8128014975:AAHwYRzNnFPoUuaYbCf9vhqTz01HwUfCngQ"
YOUR_CHAT_ID = None  # получим после /start
SPREADSHEET_NAME = "SleepLog"

# --- Google Sheets ---
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

# --- Данные пользователя ---
user_data = {}

async def ask_questions(bot: Bot):
    global YOUR_CHAT_ID
    if YOUR_CHAT_ID is None:
        print("❌ YOUR_CHAT_ID не установлен. Напиши /start боту")
        return
    await bot.send_message(YOUR_CHAT_ID, "🛌 Во сколько ты лёг?")
    user_data[YOUR_CHAT_ID] = {'stage': 1}

# --- Ответы ---
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_data:
        await message.answer("Напиши /start, чтобы бот знал, куда писать.")
        return

    stage = user_data[chat_id]['stage']

    if stage == 1:
        user_data[chat_id]['sleep_time'] = text
        user_data[chat_id]['stage'] = 2
        await message.answer("🌞 Во сколько ты проснулся?")
    elif stage == 2:
        user_data[chat_id]['wake_time'] = text
        user_data[chat_id]['stage'] = 3
        await message.answer("😊 Как ты себя чувствуешь от 1 до 10?")
    elif stage == 3:
        user_data[chat_id]['mood'] = text
        await message.answer("✅ Спасибо! Я записал это в таблицу.")

        # Сохраняем в таблицу
        sheet = get_sheet()
        today = datetime.now().strftime("%d.%m.%Y")
        sheet.append_row([
            today,
            user_data[chat_id]['sleep_time'],
            user_data[chat_id]['wake_time'],
            user_data[chat_id]['mood']
        ])

        del user_data[chat_id]

# --- Команда /start ---
async def start_handler(message: types.Message):
    global YOUR_CHAT_ID
    YOUR_CHAT_ID = message.chat.id
    await message.answer("✅ Бот активен. Я буду спрашивать тебя каждый день в 9:00.")

# --- Основной запуск ---
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.register(start_handler, Command("start"))
    dp.message.register(handle_message)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(ask_questions, "interval", minutes=1, args=[bot])  # ⏰ 9:00 по серверному времени
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
