# svyato_bot.py
import logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ---------------- Настройки ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8208653042
SHEET_NAME = "prazdnik"
SERVICE_ACCOUNT_FILE = "service_account.json"
# -------------------------------------------

# Состояния диалога
NAME, SURNAME, ATTEND = range(3)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Авторизация Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open(SHEET_NAME).sheet1

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! 🎄 Вкажи, будь ласка, своє Ім’я:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Дякую! Тепер введи Прізвище:")
    return SURNAME

async def get_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["surname"] = update.message.text.strip()
    keyboard = [["Прийду 🎁", "Не прийду 😔"]]
    await update.message.reply_text(
        "Чи прийдеш ти на Новорічне свято в Kopřivnici?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return ATTEND

async def get_attend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["attend"] = update.message.text.strip()
    name = context.user_data["name"]
    surname = context.user_data["surname"]
    attend = context.user_data["attend"]
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    sheet.append_row([name, surname, attend, date])
    await update.message.reply_text(
        "Дякую! 🎉 Твою відповідь збережено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Команда /guests — только для администратора
async def guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Ця команда лише для адміністратора.")
        return
    rows = sheet.get_all_values()[1:]  # пропускаем заголовок
    if not rows:
        await update.message.reply_text("Поки що ніхто не зареєструвався 😅")
        return
    text = "📋 *Список гостей:*\n" + "\n".join(
        [f"{r[0]} {r[1]} — {r[2]} ({r[3]})" for r in rows]
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ----------------- Main -----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_surname)],
            ATTEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_attend)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("guests", guests))

    print("✅ Бот запущено! Тепер можеш писати йому в Telegram.")
    app.run_polling()

if __name__ == "__main__":
    main()
