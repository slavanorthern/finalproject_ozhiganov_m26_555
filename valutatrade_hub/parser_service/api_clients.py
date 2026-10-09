"""Клиенты внешних API для получения валютных курсов."""

from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Базовый интерфейс клиента внешнего API."""

    source_name: str

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы в формате PAIR -> rate."""


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют из CoinGecko."""

    source_name = "CoinGecko"

    def __init__(
        self,
        config: ParserConfig,
    ) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, float]:
        """Получает криптовалютные курсы к USD."""
        ids = [
            self.config.crypto_id_map[code]
            for code in self.config.crypto_currencies
        ]

        params = {
            "ids": ",".join(ids),
            "vs_currencies": (
                self.config.base_currency.lower()
            ),
        }

        try:
            response = requests.get(
                self.config.coingecko_url,
                params=params,
                timeout=self.config.request_timeout,
            )

        except requests.exceptions.Timeout as error:
            raise ApiRequestError(
                "CoinGecko: превышено время ожидания ответа"
            ) from error

        except requests.exceptions.ConnectionError as error:
            raise ApiRequestError(
                "CoinGecko: ошибка подключения к сети"
            ) from error

        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                "CoinGecko: ошибка HTTP-запроса"
            ) from error

        self._check_status(
            response.status_code,
        )

        try:
            data: dict[str, Any] = response.json()

        except ValueError as error:
            raise ApiRequestError(
                "CoinGecko вернул некорректный JSON"
            ) from error

        result: dict[str, float] = {}

        base_key = (
            self.config.base_currency.lower()
        )

        for code in self.config.crypto_currencies:
            raw_id = self.config.crypto_id_map[
                code
            ]

            coin_data = data.get(raw_id)

            if not isinstance(
                coin_data,
                dict,
            ):
                raise ApiRequestError(
                    f"CoinGecko: отсутствуют данные для {code}"
                )

            raw_rate = coin_data.get(
                base_key
            )

            try:
                rate = float(
                    raw_rate
                )
            except (
                TypeError,
                ValueError,
            ) as error:
                raise ApiRequestError(
                    f"CoinGecko: некорректный курс для {code}"
                ) from error

            if rate <= 0:
                raise ApiRequestError(
                    f"CoinGecko: некорректный курс для {code}"
                )

            pair = (
                f"{code}_"
                f"{self.config.base_currency}"
            )

            result[pair] = rate

        return result

    @staticmethod
    def _check_status(
        status_code: int,
    ) -> None:
        """Проверяет HTTP-статус CoinGecko."""
        if status_code == 429:
            raise ApiRequestError(
                "CoinGecko: превышен лимит запросов"
            )

        if status_code in {
            401,
            403,
        }:
            raise ApiRequestError(
                "CoinGecko: доступ к API запрещен"
            )

        if status_code >= 500:
            raise ApiRequestError(
                "CoinGecko временно недоступен"
            )

        if status_code >= 400:
            raise ApiRequestError(
                f"CoinGecko вернул HTTP {status_code}"
            )


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют из ExchangeRate-API."""

    source_name = "ExchangeRate-API"

    def __init__(
        self,
        config: ParserConfig,
    ) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, float]:
        """Получает фиатные курсы и приводит их к *_USD."""
        api_key = (
            self.config.exchangerate_api_key
        )

        if not api_key:
            raise ApiRequestError(
                "не задан EXCHANGERATE_API_KEY"
            )

        url = (
            f"{self.config.exchangerate_api_url}/"
            f"{api_key}/latest/"
            f"{self.config.base_currency}"
        )

        try:
            response = requests.get(
                url,
                timeout=self.config.request_timeout,
            )

        except requests.exceptions.Timeout as error:
            raise ApiRequestError(
                "ExchangeRate-API: "
                "превышено время ожидания ответа"
            ) from error

        except requests.exceptions.ConnectionError as error:
            raise ApiRequestError(
                "ExchangeRate-API: "
                "ошибка подключения к сети"
            ) from error

        except requests.exceptions.RequestException as error:
            # Не вставляем str(error), так как он может
            # содержать URL вместе с API-ключом.
            raise ApiRequestError(
                "ExchangeRate-API: ошибка HTTP-запроса"
            ) from error

        self._check_status(
            response.status_code
        )

        try:
            data: dict[str, Any] = response.json()

        except ValueError as error:
            raise ApiRequestError(
                "ExchangeRate-API вернул некорректный JSON"
            ) from error

        if data.get("result") == "error":
            error_type = data.get(
                "error-type",
                "unknown-error",
            )

            safe_messages = {
                "unsupported-code": (
                    "неподдерживаемый код валюты"
                ),
                "malformed-request": (
                    "некорректный запрос"
                ),
                "invalid-key": (
                    "неверный API-ключ"
                ),
                "inactive-account": (
                    "аккаунт API неактивен"
                ),
                "quota-reached": (
                    "исчерпан лимит запросов"
                ),
            }

            message = safe_messages.get(
                error_type,
                "ошибка внешнего API",
            )

            raise ApiRequestError(
                f"ExchangeRate-API: {message}"
            )

        raw_rates = (
            data.get(
                "conversion_rates"
            )
            or data.get(
                "rates"
            )
        )

        if not isinstance(
            raw_rates,
            dict,
        ):
            raise ApiRequestError(
                "ExchangeRate-API: "
                "в ответе отсутствуют курсы"
            )

        result: dict[str, float] = {}

        for code in self.config.fiat_currencies:
            raw_rate = raw_rates.get(
                code
            )

            try:
                usd_to_currency = float(
                    raw_rate
                )
            except (
                TypeError,
                ValueError,
            ) as error:
                raise ApiRequestError(
                    "ExchangeRate-API: "
                    f"некорректный курс для {code}"
                ) from error

            if usd_to_currency <= 0:
                raise ApiRequestError(
                    "ExchangeRate-API: "
                    f"некорректный курс для {code}"
                )

            currency_to_usd = (
                1 / usd_to_currency
            )

            pair = (
                f"{code}_"
                f"{self.config.base_currency}"
            )

            result[pair] = (
                currency_to_usd
            )

        return result

    @staticmethod
    def _check_status(
        status_code: int,
    ) -> None:
        """Проверяет HTTP-статус ExchangeRate-API."""
        if status_code in {
            401,
            403,
        }:
            raise ApiRequestError(
                "ExchangeRate-API: "
                "неверный API-ключ или доступ запрещен"
            )

        if status_code == 429:
            raise ApiRequestError(
                "ExchangeRate-API: "
                "превышен лимит запросов"
            )

        if status_code >= 500:
            raise ApiRequestError(
                "ExchangeRate-API временно недоступен"
            )

        if status_code >= 400:
            raise ApiRequestError(
                "ExchangeRate-API вернул "
                f"HTTP {status_code}"
            )