"""Sensor platform for the Radar Traps Bremen integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RadarTrapsConfigEntry
from .const import NO_TRAPS_MESSAGE
from .coordinator import RadarTrapsCoordinator
from .entity import RadarTrapsEntity, newest

# Home Assistant caps a state at 255 characters. Locations are single sentences
# and stay well below that, but a mangled page must not break the entity.
MAX_STATE_LENGTH = 255


def _shorten(value: str) -> str:
    """Trim a location to what fits into a state."""
    if len(value) <= MAX_STATE_LENGTH:
        return value
    return value[: MAX_STATE_LENGTH - 1].rstrip() + "…"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RadarTrapsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors for a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            RadarTrapCountSensor(coordinator),
            RadarTrapLatestSensor(coordinator),
            RadarTrapLastReportedSensor(coordinator),
        ]
    )


class RadarTrapCountSensor(RadarTrapsEntity, SensorEntity):
    """How many radar traps are currently listed."""

    _attr_translation_key = "count"
    _attr_icon = "mdi:cctv"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RadarTrapsCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "count")

    @property
    def native_value(self) -> int:
        """Return the number of listed radar traps."""
        return len(self.traps)


class RadarTrapLatestSensor(RadarTrapsEntity, SensorEntity):
    """The most recently reported radar trap, ready to drop into a message."""

    _attr_translation_key = "latest"
    _attr_icon = "mdi:map-marker-alert"

    def __init__(self, coordinator: RadarTrapsCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "latest")

    @property
    def native_value(self) -> str:
        """Return the newest location, or the empty-list placeholder."""
        latest = newest(self.traps)
        return _shorten(latest.location) if latest else NO_TRAPS_MESSAGE


class RadarTrapLastReportedSensor(RadarTrapsEntity, SensorEntity):
    """When the newest radar trap was reported."""

    _attr_translation_key = "last_reported"
    _attr_icon = "mdi:clock-alert-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: RadarTrapsCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "last_reported")

    @property
    def native_value(self) -> datetime | None:
        """Return the report time of the newest trap."""
        latest = newest(self.traps)
        return latest.reported_at if latest else None
