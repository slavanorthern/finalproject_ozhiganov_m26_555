"""Координация получения и сохранения валютных курсов."""

import logging
from datetime import UTC, datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Получает курсы из API и сохраняет их в локальное хранилище."""

    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: RatesStorage,
        config: ParserConfig,
    ) -> None:
        self.clients = clients
        self.storage = storage
        self.config = config

        self.logger = logging.getLogger(
            "valutatrade"
        )

    @staticmethod
    def _utc_now_iso() -> str:
        """Возвращает текущее время UTC в ISO-формате."""
        return (
            datetime.now(UTC)
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )

    @staticmethod
    def _source_matches(
        client: BaseApiClient,
        source: str | None,
    ) -> bool:
        """Проверяет соответствие клиента выбранному источнику."""
        if source is None:
            return True

        requested = (
            source.strip()
            .lower()
        )

        client_source = (
            client.source_name
            .strip()
            .lower()
        )

        aliases = {
            "coingecko": {
                "coingecko",
            },
            "exchangerate-api": {
                "exchangerate",
                "exchangerate-api",
                "exchangerateapi",
            },
        }

        for (
            canonical_name,
            names,
        ) in aliases.items():
            if client_source in names:
                return (
                    requested in names
                    or requested
                    == canonical_name
                )

        return (
            requested
            == client_source
        )

    def run_update(
        self,
        source: str | None = None,
    ) -> dict:
        """Обновляет курсы из одного или всех источников."""
        self.logger.info(
            "RATE_UPDATE_START source=%r",
            source or "all",
        )

        selected_clients = [
            client
            for client in self.clients
            if self._source_matches(
                client,
                source,
            )
        ]

        if not selected_clients:
            self.logger.error(
                "RATE_UPDATE_END "
                "source=%r result=ERROR "
                "error_type=ValueError "
                "error_message=unknown_source",
                source,
            )

            raise ValueError(
                f"Неизвестный источник курсов: {source}"
            )

        collected_rates: dict[
            str,
            dict,
        ] = {}

        errors: list[str] = []

        for client in selected_clients:
            self.logger.info(
                "RATE_FETCH_START source=%s",
                client.source_name,
            )

            try:
                rates = (
                    client.fetch_rates()
                )

                updated_at = (
                    self._utc_now_iso()
                )

                for (
                    pair,
                    rate,
                ) in rates.items():
                    collected_rates[
                        pair
                    ] = {
                        "rate": float(
                            rate
                        ),
                        "updated_at": (
                            updated_at
                        ),
                        "source": (
                            client.source_name
                        ),
                    }

                self.logger.info(
                    "RATE_FETCH_END "
                    "source=%s "
                    "count=%s "
                    "result=OK",
                    client.source_name,
                    len(rates),
                )

            except ApiRequestError as error:
                message = (
                    f"{client.source_name}: "
                    f"{error}"
                )

                errors.append(
                    message
                )

                self.logger.error(
                    "RATE_FETCH_END "
                    "source=%s "
                    "result=ERROR "
                    "error_type=%s "
                    "error_message=%s",
                    client.source_name,
                    type(
                        error
                    ).__name__,
                    str(
                        error
                    ),
                )

        if not collected_rates:
            details = (
                "; ".join(errors)
                if errors
                else "данные не получены"
            )

            self.logger.error(
                "RATE_UPDATE_END "
                "result=ERROR "
                "error_message=%s",
                details,
            )

            raise ApiRequestError(
                "не удалось обновить курсы: "
                f"{details}"
            )

        last_refresh = (
            self._utc_now_iso()
        )

        self.logger.info(
            "RATE_STORAGE_START "
            "count=%s",
            len(
                collected_rates
            ),
        )

        self.storage.save_current_rates(
            self.config.rates_file_path,
            collected_rates,
            last_refresh,
        )

        self.storage.append_history(
            self.config.history_file_path,
            collected_rates,
        )

        self.logger.info(
            "RATE_STORAGE_END "
            "count=%s result=OK",
            len(
                collected_rates
            ),
        )

        if errors:
            result_status = (
                "PARTIAL"
            )
        else:
            result_status = "OK"

        self.logger.info(
            "RATE_UPDATE_END "
            "count=%s "
            "errors=%s "
            "last_refresh=%s "
            "result=%s",
            len(
                collected_rates
            ),
            len(errors),
            last_refresh,
            result_status,
        )

        return {
            "updated_count": len(
                collected_rates
            ),
            "errors": errors,
            "last_refresh": (
                last_refresh
            ),
        }