"""Подготовка курсов из кеша для отображения пользователю."""

from datetime import UTC, datetime
from math import isfinite

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.rates import calculate_rate
from valutatrade_hub.core.utils import (
    normalize_currency_code,
    parse_iso_datetime,
)
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


def _read_quote(
    source: str,
    target: str,
    pairs: dict,
) -> dict | None:
    """Возвращает прямой или обратный курс с метаданными."""
    if source == target:
        return {
            "rate": 1.0,
            "updated_at": None,
            "source": "local",
        }

    direct = f"{source}_{target}"
    reverse = f"{target}_{source}"

    if direct in pairs:
        pair_name = direct
    elif reverse in pairs:
        pair_name = reverse
    else:
        return None

    item = pairs[pair_name]
    if not isinstance(item, dict):
        raise ApiRequestError(f"Некорректные данные {pair_name}")

    try:
        rate = calculate_rate(
            source,
            target,
            {pair_name: item["rate"]},
        )
        timestamp = parse_iso_datetime(item["updated_at"])
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        ZeroDivisionError,
    ) as error:
        raise ApiRequestError(f"Некорректные данные курса {pair_name}") from error

    return {
        "rate": rate,
        "updated_at": timestamp.astimezone(UTC).isoformat(),
        "source": item.get("source", "unknown"),
    }


def _calculate_quote(
    source: str,
    target: str,
    pairs: dict,
) -> dict | None:
    """Рассчитывает курс и собирает данные всех его компонентов."""
    direct = _read_quote(source, target, pairs)
    if direct is not None:
        return direct

    source_quote = _read_quote(source, "USD", pairs)
    target_quote = _read_quote(target, "USD", pairs)

    if source_quote is None or target_quote is None:
        return None

    try:
        rate = calculate_rate(
            source,
            target,
            {
                f"{source}_USD": source_quote["rate"],
                f"{target}_USD": target_quote["rate"],
            },
        )
    except (ValueError, TypeError, OverflowError) as error:
        raise ApiRequestError(
            f"Не удалось рассчитать курс {source}->{target}"
        ) from error

    timestamps = [
        item["updated_at"]
        for item in (source_quote, target_quote)
        if item["updated_at"] is not None
    ]

    sources = list(
        dict.fromkeys(
            item["source"]
            for item in (source_quote, target_quote)
            if item["source"] != "local"
        )
    )

    return {
        "rate": rate,
        "updated_at": (min(timestamps, key=parse_iso_datetime) if timestamps else None),
        "source": " / ".join(sources) or "local",
    }


def get_cached_rates(
    base_currency: str = "USD",
    currency_filter: str | None = None,
    top: int | None = None,
    crypto_currencies: tuple[str, ...] = ("BTC", "ETH", "SOL"),
) -> dict:
    """Возвращает курсы, отсортированные и готовые к отображению."""
    settings = SettingsLoader()
    database = DatabaseManager()

    base = normalize_currency_code(base_currency)
    get_currency(base)

    if currency_filter is not None:
        currency_filter = normalize_currency_code(currency_filter)
        get_currency(currency_filter)

    if top is not None and top <= 0:
        raise ValueError("'top' должен быть положительным числом")

    data = database.read_json(settings.get("RATES_FILE"))
    if not isinstance(data, dict):
        raise ApiRequestError("Некорректный формат кеша курсов")

    pairs = data.get("pairs", {})
    if not isinstance(pairs, dict):
        raise ApiRequestError("Некорректный список валютных пар")

    result = {
        "base": base,
        "last_refresh": data.get("last_refresh"),
        "rows": [],
    }

    if not pairs:
        return result

    currencies = {"USD"}

    for pair in pairs:
        if not isinstance(pair, str):
            continue
        codes = pair.split("_")
        if len(codes) == 2:
            currencies.update(codes)

    now = datetime.now(UTC)
    ttl = settings.get("RATES_TTL_SECONDS", 300)

    for currency in sorted(currencies):
        if currency == base:
            continue

        if currency_filter and currency != currency_filter:
            continue

        quote = _calculate_quote(currency, base, pairs)
        if quote is None:
            continue

        rate = quote["rate"]
        if not isfinite(rate) or rate <= 0:
            raise ApiRequestError(f"Некорректный курс {currency}_{base}")

        updated_at = quote["updated_at"]

        if updated_at is None:
            status = "локальный"
        else:
            timestamp = parse_iso_datetime(updated_at)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)

            age = (now - timestamp).total_seconds()
            status = "устарел" if age > ttl else "актуален"

        result["rows"].append(
            {
                "currency": currency,
                "pair": f"{currency}_{base}",
                "rate": rate,
                "updated_at": updated_at,
                "source": quote["source"],
                "status": status,
            }
        )

    if top is not None:
        crypto_set = set(crypto_currencies)
        result["rows"] = [
            row for row in result["rows"] if row["currency"] in crypto_set
        ]
        result["rows"].sort(
            key=lambda row: row["rate"],
            reverse=True,
        )
        result["rows"] = result["rows"][:top]
    else:
        result["rows"].sort(key=lambda row: row["pair"])

    return result
