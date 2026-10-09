import functools
import logging
from collections.abc import Callable
from typing import Any


def log_action(
    action: str,
    verbose: bool = False,
):
    """Логирует доменную операцию и не подавляет исключения."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("valutatrade")

            service = args[0] if args else None
            current_user = getattr(
                service,
                "current_user",
                None,
            )

            username = (
                current_user.username
                if current_user is not None
                else None
            )

            currency_code = (
                kwargs.get("currency_code")
                or kwargs.get("currency")
            )

            amount = kwargs.get("amount")

            if amount is None and len(args) >= 3:
                amount = args[2]

            if currency_code is None and len(args) >= 2:
                currency_code = args[1]

            try:
                result = func(*args, **kwargs)

                rate = None
                base = None

                if isinstance(result, dict):
                    rate = result.get("rate")

                    if action in {"BUY", "SELL"}:
                        base = "USD"

                message = (
                    f"{action} "
                    f"user={username!r} "
                    f"currency={currency_code!r} "
                    f"amount={amount!r} "
                    f"rate={rate!r} "
                    f"base={base!r} "
                    "result=OK"
                )

                if verbose:
                    message += f" details={result!r}"

                logger.info(message)

                return result

            except Exception as error:
                logger.exception(
                    "%s user=%r currency=%r amount=%r "
                    "result=ERROR error_type=%s "
                    "error_message=%s",
                    action,
                    username,
                    currency_code,
                    amount,
                    type(error).__name__,
                    str(error),
                )
                raise

        return wrapper

    return decorator