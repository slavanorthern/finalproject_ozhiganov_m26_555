import json
import os
from pathlib import Path
from typing import Any


class DatabaseManager:
    """Singleton для работы с JSON-хранилищем."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def read_json(self, file_path: str | Path) -> Any:
        """Читает данные из JSON-файла."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write_json(self, file_path: str | Path, data: Any) -> None:
        """Атомарно записывает данные в JSON-файл."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(temp_path, path)