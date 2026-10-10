"""Управление локальным JSON-хранилищем."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Singleton для чтения и записи JSON."""

    _instance: DatabaseManager | None = None

    def __new__(cls) -> DatabaseManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        settings = SettingsLoader()

        initial_files = {
            "USERS_FILE": [],
            "PORTFOLIOS_FILE": [],
            "RATES_FILE": {"pairs": {}, "last_refresh": None},
            "HISTORY_FILE": [],
        }

        for setting_name, initial_data in initial_files.items():
            path = Path(settings.get(setting_name))
            path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # Режим x гарантирует, что существующий файл
                # не будет перезаписан.
                with path.open("x", encoding="utf-8") as file:
                    json.dump(
                        initial_data,
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )
            except FileExistsError:
                pass

        self._initialized = True

    def read_json(self, file_path: str | Path) -> Any:
        """Читает JSON-файл."""
        path = Path(file_path)

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write_json(self, file_path: str | Path, data: Any) -> None:
        """Атомарно сохраняет JSON."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

        os.replace(temp_path, path)
