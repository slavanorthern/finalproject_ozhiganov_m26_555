from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Базовый API-клиент курсов валют."""

    source_name: str

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы в стандартном формате."""


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для криптовалют."""

    source_name = "CoinGecko"

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы криптовалют к USD."""
        ids = ",".join(
            self.config.crypto_id_map[code]
            for code in self.config.crypto_currencies
        )

        params = {
            "ids": ids,
            "vs_currencies": self.config.base_currency.lower(),
        }

        try:
            response = requests.get(
                self.config.coingecko_url,
                params=params,
                timeout=self.config.request_timeout,
            )

            response.raise_for_status()
            data = response.json()

        except requests.RequestException as error:
            raise ApiRequestError(str(error)) from error

        except ValueError as error:
            raise ApiRequestError(
                "CoinGecko вернул некорректный JSON"
            ) from error

        rates: dict[str, float] = {}

        for code in self.config.crypto_currencies:
            crypto_id = self.config.crypto_id_map[code]

            try:
                rate = float(
                    data[crypto_id][
                        self.config.base_currency.lower()
                    ]
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ApiRequestError(
                    f"Нет корректного курса для {code}"
                ) from error

            pair = f"{code}_{self.config.base_currency}"
            rates[pair] = rate

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для фиатных валют."""

    source_name = "ExchangeRate-API"

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы фиатных валют к USD."""
        if not self.config.exchangerate_api_key:
            raise ApiRequestError(
                "не задан EXCHANGERATE_API_KEY"
            )

        url = (
            f"{self.config.exchangerate_api_url}/"
            f"{self.config.exchangerate_api_key}/latest/"
            f"{self.config.base_currency}"
        )

        try:
            response = requests.get(
                url,
                timeout=self.config.request_timeout,
            )

            if response.status_code == 401:
                raise ApiRequestError(
                    "неверный API-ключ ExchangeRate-API"
                )

            if response.status_code == 429:
                raise ApiRequestError(
                    "превышен лимит запросов ExchangeRate-API"
                )

            response.raise_for_status()
            data = response.json()

        except ApiRequestError:
            raise

        except requests.RequestException as error:
            raise ApiRequestError(str(error)) from error

        except ValueError as error:
            raise ApiRequestError(
                "ExchangeRate-API вернул некорректный JSON"
            ) from error

        source_rates = (
            data.get("conversion_rates")
            or data.get("rates")
            or {}
        )

        rates: dict[str, float] = {}

        for code in self.config.fiat_currencies:
            try:
                usd_to_currency = float(source_rates[code])
            except (KeyError, TypeError, ValueError) as error:
                raise ApiRequestError(
                    f"Нет корректного курса для {code}"
                ) from error

            if usd_to_currency <= 0:
                raise ApiRequestError(
                    f"Некорректный курс для {code}"
                )

            currency_to_usd = 1 / usd_to_currency

            pair = f"{code}_{self.config.base_currency}"
            rates[pair] = currency_to_usd

        return rates