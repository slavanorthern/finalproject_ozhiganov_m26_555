from pathlib import Path
from typing import Any


class SettingsLoader:
    """Singleton для хранения настроек приложения."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self) -> None:
        """Загружает основные настройки проекта."""
        project_root = Path(__file__).resolve().parents[2]

        self._settings = {
            "PROJECT_ROOT": project_root,
            "DATA_DIR": project_root / "data",
            "USERS_FILE": project_root / "data" / "users.json",
            "PORTFOLIOS_FILE": project_root / "data" / "portfolios.json",
            "RATES_FILE": project_root / "data" / "rates.json",
            "HISTORY_FILE": project_root / "data" / "exchange_rates.json",
            "LOG_FILE": project_root / "logs" / "actions.log",
            "RATES_TTL_SECONDS": 300,
            "DEFAULT_BASE_CURRENCY": "USD",
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": (
                "%(levelname)s %(asctime)s %(message)s"
            ),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки."""
        return self._settings.get(key, default)

    def reload(self) -> None:
        """Перезагружает настройки."""
        self._load_settings()