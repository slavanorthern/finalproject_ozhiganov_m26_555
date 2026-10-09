"""Декораторы для логирования доменных операций."""

import functools
import logging
from collections.abc import Callable
from typing import Any


def log_action(
    action: str,
    verbose: bool = False,
):
    """Логирует успешное выполнение и ошибки доменной операции."""

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            logger = logging.getLogger(
                "valutatrade"
            )

            service = (
                args[0]
                if args
                else None
            )

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

            user_id = (
                current_user.user_id
                if current_user is not None
                else None
            )

            currency_code = None
            amount = None

            if action in {
                "BUY",
                "SELL",
            }:
                if "currency_code" in kwargs:
                    currency_code = kwargs[
                        "currency_code"
                    ]
                elif len(args) >= 2:
                    currency_code = args[1]

                if "amount" in kwargs:
                    amount = kwargs[
                        "amount"
                    ]
                elif len(args) >= 3:
                    amount = args[2]

            try:
                result = func(
                    *args,
                    **kwargs,
                )

                # После LOGIN/REGISTER можем получить
                # корректного пользователя из результата.
                if action in {
                    "LOGIN",
                    "REGISTER",
                }:
                    result_username = getattr(
                        result,
                        "username",
                        None,
                    )

                    result_user_id = getattr(
                        result,
                        "user_id",
                        None,
                    )

                    if result_username is not None:
                        username = result_username

                    if result_user_id is not None:
                        user_id = result_user_id

                rate = None
                base = None

                if isinstance(
                    result,
                    dict,
                ):
                    rate = result.get(
                        "rate"
                    )

                    base = result.get(
                        "base"
                    )

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
                    message += (
                        f" details={result!r}"
                    )

                logger.info(
                    message
                )

                return result

            except Exception as error:
                logger.exception(
                    "%s user=%r user_id=%r "
                    "currency=%r amount=%r "
                    "result=ERROR "
                    "error_type=%s "
                    "error_message=%s",
                    action,
                    username,
                    user_id,
                    currency_code,
                    amount,
                    type(
                        error
                    ).__name__,
                    str(
                        error
                    ),
                )

                raise

        return wrapper

    return decorator