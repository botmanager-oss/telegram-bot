import os
import json
import asyncio
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)

# Logging
logging.basicConfig(level=logging.INFO)

# Env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Write credentials.json from env
with open("credentials.json", "w") as f:
    f.write(GOOGLE_CREDS_JSON)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Telegram Leads").sheet1

# States
BUDGET, DISTRICT, TIMING, CREDIT, PHONE = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ассалому алайкум! Уй қидиришда сизга ёрдам бераман. Бюджетингизни киритинг (млн сўмда):")
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["budget"] = update.message.text
    await update.message.reply_text("Қандай туманда уй қидиряпсиз?")
    return DISTRICT

async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["district"] = update.message.text
    await update.message.reply_text("Қачонга керак уй? Масалан, 1 ой ичида")
    return TIMING

async def timing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["timing"] = update.message.text
    await update.message.reply_text("Ҳисобда кредит борми ёки нақдми?")
    return CREDIT

async def credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["credit"] = update.message.text
    await update.message.reply_text("Телефон рақамингизни қолдиринг:")
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text

    user = context.user_data
    text = (
        f"📥 ЯНГИ ЛИД:\n\n"
        f"💰 Бюджет: {user['budget']}\n"
        f"📍 Туман: {user['district']}\n"
        f"⏱ Муддат: {user['timing']}\n"
        f"💳 Кредит: {user['credit']}\n"
        f"📞 Телефон: {user['phone']}"
    )

    # Send to group
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)

    # Save to Google Sheet
    sheet.append_row([
        user["budget"], user["district"],
        user["timing"], user["credit"], user["phone"]
    ])

    await update.message.reply_text("Раҳмат! Маълумотлар қабул қилинди.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бекор қилинди.")
    return ConversationHandler.END

# Keep alive server
def keep_alive():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "Bot is alive"

    from threading import Thread
    Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()

# Run bot
if __name__ == "__main__":
    keep_alive()

    async def main():
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
        await app.run_polling()

    asyncio.run(main())
