
# ValutaTrade Hub

**ValutaTrade Hub** —  консольное приложение на Python для получения валютных курсов и симуляции торговли фиатными и криптовалютами. Все операции выполняются с **виртуальными средствами**, без реальных платежей.

Проект разделен на бизнес-логику (Core Service), сервис получения курсов (Parser Service), инфраструктуру хранения данных и CLI.

## Возможности

- Регистрация и авторизация пользователей; пароли сохраняются в виде SHA-256-хеша с индивидуальной солью.
- Персональные кошельки и портфели, пополнение виртуального USD-баланса.
- Покупка и продажа валют за USD с проверкой доступных средств.
- Получение прямых, обратных и кросс-курсов через USD.
- Оценка портфеля в выбранной базовой валюте.
- Загрузка котировок через CoinGecko и ExchangeRate-API.
- Локальный кеш, проверка актуальности по TTL, история курсов и периодическое обновление.
- Логирование операций и обработка ошибок.

**Поддерживаемые валюты:** USD, EUR, GBP, RUB, BTC, ETH, SOL. Расчетная валюта для сделок — USD.

## Структура проекта

```text
finalproject_ozhiganov_m26_555/
├── data/                         # JSON-данные при запуске из репозитория
├── valutatrade_hub/
│   ├── cli/
│   │   └── interface.py          # Команды и вывод в терминал
│   ├── core/
│   │   ├── currencies.py         # Currency, FiatCurrency, CryptoCurrency, реестр
│   │   ├── exceptions.py         # Пользовательские исключения
│   │   ├── models.py             # User, Wallet, Portfolio
│   │   ├── rates.py              # Прямые, обратные и составные курсы
│   │   ├── rate_views.py         # Подготовка курсов для отображения
│   │   ├── usecases.py           # TradingService
│   │   └── utils.py              # Валидация и работа со временем
│   ├── infra/
│   │   ├── database.py           # Работа с JSON
│   │   └── settings.py           # Конфигурация (Singleton)
│   ├── parser_service/
│   │   ├── api_clients.py        # Клиенты внешних API
│   │   ├── config.py             # Настройки источников и путей
│   │   ├── scheduler.py          # Периодическое обновление
│   │   ├── storage.py            # Кеш и история котировок
│   │   └── updater.py            # Координация обновлений
│   ├── decorators.py             # @log_action
│   └── logging_config.py         # Логирование с ротацией
├── main.py                       # Запуск из исходников
├── pyproject.toml                # Зависимости и настройки
├── uv.lock
├── .gitignore
└── README.md
```

## Установка и запуск

Требуются **Python 3.12+**, [uv](https://docs.astral.sh/uv/) и доступ в интернет для обновления курсов.

```bash
git clone https://github.com/slavanorthern/finalproject_ozhiganov_m26_555.git
cd finalproject_ozhiganov_m26_555
uv sync
```

Создайте файл `.env` в корне проекта и добавьте API-ключ для фиатных курсов:

```dotenv
EXCHANGERATE_API_KEY=your_api_key
```

Ключ нужен для **ExchangeRate-API**; CoinGecko в текущей конфигурации используется без ключа. Файл `.env` исключен из Git. Если ключ не задан, получение фиатных курсов недоступно.

Запуск:

```bash
uv run python main.py
```

Или через зарегистрированную точку входа:

```bash
uv run valutatrade
```

После запуска введите `help`, чтобы увидеть доступные команды.

## Команды CLI

| Команда | Назначение |
| --- | --- |
| `register --username alice --password 1234` | Регистрация пользователя с пустым портфелем |
| `login --username alice --password 1234` | Авторизация |
| `deposit --amount 10000` | Пополнение виртуального USD-баланса |
| `show-portfolio` | Просмотр портфеля в USD |
| `show-portfolio --base EUR` | Оценка портфеля в EUR |
| `buy --currency BTC --amount 0.01` | Покупка валюты за USD |
| `sell --currency BTC --amount 0.005` | Продажа валюты с зачислением USD |
| `get-rate --from BTC --to EUR` | Курс, обратный курс, источник и время обновления |
| `update-rates` | Обновление из всех доступных источников |
| `update-rates --source coingecko` | Обновление только криптовалют |
| `update-rates --source exchangerate` | Обновление только фиатных валют |
| `show-rates` | Просмотр локального кеша курсов |
| `show-rates --base EUR` | Курсы относительно EUR |
| `show-rates --currency BTC` | Фильтр по валюте |
| `show-rates --top 2` | Две криптовалюты с наибольшим курсом |
| `schedule-rates --interval 60` | Периодическое обновление каждые 60 секунд |
| `help` / `exit` | Справка / выход |

У `show-rates` можно совмещать параметры, например `show-rates --top 3 --base EUR`. У `schedule-rates` можно указать `--source coingecko` или `--source exchangerate`; остановка — **Ctrl+C**.

Пароль `1234` в примерах используется исключительно для демонстрации.

### Пример работы

После запуска приложения:

```text
register --username alice --password 1234
login --username alice --password 1234
deposit --amount 10000
update-rates
show-rates --top 2
get-rate --from BTC --to EUR
buy --currency BTC --amount 0.01
show-portfolio
show-portfolio --base EUR
sell --currency BTC --amount 0.005
show-portfolio
exit
```

Для регистрации используйте свободное имя пользователя. Торговые операции требуют доступного баланса и актуальных котировок.

## Курсы, кеш и TTL

- **CoinGecko** предоставляет курсы BTC, ETH, SOL.
- **ExchangeRate-API** предоставляет курсы EUR, GBP, RUB; они приводятся к парам вида `EUR_USD`.
- Текущие котировки хранятся в `rates.json`, история — в `exchange_rates.json`.
- Для каждой пары сохраняются курс, время обновления и источник.
- Обратные и составные курсы рассчитываются через единую функцию `calculate_rate()`.

Пример кросс-курса:

```text
BTC/EUR = (BTC/USD) / (EUR/USD)
```

TTL по умолчанию составляет **300 секунд**. Команды `get-rate`, `buy`, `sell` и оценка ненулевых валютных позиций проверяют актуальность необходимых курсов. При истечении TTL используйте `update-rates`.

`show-rates` может отображать последнюю сохраненную котировку и после истечения TTL. В таблице для нее указывается статус **«устарел»**; для свежей — **«актуален»**. Для составных курсов учитываются источник каждого компонента и более раннее время обновления.

Обновление кеша и истории выполняется через временный файл с последующей атомарной заменой соответствующего JSON-файла.

## Хранение данных

При работе **из репозитория** JSON-файлы находятся в `data/`, а логи — в `logs/`.

При запуске **отдельно установленного wheel** используется пользовательский каталог:

```text
~/.valutatrade_hub/data/
~/.valutatrade_hub/logs/
```

Корневой каталог можно изменить переменной окружения `VALUTATRADE_HOME`. Например, для **Git Bash (Windows)**:

```bash
export VALUTATRADE_HOME="$HOME/valutatrade-data"
```

Тогда файлы создаются в `$VALUTATRADE_HOME/data/`, логи — в `$VALUTATRADE_HOME/logs/`. Чтобы вернуться к стандартному расположению, выполните `unset VALUTATRADE_HOME`.

При первом запуске автоматически создаются отсутствующие `users.json`, `portfolios.json`, `rates.json` и `exchange_rates.json`; уже существующие файлы не перезаписываются.

## Архитектура и обработка ошибок

- **Core Service:** `User`, `Wallet`, `Portfolio`, абстрактный `Currency`, наследники `FiatCurrency` и `CryptoCurrency`, `TradingService`, единая конвертация валют.
- **Parser Service:** `BaseApiClient`, `CoinGeckoClient`, `ExchangeRateApiClient`, `RatesUpdater`, `RatesStorage`, планировщик.
- **Infrastructure:** `SettingsLoader` и `DatabaseManager` реализованы как Singleton.
- **CLI:** разбирает команды, вызывает сервисы и отображает результаты.

Предусмотрены `InsufficientFundsError`, `CurrencyNotFoundError` и `ApiRequestError`. Проверяются положительность сумм, достаточность средств, корректность курсов и данных API, отсутствие валютной пары и истечение TTL.

Операции регистрации, входа, покупки, продажи и обновления курсов записываются в `logs/actions.log`. Используется `RotatingFileHandler`; пароли в лог не записываются.

Основные настройки находятся в секции `[tool.valutatrade]` файла `pyproject.toml`:

```toml
[tool.valutatrade]
rates_ttl_seconds = 300
default_base_currency = "USD"
log_level = "INFO"
log_format = "%(levelname)s %(asctime)s %(message)s"
```

## Проверка качества и сборка

```bash
uv run ruff check .
uv run ruff format --check .
uv build
```

После сборки в `dist/` создаются архив исходников (`.tar.gz`) и пакет (`.whl`).

### Отдельная установка wheel на Windows

Из корня репозитория в Git Bash:

```bash
uv venv ../valutatrade-wheel-test/.venv
uv pip install --python ../valutatrade-wheel-test/.venv/Scripts/python.exe dist/finalproject_ozhiganov_m26_555-0.1.0-py3-none-any.whl
cd ../valutatrade-wheel-test
.venv/Scripts/valutatrade.exe
```

Этот сценарий позволяет проверить запуск установленного пакета независимо от исходного репозитория.

## Демонстрация

Запись полного пользовательского сценария: **[asciinema — ValutaTrade Hub](https://asciinema.org/a/izElmESnGOYObA28)**.

В демо показаны регистрация, авторизация, обновление курсов, операции с виртуальным балансом, просмотр портфеля и обработка ошибок.
