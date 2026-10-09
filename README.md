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
- получать текущие курсы валют;
- рассчитывать кросс-курсы через USD;
- оценивать портфель в разных базовых валютах;
- загружать реальные курсы из внешних API;
- хранить локальный кеш актуальных курсов;
- сохранять историю изменения курсов;
- контролировать свежесть данных через TTL;
- автоматически обновлять курсы по расписанию;
- логировать основные операции и ошибки.

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

Внутренней базовой валютой приложения является USD.

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
```

## Архитектура

Проект разделен на несколько логических слоев.

### Core Service

Содержит основную бизнес-логику:

- класс `User`;
- класс `Wallet`;
- класс `Portfolio`;
- иерархию валют;
- регистрацию и авторизацию;
- покупку и продажу валют;
- получение и расчет валютных курсов;
- расчет стоимости портфеля;
- проверку актуальности курсов через TTL.

### Parser Service

Отвечает за получение и сохранение актуальных валютных курсов.

Основные компоненты:

- `BaseApiClient`;
- `CoinGeckoClient`;
- `ExchangeRateApiClient`;
- `RatesUpdater`;
- `RatesStorage`;
- планировщик периодического обновления.

Parser Service может работать:

- вручную через `update-rates`;
- периодически через `schedule-rates`.

### Infrastructure

Инфраструктурный слой содержит:

- `SettingsLoader`;
- `DatabaseManager`.

Оба компонента реализованы как Singleton.

`SettingsLoader` загружает основные настройки из секции
`[tool.valutatrade]` файла `pyproject.toml`.

### CLI

`cli/interface.py` является основной точкой взаимодействия пользователя
с приложением.

CLI не содержит основную бизнес-логику, а вызывает методы Core Service
и Parser Service.

## Установка

Требуется Python 3.12 или новее.

Клонирование репозитория:

```bash
git clone https://github.com/slavanorthern/finalproject_ozhiganov_m26_555.git
cd finalproject_ozhiganov_m26_555
```

Установка зависимостей:

```bash
uv sync
```

## Настройка ExchangeRate-API

Для работы с ExchangeRate-API необходимо создать файл `.env`
в корне проекта.

Пример:

```text
EXCHANGERATE_API_KEY=your_api_key
```

Реальный API-ключ не должен сохраняться в Git.

Файл `.env` включен в `.gitignore`.

Для CoinGecko отдельный API-ключ в текущей конфигурации не требуется.

## Запуск приложения

Основной вариант:

```bash
uv run python main.py
```

Также в `pyproject.toml` зарегистрирован console script:

```bash
uv run valutatrade
```

После запуска:

```text
ValutaTrade Hub
Введите help для списка команд.
>
```

## Команды CLI

### Справка

```text
help
```

### Регистрация пользователя

```text
register --username alice --password 1234
```

Пример результата:

```text
Пользователь 'alice' зарегистрирован (id=1).
Войдите: login --username alice --password ****
```

### Авторизация

```text
login --username alice --password 1234
```

Пример:

```text
Вы вошли как 'alice'
```

### Просмотр портфеля

```text
show-portfolio
```

По умолчанию используется USD.

Можно выбрать другую базовую валюту:

```text
show-portfolio --base EUR
```

### Пополнение виртуального USD-баланса

```text
deposit --amount 10000
```

Команда используется для пополнения виртуального USD-кошелька
перед симуляцией торговых операций.

### Покупка валюты

```text
buy --currency BTC --amount 0.01
```

Количество покупаемой валюты указывается в единицах самой валюты.

Стоимость покупки рассчитывается по актуальному курсу и списывается
с USD-кошелька.

### Продажа валюты

```text
sell --currency BTC --amount 0.005
```

Проданная валюта списывается с соответствующего кошелька,
а рассчитанная выручка начисляется на USD-кошелек.

### Получение курса

```text
get-rate --from BTC --to USD
```

Приложение выводит:

- прямой курс;
- обратный курс;
- время обновления;
- источник данных.

Поддерживаются также кросс-курсы:

```text
get-rate --from BTC --to EUR
```

Если прямой пары нет в кеше, курс рассчитывается через USD.

Например:

```text
BTC/EUR = BTC/USD / EUR/USD
```

### Обновление курсов

Обновить данные из всех источников:

```text
update-rates
```

Только CoinGecko:

```text
update-rates --source coingecko
```

Только ExchangeRate-API:

```text
update-rates --source exchangerate
```

### Просмотр кеша курсов

```text
show-rates
```

В другой базовой валюте:

```text
show-rates --base EUR
```

Для конкретной валюты:

```text
show-rates --currency BTC
```

Показать самые дорогие криптовалюты:

```text
show-rates --top 2
```

Параметры можно комбинировать:

```text
show-rates --top 3 --base EUR
```

### Автоматическое обновление курсов

Запуск со стандартным интервалом 300 секунд:

```text
schedule-rates
```

Изменение интервала:

```text
schedule-rates --interval 60
```

Обновление только из CoinGecko:

```text
schedule-rates --interval 60 --source coingecko
```

Для остановки планировщика:

```text
Ctrl+C
```

## Пример полного сценария

```text
register --username alice --password 1234
login --username alice --password 1234

deposit --amount 10000

update-rates

show-rates --top 2

get-rate --from BTC --to USD

buy --currency BTC --amount 0.01

show-portfolio

show-portfolio --base EUR

sell --currency BTC --amount 0.005

show-portfolio
```

## Кеш и TTL

Core Service получает актуальные курсы из:

```text
data/rates.json
```

Для каждой валютной пары сохраняются:

- `rate`;
- `updated_at`;
- `source`.

Пример:

```json
{
  "pairs": {
    "BTC_USD": {
      "rate": 83159.0,
      "updated_at": "2026-10-09T14:39:23.425732Z",
      "source": "CoinGecko"
    }
  },
  "last_refresh": "2026-10-09T14:39:28.778891Z"
}
```

Срок актуальности курса задается в `pyproject.toml`:

```toml
[tool.valutatrade]
rates_ttl_seconds = 300
```

По умолчанию TTL составляет 5 минут.

Если сохраненный курс устарел, Core Service сообщает пользователю
о необходимости выполнить:

```text
update-rates
```

## История курсов

Parser Service сохраняет историю измерений в:

```text
data/exchange_rates.json
```

Пример записи:

```json
{
  "id": "BTC_USD_2026-10-09T14:39:23.425732Z",
  "from_currency": "BTC",
  "to_currency": "USD",
  "rate": 83159.0,
  "timestamp": "2026-10-09T14:39:23.425732Z",
  "source": "CoinGecko"
}
```

Уникальный идентификатор состоит из:

```text
FROM_TO_TIMESTAMP
```

Это предотвращает повторное добавление одного и того же измерения.

Запись выполняется атомарно:

```text
временный файл → rename
```

## Пользователи и пароли

Пользователи сохраняются в:

```text
data/users.json
```

Пароли не сохраняются в открытом виде.

Используются:

- индивидуальная случайная соль;
- SHA-256;
- проверка хеша при авторизации.

Пример структуры:

```json
{
  "user_id": 1,
  "username": "alice",
  "hashed_password": "...",
  "salt": "...",
  "registration_date": "2026-10-09T12:00:00+00:00"
}
```

## Валютная модель

В проекте используется абстрактный класс:

```text
Currency
```

И два наследника:

```text
FiatCurrency
CryptoCurrency
```

Пример представления фиатной валюты:

```text
[FIAT] USD — US Dollar (Issuing: United States)
```

Пример представления криптовалюты:

```text
[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e+12)
```

Получение валюты выполняется через реестр и функцию:

```python
get_currency(code)
```

## Обработка ошибок

В проекте используются пользовательские исключения:

- `InsufficientFundsError`;
- `CurrencyNotFoundError`;
- `ApiRequestError`.

Приложение обрабатывает:

- неизвестные валюты;
- недостаток средств;
- некорректные суммы;
- ошибки внешнего API;
- превышение API-лимита;
- неверный API-ключ;
- сетевые ошибки;
- устаревшие курсы;
- отсутствие требуемого курса.

Пример:

```text
Недостаточно средств: доступно 0.0050 BTC, требуется 100.0000 BTC
```

Пример неизвестной валюты:

```text
Неизвестная валюта 'ABC'
```

## Логирование

Ключевые доменные операции логируются с помощью декоратора:

```python
@log_action(...)
```

Логируются:

- REGISTER;
- LOGIN;
- BUY;
- SELL;
- получение данных Parser Service;
- сохранение обновлений;
- ошибки.

Лог содержит:

- timestamp;
- action;
- username;
- user_id;
- currency;
- amount;
- rate;
- base;
- result;
- тип и текст ошибки при неуспешной операции.

Файл логов:

```text
logs/actions.log
```

Используется `RotatingFileHandler`.

По умолчанию:

```text
maxBytes = 1_000_000
backupCount = 3
```

## Singleton

В проекте Singleton используется для:

- `SettingsLoader`;
- `DatabaseManager`.

`SettingsLoader` обеспечивает единую точку доступа к настройкам.

`DatabaseManager` обеспечивает единый интерфейс работы с JSON-хранилищем.

## Конфигурация

Основные настройки расположены в `pyproject.toml`:

```toml
[tool.valutatrade]
rates_ttl_seconds = 300
default_base_currency = "USD"
log_level = "INFO"
log_format = "%(levelname)s %(asctime)s %(message)s"
```

Настройки Parser Service находятся в:

```text
valutatrade_hub/parser_service/config.py
```

Там задаются:

- URL API;
- базовая валюта;
- список фиатных валют;
- список криптовалют;
- `CRYPTO_ID_MAP`;
- timeout;
- пути к файлам.

Чувствительный API-ключ загружается из переменной окружения.

## Проверка качества кода

В проекте используется Ruff.

Проверка:

```bash
uv run ruff check .
```

Автоматическое исправление поддерживаемых замечаний:

```bash
uv run ruff check . --fix
```

Форматирование:

```bash
uv run ruff format .
```

## Сборка

Проект собирается как полноценный Python-пакет:

```bash
uv build
```

После успешной сборки создаются:

```text
dist/finalproject_ozhiganov_m26_555-0.1.0.tar.gz
dist/finalproject_ozhiganov_m26_555-0.1.0-py3-none-any.whl
```

Каталог `dist/` исключен из Git.

## Демо

Полная демонстрация работы приложения записана с помощью asciinema:

https://asciinema.org/a/izElmESnGOYObA28

В демонстрации показаны:

- регистрация пользователя;
- авторизация;
- пополнение виртуального USD-баланса;
- обновление курсов через Parser Service;
- просмотр актуальных курсов;
- получение кросс-курса;
- покупка BTC;
- просмотр портфеля;
- пересчет портфеля в EUR;
- продажа BTC;
- ошибка недостатка средств;
- обработка неизвестной валюты.

## Технологии

- Python 3.12
- uv
- Ruff
- PrettyTable
- Requests
- python-dotenv
- JSON
- Git
- CoinGecko API
- ExchangeRate-API
- asciinema

