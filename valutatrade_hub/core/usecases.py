"""Сценарии регистрации, торговли и оценки валютного портфеля."""

from datetime import UTC, datetime
from math import isfinite

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    normalize_currency_code,
    parse_iso_datetime,
    validate_amount,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class TradingService:
    """Управляет пользователями, портфелями и торговыми операциями."""

    def __init__(self) -> None:
        self.settings = SettingsLoader()
        self.database = DatabaseManager()
        self.current_user: User | None = None

    @log_action("REGISTER")
    def register(
        self,
        username: str,
        password: str,
    ) -> User:
        """Создает пользователя и пустой портфель."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        username = username.strip()

        users_file = self.settings.get("USERS_FILE")

        portfolios_file = self.settings.get("PORTFOLIOS_FILE")

        users = self.database.read_json(users_file)

        if any(item["username"] == username for item in users):
            raise ValueError(f"Имя пользователя '{username}' уже занято")

        user_id = (
            max(
                (item["user_id"] for item in users),
                default=0,
            )
            + 1
        )

        user = User(
            user_id=user_id,
            username=username,
            hashed_password="",
            salt="",
            registration_date=datetime.now(UTC),
        )

        user.change_password(password)

        users.append(
            {
                "user_id": user.user_id,
                "username": user.username,
                "hashed_password": user.hashed_password,
                "salt": user.salt,
                "registration_date": (user.registration_date.isoformat()),
            }
        )

        self.database.write_json(
            users_file,
            users,
        )

        portfolios = self.database.read_json(portfolios_file)

        portfolios.append(
            {
                "user_id": user.user_id,
                "wallets": {},
            }
        )

        self.database.write_json(
            portfolios_file,
            portfolios,
        )

        return user

    @log_action("LOGIN")
    def login(
        self,
        username: str,
        password: str,
    ) -> User:
        """Проверяет пароль и создает текущую сессию."""
        users_file = self.settings.get("USERS_FILE")

        users = self.database.read_json(users_file)

        if not isinstance(username, str):
            raise ValueError("Имя пользователя должно быть строкой")

        username = username.strip()

        user_data = next(
            (item for item in users if item["username"] == username),
            None,
        )

        if user_data is None:
            raise ValueError(f"Пользователь '{username}' не найден")

        user = User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            hashed_password=user_data["hashed_password"],
            salt=user_data["salt"],
            registration_date=datetime.fromisoformat(user_data["registration_date"]),
        )

        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        self.current_user = user

        return user

    def _require_login(self) -> User:
        """Возвращает текущего пользователя."""
        if self.current_user is None:
            raise ValueError("Сначала выполните login")

        return self.current_user

    def _load_portfolio(
        self,
        user: User,
    ) -> Portfolio:
        """Загружает пользовательский портфель."""
        portfolios_file = self.settings.get("PORTFOLIOS_FILE")

        portfolios = self.database.read_json(portfolios_file)

        portfolio_data = next(
            (item for item in portfolios if item["user_id"] == user.user_id),
            None,
        )

        wallets: dict[str, Wallet] = {}

        if portfolio_data is not None:
            for code, wallet_data in portfolio_data["wallets"].items():
                wallets[code] = Wallet(
                    currency_code=code,
                    balance=wallet_data["balance"],
                )

        return Portfolio(
            user=user,
            wallets=wallets,
        )

    def _save_portfolio(
        self,
        portfolio: Portfolio,
    ) -> None:
        """Сохраняет пользовательский портфель."""
        portfolios_file = self.settings.get("PORTFOLIOS_FILE")

        portfolios = self.database.read_json(portfolios_file)

        wallets_data = {
            code: {
                "balance": wallet.balance,
            }
            for code, wallet in portfolio.wallets.items()
        }

        for item in portfolios:
            if item["user_id"] == portfolio.user.user_id:
                item["wallets"] = wallets_data
                break
        else:
            portfolios.append(
                {
                    "user_id": (portfolio.user.user_id),
                    "wallets": wallets_data,
                }
            )

        self.database.write_json(
            portfolios_file,
            portfolios,
        )

    @staticmethod
    def _get_cached_quote(
        from_code: str,
        to_code: str,
        pairs: dict,
        ttl_seconds: int,
    ) -> dict | None:
        """Возвращает прямой или обратный курс из кеша."""
        if from_code == to_code:
            return {
                "rate": 1.0,
                "updated_at": None,
                "source": "local",
            }

        direct_pair = f"{from_code}_{to_code}"

        reverse_pair = f"{to_code}_{from_code}"

        is_reverse = False

        if direct_pair in pairs:
            pair_name = direct_pair

        elif reverse_pair in pairs:
            pair_name = reverse_pair
            is_reverse = True

        else:
            return None

        pair_data = pairs[pair_name]

        try:
            rate = float(pair_data["rate"])

        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ) as error:
            raise ApiRequestError(f"некорректный курс {pair_name}") from error

        if not isfinite(rate) or rate <= 0:
            raise ApiRequestError(f"некорректный курс {pair_name}")

        if is_reverse:
            rate = 1 / rate

        if not isfinite(rate) or rate <= 0:
            raise ApiRequestError(f"некорректный обратный курс {pair_name}")

        updated_at = pair_data.get("updated_at")

        if (
            not isinstance(
                updated_at,
                str,
            )
            or not updated_at
        ):
            raise ApiRequestError(f"для курса {pair_name} отсутствует время обновления")

        try:
            updated_datetime = parse_iso_datetime(updated_at)

            if updated_datetime.tzinfo is None:
                updated_datetime = updated_datetime.replace(tzinfo=UTC)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ApiRequestError(
                f"некорректное время обновления {pair_name}"
            ) from error

        age_seconds = (datetime.now(UTC) - updated_datetime).total_seconds()

        if age_seconds > ttl_seconds:
            raise ApiRequestError(f"курс {pair_name} устарел. Выполните update-rates")

        return {
            "rate": rate,
            "updated_at": (updated_datetime.isoformat()),
            "source": pair_data.get(
                "source",
                "unknown",
            ),
        }

    def get_rate_info(
        self,
        from_code: str,
        to_code: str,
    ) -> dict:
        """
        Возвращает курс и метаданные.

        Если прямой пары нет, рассчитывает
        кросс-курс через USD.
        """
        source = normalize_currency_code(from_code)

        target = normalize_currency_code(to_code)

        get_currency(source)
        get_currency(target)

        if source == target:
            return {
                "from": source,
                "to": target,
                "rate": 1.0,
                "updated_at": None,
                "source": "local",
            }

        rates_file = self.settings.get("RATES_FILE")

        ttl_seconds = self.settings.get(
            "RATES_TTL_SECONDS",
            300,
        )

        rates_data = self.database.read_json(rates_file)

        pairs = rates_data.get(
            "pairs",
            {},
        )

        quote = self._get_cached_quote(
            source,
            target,
            pairs,
            ttl_seconds,
        )

        if quote is None:
            source_quote = self._get_cached_quote(
                source,
                "USD",
                pairs,
                ttl_seconds,
            )

            target_quote = self._get_cached_quote(
                target,
                "USD",
                pairs,
                ttl_seconds,
            )

            if source_quote is None or target_quote is None:
                raise ApiRequestError(
                    f"курс {source}->{target} недоступен. Выполните update-rates"
                )

            rate = source_quote["rate"] / target_quote["rate"]

            if not isfinite(rate) or rate <= 0:
                raise ApiRequestError(f"некорректный расчет курса {source}->{target}")

            timestamps = [
                item["updated_at"]
                for item in (
                    source_quote,
                    target_quote,
                )
                if item["updated_at"] is not None
            ]

            if timestamps:
                updated_at = min(
                    timestamps,
                    key=parse_iso_datetime,
                )
            else:
                updated_at = None

            sources = list(
                dict.fromkeys(
                    item["source"]
                    for item in (
                        source_quote,
                        target_quote,
                    )
                    if item["source"] != "local"
                )
            )

            quote = {
                "rate": rate,
                "updated_at": updated_at,
                "source": (" / ".join(sources) or "local"),
            }

        return {
            "from": source,
            "to": target,
            **quote,
        }

    def get_rate(
        self,
        from_code: str,
        to_code: str,
    ) -> float:
        """Возвращает только числовое значение курса."""
        rate_info = self.get_rate_info(
            from_code,
            to_code,
        )

        return float(rate_info["rate"])

    def deposit_usd(
        self,
        amount: float,
    ) -> dict:
        """Пополняет виртуальный USD-кошелек."""
        user = self._require_login()

        amount = validate_amount(amount)

        portfolio = self._load_portfolio(user)

        usd_wallet = portfolio.get_wallet("USD")

        if usd_wallet is None:
            usd_wallet = portfolio.add_currency("USD")

        old_balance = usd_wallet.balance

        usd_wallet.deposit(amount)

        self._save_portfolio(portfolio)

        return {
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": usd_wallet.balance,
        }

    @log_action(
        "BUY",
        verbose=True,
    )
    def buy(
        self,
        currency_code: str,
        amount: float,
    ) -> dict:
        """Покупает валюту за USD."""
        user = self._require_login()

        code = normalize_currency_code(currency_code)

        amount = validate_amount(amount)

        get_currency(code)

        if code == "USD":
            raise ValueError("Нельзя купить USD за USD")

        portfolio = self._load_portfolio(user)

        usd_wallet = portfolio.get_wallet("USD")

        if usd_wallet is None:
            usd_wallet = portfolio.add_currency("USD")

        target_wallet = portfolio.get_wallet(code)

        if target_wallet is None:
            target_wallet = portfolio.add_currency(code)

        rate = self.get_rate(
            code,
            "USD",
        )

        cost = amount * rate

        if not isfinite(cost) or cost <= 0:
            raise ValueError("Некорректная стоимость покупки")

        old_balance = target_wallet.balance

        old_usd_balance = usd_wallet.balance

        usd_wallet.withdraw(cost)

        target_wallet.deposit(amount)

        self._save_portfolio(portfolio)

        return {
            "currency": code,
            "amount": amount,
            "rate": rate,
            "base": "USD",
            "cost": cost,
            "old_balance": old_balance,
            "new_balance": (target_wallet.balance),
            "old_usd_balance": (old_usd_balance),
            "new_usd_balance": (usd_wallet.balance),
        }

    @log_action(
        "SELL",
        verbose=True,
    )
    def sell(
        self,
        currency_code: str,
        amount: float,
    ) -> dict:
        """Продает валюту и зачисляет выручку в USD."""
        user = self._require_login()

        code = normalize_currency_code(currency_code)

        amount = validate_amount(amount)

        get_currency(code)

        if code == "USD":
            raise ValueError("Нельзя продать USD за USD")

        portfolio = self._load_portfolio(user)

        source_wallet = portfolio.get_wallet(code)

        if source_wallet is None:
            raise ValueError(
                f"У вас нет кошелька "
                f"'{code}'. "
                "Добавьте валюту: "
                "она создается автоматически "
                "при первой покупке."
            )

        rate = self.get_rate(
            code,
            "USD",
        )

        revenue = amount * rate

        if not isfinite(revenue) or revenue <= 0:
            raise ValueError("Некорректная сумма выручки")

        old_balance = source_wallet.balance

        source_wallet.withdraw(amount)

        usd_wallet = portfolio.get_wallet("USD")

        if usd_wallet is None:
            usd_wallet = portfolio.add_currency("USD")

        old_usd_balance = usd_wallet.balance

        usd_wallet.deposit(revenue)

        self._save_portfolio(portfolio)

        return {
            "currency": code,
            "amount": amount,
            "rate": rate,
            "base": "USD",
            "revenue": revenue,
            "old_balance": old_balance,
            "new_balance": (source_wallet.balance),
            "old_usd_balance": (old_usd_balance),
            "new_usd_balance": (usd_wallet.balance),
        }

    def show_portfolio(
        self,
        base_currency: str = "USD",
    ) -> dict:
        """Возвращает портфель и стоимость в базовой валюте."""
        user = self._require_login()

        base = normalize_currency_code(base_currency)

        get_currency(base)

        portfolio = self._load_portfolio(user)

        rows = []
        total = 0.0

        for (
            code,
            wallet,
        ) in portfolio.wallets.items():
            if code == base:
                value = wallet.balance

            else:
                rate = self.get_rate(
                    code,
                    base,
                )

                value = wallet.balance * rate

            if not isfinite(value) or value < 0:
                raise ValueError(f"Некорректная стоимость кошелька {code}")

            rows.append(
                {
                    "currency": code,
                    "balance": (wallet.balance),
                    "value": value,
                }
            )

            total += value

        if not isfinite(total) or total < 0:
            raise ValueError("Некорректная итоговая стоимость портфеля")

        return {
            "username": user.username,
            "base_currency": base,
            "wallets": rows,
            "total": total,
        }
