import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CURRENCY_REGISTRY
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.logging_config import setup_logging


def parse_options(tokens: list[str]) -> dict[str, str]:
    """Преобразует аргументы вида --key value в словарь."""
    options = {}
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if not token.startswith("--"):
            raise ValueError(f"Неизвестный аргумент: {token}")

        key = token[2:]

        if index + 1 >= len(tokens):
            raise ValueError(f"Не указано значение для --{key}")

        options[key] = tokens[index + 1]
        index += 2

    return options


def require_option(options: dict[str, str], name: str) -> str:
    """Возвращает обязательный аргумент команды."""
    value = options.get(name)

    if value is None:
        raise ValueError(f"Не указан обязательный аргумент --{name}")

    return value


def print_help() -> None:
    """Показывает список команд."""
    print(
        """
Доступные команды:

register --username <name> --password <password>
login --username <name> --password <password>
show-portfolio [--base USD]
buy --currency <code> --amount <amount>
sell --currency <code> --amount <amount>
get-rate --from <code> --to <code>
help
exit
""".strip()
    )


def handle_register(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает register."""
    username = require_option(options, "username")
    password = require_option(options, "password")

    user = service.register(username, password)

    print(
        f"Пользователь '{user.username}' зарегистрирован "
        f"(id={user.user_id})."
    )
    print(
        f"Войдите: login --username {user.username} "
        "--password ****"
    )


def handle_login(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает login."""
    username = require_option(options, "username")
    password = require_option(options, "password")

    user = service.login(username, password)

    print(f"Вы вошли как '{user.username}'")


def handle_show_portfolio(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает show-portfolio."""
    base = options.get("base", "USD")
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
    print(
        f"ИТОГО: {result['total']:.2f} "
        f"{result['base_currency']}"
    )


def handle_buy(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает buy."""
    currency = require_option(options, "currency")
    amount = float(require_option(options, "amount"))

    result = service.buy(currency, amount)

    print(
        f"Покупка выполнена: "
        f"{result['amount']:.4f} {result['currency']} "
        f"по курсу {result['rate']:.2f} USD/"
        f"{result['currency']}"
    )

    print(
        f"{result['currency']}: "
        f"{result['old_balance']:.4f} → "
        f"{result['new_balance']:.4f}"
    )

    print(
        f"Стоимость покупки: {result['cost']:.2f} USD"
    )


def handle_sell(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает sell."""
    currency = require_option(options, "currency")
    amount = float(require_option(options, "amount"))

    result = service.sell(currency, amount)

    print(
        f"Продажа выполнена: "
        f"{result['amount']:.4f} {result['currency']} "
        f"по курсу {result['rate']:.2f} USD/"
        f"{result['currency']}"
    )

    print(
        f"{result['currency']}: "
        f"{result['old_balance']:.4f} → "
        f"{result['new_balance']:.4f}"
    )

    print(
        f"Выручка: {result['revenue']:.2f} USD"
    )


def handle_get_rate(
    service: TradingService,
    options: dict[str, str],
) -> None:
    """Обрабатывает get-rate."""
    from_code = require_option(options, "from")
    to_code = require_option(options, "to")

    rate = service.get_rate(from_code, to_code)

    print(
        f"Курс {from_code.upper()}→{to_code.upper()}: "
        f"{rate:.8f}"
    )

    if rate != 0:
        print(
            f"Обратный курс "
            f"{to_code.upper()}→{from_code.upper()}: "
            f"{1 / rate:.8f}"
        )


def execute_command(
    service: TradingService,
    command_line: str,
) -> bool:
    """Выполняет одну CLI-команду."""
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

    elif command == "buy":
        handle_buy(service, options)

    elif command == "sell":
        handle_sell(service, options)

    elif command == "get-rate":
        handle_get_rate(service, options)

    elif command == "help":
        print_help()

    elif command in {"exit", "quit"}:
        return False

    else:
        print(
            f"Неизвестная команда '{command}'. "
            "Введите help."
        )

    return True


def main() -> None:
    """Запускает интерактивный CLI ValutaTrade Hub."""
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
            print(
                "Поддерживаемые валюты: "
                + ", ".join(CURRENCY_REGISTRY)
            )

        except InsufficientFundsError as error:
            print(error)

        except ApiRequestError as error:
            print(error)
            print("Повторите попытку позже.")

        except (ValueError, TypeError) as error:
            print(error)

        except KeyboardInterrupt:
            print("\nДо свидания!")
            break


if __name__ == "__main__":
    main()