# Blitzer Bremen — Home Assistant integration

Provides the radar traps ("Blitzer") that
[Bremen Vier](https://www.bremenvier.de/verkehr/index.html) lists on its traffic
page as Home Assistant entities, so you can be notified before you drive into
one.

## Installation

**HACS** — add this repository as a custom repository (category *Integration*),
install it, and restart Home Assistant.

**Manual** — copy `custom_components/radar_traps` into your Home Assistant
`config/custom_components/` directory and restart.

Then add the integration under *Settings → Devices & Services → Add Integration
→ Blitzer Bremen*. Nothing needs to be configured; the only option is how often
the page is fetched (default: every 10 minutes). It can be changed later via the
integration's *Configure* button.

## Entities

Entity ids are derived from the entity names, which are translated — on a
German instance they read `sensor.blitzer_bremen_blitzer` and so on. Check
*Developer Tools → States* for the ids on your system.

| Entity | State | Notes |
| --- | --- | --- |
| `binary_sensor.blitzer_bremen_radar_traps_reported` | `on` / `off` | On while at least one radar trap is listed — the entity to trigger notifications on |
| `sensor.blitzer_bremen_radar_traps` | number | How many radar traps are currently listed |
| `sensor.blitzer_bremen_latest_radar_trap` | text | Location of the most recently reported trap, or `Keine Blitzer` |
| `sensor.blitzer_bremen_last_reported` | timestamp | When the newest trap was reported |

All four carry the same attributes, so any of them can be used as the source for
a notification:

| Attribute | Contents |
| --- | --- |
| `count` | Number of listed radar traps |
| `locations` | List of locations, in page order |
| `messages` | Same list, but `["Keine Blitzer"]` when empty, so it is never blank in a message |
| `traps` | List of `{location, reported, reported_at}` objects |
| `last_reported` | ISO timestamp of the newest report |

If the page cannot be fetched, or what is served is no longer the traffic page,
the entities go *unavailable* rather than reporting a stale list. Having no
radar traps is a normal state (`off` / `0`), not an error — the page leaves the
radar trap section out entirely while nothing is reported.

## Example: notify when a radar trap shows up

```yaml
automation:
  - alias: Blitzer notification
    triggers:
      - trigger: state
        entity_id: binary_sensor.blitzer_bremen_radar_traps_reported
        from: "off"
        to: "on"
    actions:
      - action: notify.mobile_app_phone
        data:
          title: >
            {{ state_attr('binary_sensor.blitzer_bremen_radar_traps_reported',
                          'count') }} Blitzer in Bremen
          message: >
            {{ state_attr('binary_sensor.blitzer_bremen_radar_traps_reported',
                          'locations') | join('\n') }}
```

To be told about every *new* trap, not just the first one, trigger on the count
sensor instead and send the newest location:

```yaml
automation:
  - alias: New radar trap
    triggers:
      - trigger: numeric_state
        entity_id: sensor.blitzer_bremen_radar_traps
        above: 0
      - trigger: state
        entity_id: sensor.blitzer_bremen_latest_radar_trap
    conditions:
      - condition: numeric_state
        entity_id: sensor.blitzer_bremen_radar_traps
        above: 0
    actions:
      - action: notify.mobile_app_phone
        data:
          title: Blitzer
          message: "{{ states('sensor.blitzer_bremen_latest_radar_trap') }}"
```

Add a `condition` on `device_tracker` or a zone if you only want to hear about
it while you are actually driving.

## Notes

- Only the publicly available traffic page is read; no account or login is
  involved, and no data is sent anywhere.
- The traffic messages (accidents, roadworks) in the sibling section of the same
  page are deliberately ignored — this integration covers radar traps only.
- Report times are published in German local time and are exposed as proper
  timestamps.
- The tests in `tests/` run against saved copies of the page in
  `tests/fixtures/` — `verkehr.html` from a day with radar traps listed,
  `verkehr-no-radartraps.html` from one without. Refresh the matching one and
  update the expected values when the page layout changes:

  ```bash
  curl -sL https://www.bremenvier.de/verkehr/index.html -o tests/fixtures/verkehr.html
  pytest
  ```

## Disclaimer

Not affiliated with or endorsed by Radio Bremen or Bremen Vier. The listed
radar traps are crowd-reported, may be outdated or wrong, and are provided
without warranty. Keep to the speed limit.

## License

[MIT](LICENSE). Covers this integration's code only — the traffic reports it
reads are published by Bremen Vier and are not part of this license.
