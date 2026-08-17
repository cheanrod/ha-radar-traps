"""Shared entity plumbing for the Radar Traps Bremen integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_COUNT,
    ATTR_LAST_REPORTED,
    ATTR_LOCATION,
    ATTR_LOCATIONS,
    ATTR_MESSAGES,
    ATTR_REPORTED,
    ATTR_REPORTED_AT,
    ATTR_TRAPS,
    DOMAIN,
    NO_TRAPS_MESSAGE,
    TRAFFIC_URL,
)
from .coordinator import RadarTrapsCoordinator
from .parser import RadarTrap


def newest(traps: list[RadarTrap]) -> RadarTrap | None:
    """Return the most recently reported trap, if any.

    The page is not strictly ordered, and entries without a parsable date sort
    last so a broken date line cannot hide a fresh report.
    """
    if not traps:
        return None
    dated = [trap for trap in traps if trap.reported_at is not None]
    if dated:
        return max(dated, key=lambda trap: trap.reported_at)
    return traps[0]


def trap_attributes(traps: list[RadarTrap]) -> dict[str, Any]:
    """Build the attribute set shared by every entity.

    ``locations`` and ``messages`` hold the same list; ``messages`` falls back
    to a "Keine Blitzer" placeholder when nothing is listed, so a notification
    built from it is never blank.
    """
    latest = newest(traps)
    return {
        ATTR_COUNT: len(traps),
        ATTR_LOCATIONS: [trap.location for trap in traps],
        ATTR_MESSAGES: [trap.location for trap in traps] or [NO_TRAPS_MESSAGE],
        ATTR_TRAPS: [
            {
                ATTR_LOCATION: trap.location,
                ATTR_REPORTED: trap.reported,
                ATTR_REPORTED_AT: (
                    trap.reported_at.isoformat() if trap.reported_at else None
                ),
            }
            for trap in traps
        ],
        ATTR_LAST_REPORTED: (
            latest.reported_at.isoformat()
            if latest and latest.reported_at
            else None
        ),
    }


class RadarTrapsEntity(CoordinatorEntity[RadarTrapsCoordinator]):
    """Base entity tying every state to the one traffic page."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RadarTrapsCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Blitzer Bremen",
            manufacturer="Bremen Vier",
            model="Verkehrsmeldungen",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=TRAFFIC_URL,
        )

    @property
    def traps(self) -> list[RadarTrap]:
        """The radar traps from the last successful update."""
        return self.coordinator.data or []

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full list of traps, for notification templates."""
        return trap_attributes(self.traps)
