import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load sensitive values from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID")) if os.getenv("GROUP_CHAT_ID") else None

# Handle Google Credentials stored as JSON string
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
if GOOGLE_CREDS_JSON:
    with open("credentials.json", "w") as f:
        f.write(GOOGLE_CREDS_JSON)

# Conversation states
BUDGET, DISTRICT, TIMING, CREDIT, PHONE = range(5)

def save_to_sheet(data):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Telegram Leads").sheet1

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            data.get("phone", ""),
            data.get("budget", ""),
            data.get("district", ""),
            data.get("timing", ""),
            data.get("credit", ""), 
            now
        ]
        sheet.append_row(row)
        logger.info("Data saved to Google Sheets successfully")
    except Exception as e:
        logger.error(f"Error saving to Google Sheets: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏡 Ассалому алайкум! Менинг исмим Баходир. Тошкентдан квартира қидиряпсизми? Мен Сизга албатта ёрдам бера оламан.\nКелинг, Сизга аниқ таклиф юборишимиз учун бир нечта саволларга жавоб берсангиз\nАвваламбор, харид учун бюджетингиз қанча?:",
        reply_markup=ReplyKeyboardMarkup(
            [["💸30 000$ гача"], ["💵 30 000$ – 50 000$"], ["💰 50 000$ – 70 000$"], ["💵 70 000 дан юқори"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["budget"] = update.message.text
    await update.message.reply_text(
        "Зўр! Энди, 📍 қайси тумандан хохлайсиз?",
        reply_markup=ReplyKeyboardMarkup(
            [["🏙 Сергели"], ["🏢 Мирзо Улуғбек"], ["🏠 Чилонзор"], ["🌆 Яшнобод"], ["🌏 тумани аниқ эмас"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return DISTRICT

async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["district"] = update.message.text
    await update.message.reply_text(
        "Хўп!🕒 Қачон харид қилишни режалаштиряпсиз?",
        reply_markup=ReplyKeyboardMarkup(
            [["⏱ 1 ой ичида"], ["🕓 2-3 ойда"], ["👀 Шунчаки кўрияпман"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return TIMING

async def timing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["timing"] = update.message.text
    await update.message.reply_text(
        "🏦 Квартирани кредит орқали олишни ўйлаяпсизми?",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Ҳа"], ["❌ Йўқ"], ["🤔 Ҳали билмайман"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CREDIT

async def credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["credit"] = update.message.text
    await update.message.reply_text("Яхши, охирги қадам — Сиз билан боғланишимиз учун илтимос телефон рақамингизни ёзинг:")
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    summary = (f"📞 Телефон: {context.user_data['phone']}\n"
               f"💰 Бюджет: {context.user_data['budget']}\n"
               f"📍 Туман: {context.user_data['district']}\n"
               f"🕒 Муддат: {context.user_data['timing']}\n"
               f"🏦 Кредит: {context.user_data['credit']}")
    
    await update.message.reply_text("✅ Ma'lumotlaringiz qabul qilindi!\n\n" + summary)

    # Save to Google Sheet
    save_to_sheet(context.user_data)

    # Send admin notification to group chat
    if GROUP_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text="📥 Yangi lead:\n\n" + summary)
            logger.info("Message sent to group successfully")
        except Exception as e:
            logger.error(f"Error sending message to group: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Jarayon bekor qilindi.")
    return ConversationHandler.END

def main():
    """Main function to run the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    logger.info("Starting Telegram Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Create conversation handler
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

    # Add handlers
    application.add_handler(conv_handler)
    
    logger.info("Bot is ready and polling for messages...")
    
    # Start the bot with polling
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
