"""Настройка логирования ValutaTrade Hub."""

import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> logging.Logger:
    """Настраивает файловое логирование с ротацией."""
    settings = SettingsLoader()

    logger = logging.getLogger("valutatrade")

    log_level_name = str(
        settings.get(
            "LOG_LEVEL",
            "INFO",
        )
    ).upper()

    log_level = getattr(
        logging,
        log_level_name,
        logging.INFO,
    )

    logger.setLevel(log_level)

    # Не передаем сообщения родительскому logger,
    # чтобы записи не дублировались.
    logger.propagate = False

    # setup_logging может вызываться повторно.
    # Не создаем второй обработчик.
    if logger.handlers:
        return logger

    log_file = settings.get("LOG_FILE")

    log_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )

    handler.setLevel(log_level)

    log_format = settings.get(
        "LOG_FORMAT",
        ("%(levelname)s %(asctime)s %(message)s"),
    )

    formatter = logging.Formatter(
        fmt=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger
