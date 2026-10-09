from datetime import UTC, datetime


def normalize_currency_code(code: str) -> str:
    """Проверяет и нормализует код валюты."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не может быть пустым")

    normalized = code.strip().upper()

    if not 2 <= len(normalized) <= 5 or " " in normalized:
        raise ValueError("Некорректный код валюты")

    return normalized


def validate_amount(amount: float) -> float:
    """Проверяет, что сумма является положительным числом."""
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise ValueError("'amount' должен быть положительным числом")

    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    return float(amount)


def utc_now_iso() -> str:
    """Возвращает текущее время UTC в ISO-формате."""
    return datetime.now(UTC).isoformat()


def parse_iso_datetime(value: str) -> datetime:
    """Преобразует ISO-строку в datetime."""
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )