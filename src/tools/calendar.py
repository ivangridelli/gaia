from langchain.tools import tool
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from dateutil import parser
import asyncio
import pytz
import logging

logger = logging.getLogger(__name__)

# Scheduler setup
scheduler = BackgroundScheduler(timezone=pytz.UTC)
scheduler.start()

# Global state
telegram_callback = None
main_event_loop = None
reminders = {}


def set_telegram_callback(callback):
    """Register callback for sending reminders"""
    global telegram_callback, main_event_loop
    telegram_callback = callback
    # Capture the main event loop when callback is registered
    try:
        main_event_loop = asyncio.get_running_loop()
    except RuntimeError:
        main_event_loop = asyncio.get_event_loop()


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """Get current time in specified timezone (e.g., 'America/New_York')"""
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    except pytz.exceptions.UnknownTimeZoneError:
        return f"Unknown timezone '{timezone}'"


@tool
def set_reminder(text: str, when: str, timezone: str = "UTC") -> str:
    """
    Set a reminder. Examples: '5m', 'in 2 hours', 'tomorrow at 3pm', '2024-12-25 10:00'
    """
    if not telegram_callback:
        return "❌ Bot not ready"

    try:
        tz = pytz.timezone(timezone)
        run_time = _parse_time(when, tz)

        if run_time <= datetime.now(tz):
            return "❌ Time must be in the future"

        reminder_id = f"r_{len(reminders) + 1}"

        def send_reminder():
            try:
                # Use the captured main event loop
                if main_event_loop and main_event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(telegram_callback(f"⏰ {text}"), main_event_loop)
                else:
                    logger.error("Main event loop not available")
                reminders.pop(reminder_id, None)
            except Exception as e:
                logger.error(f"Error sending reminder: {e}")

        scheduler.add_job(send_reminder, DateTrigger(run_date=run_time), id=reminder_id)
        reminders[reminder_id] = {"text": text, "time": run_time, "type": "once"}

        time_until = run_time - datetime.now(tz)
        return f"✅ Reminder set for {run_time.strftime('%b %d at %I:%M %p')} ({_format_delta(time_until)})"

    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Failed to set reminder"


@tool
def set_recurring_reminder(text: str, pattern: str, timezone: str = "UTC") -> str:
    """
    Set recurring reminder. Examples: 'daily at 9am', 'every monday at 10am', 'every hour'
    """
    if not telegram_callback:
        return "❌ Bot not ready"

    try:
        tz = pytz.timezone(timezone)
        trigger = _parse_pattern(pattern, tz)
        reminder_id = f"rec_{len(reminders) + 1}"

        def send_reminder():
            try:
                # Use the captured main event loop
                if main_event_loop and main_event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(telegram_callback(f"🔔 {text}"), main_event_loop)
                else:
                    logger.error("Main event loop not available")
            except Exception as e:
                logger.error(f"Error sending recurring reminder: {e}")

        job = scheduler.add_job(send_reminder, trigger, id=reminder_id)
        reminders[reminder_id] = {"text": text, "pattern": pattern, "type": "recurring"}

        return f"✅ Recurring: {pattern}\n⏰ Next: {job.next_run_time.strftime('%b %d at %I:%M %p')}"

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Invalid pattern"


@tool
def list_reminders() -> str:
    """List all active reminders"""
    if not reminders:
        return "📭 No reminders"

    lines = ["📋 Active Reminders:\n"]
    jobs = scheduler.get_jobs()

    for job in jobs:
        if job.id in reminders:
            info = reminders[job.id]
            next_run = job.next_run_time

            if info["type"] == "recurring":
                lines.append(f"🔔 {job.id}: {info['text']}")
                lines.append(f"   Pattern: {info['pattern']}")
            else:
                lines.append(f"⏰ {job.id}: {info['text']}")
                lines.append(f"   Time: {info['time'].strftime('%b %d at %I:%M %p')}")

            if next_run:
                delta = next_run - datetime.now(pytz.UTC)
                lines.append(f"   Next: {_format_delta(delta)}\n")

    return "\n".join(lines)


@tool
def cancel_reminder(reminder_id: str) -> str:
    """Cancel a reminder by ID (e.g., 'r_1' or 'rec_2')"""
    if reminder_id not in reminders:
        return f"❌ '{reminder_id}' not found"

    try:
        scheduler.remove_job(reminder_id)
        text = reminders.pop(reminder_id)["text"]
        return f"✅ Cancelled: {text}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to cancel"


@tool
def clear_all_reminders() -> str:
    """Clear all reminders"""
    count = len(reminders)
    scheduler.remove_all_jobs()
    reminders.clear()
    return f"✅ Cleared {count} reminder(s)"


# Helpers

def _parse_time(when: str, tz: pytz.timezone) -> datetime:
    """Parse time expression into datetime"""
    when = when.lower().strip()
    now = datetime.now(tz)

    # Remove 'in' prefix
    if when.startswith("in "):
        when = when[3:].strip()

    # Shorthand: 5m, 30s, 2h, 3d
    if len(when) > 1 and when[-1] in 'smhd':
        unit = when[-1]
        try:
            val = float(when[:-1])
            delta = {
                's': timedelta(seconds=val),
                'm': timedelta(minutes=val),
                'h': timedelta(hours=val),
                'd': timedelta(days=val)
            }
            return now + delta[unit]
        except ValueError:
            pass

    # "5 minutes", "30 seconds", "2 hours"
    parts = when.split()
    if len(parts) >= 2:
        try:
            val = float(parts[0])
            unit = parts[1].lower()

            if unit in ['second', 'seconds', 'sec', 'secs']:
                return now + timedelta(seconds=val)
            if unit in ['minute', 'minutes', 'min', 'mins']:
                return now + timedelta(minutes=val)
            if unit in ['hour', 'hours', 'hr', 'hrs']:
                return now + timedelta(hours=val)
            if unit in ['day', 'days']:
                return now + timedelta(days=val)
            if unit in ['week', 'weeks']:
                return now + timedelta(weeks=val)
        except ValueError:
            pass

    # Natural language
    try:
        parsed = parser.parse(when, fuzzy=True)
        if parsed.tzinfo is None:
            parsed = tz.localize(parsed)
        return parsed
    except:
        raise ValueError("Try: '30s', '5m', 'in 2 hours', 'tomorrow at 3pm', or '2024-12-25 10:00'")


def _parse_pattern(pattern: str, tz: pytz.timezone) -> CronTrigger:
    """Parse recurring pattern into CronTrigger"""
    pattern = pattern.lower().strip()

    # Daily
    if "daily" in pattern or "every day" in pattern:
        hour = 9
        if "at" in pattern:
            hour = parser.parse(pattern.split("at")[1]).hour
        return CronTrigger(hour=hour, minute=0, timezone=tz)

    # Weekly
    if "monday" in pattern or "weekly" in pattern:
        hour = 9
        if "at" in pattern:
            hour = parser.parse(pattern.split("at")[1]).hour
        return CronTrigger(day_of_week='mon', hour=hour, minute=0, timezone=tz)

    # Hourly
    if "hour" in pattern:
        return CronTrigger(minute=0, timezone=tz)

    # Cron (5 parts)
    parts = pattern.split()
    if len(parts) == 5:
        return CronTrigger.from_crontab(pattern, timezone=tz)

    raise ValueError("Try: 'daily at 9am', 'every monday at 10am', or 'every hour'")


def _format_delta(td: timedelta) -> str:
    """Format time difference into readable string"""
    secs = int(td.total_seconds())

    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        hrs = secs // 3600
        mins = (secs % 3600) // 60
        return f"{hrs}h {mins}m"

    days = secs // 86400
    hrs = (secs % 86400) // 3600
    return f"{days}d {hrs}h"