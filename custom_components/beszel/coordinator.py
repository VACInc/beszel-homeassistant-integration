"""DataUpdateCoordinator for the Beszel integration."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BeszelApiAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BeszelDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching data from the Beszel API."""

    def __init__(self, hass, api_client, update_interval_seconds):
        """Initialize the data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_seconds),
        )
        self.api_client = api_client
        self.systems_list = []

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            await self.api_client.async_authenticate()

            self.systems_list = await self.api_client.async_get_systems()
            if not self.systems_list:
                _LOGGER.info("No systems found.")
                return {}

            all_system_data = {}
            systems_with_ids = [system for system in self.systems_list if system.get("id")]
            tasks = [
                self._fetch_individual_system_data(
                    system["id"], system.get("name", system["id"])
                )
                for system in systems_with_ids
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for system, result in zip(systems_with_ids, results, strict=False):
                system_id = system["id"]
                if isinstance(result, Exception):
                    _LOGGER.error(
                        "Error fetching data for system %s: %s", system_id, result
                    )
                    all_system_data[system_id] = {"error": str(result)}
                elif result:
                    all_system_data[system_id] = result
                else:
                    all_system_data[system_id] = {
                        "error": "Unknown error fetching data for system"
                    }

            return all_system_data

        except BeszelApiAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_individual_system_data(self, system_id, system_name):
        """Fetch stats and 'info' for a single system."""
        stats = await self.api_client.async_get_latest_system_stats(system_id)

        system_record = next(
            (s for s in self.systems_list if s.get("id") == system_id), None
        )
        device_info_summary = {}
        if system_record:
            device_info_summary = system_record.get("info", {})

        return {
            "id": system_id,
            "info": device_info_summary,
            "name": system_name,
            "stats": stats or {},
            "status": (
                system_record.get("status", "unknown") if system_record else "unknown"
            ),
        }
