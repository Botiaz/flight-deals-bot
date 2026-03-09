import requests
from config import AMADEUS_API_KEY, AMADEUS_API_SECRET


class FlightSearchError(Exception):
    pass


def _validate_amadeus_credentials() -> None:
    if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
        raise FlightSearchError(
            "Credenciais da Amadeus ausentes. Configure AMADEUS_API_KEY e AMADEUS_API_SECRET no .env."
        )

    markers = ("your_", "example", "replace", "placeholder")
    if any(marker in AMADEUS_API_KEY.lower() for marker in markers) or any(
        marker in AMADEUS_API_SECRET.lower() for marker in markers
    ):
        raise FlightSearchError(
            "Credenciais da Amadeus ainda estao com valor de exemplo no .env."
        )


def get_access_token():
    _validate_amadeus_credentials()

    url = "https://test.api.amadeus.com/v1/security/oauth2/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }

    try:
        response = requests.post(url, data=data, timeout=15)
    except requests.RequestException as exc:
        raise FlightSearchError(
            "Nao foi possivel conectar na API da Amadeus para autenticar."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise FlightSearchError("Resposta invalida da Amadeus ao gerar token.") from exc

    if response.status_code != 200:
        details = payload.get("error_description") or payload.get("error") or "Sem detalhes"
        raise FlightSearchError(f"Falha na autenticacao Amadeus: {details}")

    token = payload.get("access_token")
    if not token:
        raise FlightSearchError("A Amadeus nao retornou access_token na autenticacao.")

    return token


def search_flights(origin, destination, date):

    token = get_access_token()

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": date,
        "adults": 1,
        "max": 5
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.RequestException as exc:
        raise FlightSearchError("Falha de conexao ao buscar voos na Amadeus.") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise FlightSearchError("Resposta invalida da Amadeus ao buscar voos.") from exc

    if response.status_code != 200:
        errors = payload.get("errors") or []
        if errors and isinstance(errors, list):
            detail = errors[0].get("detail") or errors[0].get("title") or "Sem detalhes"
        else:
            detail = "Sem detalhes"
        raise FlightSearchError(f"Erro da Amadeus na busca de voos: {detail}")

    return payload

def get_cheapest_flight(origin, destination, date):

    data = search_flights(origin, destination, date)

    prices = []

    for flight in data.get("data", []):

        price = float(flight["price"]["total"])
        prices.append(price)

    if not prices:
        return None

    return min(prices)