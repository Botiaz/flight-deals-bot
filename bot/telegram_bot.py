from telegram.ext import ApplicationBuilder, CommandHandler
from config import TELEGRAM_BOT_TOKEN
from bot.commands import voo


def start_bot():

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("voo", voo))

    print("Bot running...")

    app.run_polling()