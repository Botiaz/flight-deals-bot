"""Unit tests for price_monitor module."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stubs for external dependencies
# ---------------------------------------------------------------------------

amadeus_stub = types.ModuleType("amadeus")


class _ResponseError(Exception):
    def __init__(self, msg="error"):
        self.description = msg
        super().__init__(msg)


amadeus_stub.ResponseError = _ResponseError
amadeus_stub.Client = MagicMock()
sys.modules["amadeus"] = amadeus_stub

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv_stub

# Use a temporary file for config.PRICES_FILE during tests
_tmp_fd, _tmp_prices_file = tempfile.mkstemp(suffix=".json", prefix="test_prices_")
os.close(_tmp_fd)

config_stub = types.ModuleType("config")
config_stub.AMADEUS_CLIENT_ID = "test_id"
config_stub.AMADEUS_CLIENT_SECRET = "test_secret"
config_stub.AMADEUS_HOSTNAME = "test"
config_stub.PRICES_FILE = _tmp_prices_file
sys.modules["config"] = config_stub

import price_monitor  # noqa: E402


class TestPriceMonitor(unittest.TestCase):

    def setUp(self):
        # Start each test with an empty prices file
        if os.path.exists(_tmp_prices_file):
            os.remove(_tmp_prices_file)

    def tearDown(self):
        if os.path.exists(_tmp_prices_file):
            os.remove(_tmp_prices_file)

    # ------------------------------------------------------------------
    # add_monitor
    # ------------------------------------------------------------------

    def test_add_monitor_creates_entry(self):
        with patch("amadeus_api.get_cheapest_price", return_value=200.0):
            msg = price_monitor.add_monitor(111, "MAD", "LHR", "2024-06-01")
        self.assertIn("MAD", msg)
        self.assertIn("LHR", msg)
        self.assertIn("200.00", msg)

        monitors = price_monitor.list_monitors(111)
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["origin"], "MAD")
        self.assertEqual(monitors[0]["last_price"], 200.0)

    def test_add_monitor_accepts_provided_price(self):
        msg = price_monitor.add_monitor(222, "JFK", "LAX", "2024-07-01", current_price=150.0)
        self.assertIn("150.00", msg)

    def test_add_monitor_deduplicates_chat_id(self):
        price_monitor.add_monitor(333, "FRA", "CDG", "2024-08-01", current_price=80.0)
        price_monitor.add_monitor(333, "FRA", "CDG", "2024-08-01", current_price=80.0)
        with open(_tmp_prices_file) as fh:
            data = json.load(fh)
        key = "FRA-CDG-2024-08-01"
        self.assertEqual(data[key]["chats"].count(333), 1)

    # ------------------------------------------------------------------
    # remove_monitor
    # ------------------------------------------------------------------

    def test_remove_monitor_removes_entry(self):
        price_monitor.add_monitor(444, "BCN", "FCO", "2024-09-01", current_price=60.0)
        msg = price_monitor.remove_monitor(444, "BCN", "FCO", "2024-09-01")
        self.assertIn("Stopped", msg)
        self.assertEqual(price_monitor.list_monitors(444), [])

    def test_remove_monitor_unknown_route(self):
        msg = price_monitor.remove_monitor(555, "XYZ", "ABC", "2024-01-01")
        self.assertIn("No active monitor", msg)

    def test_remove_monitor_keeps_other_chats(self):
        price_monitor.add_monitor(10, "LIS", "OPO", "2024-10-01", current_price=30.0)
        price_monitor.add_monitor(20, "LIS", "OPO", "2024-10-01", current_price=30.0)
        price_monitor.remove_monitor(10, "LIS", "OPO", "2024-10-01")
        with open(_tmp_prices_file) as fh:
            data = json.load(fh)
        key = "LIS-OPO-2024-10-01"
        self.assertIn(key, data, "Entry should remain because chat 20 still monitors it")
        self.assertNotIn(10, data[key]["chats"])
        self.assertIn(20, data[key]["chats"])

    # ------------------------------------------------------------------
    # list_monitors
    # ------------------------------------------------------------------

    def test_list_monitors_empty(self):
        self.assertEqual(price_monitor.list_monitors(999), [])

    def test_list_monitors_multiple_routes(self):
        price_monitor.add_monitor(100, "MAD", "LHR", "2024-11-01", current_price=120.0)
        price_monitor.add_monitor(100, "MAD", "CDG", "2024-11-10", current_price=90.0)
        monitors = price_monitor.list_monitors(100)
        destinations = {m["destination"] for m in monitors}
        self.assertEqual(destinations, {"LHR", "CDG"})

    # ------------------------------------------------------------------
    # check_and_alert
    # ------------------------------------------------------------------

    def test_check_and_alert_price_drop(self):
        price_monitor.add_monitor(200, "MAD", "LHR", "2024-12-01", current_price=300.0)
        with patch("amadeus_api.get_cheapest_price", return_value=250.0):
            result = price_monitor.check_and_alert("MAD", "LHR", "2024-12-01")
        self.assertIsNotNone(result)
        chat_ids, message = result
        self.assertIn(200, chat_ids)
        self.assertIn("250.00", message)
        self.assertIn("300.00", message)

    def test_check_and_alert_no_drop(self):
        price_monitor.add_monitor(201, "MAD", "LHR", "2024-12-02", current_price=200.0)
        with patch("amadeus_api.get_cheapest_price", return_value=220.0):
            result = price_monitor.check_and_alert("MAD", "LHR", "2024-12-02")
        self.assertIsNone(result)

    def test_check_and_alert_unknown_route(self):
        result = price_monitor.check_and_alert("ZZZ", "YYY", "2025-01-01")
        self.assertIsNone(result)

    def test_check_and_alert_updates_stored_price(self):
        price_monitor.add_monitor(202, "FCO", "CDG", "2025-02-01", current_price=100.0)
        with patch("amadeus_api.get_cheapest_price", return_value=80.0):
            price_monitor.check_and_alert("FCO", "CDG", "2025-02-01")
        monitors = price_monitor.list_monitors(202)
        self.assertAlmostEqual(monitors[0]["last_price"], 80.0)

    # ------------------------------------------------------------------
    # run_all_checks
    # ------------------------------------------------------------------

    def test_run_all_checks_returns_alerts(self):
        price_monitor.add_monitor(300, "BCN", "AMS", "2025-03-01", current_price=150.0)
        price_monitor.add_monitor(300, "BCN", "VIE", "2025-03-10", current_price=200.0)

        def _mock_price(origin, destination, departure_date, adults=1):
            if destination == "AMS":
                return 100.0  # price drop
            return 210.0  # price increase – no alert

        with patch("amadeus_api.get_cheapest_price", side_effect=_mock_price):
            alerts = price_monitor.run_all_checks()

        self.assertEqual(len(alerts), 1)
        _, msg = alerts[0]
        self.assertIn("AMS", msg)


if __name__ == "__main__":
    unittest.main()
