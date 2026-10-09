import logging
from datetime import UTC, datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Обновляет курсы валют через подключенные API."""

    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: RatesStorage,
        config: ParserConfig,
    ) -> None:
        self.clients = clients
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger("valutatrade")

    @staticmethod
    def _source_matches(
        client: BaseApiClient,
        source: str | None,
    ) -> bool:
        """Проверяет соответствие клиента выбранному источнику."""
        if source is None:
            return True

        requested = source.lower().strip()
        client_source = client.source_name.lower()

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

        for canonical_name, names in aliases.items():
            if client_source in names:
                return requested in names or requested == canonical_name

        return requested == client_source

    def run_update(
        self,
        source: str | None = None,
    ) -> dict:
        """Получает свежие курсы и сохраняет их."""
        collected_rates: dict[str, dict] = {}
        errors: list[str] = []

        selected_clients = [
            client
            for client in self.clients
            if self._source_matches(
                client,
                source,
            )
        ]

        if not selected_clients:
            raise ValueError(
                f"Неизвестный источник курсов: {source}"
            )

        for client in selected_clients:
            try:
                rates = client.fetch_rates()

                updated_at = datetime.now(
                    UTC
                ).isoformat()

                for pair, rate in rates.items():
                    collected_rates[pair] = {
                        "rate": float(rate),
                        "updated_at": updated_at,
                        "source": client.source_name,
                    }

                self.logger.info(
                    "RATE_UPDATE source=%s count=%s result=OK",
                    client.source_name,
                    len(rates),
                )

            except ApiRequestError as error:
                message = (
                    f"{client.source_name}: {error}"
                )

                errors.append(message)

                self.logger.error(
                    "RATE_UPDATE source=%s result=ERROR error=%s",
                    client.source_name,
                    error,
                )

        if not collected_rates:
            details = "; ".join(errors)

            if not details:
                details = "данные не получены"

            raise ApiRequestError(
                f"не удалось обновить курсы: {details}"
            )

        last_refresh = datetime.now(
            UTC
        ).isoformat()

        self.storage.save_current_rates(
            self.config.rates_file_path,
            collected_rates,
            last_refresh,
        )

        self.storage.append_history(
            self.config.history_file_path,
            collected_rates,
        )

        return {
            "updated_count": len(
                collected_rates
            ),
            "errors": errors,
            "last_refresh": last_refresh,
        }