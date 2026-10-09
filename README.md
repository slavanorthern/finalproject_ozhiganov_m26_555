# ValutaTrade Hub

ValutaTrade Hub — консольное Python-приложение для отслеживания курсов
фиатных и криптовалют и симуляции валютной торговли.

Проект реализован как Python-пакет с разделением на Core Service,
Parser Service, инфраструктурный слой и CLI.

## Возможности

Приложение позволяет:

- регистрировать пользователей;
- выполнять авторизацию;
- вести индивидуальный валютный портфель;
- пополнять виртуальный USD-баланс;
- покупать и продавать валюты;
- получать текущие курсы;
- рассчитывать кросс-курсы через USD;
- оценивать портфель в разных базовых валютах;
- загружать реальные курсы из внешних API;
- хранить локальный кеш актуальных курсов;
- сохранять историю измерений;
- контролировать свежесть данных через TTL;
- автоматически обновлять курсы по расписанию;
- логировать основные действия и ошибки.

## Поддерживаемые валюты

Фиатные валюты:

- USD — US Dollar
- EUR — Euro
- GBP — Pound Sterling
- RUB — Russian Ruble

Криптовалюты:

- BTC — Bitcoin
- ETH — Ethereum
- SOL — Solana

## Источники курсов

Для получения курсов используются два API.

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

Внутренней базовой валютой является USD.

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
├── valutatrade_hub/
│   ├── __init__.py
│   ├── logging_config.py
│   ├── decorators.py
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
│   │   ├── settings.py
│   │   └── database.py
│   │
│   ├── parser_service/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── api_clients.py
│   │   ├── updater.py
│   │   ├── storage.py
│   │   └── scheduler.py
│   │
│   └── cli/
│       ├── __init__.py
│       └── interface.py
│
├── main.py
├── pyproject.toml
├── uv.lock
├── README.md
└── .gitignore
