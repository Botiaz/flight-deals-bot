from flights.search import FlightSearchError, get_cheapest_flight


async def voo(update, context):

    try:

        origin = context.args[0].upper()
        destination = context.args[1].upper()
        date = context.args[2]

    except (IndexError, ValueError):

        await update.message.reply_text(
            "Use:\n/voo ORIGEM DESTINO DATA\n\nExemplo:\n/voo CNF MDE 2026-05-10"
        )
        return

    await update.message.reply_text("Buscando voos... ✈️")

    try:
        price = get_cheapest_flight(origin, destination, date)
    except FlightSearchError as exc:
        await update.message.reply_text(f"Erro ao consultar voos: {exc}")
        return

    if price is None:

        await update.message.reply_text("Nenhum voo encontrado.")

    else:

        message = f"""
✈️ Melhor preço encontrado

{origin} → {destination}
📅 Data: {date}

💰 Preço: ${price}
"""

        await update.message.reply_text(message)