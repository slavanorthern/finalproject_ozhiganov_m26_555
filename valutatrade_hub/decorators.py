"""Декораторы для логирования доменных операций."""

import functools
import logging
from collections.abc import Callable
from typing import Any


def log_action(
    action: str,
    verbose: bool = False,
):
    """Логирует успешные операции и исключения."""

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("valutatrade")
            service = args[0] if args else None

            current_user = getattr(service, "current_user", None)
            username = current_user.username if current_user is not None else None
            user_id = current_user.user_id if current_user is not None else None

            currency_code = None
            amount = None

            # Для регистрации и входа фиксируем именно
            # запрошенное имя, даже если операция завершится ошибкой.
            if action in {"REGISTER", "LOGIN"}:
                username = (
                    kwargs.get("username")
                    if "username" in kwargs
                    else args[1]
                    if len(args) > 1
                    else None
                )
                user_id = None

            if action in {"BUY", "SELL"}:
                currency_code = (
                    kwargs.get("currency_code")
                    if "currency_code" in kwargs
                    else args[1]
                    if len(args) > 1
                    else None
                )
                amount = (
                    kwargs.get("amount")
                    if "amount" in kwargs
                    else args[2]
                    if len(args) > 2
                    else None
                )

            try:
                result = func(*args, **kwargs)

                if action in {"REGISTER", "LOGIN"}:
                    username = getattr(result, "username", username)
                    user_id = getattr(result, "user_id", user_id)

                rate = None
                base = None

                if isinstance(result, dict):
                    rate = result.get("rate")
                    base = result.get("base")

                message = (
                    f"{action} "
                    f"user={username!r} "
                    f"user_id={user_id!r} "
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
                    "%s user=%r user_id=%r "
                    "currency=%r amount=%r "
                    "result=ERROR error_type=%s error_message=%s",
                    action,
                    username,
                    user_id,
                    currency_code,
                    amount,
                    type(error).__name__,
                    str(error),
                )
                raise

        return wrapper

    return decorator
