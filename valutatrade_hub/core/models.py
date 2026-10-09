import hashlib
import os
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError


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
        """Проверяет и устанавливает имя пользователя."""
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
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._salt = os.urandom(16).hex()
        self._hashed_password = self._hash_password(
            new_password,
            self._salt,
        )

    def verify_password(self, password: str) -> bool:
        """Проверяет пароль пользователя."""
        return self._hashed_password == self._hash_password(
            password,
            self._salt,
        )

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Создает SHA-256 хеш пароля с солью."""
        value = f"{password}{salt}".encode()
        return hashlib.sha256(value).hexdigest()


class Wallet:
    """Кошелек пользователя для одной валюты."""

    def __init__(
        self,
        currency_code: str,
        balance: float = 0.0,
    ) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code = currency_code.strip().upper()
        self.balance = balance

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс и запрещает отрицательные значения."""
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
        ):
            raise TypeError("Баланс должен быть числом")

        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс."""
        self._validate_amount(amount)
        self._balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снимает средства с баланса."""
        self._validate_amount(amount)

        if amount > self._balance:
            raise InsufficientFundsError(
                self._balance,
                amount,
                self.currency_code,
            )

        self._balance -= float(amount)

    def get_balance_info(self) -> str:
        """Возвращает информацию о балансе."""
        return f"{self.currency_code}: {self._balance:.4f}"

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверяет сумму операции."""
        if (
            not isinstance(amount, (int, float))
            or isinstance(amount, bool)
            or amount <= 0
        ):
            raise ValueError(
                "'amount' должен быть положительным числом"
            )


class Portfolio:
    """Управляет всеми кошельками одного пользователя."""

    def __init__(
        self,
        user: User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        self._user = user
        self._wallets = wallets.copy() if wallets else {}

    @property
    def user(self) -> User:
        """Возвращает владельца портфеля."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет кошелек для валюты, если его еще нет."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()

        if code in self._wallets:
            return self._wallets[code]

        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелек по коду валюты."""
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, float] | None = None,
    ) -> float:
        """Возвращает общую стоимость портфеля."""
        rates = exchange_rates or {}
        base = base_currency.strip().upper()
        total = 0.0

        for code, wallet in self._wallets.items():
            if code == base:
                total += wallet.balance
                continue

            pair = f"{code}_{base}"
            rate = rates.get(pair)

            if rate is None:
                raise ValueError(
                    f"Нет курса для {code}->{base}"
                )

            total += wallet.balance * rate

        return total