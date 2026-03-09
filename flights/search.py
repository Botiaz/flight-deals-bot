import requests
from config import AMADEUS_API_KEY, AMADEUS_API_SECRET


def get_access_token():

    url = "https://test.api.amadeus.com/v1/security/oauth2/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }

    response = requests.post(url, data=data)

    return response.json()["access_token"]


def search_flights(origin, destination):

    token = get_access_token()

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": "2026-05-10",
        "adults": 1,
        "max": 5
    }

    response = requests.get(url, headers=headers, params=params)

    return response.json()

def get_cheapest_flight(origin, destination):

    data = search_flights(origin, destination)

    prices = []

    for flight in data["data"]:
        price = float(flight["price"]["total"])
        prices.append(price)

    if not prices:
        return None

    return min(prices)