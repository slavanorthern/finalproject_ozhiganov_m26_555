"""Консольный интерфейс приложения ValutaTrade Hub."""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CURRENCY_REGISTRY
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.rate_views import get_cached_rates
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import run_scheduler
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def parse_options(tokens: list[str]) -> dict[str, str]:
    """Преобразует аргументы --key value в словарь."""
    options = {}
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if not token.startswith("--"):
            raise ValueError(f"Неизвестный аргумент: {token}")

        key = token[2:]

        if not key:
            raise ValueError("Некорректное имя аргумента")

        if index + 1 >= len(tokens):
            raise ValueError(f"Не указано значение для --{key}")

        value = tokens[index + 1]

        if value.startswith("--"):
            raise ValueError(f"Не указано значение для --{key}")

        if key in options:
            raise ValueError(f"Аргумент --{key} указан повторно")

        options[key] = value
        index += 2

    return options


def require_option(options: dict[str, str], name: str) -> str:
    """Возвращает обязательный параметр команды."""
    value = options.get(name)

    if value is None:
        raise ValueError(f"Не указан обязательный аргумент --{name}")

    return value


def print_help() -> None:
    """Показывает справку по командам."""
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
    """Регистрирует пользователя."""
    username = require_option(options, "username")
    password = require_option(options, "password")
    user = service.register(username, password)

    print(f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}).")
    print(f"Войдите: login --username {user.username} --password ****")


def handle_login(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Авторизует пользователя."""
    username = require_option(options, "username")
    password = require_option(options, "password")

    user = service.login(username, password)
    print(f"Вы вошли как '{user.username}'")


def handle_show_portfolio(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Показывает стоимость портфеля."""
    settings = SettingsLoader()
    default_base = settings.get("DEFAULT_BASE_CURRENCY", "USD")
    base = options.get("base", default_base)

    result = service.show_portfolio(base)

    print(
        f"Портфель пользователя '{result['username']}' "
        f"(база: {result['base_currency']}):"
    )

    if not result["wallets"]:
        print("Портфель пуст")
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

    print(table)
    print(f"ИТОГО: {result['total']:.2f} {result['base_currency']}")


def handle_deposit(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Пополняет виртуальный USD-баланс."""
    amount = float(require_option(options, "amount"))
    result = service.deposit_usd(amount)

    print(f"USD-баланс пополнен на {result['amount']:.2f} USD")
    print(f"USD: {result['old_balance']:.2f} → {result['new_balance']:.2f}")


def handle_buy(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Покупает валюту."""
    currency = require_option(options, "currency")
    amount = float(require_option(options, "amount"))
    result = service.buy(currency, amount)

    print(f"Покупка выполнена: {result['amount']:.4f} {result['currency']}")
    print(f"Курс: {result['rate']:.8f} USD/{result['currency']}")
    print(f"Стоимость покупки: {result['cost']:.2f} USD")
    print(
        f"{result['currency']}: "
        f"{result['old_balance']:.4f} → "
        f"{result['new_balance']:.4f}"
    )
    print(f"USD: {result['old_usd_balance']:.2f} → {result['new_usd_balance']:.2f}")


def handle_sell(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Продает валюту."""
    currency = require_option(options, "currency")
    amount = float(require_option(options, "amount"))
    result = service.sell(currency, amount)

    print(f"Продажа выполнена: {result['amount']:.4f} {result['currency']}")
    print(f"Курс: {result['rate']:.8f} USD/{result['currency']}")
    print(f"Выручка: {result['revenue']:.2f} USD")
    print(
        f"{result['currency']}: "
        f"{result['old_balance']:.4f} → "
        f"{result['new_balance']:.4f}"
    )
    print(f"USD: {result['old_usd_balance']:.2f} → {result['new_usd_balance']:.2f}")


def handle_get_rate(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Показывает курс валютной пары."""
    from_code = require_option(options, "from")
    to_code = require_option(options, "to")

    result = service.get_rate_info(from_code, to_code)
    rate = float(result["rate"])

    print(f"Курс {result['from']}→{result['to']}: {rate:.8f}")

    if rate != 0:
        print(f"Обратный курс {result['to']}→{result['from']}: {1 / rate:.8f}")

    if result["updated_at"] is not None:
        print(f"Обновлено: {result['updated_at']}")

    print(f"Источник: {result['source']}")


def build_rates_updater() -> RatesUpdater:
    """Создает Parser Service и его зависимости."""
    config = ParserConfig()

    clients = [
        CoinGeckoClient(config),
        ExchangeRateApiClient(config),
    ]

    storage = RatesStorage()

    return RatesUpdater(
        clients=clients,
        storage=storage,
        config=config,
    )


def handle_update_rates(options: dict[str, str]) -> None:
    """Запускает обновление курсов."""
    source = options.get("source")
    updater = build_rates_updater()
    result = updater.run_update(source=source)

    if result["errors"]:
        print("Обновление завершено с отдельными ошибками.")
    else:
        print("Обновление курсов завершено.")

    print(f"Обновлено курсов: {result['updated_count']}")
    print(f"Последнее обновление: {result['last_refresh']}")

    if result["errors"]:
        print("Ошибки:")
        for error in result["errors"]:
            print(f"- {error}")


def handle_schedule_rates(options: dict[str, str]) -> None:
    """Запускает периодическое обновление курсов."""
    interval_text = options.get("interval", "300")

    try:
        interval = int(interval_text)
    except ValueError as error:
        raise ValueError("'interval' должен быть целым числом секунд") from error

    if interval <= 0:
        raise ValueError("'interval' должен быть положительным числом")

    source = options.get("source")
    updater = build_rates_updater()

    print("Планировщик запущен.")
    print(f"Интервал: {interval} сек.")
    print(f"Источник: {source}" if source else "Источники: все")
    print("Для остановки нажмите Ctrl+C.")

    run_scheduler(
        updater=updater,
        interval_seconds=interval,
        source=source,
    )


def handle_show_rates(options: dict[str, str]) -> None:
    """Показывает сохраненные курсы валют."""
    settings = SettingsLoader()
    config = ParserConfig()

    base = options.get(
        "base",
        settings.get("DEFAULT_BASE_CURRENCY", "USD"),
    )
    currency = options.get("currency")
    top_text = options.get("top")

    top = None

    if top_text is not None:
        try:
            top = int(top_text)
        except ValueError as error:
            raise ValueError("'top' должен быть целым числом") from error

    result = get_cached_rates(
        base_currency=base,
        currency_filter=currency,
        top=top,
        crypto_currencies=config.crypto_currencies,
    )

    rows = result["rows"]

    if not rows:
        if currency:
            print(f"Курс для '{currency.upper()}' в базе '{result['base']}' не найден.")
        elif top is not None:
            print("Криптовалютные курсы не найдены в кеше.")
        else:
            print(
                "Локальный кеш курсов пуст или подходящих "
                "пар нет. Выполните 'update-rates'."
            )
        return

    print(
        f"Rates from cache "
        f"(base={result['base']}, "
        f"updated at {result['last_refresh']}):"
    )

    table = PrettyTable()
    table.field_names = [
        "Пара",
        "Курс",
        "Обновлено",
        "Источник",
        "Статус",
    ]

    for row in rows:
        table.add_row(
            [
                row["pair"],
                f"{row['rate']:.8f}",
                row["updated_at"],
                row["source"],
                row["status"],
            ]
        )

    print(table)


def execute_command(
    service: TradingService,
    command_line: str,
) -> bool:
    """Выполняет одну консольную команду."""
    tokens = shlex.split(command_line)

    if not tokens:
        return True

    command = tokens[0].lower()
    options = parse_options(tokens[1:])

    if command == "register":
        handle_register(service, options)

    elif command == "login":
        handle_login(service, options)

    elif command == "show-portfolio":
        handle_show_portfolio(service, options)

    elif command == "deposit":
        handle_deposit(service, options)

    elif command == "buy":
        handle_buy(service, options)

    elif command == "sell":
        handle_sell(service, options)

    elif command == "get-rate":
        handle_get_rate(service, options)

    elif command == "update-rates":
        handle_update_rates(options)

    elif command == "schedule-rates":
        handle_schedule_rates(options)

    elif command == "show-rates":
        handle_show_rates(options)

    elif command == "help":
        print_help()

    elif command in {"exit", "quit"}:
        return False

    else:
        print(f"Неизвестная команда '{command}'. Введите help.")

    return True


def main() -> None:
    """Запускает интерактивный CLI."""
    setup_logging()
    service = TradingService()

    print("ValutaTrade Hub")
    print("Введите help для списка команд.")

    while True:
        try:
            command_line = input("> ")

            if not execute_command(service, command_line):
                print("До свидания!")
                break

        except CurrencyNotFoundError as error:
            print(error)
            print("Поддерживаемые валюты: " + ", ".join(CURRENCY_REGISTRY))

        except InsufficientFundsError as error:
            print(error)

        except ApiRequestError as error:
            print(error)
            print("Повторите попытку позже или выполните update-rates.")

        except (ValueError, TypeError) as error:
            print(error)

        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break


if __name__ == "__main__":
    main()
