# ValutaTrade Hub

Консольное приложение для отслеживания курсов валют и симуляции валютной торговли.

Проект выполнен в рамках итоговой работы по Python.

## Возможности

ValutaTrade Hub позволяет:

- регистрировать пользователей;
- выполнять вход в систему;
- вести индивидуальный валютный портфель;
- пополнять виртуальный USD-баланс;
- покупать и продавать валюты;
- получать текущие курсы валют;
- пересчитывать стоимость портфеля в выбранную базовую валюту;
- загружать реальные курсы из внешних API;
- хранить текущий кеш курсов;
- сохранять историю изменений курсов;
- контролировать актуальность курсов через TTL;
- логировать основные операции приложения.

## Поддерживаемые валюты

Фиатные валюты:

- USD
- EUR
- GBP
- RUB

Криптовалюты:

- BTC
- ETH
- SOL

## Источники данных

Для получения курсов используются два внешних API.

### CoinGecko

Используется для криптовалют:

- BTC
- ETH
- SOL

### ExchangeRate-API

Используется для фиатных валют:

- EUR
- GBP
- RUB

Базовая валюта для внутреннего хранения курсов — USD.

## Структура проекта

```text
finalproject_ozhiganov_m26_555/
│
├── data/
│   ├── users.json
│   ├── portfolios.json
│   ├── rates.json
│   └── exchange_rates.json
│
├── logs/
│
├── valutatrade_hub/
│   ├── __init__.py
│   ├── decorators.py
│   ├── logging_config.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── currencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── usecases.py
│   │   └── utils.py
│   │
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── settings.py
│   │
│   ├── parser_service/
│   │   ├── __init__.py
│   │   ├── api_clients.py
│   │   ├── config.py
│   │   ├── scheduler.py
│   │   ├── storage.py
│   │   └── updater.py
│   │
│   └── cli/
│       ├── __init__.py
│       └── interface.py
│
├── main.py
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md