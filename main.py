"""Entry point for the Flight Deals Telegram bot.

Run with:
    python main.py

The bot reads credentials from the environment (or a .env file).
Copy .env.example to .env and fill in the values before starting.
"""

from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

import bot_handlers
import config
import price_monitor


logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _send_price_alerts(context) -> None:  # type: ignore[type-arg]
    """Scheduled job: check all monitored routes and send price-drop alerts."""
    alerts = price_monitor.run_all_checks()
    for chat_ids, message in alerts:
        for chat_id in chat_ids:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message)
            except Exception:
                logger.exception("Failed to send price alert to chat %s", chat_id)


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", bot_handlers.start))
    app.add_handler(CommandHandler("search", bot_handlers.search))
    app.add_handler(CommandHandler("cheapest", bot_handlers.cheapest))
    app.add_handler(CommandHandler("nearby", bot_handlers.nearby))
    app.add_handler(CommandHandler("monitor", bot_handlers.monitor))
    app.add_handler(CommandHandler("unmonitor", bot_handlers.unmonitor))
    app.add_handler(CommandHandler("alerts", bot_handlers.alerts))

    # Schedule periodic price-drop checks every hour
    job_queue = app.job_queue
    if job_queue is not None:
        job_queue.run_repeating(_send_price_alerts, interval=3600, first=60)
        logger.info("Price-drop check job scheduled (every 60 minutes).")

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
