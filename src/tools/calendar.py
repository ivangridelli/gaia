from langchain.tools import tool
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import asyncio

scheduler = BackgroundScheduler()
scheduler.start()

# Keep a reference to Telegram callback
telegram_callback = None


def set_telegram_callback(callback):
    global telegram_callback
    telegram_callback = callback


@tool
def set_reminder(text: str, minutes: float) -> str:
    """
    Schedule a reminder to be sent in X minutes.

    Args:
        text: Text of the reminder
        minutes: Minutes until reminder

    Returns:
        Confirmation string
    """
    if telegram_callback is None:
        return "Telegram callback not set. Reminder cannot be scheduled."

    run_time = datetime.now() + timedelta(minutes=float(minutes))

    def job():
        asyncio.create_task(telegram_callback(f"⏰ Reminder: {text}"))

    scheduler.add_job(job, trigger=DateTrigger(run_date=run_time))
    return f"Reminder set for {minutes} minute(s) from now."
