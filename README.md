
# ValutaTrade Hub

Консольное приложение на Python для отслеживания курсов фиатных и криптовалют и симуляции торговли с виртуальным балансом. Проект разделен на Core Service, Parser Service, инфраструктуру и CLI.

## Возможности

- Регистрация и авторизация пользователей с индивидуальной солью и SHA-256 для хранения паролей.
- Отдельные кошельки и портфели пользователей, пополнение виртуального USD-баланса.
- Покупка и продажа валют за USD с проверкой средств.
- Прямые, обратные и кросс-курсы через USD; оценка портфеля в выбранной валюте.
- Получение данных через CoinGecko и ExchangeRate-API.
- Кеш котировок, TTL, история обновлений, автоматический планировщик и логирование операций.
- JSON-хранилище с атомарной записью.

Поддерживаемые валюты: **USD, EUR, GBP, RUB, BTC, ETH, SOL**. Расчетная валюта для торговых операций — USD.

## Структура

```text
finalproject_ozhiganov_m26_555/
├── data/                      # JSON-данные при запуске из репозитория
├── valutatrade_hub/
│   ├── cli/
│   │   └── interface.py       # Команды и вывод
│   ├── core/
│   │   ├── currencies.py      # Иерархия и реестр валют
│   │   ├── exceptions.py
│   │   ├── models.py          # User, Wallet, Portfolio
│   │   ├── rates.py           # Единая формула конвертации
│   │   ├── rate_views.py      # Подготовка списка котировок
│   │   ├── usecases.py        # TradingService
│   │   └── utils.py
│   ├── infra/
│   │   ├── database.py        # JSON и инициализация хранилища
│   │   └── settings.py        # SettingsLoader (Singleton)
│   ├── parser_service/
│   │   ├── api_clients.py     # CoinGecko, ExchangeRate-API
│   │   ├── config.py
│   │   ├── scheduler.py
│   │   ├── storage.py
│   │   └── updater.py
│   ├── decorators.py          # @log_action
│   └── logging_config.py
├── main.py
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

## Требования и установка

Требуется **Python 3.12+** и [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/slavanorthern/finalproject_ozhiganov_m26_555.git
cd finalproject_ozhiganov_m26_555
uv sync
```

Запуск из репозитория:

```bash
uv run python main.py
```

Или через точку входа пакета:

```bash
uv run valutatrade
```

### Сборка и отдельная установка wheel

```bash
uv build
```

Сборка создает `.whl` и `.tar.gz` в `dist/`. Для установки собранного wheel в отдельное виртуальное окружение на Windows:

```bash
uv venv ../valutatrade-wheel-test/.venv
uv pip install --python ../valutatrade-wheel-test/.venv/Scripts/python.exe dist/finalproject_ozhiganov_m26_555-0.1.0-py3-none-any.whl
../valutatrade-wheel-test/.venv/Scripts/valutatrade.exe
```

### Где хранятся данные

- При запуске из исходного репозитория — в его каталоге `data/`.
- При отдельной установке wheel — в пользовательском каталоге `~/.valutatrade_hub/data/`.
- Каталог можно явно задать переменной окружения `VALUTATRADE_HOME`; тогда файлы окажутся в `$VALUTATRADE_HOME/data/`.
- Отсутствующие JSON-файлы создаются автоматически при первой инициализации хранилища, существующие файлы не перезаписываются.

Пример для **Git Bash (Windows)**:

```bash
export VALUTATRADE_HOME="$HOME/valutatrade-data"
```

Для удаления переопределения в текущем терминале:

```bash
unset VALUTATRADE_HOME
```

В каталоге `data/` используются `users.json`, `portfolios.json`, `rates.json`, `exchange_rates.json`.

## API-ключ

Для фиатных курсов необходим ключ ExchangeRate-API. Создайте `.env` в корне проекта:

```dotenv
EXCHANGERATE_API_KEY=your_api_key
```

При установленном wheel переменную можно передать через окружение либо `.env` в рабочем каталоге. Не добавляйте реальные ключи в Git. CoinGecko используется без API-ключа в текущей конфигурации.

## Команды CLI

```text
help
register --username alice --password 1234
login --username alice --password 1234
show-portfolio
show-portfolio --base EUR
deposit --amount 10000
buy --currency BTC --amount 0.01
sell --currency BTC --amount 0.005
get-rate --from BTC --to USD
get-rate --from BTC --to EUR
update-rates
update-rates --source coingecko
update-rates --source exchangerate
show-rates
show-rates --base EUR
show-rates --currency BTC
show-rates --top 2
show-rates --top 3 --base EUR
schedule-rates
schedule-rates --interval 60
schedule-rates --interval 60 --source coingecko
exit
```

`register` создает пользователя с пустым портфелем. `deposit` добавляет виртуальные USD, после чего доступны покупки. При продаже средства возвращаются в USD. `get-rate` выводит курс, обратный курс, источник и время обновления.

Планировщик запускает повторные обновления; для его остановки используйте **Ctrl+C**.

## Котировки и TTL

Parser Service получает котировки BTC, ETH, SOL через CoinGecko, а USD-курсы EUR, GBP, RUB — через ExchangeRate-API. Данные записываются в `data/rates.json`; история изменений — в `data/exchange_rates.json`.

Пример кеша:

```json
{
  "pairs": {
    "BTC_USD": {
      "rate": 80000.0,
      "updated_at": "2026-10-09T14:39:23+00:00",
      "source": "CoinGecko"
    },
    "EUR_USD": {
      "rate": 1.25,
      "updated_at": "2026-10-09T14:39:24+00:00",
      "source": "ExchangeRate-API"
    }
  },
  "last_refresh": "2026-10-09T14:39:24+00:00"
}
```

Кросс-курс через USD рассчитывается, например, по формуле:

```text
BTC/EUR = (BTC/USD) / (EUR/USD)
```

Торговые операции и `get-rate` требуют актуальных курсов. По умолчанию TTL составляет **300 секунд**; при истечении срока необходимо выполнить `update-rates`.

`show-rates` показывает сохраненные курсы и отдельный статус **«актуален» / «устарел»**. Устаревшее значение остается видимым в списке, но не используется для торговли. Для составной котировки показываются объединенные источники и время более старого компонента.

## Модели и обработка ошибок

- `Currency` — абстрактный базовый класс; `FiatCurrency` и `CryptoCurrency` — наследники. Поиск по коду: `get_currency(code)`.
- `User` — пользователь, пароль хранится как хеш с солью.
- `Wallet` — баланс конкретной валюты, положительные пополнения и списания.
- `Portfolio` — кошельки пользователя и расчет общей стоимости, включая кросс-курсы.
- `TradingService` — регистрация, вход, сделки, курсы и оценка портфеля.

Обрабатываются неизвестные валюты, недостаток средств, некорректные суммы, отсутствие/устаревание курсов, ошибки сети, HTTP-статусы и некорректные ответы API. Основные пользовательские исключения: `InsufficientFundsError`, `CurrencyNotFoundError`, `ApiRequestError`.

## Настройки и логи

Настройки приложения находятся в `pyproject.toml`, секция `[tool.valutatrade]`:

```toml
[tool.valutatrade]
rates_ttl_seconds = 300
default_base_currency = "USD"
log_level = "INFO"
log_format = "%(levelname)s %(asctime)s %(message)s"
```

`SettingsLoader` и `DatabaseManager` реализованы как Singleton. Параметры источников API определены в `parser_service/config.py`.

Декоратор `@log_action` записывает регистрацию, вход, покупку, продажу и ошибки в `logs/actions.log`. Используется `RotatingFileHandler` с ротацией логов. Пароли в логи не записываются.

## Проверка кода

```bash
uv run ruff check .
uv run ruff format --check .
uv build
```

## Демонстрация

Запись работы приложения на asciinema: [открыть демо](https://asciinema.org/a/izElmESnGOYObA28).

В записи показаны регистрация, авторизация, пополнение виртуального счета, обновление и просмотр курсов, получение кросс-курса, покупка и продажа BTC, оценка портфеля в USD/EUR и обработка ошибок.

## Технологии

Python 3.12, uv, Ruff, PrettyTable, Requests, python-dotenv, JSON, Git, CoinGecko API, ExchangeRate-API, asciinema.


