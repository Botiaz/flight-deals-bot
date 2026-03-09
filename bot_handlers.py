"""Telegram bot command handlers.

Available commands
------------------
/start          – Welcome message and usage summary
/search         – Search flights: /search <origin> <dest> <date> [adults]
/cheapest       – Cheapest destinations from a city: /cheapest <origin>
/nearby         – Airports near a location: /nearby <lat> <lon> [radius_km]
/monitor        – Start price-drop monitoring: /monitor <origin> <dest> <date>
/unmonitor      – Stop monitoring: /unmonitor <origin> <dest> <date>
/alerts         – List your active monitors
"""

from __future__ import annotations

import logging

from amadeus import ResponseError
from telegram import Update
from telegram.ext import ContextTypes

import amadeus_api
import price_monitor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USAGE = {
    "search": "/search <origin> <destination> <date YYYY-MM-DD> [adults]",
    "cheapest": "/cheapest <origin>",
    "nearby": "/nearby <latitude> <longitude> [radius_km]",
    "monitor": "/monitor <origin> <destination> <date YYYY-MM-DD>",
    "unmonitor": "/unmonitor <origin> <destination> <date YYYY-MM-DD>",
}


def _error_msg(cmd: str) -> str:
    return f"⚠️ Usage: {_USAGE[cmd]}"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    text = (
        "✈️ *Flight Deals Bot*\n\n"
        "I can help you find cheap flights and alert you when prices drop.\n\n"
        "*Commands:*\n"
        f"`{_USAGE['search']}`\n"
        f"`{_USAGE['cheapest']}`\n"
        f"`{_USAGE['nearby']}`\n"
        f"`{_USAGE['monitor']}`\n"
        f"`{_USAGE['unmonitor']}`\n"
        "`/alerts` – List your active price monitors\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /search command.

    Usage: /search <origin> <destination> <date YYYY-MM-DD> [adults]
    """
    args = context.args or []
    if len(args) < 3:
        await update.message.reply_text(_error_msg("search"))
        return

    origin, destination, departure_date = args[0], args[1], args[2]
    adults = 1
    if len(args) >= 4:
        try:
            adults = int(args[3])
        except ValueError:
            await update.message.reply_text("⚠️ adults must be a number.")
            return

    await update.message.reply_text(
        f"🔍 Searching flights {origin.upper()} → {destination.upper()} on {departure_date}…"
    )

    try:
        offers = amadeus_api.search_flights(origin, destination, departure_date, adults=adults)
    except ResponseError as exc:
        logger.exception("Amadeus API error in /search")
        await update.message.reply_text(f"❌ API error: {exc.description}")
        return

    if not offers:
        await update.message.reply_text("No flights found for your search.")
        return

    lines = [f"✈️ *Flights {origin.upper()} → {destination.upper()} on {departure_date}*\n"]
    for i, offer in enumerate(offers, 1):
        lines.append(
            f"{i}. Carrier: {offer['carrier']} | "
            f"{offer['price']} {offer['currency']} | "
            f"Duration: {offer['duration']}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cheapest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /cheapest command.

    Usage: /cheapest <origin>
    """
    args = context.args or []
    if not args:
        await update.message.reply_text(_error_msg("cheapest"))
        return

    origin = args[0]
    await update.message.reply_text(f"🔍 Finding cheapest destinations from {origin.upper()}…")

    try:
        destinations = amadeus_api.get_cheapest_destinations(origin)
    except ResponseError as exc:
        logger.exception("Amadeus API error in /cheapest")
        await update.message.reply_text(f"❌ API error: {exc.description}")
        return

    if not destinations:
        await update.message.reply_text("No destinations found.")
        return

    lines = [f"💸 *Cheapest destinations from {origin.upper()}*\n"]
    for i, dest in enumerate(destinations, 1):
        lines.append(
            f"{i}. {dest['destination']} – {dest['price']} {dest['currency']} "
            f"(depart {dest['departure_date']})"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def nearby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /nearby command.

    Usage: /nearby <latitude> <longitude> [radius_km]
    """
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(_error_msg("nearby"))
        return

    try:
        lat = float(args[0])
        lon = float(args[1])
    except ValueError:
        await update.message.reply_text("⚠️ latitude and longitude must be numbers.")
        return

    radius = 500
    if len(args) >= 3:
        try:
            radius = int(args[2])
        except ValueError:
            await update.message.reply_text("⚠️ radius must be a number.")
            return

    await update.message.reply_text(f"🔍 Looking for airports near ({lat}, {lon})…")

    try:
        airports = amadeus_api.get_nearby_airports(lat, lon, radius)
    except ResponseError as exc:
        logger.exception("Amadeus API error in /nearby")
        await update.message.reply_text(f"❌ API error: {exc.description}")
        return

    if not airports:
        await update.message.reply_text("No airports found near that location.")
        return

    lines = [f"🛫 *Airports near ({lat}, {lon})*\n"]
    for i, ap in enumerate(airports, 1):
        lines.append(
            f"{i}. [{ap['iata_code']}] {ap['name']}, {ap['city']}, {ap['country']} "
            f"– {ap['distance_km']} km"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /monitor command.

    Usage: /monitor <origin> <destination> <date YYYY-MM-DD>
    """
    args = context.args or []
    if len(args) < 3:
        await update.message.reply_text(_error_msg("monitor"))
        return

    origin, destination, departure_date = args[0], args[1], args[2]
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"⏳ Setting up monitor for {origin.upper()} → {destination.upper()} on {departure_date}…"
    )

    try:
        msg = price_monitor.add_monitor(chat_id, origin, destination, departure_date)
    except ResponseError as exc:
        logger.exception("Amadeus API error in /monitor")
        await update.message.reply_text(f"❌ API error: {exc.description}")
        return

    await update.message.reply_text(msg)


async def unmonitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /unmonitor command.

    Usage: /unmonitor <origin> <destination> <date YYYY-MM-DD>
    """
    args = context.args or []
    if len(args) < 3:
        await update.message.reply_text(_error_msg("unmonitor"))
        return

    origin, destination, departure_date = args[0], args[1], args[2]
    chat_id = update.effective_chat.id
    msg = price_monitor.remove_monitor(chat_id, origin, destination, departure_date)
    await update.message.reply_text(msg)


async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /alerts command – list active price monitors."""
    chat_id = update.effective_chat.id
    monitors = price_monitor.list_monitors(chat_id)

    if not monitors:
        await update.message.reply_text("You have no active price monitors. Use /monitor to add one.")
        return

    lines = ["📋 *Your active monitors:*\n"]
    for i, m in enumerate(monitors, 1):
        price_str = f"{m['last_price']:.2f}" if m["last_price"] is not None else "unknown"
        lines.append(
            f"{i}. {m['origin']} → {m['destination']} on {m['departure_date']} "
            f"(last price: {price_str})"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
