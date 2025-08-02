
import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from keep_alive import keep_alive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

keep_alive()

# Load secrets from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not BOT_TOKEN or not GROUP_CHAT_ID or not GOOGLE_CREDS_JSON:
    raise ValueError("Missing required environment variables. Please set BOT_TOKEN, GROUP_CHAT_ID, and GOOGLE_CREDS_JSON in Secrets.")

BUDGET, DISTRICT, TIMING, CREDIT, PHONE = range(5)

# Initialize Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Telegram Leads").sheet1

def save_to_sheet(data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        data.get("phone", ""),
        data.get("budget", ""),
        data.get("district", ""),
        data.get("timing", ""),
        data.get("credit", ""), now
    ]
    sheet.append_row(row)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏡 Ассалому алайкум! Менинг исмим Баходир. Тошкентдан квартира қидиряпсизми? Мен Сизга албатта ёрдам бера оламан.\nКелинг, Сизга аниқ таклиф юборишимиз учун бир нечта саволларга жавоб берсангиз.\n\nАвваламбор, харид учун бюджетингиз қанча?:",
        reply_markup=ReplyKeyboardMarkup(
            [["💸30 000$ гача"], ["💵 30 000$ – 50 000$"],
             ["💰 50 000$ – 70 000$"], ["💵 70 000 дан юқори"]],
            one_time_keyboard=True,
            resize_keyboard=True))
    return BUDGET


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["budget"] = update.message.text
    await update.message.reply_text(
        "Зўр! Энди, 📍 қайси тумандан хохлайсиз?",
        reply_markup=ReplyKeyboardMarkup(
            [["🏙 Сергели"], ["🏢 Мирзо Улуғбек"], ["🏠 Чилонзор"], ["🌆 Яшнобод"],
             ["🌏 тумани аниқ эмас"]],
            one_time_keyboard=True,
            resize_keyboard=True))
    return DISTRICT


async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["district"] = update.message.text
    await update.message.reply_text(
        "Хўп!🕒 Қачон харид қилишни режалаштиряпсиз?",
        reply_markup=ReplyKeyboardMarkup(
            [["⏱ 1 ой ичида"], ["🕓 2-3 ойда"], ["👀 Шунчаки кўрияпман"]],
            one_time_keyboard=True,
            resize_keyboard=True))
    return TIMING


async def timing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["timing"] = update.message.text
    await update.message.reply_text(
        "🏦 Квартирани кредит орқали олишни ўйлаяпсизми?",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Ҳа"], ["❌ Йўқ"], ["🤔 Ҳали билмайман"]],
            one_time_keyboard=True,
            resize_keyboard=True))
    return CREDIT


async def credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["credit"] = update.message.text
    await update.message.reply_text(
        "Яхши, охирги қадам — Сиз билан боғланишимиз учун илтимос телефон рақамингизни ёзинг:"
    )
    return PHONE


async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    summary = (f"📞 Телефон: {context.user_data['phone']}\n"
               f"💰 Бюджет: {context.user_data['budget']}\n"
               f"📍 Туман: {context.user_data['district']}\n"
               f"🕒 Муддат: {context.user_data['timing']}\n"
               f"🏦 Кредит: {context.user_data['credit']}")
    await update.message.reply_text(
        "✅ Рахмат! Маълумотлар қабул қилинди. Энг мос таклифларни тайёрлаб, тез орада Сиз билан боғланамиз.\n\n"
        + summary)

    save_to_sheet(context.user_data)

    await context.bot.send_message(chat_id=GROUP_CHAT_ID,
                                   text="📥 Yangi lead:\n\n" + summary)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Жараён бекор қилинди.")
    return ConversationHandler.END


app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
        DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district)],
        TIMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, timing)],
        CREDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, credit)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)
app.run_polling()
