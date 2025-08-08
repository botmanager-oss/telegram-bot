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

# --- Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables & Credentials ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID")) if os.getenv("GROUP_CHAT_ID") else None
RESTART_KEYWORD = "♻️ Бошидан бошлаш" # Keyword for the restart button

# Handle Google Credentials stored as a JSON string in environment variables
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
if GOOGLE_CREDS_JSON:
    try:
        # Create a temporary credentials file
        with open("credentials.json", "w") as f:
            f.write(GOOGLE_CREDS_JSON)
    except Exception as e:
        logger.error(f"Failed to write Google credentials to file: {e}")
else:
    logger.warning("GOOGLE_CREDS_JSON environment variable not set.")


# --- Conversation States ---
BUDGET, DISTRICT, TIMING, CREDIT, PHONE = range(5)


# --- Google Sheets Integration ---
def save_to_sheet(data):
    """Saves the collected lead data to a Google Sheet."""
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
        # Ensure all keys exist before creating the row
        row = [
            data.get("phone", "N/A"),
            data.get("budget", "N/A"),
            data.get("district", "N/A"),
            data.get("timing", "N/A"),
            data.get("credit", "N/A"),
            now
        ]
        sheet.append_row(row)
        logger.info("Data saved to Google Sheets successfully.")
    except FileNotFoundError:
        logger.error("credentials.json not found. Cannot connect to Google Sheets.")
    except Exception as e:
        logger.error(f"Error saving to Google Sheets: {e}")


# --- Conversation Steps ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts or restarts the conversation."""
    await update.message.reply_text(
        "🏡 Ассалому алайкум! Менинг исмим Баходир. Тошкентдан квартира қидиряпсизми? "
        "Мен Сизга албатта ёрдам бера оламан.\n\n"
        "Келинг, Сизга аниқ таклиф юборишимиз учун бир нечта саволларга жавоб берсангиз.\n\n"
        "Авваламбор, харид учун бюджетингиз қанча?:",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["💸30 000$ гача"], 
                ["💵 30 000$ – 50 000$"], 
                ["💰 50 000$ – 70 000$"], 
                ["💵 70 000 дан юқори"],
                [RESTART_KEYWORD]
            ],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the budget selection and asks for the district."""
    context.user_data["budget"] = update.message.text
    await update.message.reply_text(
        "Зўр! Энди, 📍 қайси тумандан хохлайсиз?",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["🏙 Сергели"], ["🏢 Мирзо Улуғбек"], 
                ["🏠 Чилонзор"], ["🌆 Яшнобод"], 
                ["🌏 тумани аниқ эмас"], [RESTART_KEYWORD]
            ],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return DISTRICT

async def district(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the district selection and asks for the timing."""
    context.user_data["district"] = update.message.text
    await update.message.reply_text(
        "Хўп!🕒 Қачон харид қилишни режалаштиряпсиз?",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["⏱ 1 ой ичида"], 
                ["🕓 2-3 ойда"], 
                ["👀 Шунчаки кўрияпман"],
                [RESTART_KEYWORD]
            ],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return TIMING

async def timing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the timing selection and asks about credit."""
    context.user_data["timing"] = update.message.text
    await update.message.reply_text(
        "🏦 Квартирани кредит орқали олишни ўйлаяпсизми?",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["✅ Ҳа"], 
                ["❌ Йўқ"], 
                ["🤔 Ҳали билмайман"],
                [RESTART_KEYWORD]
            ],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CREDIT

async def credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the credit selection and asks for the phone number."""
    context.user_data["credit"] = update.message.text
    await update.message.reply_text(
        "Яхши, охирги қадам — Сиз билан боғланишимиз учун илтимос 📞телефон рақамингизни ёзинг:",
        reply_markup=ReplyKeyboardMarkup([[RESTART_KEYWORD]], one_time_keyboard=True, resize_keyboard=True)
    )
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the phone number, saves data, sends notification, and ends the conversation."""
    context.user_data["phone"] = update.message.text
    
    # Create a summary message
    summary = (
        f"📞 Телефон: {context.user_data.get('phone', 'N/A')}\n"
        f"💰 Бюджет: {context.user_data.get('budget', 'N/A')}\n"
        f"📍 Туман: {context.user_data.get('district', 'N/A')}\n"
        f"🕒 Муддат: {context.user_data.get('timing', 'N/A')}\n"
        f"🏦 Кредит: {context.user_data.get('credit', 'N/A')}"
    )

    await update.message.reply_text(f"✅ Рахмат! Маълумотлар қабул қилинди. Энг мос таклифларни тайёрлаб, тез орада Сиз билан боғланамиз.\n\n{summary}")

    # Save data to Google Sheet
    save_to_sheet(context.user_data)

    # Send admin notification to group chat if ID is provided
    if GROUP_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=f"📥 Янги лид:\n\n{summary}")
            logger.info("Admin notification sent successfully.")
        except Exception as e:
            logger.error(f"Error sending message to group: {e}")

    # End the conversation
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the conversation."""
    await update.message.reply_text("Jarayon bekor qilindi.")
    context.user_data.clear()
    return ConversationHandler.END


# --- Main Bot Function ---
def main():
    """Main function to configure and run the bot."""
    if not BOT_TOKEN:
        logger.critical("FATAL: BOT_TOKEN environment variable not found.")
        return

    logger.info("Starting Telegram Bot...")

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Define a filter for the restart button
    restart_filter = filters.Text([RESTART_KEYWORD])

    # Create the ConversationHandler with restart functionality
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("restart", start)
        ],
        states={
            BUDGET: [MessageHandler(restart_filter, start), MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
            DISTRICT: [MessageHandler(restart_filter, start), MessageHandler(filters.TEXT & ~filters.COMMAND, district)],
            TIMING: [MessageHandler(restart_filter, start), MessageHandler(filters.TEXT & ~filters.COMMAND, timing)],
            CREDIT: [MessageHandler(restart_filter, start), MessageHandler(filters.TEXT & ~filters.COMMAND, credit)],
            PHONE: [MessageHandler(restart_filter, start), MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add the conversation handler to the application
    application.add_handler(conv_handler)

    logger.info("Bot is ready and polling for messages...")

    # Start the bot
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
