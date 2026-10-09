import logging
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler(
    updater: RatesUpdater,
    interval_seconds: int = 300,
    source: str | None = None,
) -> None:
    """Периодически обновляет курсы валют."""
    if interval_seconds <= 0:
        raise ValueError(
            "Интервал обновления должен быть больше 0"
        )

    logger = logging.getLogger(
        "valutatrade"
    )

    logger.info(
        "SCHEDULER_STARTED interval=%s source=%s",
        interval_seconds,
        source,
    )

    while True:
        try:
            result = updater.run_update(
                source=source
            )

            logger.info(
                "SCHEDULER_UPDATE count=%s last_refresh=%s",
                result["updated_count"],
                result["last_refresh"],
            )

        except ApiRequestError as error:
            logger.error(
                "SCHEDULER_UPDATE result=ERROR error=%s",
                error,
            )

        time.sleep(interval_seconds)