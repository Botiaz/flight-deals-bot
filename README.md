# Smart Flight Finder

Bot de Telegram para buscar passagens usando a API Kiwi Tequila.

## Status atual do projeto

Implementado no momento:

- Comando `/voo` no Telegram
- Busca de menor preco entre origem e destino em uma data especifica

Ainda nao implementado no fluxo principal (arquivos existem, mas sem logica final):

- Scanner/agendador de aeroportos
- Detector de deals

## Como usar

Formato do comando:

`/voo ORIGEM DESTINO DATA`

Exemplo:

`/voo CNF MDE 2026-05-10`

Detalhes:

- `ORIGEM`: codigo IATA de 3 letras (ex: CNF)
- `DESTINO`: codigo IATA de 3 letras (ex: MDE)
- `DATA`: formato `YYYY-MM-DD`

## Requisitos

- Python 3.11+ (recomendado)
- Token do Telegram (via @BotFather)
- Chave da Kiwi Tequila (https://tequila.kiwi.com)

## Configuracao

Crie/edite o arquivo `.env` na raiz com:

```dotenv
KIWI_API_KEY=sua_chave_kiwi
TELEGRAM_BOT_TOKEN=seu_token_do_bot
```

## Execucao local (Windows / PowerShell)

1. (Opcional) Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependencias:

```powershell
python -m pip install -r requirements.txt
```

3. Rode o bot:

```powershell
python main.py
```

Saida esperada no terminal:

- `Starting Smart Flight Finder...`
- `Bot running...`

Depois disso, abra o Telegram e teste o comando no chat com o bot.

## Troubleshooting

### Erro de autenticacao Kiwi (401/403)

Mensagem comum:

`Erro ao consultar voos: Erro da Kiwi Tequila API (status 401): Unauthorized`

Checklist:

1. Verifique se `KIWI_API_KEY` esta correta no `.env` (sem espacos extras e sem aspas).
2. Confirme que a chave foi copiada de https://tequila.kiwi.com e esta ativa.
3. Gere uma nova chave na Kiwi e atualize o `.env`.
4. Pare e inicie o bot novamente apos trocar a chave.

### Erro `Conflict` no Telegram

Esse erro indica mais de uma instancia do bot em polling ao mesmo tempo.

1. Feche outras execucoes do bot.
2. Rode apenas uma instancia de `python main.py`.

## Stack

- Python
- python-telegram-bot
- Kiwi Tequila API

## Autor

Mateus Soares Gatti Vasconcellos