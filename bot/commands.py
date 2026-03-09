from flights.search import get_cheapest_flight


async def voo(update, context):

    try:

        origin = context.args[0].upper()
        destination = context.args[1].upper()

    except:
        await update.message.reply_text(
            "Use: /voo ORIGEM DESTINO\nExemplo: /voo CNF MDE"
        )
        return

    await update.message.reply_text("Buscando voos... ✈️")

    price = get_cheapest_flight(origin, destination)

    if price is None:

        await update.message.reply_text("Nenhum voo encontrado.")

    else:

        message = f"""
✈️ Melhor preço encontrado

{origin} → {destination}

💰 Preço: ${price}
"""

        await update.message.reply_text(message)