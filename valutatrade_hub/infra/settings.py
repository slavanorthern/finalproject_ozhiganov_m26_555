"""Настройки приложения ValutaTrade Hub."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any


class SettingsLoader:
    """Загружает настройки приложения (Singleton)."""

    _instance: SettingsLoader | None = None

    def __new__(cls) -> SettingsLoader:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self.project_root = self._resolve_project_root()
        self.pyproject_file = self.project_root / "pyproject.toml"
        self._settings: dict[str, Any] = {}

        self.reload()
        self._initialized = True

    @staticmethod
    def _resolve_project_root() -> Path:
        """Определяет каталог хранения данных."""
        custom_home = os.getenv("VALUTATRADE_HOME")

        if custom_home:
            return Path(custom_home).expanduser().resolve()

        source_root = Path(__file__).resolve().parents[2]

        # Работа непосредственно из исходного репозитория.
        if (source_root / "pyproject.toml").is_file() and (
            source_root / "valutatrade_hub"
        ).is_dir():
            return source_root

        # Работа из установленного wheel.
        return Path.home() / ".valutatrade_hub"

    def reload(self) -> None:
        """Перезагружает параметры конфигурации."""
        config = {}

        if self.pyproject_file.is_file():
            with self.pyproject_file.open("rb") as file:
                project_data = tomllib.load(file)

            config = project_data.get("tool", {}).get("valutatrade", {})

        data_dir = self.project_root / "data"
        logs_dir = self.project_root / "logs"

        self._settings = {
            "PROJECT_ROOT": self.project_root,
            "DATA_DIR": data_dir,
            "USERS_FILE": data_dir / "users.json",
            "PORTFOLIOS_FILE": data_dir / "portfolios.json",
            "RATES_FILE": data_dir / "rates.json",
            "HISTORY_FILE": data_dir / "exchange_rates.json",
            "LOG_DIR": logs_dir,
            "LOG_FILE": logs_dir / "actions.log",
            "RATES_TTL_SECONDS": config.get("rates_ttl_seconds", 300),
            "DEFAULT_BASE_CURRENCY": config.get("default_base_currency", "USD"),
            "LOG_LEVEL": config.get("log_level", "INFO"),
            "LOG_FORMAT": config.get(
                "log_format",
                "%(levelname)s %(asctime)s %(message)s",
            ),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает настройку по имени."""
        return self._settings.get(key, default)
