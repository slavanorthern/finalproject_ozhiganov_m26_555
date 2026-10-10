"""Клиенты внешних API для получения валютных курсов."""

from abc import ABC, abstractmethod
from math import isfinite

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


def _validate_rate(value: object, source: str, code: str) -> float:
    """Проверяет, что курс является положительным конечным числом."""
    if isinstance(value, bool):
        raise ApiRequestError(f"{source}: некорректный курс для {code}")

    try:
        rate = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ApiRequestError(f"{source}: некорректный курс для {code}") from error

    if not isfinite(rate) or rate <= 0:
        raise ApiRequestError(f"{source}: некорректный курс для {code}")

    return rate


def _parse_json(response: requests.Response, source: str) -> dict:
    """Проверяет формат JSON-ответа."""
    try:
        data = response.json()
    except ValueError as error:
        raise ApiRequestError(f"{source}: сервер вернул некорректный JSON") from error

    if not isinstance(data, dict):
        raise ApiRequestError(f"{source}: ожидался JSON-объект")

    return data


def _request(
    url: str,
    source: str,
    timeout: int,
    params: dict[str, str] | None = None,
) -> requests.Response:
    """Выполняет запрос и безопасно обрабатывает сетевые ошибки."""
    try:
        return requests.get(
            url,
            params=params,
            timeout=timeout,
        )
    except requests.exceptions.Timeout as error:
        raise ApiRequestError(f"{source}: превышено время ожидания ответа") from error
    except requests.exceptions.ConnectionError as error:
        raise ApiRequestError(f"{source}: ошибка подключения к сети") from error
    except requests.exceptions.RequestException as error:
        # Не включаем URL запроса в текст ошибки:
        # ExchangeRate-API содержит ключ непосредственно в URL.
        raise ApiRequestError(f"{source}: ошибка HTTP-запроса") from error


class BaseApiClient(ABC):
    """Абстрактный интерфейс клиента внешнего API."""

    source_name: str

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает валютные пары и их курсы."""


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют из CoinGecko."""

    source_name = "CoinGecko"

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, float]:
        """Загружает криптовалютные курсы к базовой валюте."""
        ids = [
            self.config.crypto_id_map[code] for code in self.config.crypto_currencies
        ]

        params = {
            "ids": ",".join(ids),
            "vs_currencies": self.config.base_currency.lower(),
        }

        response = _request(
            url=self.config.coingecko_url,
            source=self.source_name,
            timeout=self.config.request_timeout,
            params=params,
        )

        self._check_status(response.status_code)
        data = _parse_json(response, self.source_name)

        result: dict[str, float] = {}
        base_key = self.config.base_currency.lower()

        for code in self.config.crypto_currencies:
            coin_id = self.config.crypto_id_map[code]
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict):
                raise ApiRequestError(f"CoinGecko: отсутствуют данные для {code}")

            rate = _validate_rate(
                coin_data.get(base_key),
                self.source_name,
                code,
            )

            result[f"{code}_{self.config.base_currency}"] = rate

        return result

    @staticmethod
    def _check_status(status_code: int) -> None:
        """Проверяет HTTP-статус CoinGecko."""
        if status_code == 429:
            raise ApiRequestError("CoinGecko: превышен лимит запросов")

        if status_code in (401, 403):
            raise ApiRequestError("CoinGecko: доступ к API запрещен")

        if status_code >= 500:
            raise ApiRequestError("CoinGecko временно недоступен")

        if status_code >= 400:
            raise ApiRequestError(f"CoinGecko вернул HTTP {status_code}")


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют из ExchangeRate-API."""

    source_name = "ExchangeRate-API"

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, float]:
        """Загружает фиатные курсы и приводит их к формату *_USD."""
        api_key = self.config.exchangerate_api_key

        if not api_key:
            raise ApiRequestError("не задан EXCHANGERATE_API_KEY")

        url = (
            f"{self.config.exchangerate_api_url}/"
            f"{api_key}/latest/{self.config.base_currency}"
        )

        response = _request(
            url=url,
            source=self.source_name,
            timeout=self.config.request_timeout,
        )

        self._check_status(response.status_code)
        data = _parse_json(response, self.source_name)

        if data.get("result") == "error":
            error_type = data.get("error-type")

            messages = {
                "unsupported-code": "неподдерживаемый код валюты",
                "malformed-request": "некорректный запрос",
                "invalid-key": "неверный API-ключ",
                "inactive-account": "аккаунт API неактивен",
                "quota-reached": "исчерпан лимит запросов",
            }

            message = messages.get(
                error_type,
                "ошибка внешнего API",
            )

            raise ApiRequestError(f"ExchangeRate-API: {message}")

        raw_rates = data.get("conversion_rates")

        if raw_rates is None:
            raw_rates = data.get("rates")

        if not isinstance(raw_rates, dict):
            raise ApiRequestError("ExchangeRate-API: в ответе отсутствуют курсы")

        result: dict[str, float] = {}

        for code in self.config.fiat_currencies:
            usd_to_currency = _validate_rate(
                raw_rates.get(code),
                self.source_name,
                code,
            )

            # API возвращает количество валюты за 1 USD.
            # Для EUR_USD нужен обратный курс.
            currency_to_usd = 1.0 / usd_to_currency

            if not isfinite(currency_to_usd) or currency_to_usd <= 0:
                raise ApiRequestError(
                    f"ExchangeRate-API: некорректный обратный курс для {code}"
                )

            result[f"{code}_{self.config.base_currency}"] = currency_to_usd

        return result

    @staticmethod
    def _check_status(status_code: int) -> None:
        """Проверяет HTTP-статус ExchangeRate-API."""
        if status_code in (401, 403):
            raise ApiRequestError(
                "ExchangeRate-API: неверный API-ключ или доступ запрещен"
            )

        if status_code == 429:
            raise ApiRequestError("ExchangeRate-API: превышен лимит запросов")

        if status_code >= 500:
            raise ApiRequestError("ExchangeRate-API временно недоступен")

        if status_code >= 400:
            raise ApiRequestError(f"ExchangeRate-API вернул HTTP {status_code}")
