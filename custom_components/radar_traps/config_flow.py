"""Config flow for the Radar Traps Bremen integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    TRAFFIC_URL,
)
from .parser import RadarPageError, parse_radar_page

_LOGGER = logging.getLogger(__name__)

TITLE = "Blitzer Bremen"


def _schema(scan_interval: int) -> vol.Schema:
    """Build the options schema, pre-filled with the current interval."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL_MINUTES, default=scan_interval
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL_MINUTES,
                    max=MAX_SCAN_INTERVAL_MINUTES,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            )
        }
    )


async def _async_validate_page(hass: HomeAssistant) -> None:
    """Confirm the traffic page is reachable and carries a radar trap section."""
    session = async_get_clientsession(hass)
    response = await session.get(TRAFFIC_URL, timeout=aiohttp.ClientTimeout(total=30))
    response.raise_for_status()
    html = await response.text()
    await hass.async_add_executor_job(parse_radar_page, html)


class RadarTrapsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the setup; the page needs no configuration to be read.

        There is one page and one set of radar traps, so the manifest marks the
        integration as single-instance and Home Assistant blocks a second entry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate_page(self.hass)
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except RadarPageError:
                errors["base"] = "cannot_parse"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=TITLE,
                    data={},
                    options={
                        CONF_SCAN_INTERVAL_MINUTES: int(
                            user_input[CONF_SCAN_INTERVAL_MINUTES]
                        )
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(DEFAULT_SCAN_INTERVAL_MINUTES),
            errors=errors,
            description_placeholders={"url": TRAFFIC_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> RadarTrapsOptionsFlow:
        """Return the options flow."""
        return RadarTrapsOptionsFlow()


class RadarTrapsOptionsFlow(OptionsFlow):
    """Allow the polling interval to be changed after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL_MINUTES: int(
                        user_input[CONF_SCAN_INTERVAL_MINUTES]
                    )
                }
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        return self.async_show_form(step_id="init", data_schema=_schema(current))
