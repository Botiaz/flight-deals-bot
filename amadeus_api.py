"""Amadeus API wrapper for flight data retrieval."""

from __future__ import annotations

from typing import Any

from amadeus import Client, ResponseError

import config


def _make_client() -> Client:
    return Client(
        client_id=config.AMADEUS_CLIENT_ID,
        client_secret=config.AMADEUS_CLIENT_SECRET,
        hostname=config.AMADEUS_HOSTNAME,
    )


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search for one-way flight offers between two airports.

    Args:
        origin: IATA code of the departure airport (e.g. ``"MAD"``).
        destination: IATA code of the arrival airport (e.g. ``"LHR"``).
        departure_date: Date in ``YYYY-MM-DD`` format.
        adults: Number of adult passengers.
        max_results: Maximum number of offers to return.

    Returns:
        A list of offer dictionaries with keys ``price``, ``currency``,
        ``origin``, ``destination``, ``departure_date``, ``carrier``,
        and ``duration``.

    Raises:
        ResponseError: When the Amadeus API returns an error response.
    """
    client = _make_client()
    response = client.shopping.flight_offers_search.get(
        originLocationCode=origin.upper(),
        destinationLocationCode=destination.upper(),
        departureDate=departure_date,
        adults=adults,
        max=max_results,
    )
    return _parse_flight_offers(response.data)


def get_cheapest_destinations(origin: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Return the cheapest flight destinations from *origin*.

    Args:
        origin: IATA city/airport code of the departure location.
        max_results: Maximum number of destinations to return.

    Returns:
        A list of destination dictionaries with keys ``destination``,
        ``departure_date``, ``return_date``, ``price``, and ``currency``.

    Raises:
        ResponseError: When the Amadeus API returns an error response.
    """
    client = _make_client()
    response = client.shopping.flight_destinations.get(
        origin=origin.upper(),
        maxPrice=9999,
    )
    results = []
    for item in response.data[:max_results]:
        results.append(
            {
                "destination": item.get("destination", ""),
                "departure_date": item.get("departureDate", ""),
                "return_date": item.get("returnDate", ""),
                "price": item.get("price", {}).get("total", "N/A"),
                "currency": item.get("price", {}).get("currency", ""),
            }
        )
    return results


def get_nearby_airports(latitude: float, longitude: float, radius: int = 500) -> list[dict[str, Any]]:
    """Return airports near the given coordinates.

    Args:
        latitude: Decimal latitude of the reference point.
        longitude: Decimal longitude of the reference point.
        radius: Search radius in kilometres (max 500).

    Returns:
        A list of airport dictionaries with keys ``iata_code``, ``name``,
        ``city``, ``country``, and ``distance_km``.

    Raises:
        ResponseError: When the Amadeus API returns an error response.
    """
    client = _make_client()
    response = client.reference_data.locations.airports.get(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
    )
    results = []
    for item in response.data:
        results.append(
            {
                "iata_code": item.get("iataCode", ""),
                "name": item.get("name", ""),
                "city": item.get("address", {}).get("cityName", ""),
                "country": item.get("address", {}).get("countryName", ""),
                "distance_km": item.get("distance", {}).get("value", 0),
            }
        )
    return results


def get_cheapest_price(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
) -> float | None:
    """Return the cheapest available price for the given route and date.

    Returns ``None`` if no offers are found.
    """
    offers = search_flights(origin, destination, departure_date, adults=adults, max_results=1)
    if not offers:
        return None
    try:
        return float(offers[0]["price"])
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_flight_offers(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for offer in data:
        try:
            price = offer["price"]["grandTotal"]
            currency = offer["price"]["currency"]
            itinerary = offer["itineraries"][0]
            segment = itinerary["segments"][0]
            origin_code = segment["departure"]["iataCode"]
            destination_code = segment["arrival"]["iataCode"]
            departure = segment["departure"]["at"][:10]
            carrier = segment["carrierCode"]
            duration = itinerary["duration"]
            results.append(
                {
                    "price": price,
                    "currency": currency,
                    "origin": origin_code,
                    "destination": destination_code,
                    "departure_date": departure,
                    "carrier": carrier,
                    "duration": duration,
                }
            )
        except (KeyError, IndexError):
            continue
    return results
