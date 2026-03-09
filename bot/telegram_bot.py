from telegram.error import InvalidToken
from telegram.ext import ApplicationBuilder, CommandHandler
from config import TELEGRAM_BOT_TOKEN
from bot.commands import voo


async def _error_handler(update, context):
    print(f"Unhandled error: {context.error}")
    if update and getattr(update, "effective_message", None):
        await update.effective_message.reply_text(
            "Ocorreu um erro interno ao processar sua solicitacao. Tente novamente em alguns segundos."
        )


def _validate_token(token: str | None) -> str:
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN nao foi definido. Configure a variavel no arquivo .env."
        )

    normalized = token.strip()

    # Prevent common .env.example placeholders from being used at runtime.
    placeholder_markers = {
        "your-real-telegram-token",
        "abc",
        "example",
        "your_token_here",
    }
    lowered = normalized.lower()
    if any(marker in lowered for marker in placeholder_markers):
        raise ValueError(
            "TELEGRAM_BOT_TOKEN ainda esta com valor de exemplo. Substitua pelo token real gerado no @BotFather."
        )

    if normalized.count(":") != 1 or " " in normalized:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN parece invalido. Use o formato '123456789:ABCDEF...'."
        )

    return normalized


def start_bot():
    token = _validate_token(TELEGRAM_BOT_TOKEN)

    try:
        app = ApplicationBuilder().token(token).build()
    except InvalidToken as exc:
        raise ValueError(
            "Token do Telegram invalido. Gere um novo token no @BotFather e atualize o .env."
        ) from exc

    app.add_handler(CommandHandler("voo", voo))
    app.add_error_handler(_error_handler)

    print("Bot running...")

    app.run_polling()