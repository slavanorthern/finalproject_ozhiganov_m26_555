import functools
import logging
from collections.abc import Callable
from typing import Any


def log_action(
    action: str,
    verbose: bool = False,
):
    """Логирует доменную операцию."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("valutatrade")

            try:
                result = func(*args, **kwargs)

                if verbose:
                    logger.info(
                        "%s result=OK details=%s",
                        action,
                        result,
                    )
                else:
                    logger.info(
                        "%s result=OK",
                        action,
                    )

                return result

            except Exception as error:
                logger.exception(
                    "%s result=ERROR error_type=%s error_message=%s",
                    action,
                    type(error).__name__,
                    str(error),
                )
                raise

        return wrapper

    return decorator