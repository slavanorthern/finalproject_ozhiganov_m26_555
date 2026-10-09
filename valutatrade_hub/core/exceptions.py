class InsufficientFundsError(Exception):
    """Недостаточно средств в кошельке."""

    def __init__(self, available: float, required: float, code: str) -> None:
        message = (
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(Exception):
    """Неизвестная валюта."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Ошибка при обращении к внешнему API."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")