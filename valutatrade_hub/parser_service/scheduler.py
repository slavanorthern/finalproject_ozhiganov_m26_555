"""Планировщик периодического обновления валютных курсов."""

import logging
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler(
    updater: RatesUpdater,
    interval_seconds: int = 300,
    source: str | None = None,
) -> None:
    """Периодически запускает обновление валютных курсов."""
    if (
        not isinstance(interval_seconds, int)
        or isinstance(interval_seconds, bool)
        or interval_seconds <= 0
    ):
        raise ValueError(
            "Интервал обновления должен быть "
            "положительным целым числом"
        )

    logger = logging.getLogger(
        "valutatrade"
    )

    logger.info(
        "SCHEDULER_START interval=%s source=%s",
        interval_seconds,
        source,
    )

    while True:
        try:
            result = updater.run_update(
                source=source
            )

            logger.info(
                "SCHEDULER_UPDATE "
                "count=%s "
                "last_refresh=%s "
                "result=OK",
                result["updated_count"],
                result["last_refresh"],
            )

            print(
                "Автоматическое обновление выполнено: "
                f"{result['updated_count']} курсов. "
                f"Время: {result['last_refresh']}"
            )

            if result["errors"]:
                for error in result["errors"]:
                    logger.warning(
                        "SCHEDULER_PARTIAL_ERROR %s",
                        error,
                    )

        except ApiRequestError as error:
            logger.error(
                "SCHEDULER_UPDATE "
                "result=ERROR error=%s",
                error,
            )

            print(
                f"Ошибка автоматического обновления: "
                f"{error}"
            )

        time.sleep(
            interval_seconds
        )