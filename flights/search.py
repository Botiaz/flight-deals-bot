import requests
from config import KIWI_API_KEY


TEQUILA_BASE_URL = "https://tequila-api.kiwi.com"


class FlightSearchError(Exception):
    pass


def _validate_kiwi_credentials() -> None:
    if not KIWI_API_KEY:
        raise FlightSearchError(
            "KIWI_API_KEY nao foi definido. Configure a variavel no arquivo .env. "
            "Registre-se gratuitamente em: https://tequila.kiwi.com"
        )

    markers = ("your_", "example", "replace", "placeholder", "api_key_here")
    if any(marker in KIWI_API_KEY.lower() for marker in markers):
        raise FlightSearchError(
            "KIWI_API_KEY ainda esta com valor de exemplo no .env. "
            "Substitua pela chave real gerada em tequila.kiwi.com."
        )


def search_flights(origin: str, destination: str, date: str) -> dict:
    """
    Busca voos entre dois aeroportos em uma data especifica.

    Args:
        origin: Codigo IATA do aeroporto de origem (ex: 'CNF')
        destination: Codigo IATA do aeroporto de destino (ex: 'MDE')
        date: Data de partida no formato 'YYYY-MM-DD' (ex: '2026-05-10')

    Returns:
        Dicionario com os dados de voos retornados pela API Kiwi Tequila.

    Raises:
        FlightSearchError: Se as credenciais forem invalidas ou a busca falhar.
    """
    _validate_kiwi_credentials()

    # A Tequila API usa o formato DD/MM/YYYY
    try:
        year, month, day = date.split("-")
        tequila_date = f"{day}/{month}/{year}"
    except ValueError:
        raise FlightSearchError(
            f"Formato de data invalido: '{date}'. Use o formato YYYY-MM-DD (ex: 2026-05-10)."
        )

    url = f"{TEQUILA_BASE_URL}/v2/search"

    headers = {
        "apikey": KIWI_API_KEY,
        "Content-Type": "application/json",
    }

    params = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": tequila_date,
        "date_to": tequila_date,
        "adults": 1,
        "limit": 5,
        "curr": "BRL",
        "sort": "price",
        "asc_or_desc": "asc",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.RequestException as exc:
        raise FlightSearchError(
            "Falha de conexao ao buscar voos na Kiwi Tequila API."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise FlightSearchError(
            "Resposta invalida da Kiwi Tequila API ao buscar voos."
        ) from exc

    if response.status_code == 403:
        raise FlightSearchError(
            "Autenticacao falhou (403). Verifique se sua KIWI_API_KEY esta correta "
            "e se sua conta em tequila.kiwi.com esta ativa."
        )

    if response.status_code != 200:
        error_msg = payload.get("message") or payload.get("error") or "Sem detalhes"
        raise FlightSearchError(
            f"Erro da Kiwi Tequila API (status {response.status_code}): {error_msg}"
        )

    return payload


def get_cheapest_flight(origin: str, destination: str, date: str) -> float | None:
    """
    Retorna o preco do voo mais barato encontrado entre origem e destino.

    Args:
        origin: Codigo IATA do aeroporto de origem.
        destination: Codigo IATA do aeroporto de destino.
        date: Data de partida no formato 'YYYY-MM-DD'.

    Returns:
        Preco minimo encontrado (float em BRL) ou None se nenhum voo for encontrado.
    """
    data = search_flights(origin, destination, date)

    prices = [float(flight["price"]) for flight in data.get("data", [])]

    return min(prices) if prices else None


def get_cheapest_destinations(origin: str, date_from: str, date_to: str, limit: int = 10) -> list[dict]:
    """
    Busca os destinos mais baratos a partir de uma cidade de origem.
    Util para o comando /anywhere do bot.

    Args:
        origin: Codigo IATA do aeroporto de origem.
        date_from: Data minima de partida no formato 'YYYY-MM-DD'.
        date_to: Data maxima de partida no formato 'YYYY-MM-DD'.
        limit: Numero maximo de destinos a retornar.

    Returns:
        Lista de dicionarios com destino e preco, ordenados pelo mais barato.
    """
    _validate_kiwi_credentials()

    def fmt_date(d: str) -> str:
        y, m, day = d.split("-")
        return f"{day}/{m}/{y}"

    url = f"{TEQUILA_BASE_URL}/v2/search"
    headers = {
        "apikey": KIWI_API_KEY,
        "Content-Type": "application/json",
    }
    params = {
        "fly_from": origin,
        "date_from": fmt_date(date_from),
        "date_to": fmt_date(date_to),
        "adults": 1,
        "limit": limit,
        "curr": "BRL",
        "sort": "price",
        "asc_or_desc": "asc",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise FlightSearchError("Erro ao buscar destinos baratos na Kiwi API.") from exc

    if response.status_code != 200:
        error_msg = payload.get("message") or "Sem detalhes"
        raise FlightSearchError(f"Erro da Kiwi API ao buscar destinos: {error_msg}")

    results = []
    for flight in payload.get("data", []):
        results.append({
            "destination": flight.get("cityTo", "Desconhecido"),
            "destination_code": flight.get("flyTo", "???"),
            "country": flight.get("countryTo", {}).get("name", ""),
            "price": float(flight["price"]),
            "departure": flight.get("local_departure", "")[:10],
        })

    return results
