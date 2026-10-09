import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> None:
    """Настраивает логирование приложения."""
    settings = SettingsLoader()

    log_file = settings.get("LOG_FILE")
    log_level = settings.get("LOG_LEVEL", "INFO")
    log_format = settings.get(
        "LOG_FORMAT",
        "%(levelname)s %(asctime)s %(message)s",
    )

    log_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger = logging.getLogger("valutatrade")
    logger.setLevel(log_level)

    if logger.handlers:
        return

    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        log_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)