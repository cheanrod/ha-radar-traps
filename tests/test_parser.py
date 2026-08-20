"""Tests for the Bremen Vier traffic page parser.

These run against a saved copy of the real page, so they double as a canary for
layout changes: refresh the fixture and the expected values below when Bremen
Vier reworks the page.
"""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# Load the parser as a standalone module. Importing the component package would
# pull in its Home Assistant dependencies, which the parser itself does not need.
_COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "radar_traps"
_pkg = types.ModuleType("_radar_traps")
_pkg.__path__ = [str(_COMPONENT)]
sys.modules.setdefault("_radar_traps", _pkg)

_parser = importlib.import_module("_radar_traps.parser")
RadarPageError = _parser.RadarPageError
parse_radar_page = _parser.parse_radar_page
parse_reported_at = _parser.parse_reported_at

FIXTURE = Path(__file__).parent / "fixtures" / "verkehr.html"
# The same page on a day without a single radar trap: the section is left out.
FIXTURE_NO_RADARTRAPS = (
    Path(__file__).parent / "fixtures" / "verkehr-no-radartraps.html"
)
BERLIN = ZoneInfo("Europe/Berlin")


@pytest.fixture(name="traps", scope="module")
def traps_fixture():
    """Parse the saved traffic page once for all tests."""
    return parse_radar_page(FIXTURE.read_text(encoding="utf-8"))


def _section(entries: str) -> str:
    """Wrap entry markup in the page's radar trap section."""
    return f"""
    <html><body>
      <section class="traffic-section -traffic-section-faults">
        <ul><li class="traffic-section-entry"><div class="traffic-event">
          <p class="traffic-event-topline">Unfall</p>
          <h3 class="traffic-event-title">A27, Unfall bei Ihlpohl.</h3>
        </div></li></ul>
      </section>
      <section class="traffic-section -traffic-section-radartraps">
        <h2 class="traffic-section-title">Blitzer</h2>
        <ul class="traffic-section-entries">{entries}</ul>
        <div class="article-legal"><p>Quelle Blitzer: Bremen Vier</p></div>
      </section>
    </body></html>
    """


ENTRY = """
<li class="traffic-section-entry"><div class="traffic-event">
  <span class="icon -icon-radartrap"></span>
  <div class="traffic-event-text">
    <p class="traffic-event-topline">Blitzer</p>
    <h3 class="traffic-event-title">{location}</h3>
    <p class="traffic-event-date">{date}</p>
  </div>
</div></li>
"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("17. August 2026, 08:41 Uhr", datetime(2026, 8, 17, 8, 41, tzinfo=BERLIN)),
        ("1. März 2026, 23:05 Uhr", datetime(2026, 3, 1, 23, 5, tzinfo=BERLIN)),
        # Defensive: a date line that lost its time.
        ("3. Dezember 2025", datetime(2025, 12, 3, 0, 0, tzinfo=BERLIN)),
        ("gestern", None),
        ("32. August 2026, 08:41 Uhr", None),
        ("", None),
    ],
)
def test_parse_reported_at(text, expected):
    """German date lines are parsed as Bremen local time."""
    assert parse_reported_at(text) == expected


def test_fixture_entries(traps):
    """The saved page lists two radar traps, in page order."""
    assert [trap.location for trap in traps] == [
        "B75, Bremen Richtung Delmenhorst, Höhe Abfahrt Mittelshuchting.",
        "Bremen, Breitenweg, kurz hinter dem Flyover, stadteinwärtsd",
    ]


def test_fixture_report_times(traps):
    """Each entry carries the time it was reported."""
    assert traps[0].reported == "17. August 2026, 08:41 Uhr"
    assert traps[0].reported_at == datetime(2026, 8, 17, 8, 41, tzinfo=BERLIN)
    assert traps[1].reported_at == datetime(2026, 8, 17, 18, 6, tzinfo=BERLIN)


def test_topline_is_dropped(traps):
    """The repeated "Blitzer" topline is not part of the location."""
    assert all(not trap.location.startswith("Blitzer") for trap in traps)


def test_traffic_messages_are_ignored(traps):
    """Accidents and roadworks live in a sibling section and stay out."""
    assert all("Unfall" not in trap.location for trap in traps)


def test_empty_section_is_not_an_error():
    """No radar traps right now is a valid, empty result."""
    assert parse_radar_page(_section("")) == []


def test_missing_section_is_not_an_error():
    """The page drops the section entirely when nothing is reported."""
    html = """
    <html><body><div class="traffic">
      <section class="traffic-section -traffic-section-warnings">
        <ul><li class="traffic-section-entry"><div class="traffic-event">
          <p class="traffic-event-topline">Gegenstände auf der Fahrbahn</p>
          <h3 class="traffic-event-title">Vorsicht bitte auf der A7.</h3>
        </div></li></ul>
      </section>
    </div></body></html>
    """
    assert parse_radar_page(html) == []


def test_saved_page_without_the_section():
    """A real copy of the page on a trap-free day parses as empty, not an error."""
    html = FIXTURE_NO_RADARTRAPS.read_text(encoding="utf-8")
    assert "radartraps" not in html
    assert parse_radar_page(html) == []


def test_page_without_traffic_container_raises():
    """Losing the container around the sections means the page was reworked."""
    with pytest.raises(RadarPageError):
        parse_radar_page("<html><body><p>Wartung</p></body></html>")


def test_entry_without_date():
    """An entry that lost its date line still yields its location."""
    html = _section(
        """
        <li class="traffic-section-entry"><div class="traffic-event">
          <p class="traffic-event-topline">Blitzer</p>
          <h3 class="traffic-event-title">Bremen, Kurfürstenallee</h3>
        </div></li>
        """
    )
    (trap,) = parse_radar_page(html)
    assert trap.location == "Bremen, Kurfürstenallee"
    assert trap.reported is None
    assert trap.reported_at is None


def test_entry_without_title_class():
    """A retitled entry falls back to its remaining text, minus topline/date."""
    html = _section(
        """
        <li class="traffic-section-entry"><div class="traffic-event">
          <p class="traffic-event-topline">Blitzer</p>
          <h3>Bremen, Osterdeich, stadtauswärts</h3>
          <p class="traffic-event-date">17. August 2026, 08:41 Uhr</p>
        </div></li>
        """
    )
    (trap,) = parse_radar_page(html)
    assert trap.location == "Bremen, Osterdeich, stadtauswärts"
    assert trap.reported_at == datetime(2026, 8, 17, 8, 41, tzinfo=BERLIN)


def test_markup_inside_a_title_is_flattened():
    """Line breaks and inline markup collapse into one clean sentence."""
    html = _section(
        ENTRY.format(
            location="A1,<br> Richtung Osnabr&uuml;ck, <strong>H&ouml;he Arsten</strong>",
            date="17. August 2026, 08:41 Uhr",
        )
    )
    (trap,) = parse_radar_page(html)
    assert trap.location == "A1, Richtung Osnabrück, Höhe Arsten"


def test_multiple_entries_keep_page_order():
    """Every entry in the section is returned, in the order it is listed."""
    html = _section(
        ENTRY.format(location="Erster", date="17. August 2026, 08:41 Uhr")
        + ENTRY.format(location="Zweiter", date="17. August 2026, 18:06 Uhr")
        + ENTRY.format(location="Dritter", date="17. August 2026, 09:12 Uhr")
    )
    assert [trap.location for trap in parse_radar_page(html)] == [
        "Erster",
        "Zweiter",
        "Dritter",
    ]
