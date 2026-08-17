"""Constants for the Radar Traps Bremen integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "radar_traps"

# Bremen Vier publishes the radar traps its listeners report, together with the
# regular traffic messages, on this page.
TRAFFIC_URL: Final = "https://www.bremenvier.de/verkehr/index.html"

CONF_SCAN_INTERVAL_MINUTES: Final = "scan_interval_minutes"

# Entries live on the page for hours, so there is nothing to gain from polling
# harder than this.
DEFAULT_SCAN_INTERVAL_MINUTES: Final = 10
MIN_SCAN_INTERVAL_MINUTES: Final = 5
MAX_SCAN_INTERVAL_MINUTES: Final = 180

# Stands in for the empty list in the `messages` attribute, so a notification
# built from it reads as a sentence rather than as nothing at all.
NO_TRAPS_MESSAGE: Final = "Keine Blitzer"

ATTR_COUNT: Final = "count"
ATTR_LAST_REPORTED: Final = "last_reported"
ATTR_LOCATION: Final = "location"
ATTR_LOCATIONS: Final = "locations"
ATTR_MESSAGES: Final = "messages"
ATTR_REPORTED: Final = "reported"
ATTR_REPORTED_AT: Final = "reported_at"
ATTR_TRAPS: Final = "traps"
