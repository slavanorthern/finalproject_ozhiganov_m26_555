from datetime import UTC, datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import normalize_currency_code, validate_amount
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class TradingService:
    """Основная бизнес-логика приложения."""

    def __init__(self) -> None:
        self.settings = SettingsLoader()
        self.database = DatabaseManager()
        self.current_user: User | None = None

    @log_action("REGISTER")
    def register(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        username = username.strip()

        users_file = self.settings.get("USERS_FILE")
        portfolios_file = self.settings.get("PORTFOLIOS_FILE")

        users = self.database.read_json(users_file)

        if any(user["username"] == username for user in users):
            raise ValueError(
                f"Имя пользователя '{username}' уже занято"
            )

        user_id = max(
            (user["user_id"] for user in users),
            default=0,
        ) + 1

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
                "registration_date": (
                    user.registration_date.isoformat()
                ),
            }
        )

        self.database.write_json(
            users_file,
            users,
        )

        portfolios = self.database.read_json(
            portfolios_file
        )

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
        """Выполняет вход пользователя."""
        users_file = self.settings.get("USERS_FILE")
        users = self.database.read_json(users_file)

        user_data = next(
            (
                user
                for user in users
                if user["username"] == username
            ),
            None,
        )

        if user_data is None:
            raise ValueError(
                f"Пользователь '{username}' не найден"
            )

        user = User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            hashed_password=user_data["hashed_password"],
            salt=user_data["salt"],
            registration_date=datetime.fromisoformat(
                user_data["registration_date"]
            ),
        )

        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        self.current_user = user

        return user

    def _require_login(self) -> User:
        """Проверяет наличие активной сессии."""
        if self.current_user is None:
            raise ValueError("Сначала выполните login")

        return self.current_user

    def _load_portfolio(
        self,
        user: User,
    ) -> Portfolio:
        """Загружает портфель пользователя из JSON."""
        portfolios_file = self.settings.get(
            "PORTFOLIOS_FILE"
        )

        portfolios = self.database.read_json(
            portfolios_file
        )

        portfolio_data = next(
            (
                portfolio
                for portfolio in portfolios
                if portfolio["user_id"] == user.user_id
            ),
            None,
        )

        wallets: dict[str, Wallet] = {}

        if portfolio_data is not None:
            for code, wallet_data in (
                portfolio_data["wallets"].items()
            ):
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
        """Сохраняет портфель пользователя в JSON."""
        portfolios_file = self.settings.get(
            "PORTFOLIOS_FILE"
        )

        portfolios = self.database.read_json(
            portfolios_file
        )

        wallets_data = {
            code: {
                "balance": wallet.balance,
            }
            for code, wallet in portfolio.wallets.items()
        }

        updated = False

        for item in portfolios:
            if item["user_id"] == portfolio.user.user_id:
                item["wallets"] = wallets_data
                updated = True
                break

        if not updated:
            portfolios.append(
                {
                    "user_id": portfolio.user.user_id,
                    "wallets": wallets_data,
                }
            )

        self.database.write_json(
            portfolios_file,
            portfolios,
        )

    def get_rate(
        self,
        from_code: str,
        to_code: str,
    ) -> float:
        """Возвращает курс одной валюты к другой."""
        source = normalize_currency_code(from_code)
        target = normalize_currency_code(to_code)

        get_currency(source)
        get_currency(target)

        if source == target:
            return 1.0

        rates_file = self.settings.get("RATES_FILE")
        rates_data = self.database.read_json(
            rates_file
        )

        pairs = rates_data.get("pairs", {})

        direct_pair = f"{source}_{target}"

        if direct_pair in pairs:
            return float(
                pairs[direct_pair]["rate"]
            )

        reverse_pair = f"{target}_{source}"

        if reverse_pair in pairs:
            reverse_rate = float(
                pairs[reverse_pair]["rate"]
            )

            if reverse_rate == 0:
                raise ValueError(
                    f"Некорректный курс для {reverse_pair}"
                )

            return 1 / reverse_rate

        raise ValueError(
            f"Не удалось получить курс для "
            f"{source}->{target}"
        )

    @log_action("BUY")
    def buy(
        self,
        currency_code: str,
        amount: float,
    ) -> dict:
        """Покупает валюту за USD."""
        user = self._require_login()

        code = normalize_currency_code(
            currency_code
        )
        amount = validate_amount(amount)

        get_currency(code)

        if code == "USD":
            raise ValueError(
                "Нельзя купить USD за USD"
            )

        portfolio = self._load_portfolio(user)

        usd_wallet = portfolio.get_wallet("USD")

        if usd_wallet is None:
            usd_wallet = portfolio.add_currency(
                "USD"
            )

        target_wallet = portfolio.get_wallet(code)

        if target_wallet is None:
            target_wallet = portfolio.add_currency(
                code
            )

        rate = self.get_rate(
            code,
            "USD",
        )

        cost = amount * rate
        old_balance = target_wallet.balance

        usd_wallet.withdraw(cost)
        target_wallet.deposit(amount)

        self._save_portfolio(portfolio)

        return {
            "currency": code,
            "amount": amount,
            "rate": rate,
            "cost": cost,
            "old_balance": old_balance,
            "new_balance": target_wallet.balance,
        }

    @log_action("SELL")
    def sell(
        self,
        currency_code: str,
        amount: float,
    ) -> dict:
        """Продает валюту и начисляет выручку в USD."""
        user = self._require_login()

        code = normalize_currency_code(
            currency_code
        )
        amount = validate_amount(amount)

        get_currency(code)

        if code == "USD":
            raise ValueError(
                "Нельзя продать USD за USD"
            )

        portfolio = self._load_portfolio(user)

        source_wallet = portfolio.get_wallet(code)

        if source_wallet is None:
            raise ValueError(
                f"У вас нет кошелька '{code}'"
            )

        rate = self.get_rate(
            code,
            "USD",
        )

        revenue = amount * rate
        old_balance = source_wallet.balance

        source_wallet.withdraw(amount)

        usd_wallet = portfolio.get_wallet("USD")

        if usd_wallet is None:
            usd_wallet = portfolio.add_currency(
                "USD"
            )

        usd_wallet.deposit(revenue)

        self._save_portfolio(portfolio)

        return {
            "currency": code,
            "amount": amount,
            "rate": rate,
            "revenue": revenue,
            "old_balance": old_balance,
            "new_balance": source_wallet.balance,
        }

    def show_portfolio(
        self,
        base_currency: str = "USD",
    ) -> dict:
        """Возвращает портфель пользователя и его стоимость."""
        user = self._require_login()

        base = normalize_currency_code(
            base_currency
        )

        get_currency(base)

        portfolio = self._load_portfolio(user)

        rows = []
        total = 0.0

        for code, wallet in (
            portfolio.wallets.items()
        ):
            if code == base:
                value = wallet.balance
            else:
                rate = self.get_rate(
                    code,
                    base,
                )
                value = wallet.balance * rate

            rows.append(
                {
                    "currency": code,
                    "balance": wallet.balance,
                    "value": value,
                }
            )

            total += value

        return {
            "username": user.username,
            "base_currency": base,
            "wallets": rows,
            "total": total,
        }