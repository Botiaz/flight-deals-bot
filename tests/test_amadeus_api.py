"""Unit tests for amadeus_api._parse_flight_offers."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub out external dependencies so tests run without real credentials or
# installed packages.
# ---------------------------------------------------------------------------

# Stub config
config_stub = types.ModuleType("config")
config_stub.AMADEUS_CLIENT_ID = "test_id"
config_stub.AMADEUS_CLIENT_SECRET = "test_secret"
config_stub.AMADEUS_HOSTNAME = "test"
config_stub.PRICES_FILE = "/tmp/test_prices.json"
sys.modules["config"] = config_stub

# Stub amadeus package
amadeus_stub = types.ModuleType("amadeus")


class _ResponseError(Exception):
    def __init__(self, msg="error"):
        self.description = msg
        super().__init__(msg)


amadeus_stub.ResponseError = _ResponseError
amadeus_stub.Client = MagicMock()
sys.modules["amadeus"] = amadeus_stub

# Stub dotenv
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv_stub

import amadeus_api  # noqa: E402  (must come after stubs)


class TestParseFlightOffers(unittest.TestCase):
    """Tests for the internal _parse_flight_offers helper."""

    def _sample_offer(
        self,
        grand_total: str = "150.00",
        currency: str = "EUR",
        carrier: str = "IB",
        origin: str = "MAD",
        destination: str = "LHR",
        departure_at: str = "2024-06-01T08:00:00",
        duration: str = "PT2H15M",
    ) -> dict:
        return {
            "price": {"grandTotal": grand_total, "currency": currency},
            "itineraries": [
                {
                    "duration": duration,
                    "segments": [
                        {
                            "departure": {"iataCode": origin, "at": departure_at},
                            "arrival": {"iataCode": destination, "at": "2024-06-01T10:15:00"},
                            "carrierCode": carrier,
                        }
                    ],
                }
            ],
        }

    def test_single_offer_parsed_correctly(self):
        data = [self._sample_offer()]
        result = amadeus_api._parse_flight_offers(data)
        self.assertEqual(len(result), 1)
        offer = result[0]
        self.assertEqual(offer["price"], "150.00")
        self.assertEqual(offer["currency"], "EUR")
        self.assertEqual(offer["origin"], "MAD")
        self.assertEqual(offer["destination"], "LHR")
        self.assertEqual(offer["departure_date"], "2024-06-01")
        self.assertEqual(offer["carrier"], "IB")
        self.assertEqual(offer["duration"], "PT2H15M")

    def test_multiple_offers(self):
        data = [
            self._sample_offer(grand_total="100.00"),
            self._sample_offer(grand_total="200.00", carrier="BA"),
        ]
        result = amadeus_api._parse_flight_offers(data)
        self.assertEqual(len(result), 2)

    def test_malformed_offer_skipped(self):
        """Offers missing required keys must be silently skipped."""
        good = self._sample_offer()
        bad = {"price": {}}  # missing itineraries
        result = amadeus_api._parse_flight_offers([bad, good])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["carrier"], "IB")

    def test_empty_input(self):
        self.assertEqual(amadeus_api._parse_flight_offers([]), [])


class TestSearchFlights(unittest.TestCase):
    """Tests for search_flights calling the Amadeus client."""

    def _mock_response(self, data):
        resp = MagicMock()
        resp.data = data
        return resp

    def test_returns_parsed_offers(self):
        sample_offer = {
            "price": {"grandTotal": "99.00", "currency": "USD"},
            "itineraries": [
                {
                    "duration": "PT3H",
                    "segments": [
                        {
                            "departure": {"iataCode": "JFK", "at": "2024-07-01T10:00:00"},
                            "arrival": {"iataCode": "LAX", "at": "2024-07-01T13:00:00"},
                            "carrierCode": "AA",
                        }
                    ],
                }
            ],
        }
        mock_client = MagicMock()
        mock_client.shopping.flight_offers_search.get.return_value = self._mock_response([sample_offer])

        with patch("amadeus_api._make_client", return_value=mock_client):
            result = amadeus_api.search_flights("JFK", "LAX", "2024-07-01")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], "99.00")
        self.assertEqual(result[0]["carrier"], "AA")
        mock_client.shopping.flight_offers_search.get.assert_called_once_with(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2024-07-01",
            adults=1,
            max=5,
        )

    def test_origin_normalised_to_uppercase(self):
        mock_client = MagicMock()
        mock_client.shopping.flight_offers_search.get.return_value = self._mock_response([])
        with patch("amadeus_api._make_client", return_value=mock_client):
            amadeus_api.search_flights("jfk", "lax", "2024-07-01")
        call_kwargs = mock_client.shopping.flight_offers_search.get.call_args.kwargs
        self.assertEqual(call_kwargs["originLocationCode"], "JFK")
        self.assertEqual(call_kwargs["destinationLocationCode"], "LAX")


class TestGetCheapestDestinations(unittest.TestCase):
    def test_returns_destinations(self):
        mock_data = [
            {
                "destination": "BCN",
                "departureDate": "2024-08-10",
                "returnDate": "2024-08-17",
                "price": {"total": "80.00", "currency": "EUR"},
            }
        ]
        mock_client = MagicMock()
        mock_client.shopping.flight_destinations.get.return_value = MagicMock(data=mock_data)
        with patch("amadeus_api._make_client", return_value=mock_client):
            result = amadeus_api.get_cheapest_destinations("MAD")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["destination"], "BCN")
        self.assertEqual(result[0]["price"], "80.00")

    def test_respects_max_results(self):
        mock_data = [
            {
                "destination": f"C{i:02d}",
                "departureDate": "2024-09-01",
                "returnDate": "2024-09-08",
                "price": {"total": str(50 + i), "currency": "EUR"},
            }
            for i in range(20)
        ]
        mock_client = MagicMock()
        mock_client.shopping.flight_destinations.get.return_value = MagicMock(data=mock_data)
        with patch("amadeus_api._make_client", return_value=mock_client):
            result = amadeus_api.get_cheapest_destinations("MAD", max_results=5)
        self.assertEqual(len(result), 5)


class TestGetNearbyAirports(unittest.TestCase):
    def test_returns_airports(self):
        mock_data = [
            {
                "iataCode": "LHR",
                "name": "Heathrow",
                "address": {"cityName": "London", "countryName": "United Kingdom"},
                "distance": {"value": 24},
            }
        ]
        mock_client = MagicMock()
        mock_client.reference_data.locations.airports.get.return_value = MagicMock(data=mock_data)
        with patch("amadeus_api._make_client", return_value=mock_client):
            result = amadeus_api.get_nearby_airports(51.5, -0.1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["iata_code"], "LHR")
        self.assertEqual(result[0]["city"], "London")
        self.assertEqual(result[0]["distance_km"], 24)

    def test_empty_response(self):
        mock_client = MagicMock()
        mock_client.reference_data.locations.airports.get.return_value = MagicMock(data=[])
        with patch("amadeus_api._make_client", return_value=mock_client):
            result = amadeus_api.get_nearby_airports(0.0, 0.0)
        self.assertEqual(result, [])


class TestGetCheapestPrice(unittest.TestCase):
    def test_returns_float_price(self):
        sample = {
            "price": {"grandTotal": "123.45", "currency": "EUR"},
            "itineraries": [
                {
                    "duration": "PT1H",
                    "segments": [
                        {
                            "departure": {"iataCode": "FCO", "at": "2024-10-01T06:00:00"},
                            "arrival": {"iataCode": "CDG", "at": "2024-10-01T08:00:00"},
                            "carrierCode": "AZ",
                        }
                    ],
                }
            ],
        }
        mock_client = MagicMock()
        mock_client.shopping.flight_offers_search.get.return_value = MagicMock(data=[sample])
        with patch("amadeus_api._make_client", return_value=mock_client):
            price = amadeus_api.get_cheapest_price("FCO", "CDG", "2024-10-01")
        self.assertAlmostEqual(price, 123.45)

    def test_returns_none_when_no_offers(self):
        mock_client = MagicMock()
        mock_client.shopping.flight_offers_search.get.return_value = MagicMock(data=[])
        with patch("amadeus_api._make_client", return_value=mock_client):
            price = amadeus_api.get_cheapest_price("FCO", "CDG", "2024-10-01")
        self.assertIsNone(price)


if __name__ == "__main__":
    unittest.main()
