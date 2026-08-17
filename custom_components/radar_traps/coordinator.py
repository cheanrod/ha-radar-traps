"""Data update coordinator for the Radar Traps Bremen integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    TRAFFIC_URL,
)
from .parser import RadarPageError, RadarTrap, parse_radar_page

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class RadarTrapsCoordinator(DataUpdateCoordinator[list[RadarTrap]]):
    """Fetch and parse the Bremen Vier traffic page."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        minutes = entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
            config_entry=entry,
        )
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> list[RadarTrap]:
        """Fetch the traffic page and parse the radar traps off it."""
        try:
            response = await self._session.get(TRAFFIC_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            html = await response.text()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching {TRAFFIC_URL}: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching {TRAFFIC_URL}") from err

        # Parsing is pure CPU work on an ~80 kB document; keep it off the event
        # loop so a pathological page cannot stall Home Assistant.
        try:
            traps = await self.hass.async_add_executor_job(parse_radar_page, html)
        except RadarPageError as err:
            raise UpdateFailed(str(err)) from err

        _LOGGER.debug("Fetched %d radar trap entries", len(traps))
        return traps
