"""Price-drop monitor backed by a JSON file.

The monitor stores the lowest observed price for each (origin, destination,
departure_date) triple.  When ``check_and_alert`` is called it fetches the
current cheapest price from the Amadeus API and compares it to the stored
value.  If the new price is lower, it updates the stored price and returns
an alert message that the caller (usually the Telegram bot) can forward to
the subscribed chat.
"""

from __future__ import annotations

import json
import os
from typing import Any

import amadeus_api
import config


def _load_prices() -> dict[str, Any]:
    if os.path.exists(config.PRICES_FILE):
        with open(config.PRICES_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _save_prices(prices: dict[str, Any]) -> None:
    with open(config.PRICES_FILE, "w", encoding="utf-8") as fh:
        json.dump(prices, fh, indent=2)


def _route_key(origin: str, destination: str, departure_date: str) -> str:
    return f"{origin.upper()}-{destination.upper()}-{departure_date}"


def add_monitor(
    chat_id: int,
    origin: str,
    destination: str,
    departure_date: str,
    current_price: float | None = None,
) -> str:
    """Register a route to monitor for price drops.

    Args:
        chat_id: Telegram chat ID that will receive alerts.
        origin: Departure airport IATA code.
        destination: Arrival airport IATA code.
        departure_date: Date in ``YYYY-MM-DD`` format.
        current_price: Seed price; fetched from the API when ``None``.

    Returns:
        A human-readable confirmation message.
    """
    prices = _load_prices()
    key = _route_key(origin, destination, departure_date)

    if current_price is None:
        current_price = amadeus_api.get_cheapest_price(origin, destination, departure_date)

    entry: dict[str, Any] = prices.get(key, {"chats": []})
    entry["origin"] = origin.upper()
    entry["destination"] = destination.upper()
    entry["departure_date"] = departure_date
    if current_price is not None:
        entry["last_price"] = current_price
    if chat_id not in entry["chats"]:
        entry["chats"].append(chat_id)
    prices[key] = entry
    _save_prices(prices)

    price_str = f"{current_price:.2f}" if current_price else "unknown"
    return (
        f"✅ Monitoring {origin.upper()} → {destination.upper()} on {departure_date}.\n"
        f"Current price: {price_str}"
    )


def remove_monitor(chat_id: int, origin: str, destination: str, departure_date: str) -> str:
    """Unregister a monitored route for *chat_id*.

    Returns:
        A human-readable confirmation or error message.
    """
    prices = _load_prices()
    key = _route_key(origin, destination, departure_date)

    if key not in prices:
        return f"⚠️ No active monitor found for {origin.upper()} → {destination.upper()} on {departure_date}."

    entry = prices[key]
    if chat_id in entry.get("chats", []):
        entry["chats"].remove(chat_id)
    if not entry["chats"]:
        del prices[key]
    else:
        prices[key] = entry
    _save_prices(prices)
    return f"🗑️ Stopped monitoring {origin.upper()} → {destination.upper()} on {departure_date}."


def list_monitors(chat_id: int) -> list[dict[str, Any]]:
    """Return all monitored routes for *chat_id*."""
    prices = _load_prices()
    results = []
    for entry in prices.values():
        if chat_id in entry.get("chats", []):
            results.append(
                {
                    "origin": entry["origin"],
                    "destination": entry["destination"],
                    "departure_date": entry["departure_date"],
                    "last_price": entry.get("last_price"),
                }
            )
    return results


def check_and_alert(
    origin: str,
    destination: str,
    departure_date: str,
) -> tuple[list[int], str] | None:
    """Check whether the price for a route has dropped.

    Returns:
        A ``(chat_ids, message)`` tuple when a price drop is detected, or
        ``None`` if no drop occurred or the route is not monitored.
    """
    prices = _load_prices()
    key = _route_key(origin, destination, departure_date)
    entry = prices.get(key)
    if not entry:
        return None

    new_price = amadeus_api.get_cheapest_price(origin, destination, departure_date)
    if new_price is None:
        return None

    last_price = entry.get("last_price")
    if last_price is not None and new_price < last_price:
        drop = last_price - new_price
        pct = (drop / last_price) * 100
        entry["last_price"] = new_price
        prices[key] = entry
        _save_prices(prices)
        msg = (
            f"🔔 Price drop alert!\n"
            f"{origin.upper()} → {destination.upper()} on {departure_date}\n"
            f"New price: {new_price:.2f} (was {last_price:.2f}, "
            f"saved {drop:.2f} / {pct:.1f}%)"
        )
        return entry["chats"], msg

    # Update stored price even if no drop, in case price rose
    entry["last_price"] = new_price
    prices[key] = entry
    _save_prices(prices)
    return None


def run_all_checks() -> list[tuple[list[int], str]]:
    """Check every monitored route and collect alerts.

    Returns:
        A list of ``(chat_ids, message)`` tuples for all detected price drops.
    """
    prices = _load_prices()
    alerts = []
    for entry in prices.values():
        result = check_and_alert(
            entry["origin"], entry["destination"], entry["departure_date"]
        )
        if result:
            alerts.append(result)
    return alerts
