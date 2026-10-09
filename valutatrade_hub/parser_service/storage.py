"""Хранение текущих и исторических курсов валют."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RatesStorage:
    """Работает с кешем текущих курсов и историей."""

    @staticmethod
    def read_json(
        file_path: Path,
        default: Any = None,
    ) -> Any:
        """Читает JSON-файл и возвращает default, если файла нет."""
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
        """Атомарно записывает JSON через временный файл."""
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
                allow_nan=False,
            )

        os.replace(
            temp_path,
            file_path,
        )

    @staticmethod
    def _parse_timestamp(
        value: str | None,
    ) -> datetime | None:
        """Преобразует ISO-время в datetime."""
        if not value:
            return None

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=UTC
            )

        return parsed

    @staticmethod
    def _to_utc_iso(
        value: str,
    ) -> str:
        """Нормализует timestamp в ISO-UTC с суффиксом Z."""
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=UTC
            )

        parsed = parsed.astimezone(
            UTC
        )

        return (
            parsed.isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )

    def save_current_rates(
        self,
        file_path: Path,
        rates: dict[str, dict],
        last_refresh: str,
    ) -> None:
        """Обновляет кеш, сохраняя более свежие значения."""
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
            old_data = current_pairs.get(
                pair
            )

            if old_data is None:
                current_pairs[pair] = (
                    new_data
                )
                continue

            old_time = self._parse_timestamp(
                old_data.get(
                    "updated_at"
                )
            )

            new_time = self._parse_timestamp(
                new_data.get(
                    "updated_at"
                )
            )

            if old_time is None:
                current_pairs[pair] = (
                    new_data
                )
                continue

            if new_time is None:
                continue

            if new_time >= old_time:
                current_pairs[pair] = (
                    new_data
                )

        normalized_refresh = (
            self._to_utc_iso(
                last_refresh
            )
        )

        for pair_data in current_pairs.values():
            updated_at = pair_data.get(
                "updated_at"
            )

            if updated_at:
                pair_data["updated_at"] = (
                    self._to_utc_iso(
                        updated_at
                    )
                )

        result = {
            "pairs": current_pairs,
            "last_refresh": normalized_refresh,
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
        """Добавляет новые измерения курсов в историю."""
        history = self.read_json(
            file_path,
            [],
        )

        if not isinstance(
            history,
            list,
        ):
            history = []

        existing_ids = {
            item.get("id")
            for item in history
            if isinstance(
                item,
                dict,
            )
        }

        for pair, data in rates.items():
            from_currency, to_currency = (
                pair.split(
                    "_",
                    1,
                )
            )

            from_currency = (
                from_currency.upper()
            )

            to_currency = (
                to_currency.upper()
            )

            timestamp = self._to_utc_iso(
                data["updated_at"]
            )

            record_id = (
                f"{from_currency}_"
                f"{to_currency}_"
                f"{timestamp}"
            )

            if record_id in existing_ids:
                continue

            history.append(
                {
                    "id": record_id,
                    "from_currency": (
                        from_currency
                    ),
                    "to_currency": (
                        to_currency
                    ),
                    "rate": float(
                        data["rate"]
                    ),
                    "timestamp": timestamp,
                    "source": data[
                        "source"
                    ],
                }
            )

            existing_ids.add(
                record_id
            )

        self._write_json_atomic(
            file_path,
            history,
        )