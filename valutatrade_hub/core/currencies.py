"""Модели поддерживаемых фиатных и криптовалют."""

from abc import ABC, abstractmethod
from math import isfinite

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты."""

    def __init__(
        self,
        name: str,
        code: str,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")

        normalized_code = code.strip().upper()

        if not 2 <= len(normalized_code) <= 5 or " " in normalized_code:
            raise ValueError(
                "Код валюты должен содержать от 2 до 5 символов без пробелов"
            )

        self.name = name.strip()
        self.code = normalized_code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое описание валюты."""


class FiatCurrency(Currency):
    """Фиатная валюта."""

    def __init__(
        self,
        name: str,
        code: str,
        issuing_country: str,
    ) -> None:
        super().__init__(
            name=name,
            code=code,
        )

        if (
            not isinstance(
                issuing_country,
                str,
            )
            or not issuing_country.strip()
        ):
            raise ValueError("Страна или зона эмиссии не может быть пустой")

        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Возвращает описание фиатной валюты."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(
            name=name,
            code=code,
        )

        if (
            not isinstance(
                algorithm,
                str,
            )
            or not algorithm.strip()
        ):
            raise ValueError("Алгоритм криптовалюты не может быть пустым")

        if not isinstance(
            market_cap,
            (int, float),
        ) or isinstance(
            market_cap,
            bool,
        ):
            raise ValueError("Капитализация должна быть числом")

        numeric_market_cap = float(market_cap)

        if not isfinite(numeric_market_cap) or numeric_market_cap < 0:
            raise ValueError(
                "Капитализация должна быть неотрицательным конечным числом"
            )

        self.algorithm = algorithm.strip()

        self.market_cap = numeric_market_cap

    def get_display_info(self) -> str:
        """Возвращает описание криптовалюты."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, "
            f"MCAP: {self.market_cap:.2e})"
        )


CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency(
        name="US Dollar",
        code="USD",
        issuing_country="United States",
    ),
    "EUR": FiatCurrency(
        name="Euro",
        code="EUR",
        issuing_country="Eurozone",
    ),
    "GBP": FiatCurrency(
        name="Pound Sterling",
        code="GBP",
        issuing_country="United Kingdom",
    ),
    "RUB": FiatCurrency(
        name="Russian Ruble",
        code="RUB",
        issuing_country="Russia",
    ),
    "BTC": CryptoCurrency(
        name="Bitcoin",
        code="BTC",
        algorithm="SHA-256",
        market_cap=1.12e12,
    ),
    "ETH": CryptoCurrency(
        name="Ethereum",
        code="ETH",
        algorithm="Proof of Stake",
        market_cap=4.5e11,
    ),
    "SOL": CryptoCurrency(
        name="Solana",
        code="SOL",
        algorithm="Proof of History",
        market_cap=8.0e10,
    ),
}


def get_currency(
    code: str,
) -> Currency:
    """Возвращает валюту из реестра по коду."""
    if not isinstance(code, str):
        raise CurrencyNotFoundError(str(code))

    normalized_code = code.strip().upper()

    currency = CURRENCY_REGISTRY.get(normalized_code)

    if currency is None:
        raise CurrencyNotFoundError(normalized_code)

    return currency
