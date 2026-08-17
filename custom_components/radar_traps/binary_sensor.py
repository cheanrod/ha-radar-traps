"""Binary sensor platform for the Radar Traps Bremen integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RadarTrapsConfigEntry
from .coordinator import RadarTrapsCoordinator
from .entity import RadarTrapsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RadarTrapsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor for a config entry."""
    async_add_entities([RadarTrapsActiveBinarySensor(entry.runtime_data)])


class RadarTrapsActiveBinarySensor(RadarTrapsEntity, BinarySensorEntity):
    """On while Bremen Vier lists at least one radar trap.

    This is the entity to trigger notifications on: it flips off again once the
    last trap disappears from the page, so an automation can announce both.
    """

    _attr_translation_key = "active"
    _attr_icon = "mdi:cctv"

    def __init__(self, coordinator: RadarTrapsCoordinator) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, "active")

    @property
    def is_on(self) -> bool:
        """Return True while radar traps are listed."""
        return bool(self.traps)
