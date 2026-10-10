"""Общие функции конвертации валют по словарю курсов."""

from math import isfinite

from valutatrade_hub.core.utils import normalize_currency_code


def calculate_rate(
    from_currency: str,
    to_currency: str,
    exchange_rates: dict[str, float],
) -> float:
    """Находит прямой, обратный или составной курс через USD."""
    source = normalize_currency_code(from_currency)
    target = normalize_currency_code(to_currency)

    if source == target:
        return 1.0

    def direct_or_reverse(from_code: str, to_code: str) -> float | None:
        if from_code == to_code:
            return 1.0

        direct = f"{from_code}_{to_code}"
        reverse = f"{to_code}_{from_code}"

        if direct in exchange_rates:
            value = float(exchange_rates[direct])
            if not isfinite(value) or value <= 0:
                raise ValueError(f"Некорректный курс {direct}")
            return value

        if reverse in exchange_rates:
            value = float(exchange_rates[reverse])
            if not isfinite(value) or value <= 0:
                raise ValueError(f"Некорректный курс {reverse}")

            result = 1.0 / value
            if not isfinite(result) or result <= 0:
                raise ValueError(f"Некорректный обратный курс {reverse}")
            return result

        return None

    # Сначала проверяем прямую и обратную пару.
    rate = direct_or_reverse(source, target)
    if rate is not None:
        return rate

    # Если прямой пары нет, используем USD как промежуточную валюту.
    source_usd = direct_or_reverse(source, "USD")
    target_usd = direct_or_reverse(target, "USD")

    if source_usd is None or target_usd is None:
        raise ValueError(f"Нет курса {source}->{target}")

    result = source_usd / target_usd

    if not isfinite(result) or result <= 0:
        raise ValueError(f"Некорректный расчет курса {source}->{target}")

    return result
