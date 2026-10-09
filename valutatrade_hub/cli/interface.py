"""Консольный интерфейс приложения ValutaTrade Hub."""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import (
    CURRENCY_REGISTRY,
    get_currency,
)
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import run_scheduler
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def parse_options(
    tokens: list[str],
) -> dict[str, str]:
    """Преобразует аргументы вида --key value в словарь."""
    options: dict[str, str] = {}
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if not token.startswith("--"):
            raise ValueError(
                f"Неизвестный аргумент: {token}"
            )

        key = token[2:]

        if not key:
            raise ValueError(
                "Некорректное имя аргумента"
            )

        if index + 1 >= len(tokens):
            raise ValueError(
                f"Не указано значение для --{key}"
            )

        value = tokens[index + 1]

        if value.startswith("--"):
            raise ValueError(
                f"Не указано значение для --{key}"
            )

        options[key] = value
        index += 2

    return options


def require_option(
    options: dict[str, str],
    name: str,
) -> str:
    """Возвращает обязательный аргумент CLI."""
    value = options.get(name)

    if value is None:
        raise ValueError(
            f"Не указан обязательный аргумент --{name}"
        )

    return value


def print_help() -> None:
    """Показывает список доступных команд."""
    print(
        """
Доступные команды:

register --username <name> --password <password>
login --username <name> --password <password>

show-portfolio [--base USD]

deposit --amount <amount>
buy --currency <code> --amount <amount>
sell --currency <code> --amount <amount>

get-rate --from <code> --to <code>

update-rates [--source coingecko|exchangerate]
schedule-rates [--interval 300] [--source coingecko|exchangerate]

show-rates [--base USD] [--currency BTC] [--top 2]

help
exit
""".strip()
    )


def handle_register(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает команду register."""
    username = require_option(
        options,
        "username",
    )

    password = require_option(
        options,
        "password",
    )

    user = service.register(
        username,
        password,
    )

    print(
        f"Пользователь '{user.username}' "
        f"зарегистрирован (id={user.user_id})."
    )

    print(
        f"Войдите: login --username "
        f"{user.username} --password ****"
    )


def handle_login(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает команду login."""
    username = require_option(
        options,
        "username",
    )

    password = require_option(
        options,
        "password",
    )

    user = service.login(
        username,
        password,
    )

    print(
        f"Вы вошли как '{user.username}'"
    )


def handle_show_portfolio(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Показывает портфель пользователя."""
    base = options.get(
        "base",
        "USD",
    )

    result = service.show_portfolio(
        base
    )

    print(
        f"Портфель пользователя "
        f"'{result['username']}' "
        f"(база: {result['base_currency']}):"
    )

    if not result["wallets"]:
        print(
            "Портфель пуст"
        )
        return

    table = PrettyTable()

    table.field_names = [
        "Валюта",
        "Баланс",
        f"Стоимость ({result['base_currency']})",
    ]

    for wallet in result["wallets"]:
        table.add_row(
            [
                wallet["currency"],
                f"{wallet['balance']:.4f}",
                f"{wallet['value']:.2f}",
            ]
        )

    print(
        table
    )

    print(
        f"ИТОГО: "
        f"{result['total']:.2f} "
        f"{result['base_currency']}"
    )


def handle_deposit(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Пополняет виртуальный USD-баланс."""
    amount = float(
        require_option(
            options,
            "amount",
        )
    )

    result = service.deposit_usd(
        amount
    )

    print(
        f"USD-баланс пополнен на "
        f"{result['amount']:.2f} USD"
    )

    print(
        f"USD: "
        f"{result['old_balance']:.2f} → "
        f"{result['new_balance']:.2f}"
    )


def handle_buy(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает покупку валюты."""
    currency = require_option(
        options,
        "currency",
    )

    amount = float(
        require_option(
            options,
            "amount",
        )
    )

    result = service.buy(
        currency,
        amount,
    )

    print(
        f"Покупка выполнена: "
        f"{result['amount']:.4f} "
        f"{result['currency']}"
    )

    print(
        f"Курс: "
        f"{result['rate']:.8f} "
        f"USD/{result['currency']}"
    )

    print(
        f"Стоимость покупки: "
        f"{result['cost']:.2f} USD"
    )

    print(
        f"{result['currency']}: "
        f"{result['old_balance']:.4f} → "
        f"{result['new_balance']:.4f}"
    )

    print(
        f"USD: "
        f"{result['old_usd_balance']:.2f} → "
        f"{result['new_usd_balance']:.2f}"
    )


def handle_sell(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает продажу валюты."""
    currency = require_option(
        options,
        "currency",
    )

    amount = float(
        require_option(
            options,
            "amount",
        )
    )

    result = service.sell(
        currency,
        amount,
    )

    print(
        f"Продажа выполнена: "
        f"{result['amount']:.4f} "
        f"{result['currency']}"
    )

    print(
        f"Курс: "
        f"{result['rate']:.8f} "
        f"USD/{result['currency']}"
    )

    print(
        f"Выручка: "
        f"{result['revenue']:.2f} USD"
    )

    print(
        f"{result['currency']}: "
        f"{result['old_balance']:.4f} → "
        f"{result['new_balance']:.4f}"
    )

    print(
        f"USD: "
        f"{result['old_usd_balance']:.2f} → "
        f"{result['new_usd_balance']:.2f}"
    )


def handle_get_rate(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Показывает текущий курс валют."""
    from_code = require_option(
        options,
        "from",
    )

    to_code = require_option(
        options,
        "to",
    )

    result = service.get_rate_info(
        from_code,
        to_code,
    )

    rate = float(
        result["rate"]
    )

    print(
        f"Курс "
        f"{result['from']}→{result['to']}: "
        f"{rate:.8f}"
    )

    if rate != 0:
        print(
            f"Обратный курс "
            f"{result['to']}→"
            f"{result['from']}: "
            f"{1 / rate:.8f}"
        )

    if result["updated_at"] is not None:
        print(
            f"Обновлено: "
            f"{result['updated_at']}"
        )

    print(
        f"Источник: "
        f"{result['source']}"
    )


def build_rates_updater() -> RatesUpdater:
    """Создает Parser Service и его зависимости."""
    config = ParserConfig()

    clients = [
        CoinGeckoClient(
            config
        ),
        ExchangeRateApiClient(
            config
        ),
    ]

    storage = RatesStorage()

    return RatesUpdater(
        clients=clients,
        storage=storage,
        config=config,
    )


def handle_update_rates(
    options: dict[str, str],
) -> None:
    """Запускает ручное обновление курсов."""
    source = options.get(
        "source"
    )

    updater = build_rates_updater()

    result = updater.run_update(
        source=source,
    )

    if result["errors"]:
        print(
            "Обновление завершено "
            "с отдельными ошибками."
        )
    else:
        print(
            "Обновление курсов завершено."
        )

    print(
        f"Обновлено курсов: "
        f"{result['updated_count']}"
    )

    print(
        f"Последнее обновление: "
        f"{result['last_refresh']}"
    )

    if result["errors"]:
        print(
            "Ошибки:"
        )

        for error in result["errors"]:
            print(
                f"- {error}"
            )


def handle_schedule_rates(
    options: dict[str, str],
) -> None:
    """Запускает периодическое обновление курсов."""
    interval_text = options.get(
        "interval",
        "300",
    )

    try:
        interval = int(
            interval_text
        )

    except ValueError as error:
        raise ValueError(
            "'interval' должен быть "
            "целым числом секунд"
        ) from error

    if interval <= 0:
        raise ValueError(
            "'interval' должен быть "
            "положительным числом"
        )

    source = options.get(
        "source"
    )

    updater = build_rates_updater()

    print(
        "Планировщик запущен."
    )

    print(
        f"Интервал: {interval} сек."
    )

    if source:
        print(
            f"Источник: {source}"
        )
    else:
        print(
            "Источники: все"
        )

    print(
        "Для остановки нажмите Ctrl+C."
    )

    run_scheduler(
        updater=updater,
        interval_seconds=interval,
        source=source,
    )


def get_cached_usd_rate(
    currency_code: str,
    pairs: dict,
) -> tuple[float, dict]:
    """Возвращает стоимость валюты в USD из кеша."""
    code = currency_code.upper()

    if code == "USD":
        return (
            1.0,
            {
                "updated_at": None,
                "source": "local",
            },
        )

    direct_pair = (
        f"{code}_USD"
    )

    reverse_pair = (
        f"USD_{code}"
    )

    if direct_pair in pairs:
        item = pairs[
            direct_pair
        ]

        return (
            float(
                item["rate"]
            ),
            item,
        )

    if reverse_pair in pairs:
        item = pairs[
            reverse_pair
        ]

        reverse_rate = float(
            item["rate"]
        )

        if reverse_rate <= 0:
            raise ValueError(
                f"Некорректный курс "
                f"{reverse_pair}"
            )

        return (
            1 / reverse_rate,
            item,
        )

    raise ValueError(
        f"В кеше отсутствует курс "
        f"{code} относительно USD"
    )


def handle_show_rates(
    options: dict[str, str],
) -> None:
    """Показывает курсы из локального кеша."""
    config = ParserConfig()
    storage = RatesStorage()

    data = storage.read_json(
        config.rates_file_path,
        {
            "pairs": {},
            "last_refresh": None,
        },
    )

    pairs = data.get(
        "pairs",
        {},
    )

    if not pairs:
        print(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates'."
        )
        return

    base = options.get(
        "base",
        "USD",
    ).upper()

    get_currency(
        base
    )

    currency_filter = options.get(
        "currency"
    )

    if currency_filter is not None:
        currency_filter = (
            currency_filter.upper()
        )

        get_currency(
            currency_filter
        )

    base_usd_rate, base_item = (
        get_cached_usd_rate(
            base,
            pairs,
        )
    )

    currencies = {
        "USD"
    }

    for pair in pairs:
        from_code, to_code = pair.split(
            "_",
            1,
        )

        currencies.add(
            from_code
        )

        currencies.add(
            to_code
        )

    rows = []

    for currency in sorted(
        currencies
    ):
        if currency == base:
            continue

        if (
            currency_filter
            and currency
            != currency_filter
        ):
            continue

        try:
            currency_usd_rate, item = (
                get_cached_usd_rate(
                    currency,
                    pairs,
                )
            )

        except ValueError:
            continue

        rate = (
            currency_usd_rate
            / base_usd_rate
        )

        info_item = (
            item
            if currency != "USD"
            else base_item
        )

        rows.append(
            {
                "currency": currency,
                "pair": (
                    f"{currency}_{base}"
                ),
                "rate": rate,
                "updated_at": (
                    info_item.get(
                        "updated_at"
                    )
                    or data.get(
                        "last_refresh"
                    )
                ),
                "source": (
                    info_item.get(
                        "source",
                        "calculated",
                    )
                ),
            }
        )

    top = options.get(
        "top"
    )

    if top is not None:
        try:
            top_count = int(
                top
            )

        except ValueError as error:
            raise ValueError(
                "'top' должен быть "
                "целым числом"
            ) from error

        if top_count <= 0:
            raise ValueError(
                "'top' должен быть "
                "положительным числом"
            )

        crypto_codes = set(
            config.crypto_currencies
        )

        rows = [
            row
            for row in rows
            if row["currency"]
            in crypto_codes
        ]

        rows.sort(
            key=lambda row: row["rate"],
            reverse=True,
        )

        rows = rows[
            :top_count
        ]

    else:
        rows.sort(
            key=lambda row: row["pair"]
        )

    if not rows:
        if currency_filter:
            print(
                f"Курс для "
                f"'{currency_filter}' "
                f"в базе '{base}' "
                "не найден."
            )

        elif top is not None:
            print(
                "Криптовалютные курсы "
                "не найдены в кеше."
            )

        else:
            print(
                "Подходящие курсы "
                "не найдены."
            )

        return

    print(
        "Rates from cache "
        f"(base={base}, "
        f"updated at "
        f"{data.get('last_refresh')}):"
    )

    table = PrettyTable()

    table.field_names = [
        "Пара",
        "Курс",
        "Обновлено",
        "Источник",
    ]

    for row in rows:
        table.add_row(
            [
                row["pair"],
                f"{row['rate']:.8f}",
                row["updated_at"],
                row["source"],
            ]
        )

    print(
        table
    )


def execute_command(
    service: TradingService,
    command_line: str,
) -> bool:
    """Выполняет одну CLI-команду."""
    tokens = shlex.split(
        command_line
    )

    if not tokens:
        return True

    command = tokens[
        0
    ].lower()

    options = parse_options(
        tokens[1:]
    )

    if command == "register":
        handle_register(
            service,
            options,
        )

    elif command == "login":
        handle_login(
            service,
            options,
        )

    elif command == "show-portfolio":
        handle_show_portfolio(
            service,
            options,
        )

    elif command == "deposit":
        handle_deposit(
            service,
            options,
        )

    elif command == "buy":
        handle_buy(
            service,
            options,
        )

    elif command == "sell":
        handle_sell(
            service,
            options,
        )

    elif command == "get-rate":
        handle_get_rate(
            service,
            options,
        )

    elif command == "update-rates":
        handle_update_rates(
            options,
        )

    elif command == "schedule-rates":
        handle_schedule_rates(
            options,
        )

    elif command == "show-rates":
        handle_show_rates(
            options,
        )

    elif command == "help":
        print_help()

    elif command in {
        "exit",
        "quit",
    }:
        return False

    else:
        print(
            f"Неизвестная команда "
            f"'{command}'. "
            "Введите help."
        )

    return True


def main() -> None:
    """Запускает интерактивный CLI."""
    setup_logging()

    service = TradingService()

    print(
        "ValutaTrade Hub"
    )

    print(
        "Введите help для списка команд."
    )

    while True:
        try:
            command_line = input(
                "> "
            )

            if not execute_command(
                service,
                command_line,
            ):
                print(
                    "До свидания!"
                )
                break

        except CurrencyNotFoundError as error:
            print(
                error
            )

            print(
                "Поддерживаемые валюты: "
                + ", ".join(
                    CURRENCY_REGISTRY
                )
            )

        except InsufficientFundsError as error:
            print(
                error
            )

        except ApiRequestError as error:
            print(
                error
            )

            print(
                "Повторите попытку позже "
                "или выполните update-rates."
            )

        except (
            ValueError,
            TypeError,
        ) as error:
            print(
                error
            )

        except KeyboardInterrupt:
            print(
                "\nДо свидания!"
            )
            break


if __name__ == "__main__":
    main()