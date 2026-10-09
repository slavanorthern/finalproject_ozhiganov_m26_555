"""Вспомогательные функции валидации и работы со временем."""

from datetime import datetime
from math import isfinite


def normalize_currency_code(
    code: str,
) -> str:
    """Проверяет и нормализует код валюты."""
    if not isinstance(code, str):
        raise ValueError(
            "Код валюты должен быть строкой"
        )

    normalized = code.strip().upper()

    if not normalized:
        raise ValueError(
            "Код валюты не может быть пустым"
        )

    if (
        not 2 <= len(normalized) <= 5
        or " " in normalized
    ):
        raise ValueError(
            "Код валюты должен содержать "
            "от 2 до 5 символов без пробелов"
        )

    return normalized


def validate_amount(
    amount: float,
) -> float:
    """Проверяет положительную конечную сумму."""
    if (
        not isinstance(
            amount,
            (int, float),
        )
        or isinstance(
            amount,
            bool,
        )
    ):
        raise ValueError(
            "'amount' должен быть "
            "положительным числом"
        )

    value = float(amount)

    if (
        not isfinite(value)
        or value <= 0
    ):
        raise ValueError(
            "'amount' должен быть "
            "положительным числом"
        )

    return value


def utc_now_iso() -> str:
    """Возвращает текущее время UTC в ISO-формате."""
    return datetime.now().astimezone().isoformat()


def parse_iso_datetime(
    value: str,
) -> datetime:
    """Преобразует ISO-строку в datetime."""
    if not isinstance(value, str):
        raise ValueError(
            "Дата должна быть строкой"
        )

    return datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )