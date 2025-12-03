import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from agent import agent, SystemMessage, HumanMessage
from tools.calendar import set_telegram_callback  # For reminders

load_dotenv()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Keep track of last chat_id for sending reminders
last_chat_id = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.message.chat_id
    await update.message.reply_text("Gaia Assistant is running!")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.message.chat_id
    user_msg = update.message.text

    messages = [
        SystemMessage(content="You are a helpful assistant. Use the available tools."),
        HumanMessage(content=user_msg)
    ]
    result = agent.invoke({"messages": messages})
    await update.message.reply_text(result["messages"][-1].content)

# Telegram callback for reminders
async def telegram_callback(msg: str):
    if last_chat_id:
        await app.bot.send_message(last_chat_id, msg)

def main():
    global app
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    # Create Telegram application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    # Set reminder callback for calendar tool
    set_telegram_callback(telegram_callback)

    # Run the bot
    app.run_polling()

if __name__ == "__main__":
    main()
