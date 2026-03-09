# Smart Flight Finder ✈️

Smart Flight Finder is a Telegram bot that searches for cheap flights using the Amadeus API.

The bot can:

- Search flights to a specific destination
- Find the cheapest destinations from a city
- Scan nearby airports
- Detect flight price drops
- Send alerts via Telegram

## Features

### Search flights

Example command:

/voo CNF MDE

Returns the cheapest flight between Belo Horizonte and Medellín.

### Explore cheap destinations

/anywhere CNF

Returns the cheapest destinations from Belo Horizonte.

### Nearby airport scanner

The bot automatically checks nearby airports:

CNF – Belo Horizonte  
GRU – São Paulo  
GIG – Rio de Janeiro  
BSB – Brasília  

## Tech Stack

- Python
- Telegram Bot API
- Amadeus Flight API
- SQLite

## Future Improvements

- Price history tracking
- Machine learning price prediction
- Global flight deals scanner

## Local Setup

1. Create a `.env` file in the project root based on `.env.example`.
2. Fill in your real credentials, mainly `TELEGRAM_BOT_TOKEN` from `@BotFather`.
3. Run `python main.py`.

## Author

Mateus Soares Gatti Vasconcellos