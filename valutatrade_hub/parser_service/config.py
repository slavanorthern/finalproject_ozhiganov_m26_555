"""Конфигурация источников валютных курсов."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from valutatrade_hub.infra.settings import SettingsLoader

PROJECT_ROOT = SettingsLoader().get("PROJECT_ROOT")

# API-ключ загружается из окружения или локального .env.
load_dotenv(Path.cwd() / ".env")
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class ParserConfig:
    """Параметры API, отслеживаемых валют и путей к JSON."""

    exchangerate_api_key: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )

    coingecko_url: str = "https://api.coingecko.com/api/v3/simple/price"

    exchangerate_api_url: str = "https://v6.exchangerate-api.com/v6"

    base_currency: str = "USD"

    fiat_currencies: tuple[str, ...] = (
        "EUR",
        "GBP",
        "RUB",
    )

    crypto_currencies: tuple[str, ...] = (
        "BTC",
        "ETH",
        "SOL",
    )

    crypto_id_map: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    request_timeout: int = 10

    project_root: Path = PROJECT_ROOT

    @property
    def rates_file_path(self) -> Path:
        """Возвращает путь к кешу курсов."""
        return self.project_root / "data" / "rates.json"

    @property
    def history_file_path(self) -> Path:
        """Возвращает путь к истории курсов."""
        return self.project_root / "data" / "exchange_rates.json"
