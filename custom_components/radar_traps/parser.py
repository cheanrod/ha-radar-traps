"""Parsing of the Bremen Vier traffic page.

The radar traps live in their own ``<section class="traffic-section
-traffic-section-radartraps">``, one ``<li>`` per trap holding a topline
("Blitzer"), the location as the entry title and the time it was reported. We
anchor on those class names and keep the location text only -- the topline is
the same word on every entry and the date is parsed separately.

The page only renders the sections that currently carry something, so the radar
trap section is absent whenever no trap is reported -- that is a normal, empty
result, not a failure. The same holds for the ``<div class="traffic">`` container
around the sections: on a quiet morning, with nothing at all to report, the page
leaves that out too. Missing markup therefore never raises; only markup we cannot
feed to the parser at all does.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

RADAR_SECTION_CLASS = "-traffic-section-radartraps"
ENTRY_CLASS = "traffic-section-entry"
TITLE_CLASS = "traffic-event-title"
DATE_CLASS = "traffic-event-date"
TOPLINE_CLASS = "traffic-event-topline"

# The page is published in German local time and carries no timezone.
SOURCE_TIMEZONE = ZoneInfo("Europe/Berlin")

_LOGGER = logging.getLogger(__name__)

# Tags that never carry an end tag, so they must not affect nesting counters.
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "maerz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}

# "17. August 2026, 08:41 Uhr"
_DATE_RE = re.compile(
    r"(?P<day>\d{1,2})\.\s*(?P<month>[A-Za-zÄÖÜäöüß]+)\s+(?P<year>\d{4})"
    r"(?:[,\s]+(?P<hour>\d{1,2}):(?P<minute>\d{2}))?",
)


class RadarPageError(Exception):
    """Raised when the document could not be parsed at all."""


@dataclass(frozen=True)
class RadarTrap:
    """A single reported radar trap."""

    location: str
    reported: str | None = None
    reported_at: datetime | None = None


def parse_reported_at(value: str) -> datetime | None:
    """Parse a German date line such as ``17. August 2026, 08:41 Uhr``."""
    match = _DATE_RE.search(value)
    if not match:
        return None
    month = _MONTHS.get(match.group("month").lower())
    if month is None:
        return None
    try:
        return datetime(
            year=int(match.group("year")),
            month=month,
            day=int(match.group("day")),
            hour=int(match.group("hour") or 0),
            minute=int(match.group("minute") or 0),
            tzinfo=SOURCE_TIMEZONE,
        )
    except ValueError:
        return None


def _clean(value: str) -> str:
    """Collapse whitespace, including the non-breaking kind."""
    return re.sub(r"[\s\xa0]+", " ", value).strip()


class _RadarParser(HTMLParser):
    """Collect the entries of the radar trap section."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section_found = False
        self.traps: list[RadarTrap] = []
        self._section_nesting = 0
        self._in_section = False
        self._entry_nesting = 0
        # Text of the current entry, split into the fields we care about.
        self._title: list[str] = []
        self._date: list[str] = []
        self._rest: list[str] = []
        self._field: str | None = None
        self._field_nesting = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()

        if not self._in_section:
            if tag == "section" and RADAR_SECTION_CLASS in classes:
                self._in_section = True
                self.section_found = True
                self._section_nesting = 0
            return

        if tag not in _VOID_TAGS:
            if tag == "section":
                self._section_nesting += 1
            if self._entry_nesting:
                self._entry_nesting += 1
            if self._field is not None:
                self._field_nesting += 1

        if self._entry_nesting == 0 and ENTRY_CLASS in classes:
            self._start_entry()
        elif self._entry_nesting and self._field is None:
            if TITLE_CLASS in classes:
                self._field, self._field_nesting = "title", 1
            elif DATE_CLASS in classes:
                self._field, self._field_nesting = "date", 1
            elif TOPLINE_CLASS in classes:
                # Always the literal word "Blitzer"; carries no information.
                self._field, self._field_nesting = "topline", 1

    def handle_endtag(self, tag: str) -> None:
        if not self._in_section or tag in _VOID_TAGS:
            return

        if self._field is not None:
            self._field_nesting -= 1
            if self._field_nesting <= 0:
                self._field = None

        if self._entry_nesting:
            self._entry_nesting -= 1
            if self._entry_nesting == 0:
                self._finish_entry()

        if tag == "section":
            if self._section_nesting:
                self._section_nesting -= 1
            else:
                self._in_section = False

    def handle_data(self, data: str) -> None:
        if not self._entry_nesting:
            return
        if self._field == "title":
            self._title.append(data)
        elif self._field == "date":
            self._date.append(data)
        elif self._field is None:
            # Fallback for a reworded entry that no longer marks its title.
            self._rest.append(data)

    def _start_entry(self) -> None:
        self._entry_nesting = 1
        self._title, self._date, self._rest = [], [], []
        self._field, self._field_nesting = None, 0

    def _finish_entry(self) -> None:
        location = _clean("".join(self._title)) or _clean("".join(self._rest))
        if not location:
            return
        reported = _clean("".join(self._date)) or None
        self.traps.append(
            RadarTrap(
                location=location,
                reported=reported,
                reported_at=parse_reported_at(reported) if reported else None,
            )
        )


def parse_radar_page(html: str) -> list[RadarTrap]:
    """Parse the traffic page and return the radar traps listed on it.

    An absent radar trap section is an empty result: the page leaves the section
    out while nothing is reported, and on a quiet day the whole traffic block is
    missing along with it.

    Raises:
        RadarPageError: if the document could not be parsed at all.
    """
    parser = _RadarParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as err:  # noqa: BLE001 - malformed markup must not raise
        raise RadarPageError(f"Could not parse the traffic page: {err}") from err

    if not parser.section_found:
        _LOGGER.debug("No radar trap section on the page; reporting no traps")

    return parser.traps
