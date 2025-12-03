import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from agent import agent, SystemMessage, HumanMessage
from tools.calendar import set_telegram_callback
import traceback

load_dotenv()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Global app instance
app = None
last_chat_id = None
log_messages = []


async def telegram_callback(msg: str):
    if last_chat_id and app:
        await app.bot.send_message(last_chat_id, msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.message.chat_id
    log_messages.append(f"Start command from chat_id {last_chat_id}")
    await update.message.reply_text("Gaia Assistant is running!")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.message.chat_id
    user_msg = update.message.text
    log_messages.append(f"Received message from {last_chat_id}: {user_msg}")
    try:
        messages = [
            SystemMessage(content="You are a helpful assistant. Use the available tools."),
            HumanMessage(content=user_msg)
        ]
        result = agent.invoke({"messages": messages})
        reply = result["messages"][-1].content
        log_messages.append(f"Reply sent: {reply}")
        await update.message.reply_text(reply)
    except Exception as e:
        tb = traceback.format_exc()
        log_messages.append(f"Error processing message:\n{tb}")
        await update.message.reply_text(f"An error occurred:\n{str(e)}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    log_messages.append(f"Status requested by {chat_id}")
    recent_logs = "\n".join(log_messages[-20:])
    await update.message.reply_text(f"Bot Status:\nLast chat_id: {last_chat_id}\nRecent logs:\n{recent_logs}")


def main():
    global app
    try:
        if not BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

        print("Starting Telegram bot...")
        print(f"Bot token loaded: {BOT_TOKEN[:10]}...")

        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
        app.add_handler(CommandHandler("status", status))

        set_telegram_callback(telegram_callback)

        print("Bot is now polling for messages...")
        app.run_polling()

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()