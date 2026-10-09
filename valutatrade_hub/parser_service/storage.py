import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class RatesStorage:
    """Работает с кешем текущих курсов и историей."""

    @staticmethod
    def read_json(
        file_path: Path,
        default: Any = None,
    ) -> Any:
        """Читает JSON-файл."""
        if not file_path.exists():
            return default

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    @staticmethod
    def _write_json_atomic(
        file_path: Path,
        data: Any,
    ) -> None:
        """Атомарно записывает данные в JSON."""
        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = file_path.with_suffix(
            file_path.suffix + ".tmp"
        )

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temp_path,
            file_path,
        )

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        """Преобразует ISO-время в datetime."""
        if not value:
            return None

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    def save_current_rates(
        self,
        file_path: Path,
        rates: dict[str, dict],
        last_refresh: str,
    ) -> None:
        """Добавляет новые курсы в кеш, не удаляя остальные."""
        current_data = self.read_json(
            file_path,
            {
                "pairs": {},
                "last_refresh": None,
            },
        )

        current_pairs = current_data.get(
            "pairs",
            {},
        )

        for pair, new_data in rates.items():
            old_data = current_pairs.get(pair)

            if old_data is None:
                current_pairs[pair] = new_data
                continue

            old_time = self._parse_timestamp(
                old_data.get("updated_at")
            )

            new_time = self._parse_timestamp(
                new_data.get("updated_at")
            )

            if old_time is None:
                current_pairs[pair] = new_data
                continue

            if new_time is None:
                continue

            if new_time >= old_time:
                current_pairs[pair] = new_data

        result = {
            "pairs": current_pairs,
            "last_refresh": last_refresh,
        }

        self._write_json_atomic(
            file_path,
            result,
        )

    def append_history(
        self,
        file_path: Path,
        rates: dict[str, dict],
    ) -> None:
        """Добавляет новые значения курсов в историю."""
        history = self.read_json(
            file_path,
            [],
        )

        existing_ids = {
            item.get("id")
            for item in history
        }

        for pair, data in rates.items():
            from_code, to_code = pair.split(
                "_",
                1,
            )

            timestamp = data["updated_at"]

            record_id = (
                f"{pair}_"
                f"{timestamp.replace('+00:00', 'Z')}"
            )

            if record_id in existing_ids:
                continue

            history.append(
                {
                    "id": record_id,
                    "from": from_code,
                    "to": to_code,
                    "rate": float(
                        data["rate"]
                    ),
                    "timestamp": timestamp,
                    "source": data["source"],
                }
            )

            existing_ids.add(record_id)

        self._write_json_atomic(
            file_path,
            history,
        )