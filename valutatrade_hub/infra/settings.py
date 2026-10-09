"""Загрузка и кеширование настроек приложения."""

import tomllib
from pathlib import Path
from typing import Any


class SettingsLoader:
    """Singleton для централизованного доступа к конфигурации."""

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        """
        Возвращает единственный экземпляр SettingsLoader.

        __new__ выбран как простой и читаемый способ
        реализации Singleton без дополнительного метакласса.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False

        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self.project_root = Path(__file__).resolve().parents[2]

        self.pyproject_file = self.project_root / "pyproject.toml"

        self._settings: dict[str, Any] = {}

        self.reload()

        self._initialized = True

    def reload(self) -> None:
        """Перезагружает настройки из pyproject.toml."""
        config = self._load_pyproject_config()

        data_dir = self.project_root / "data"

        logs_dir = self.project_root / "logs"

        self._settings = {
            "PROJECT_ROOT": (self.project_root),
            "DATA_DIR": data_dir,
            "USERS_FILE": (data_dir / "users.json"),
            "PORTFOLIOS_FILE": (data_dir / "portfolios.json"),
            "RATES_FILE": (data_dir / "rates.json"),
            "HISTORY_FILE": (data_dir / "exchange_rates.json"),
            "LOG_DIR": logs_dir,
            "LOG_FILE": (logs_dir / "actions.log"),
            "RATES_TTL_SECONDS": (
                config.get(
                    "rates_ttl_seconds",
                    300,
                )
            ),
            "DEFAULT_BASE_CURRENCY": (
                config.get(
                    "default_base_currency",
                    "USD",
                )
            ),
            "LOG_LEVEL": (
                config.get(
                    "log_level",
                    "INFO",
                )
            ),
            "LOG_FORMAT": (
                config.get(
                    "log_format",
                    ("%(levelname)s %(asctime)s %(message)s"),
                )
            ),
        }

    def _load_pyproject_config(
        self,
    ) -> dict[str, Any]:
        """Читает секцию [tool.valutatrade]."""
        if not self.pyproject_file.exists():
            return {}

        with self.pyproject_file.open(
            "rb",
        ) as file:
            data = tomllib.load(file)

        tool_section = data.get(
            "tool",
            {},
        )

        config = tool_section.get(
            "valutatrade",
            {},
        )

        if not isinstance(
            config,
            dict,
        ):
            return {}

        return config

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Возвращает настройку по ключу."""
        return self._settings.get(
            key,
            default,
        )
