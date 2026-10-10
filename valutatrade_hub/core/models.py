"""Основные модели пользователей, кошельков и портфелей."""

import hashlib
import hmac
import os
from datetime import datetime
from math import isfinite

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.rates import calculate_rate
from valutatrade_hub.core.utils import normalize_currency_code, validate_amount


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Возвращает имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Проверяет имя пользователя."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Возвращает хеш пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Возвращает соль пароля."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Возвращает дату регистрации."""
        return self._registration_date

    def get_user_info(self) -> dict:
        """Возвращает данные пользователя без пароля."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Генерирует соль и новый SHA-256 хеш пароля."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._salt = os.urandom(16).hex()
        password_data = (new_password + self._salt).encode("utf-8")
        self._hashed_password = hashlib.sha256(password_data).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет пароль пользователя."""
        if not isinstance(password, str):
            return False

        password_data = (password + self._salt).encode("utf-8")
        candidate_hash = hashlib.sha256(password_data).hexdigest()

        return hmac.compare_digest(candidate_hash, self._hashed_password)


class Wallet:
    """Кошелек для одной валюты."""

    def __init__(
        self,
        currency_code: str,
        balance: float = 0.0,
    ) -> None:
        self.currency_code = normalize_currency_code(currency_code)
        self.balance = balance

    @property
    def balance(self) -> float:
        """Возвращает баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Запрещает отрицательные и неконечные балансы."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")

        numeric_value = float(value)

        if not isfinite(numeric_value):
            raise ValueError("Баланс должен быть конечным числом")

        if numeric_value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = numeric_value

    def deposit(self, amount: float) -> None:
        """Пополняет баланс."""
        amount = validate_amount(amount)
        new_balance = self.balance + amount

        if not isfinite(new_balance):
            raise ValueError("Результирующий баланс некорректен")

        self.balance = new_balance

    def withdraw(self, amount: float) -> None:
        """Списывает средства, проверяя остаток."""
        amount = validate_amount(amount)

        if amount > self.balance:
            raise InsufficientFundsError(
                available=self.balance,
                required=amount,
                code=self.currency_code,
            )

        self.balance = self.balance - amount

    def get_balance_info(self) -> dict:
        """Возвращает данные кошелька."""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }


class Portfolio:
    """Набор валютных кошельков пользователя."""

    def __init__(
        self,
        user: User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        if not isinstance(user, User):
            raise TypeError("user должен быть объектом User")

        self._user = user
        self._wallets = dict(wallets) if wallets is not None else {}

    @property
    def user(self) -> User:
        """Возвращает владельца портфеля."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        """Создает кошелек, если он отсутствует."""
        code = normalize_currency_code(currency_code)

        existing_wallet = self._wallets.get(code)
        if existing_wallet is not None:
            return existing_wallet

        wallet = Wallet(currency_code=code, balance=0.0)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелек по коду валюты."""
        code = normalize_currency_code(currency_code)
        return self._wallets.get(code)

    def get_total_value(
        self,
        exchange_rates: dict[str, float],
        base_currency: str = "USD",
    ) -> float:
        """Оценивает портфель по прямым или составным курсам."""
        base = normalize_currency_code(base_currency)
        total = 0.0

        for code, wallet in self._wallets.items():
            # Пустой кошелек не требует обращения к курсам.
            if wallet.balance == 0:
                continue

            rate = calculate_rate(code, base, exchange_rates)
            value = wallet.balance * rate

            if not isfinite(value) or value < 0:
                raise ValueError(f"Некорректная стоимость кошелька {code}")

            total += value

            if not isfinite(total):
                raise ValueError("Некорректная итоговая стоимость портфеля")

        return total
