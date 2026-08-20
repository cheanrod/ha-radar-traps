# Blitzer Bremen — notes for Claude

A Home Assistant custom integration that scrapes the Bremen Vier traffic page.

## Releasing

HACS takes the version from the release tag, Home Assistant from the manifest,
so the two have to agree — the tag carries a `v`, the manifest does not:

1. Bump `version` in `custom_components/radar_traps/manifest.json`
2. Commit, then `git tag -a vX.Y.Z` and push both
3. `gh release create vX.Y.Z` — the release, not just the tag, is what HACS
   offers users

## Translations

`strings.json` and `translations/en.json` are byte-identical duplicates, and
`translations/de.json` mirrors their structure. Any wording change has to land
in all three; changing only one leaves the UI showing the stale text.

## Tests

The parser is deliberately standard-library only, so the suite needs nothing but
pytest and runs without Home Assistant installed:

```bash
pip install pytest && pytest
```

`tests/fixtures/` holds two saved copies of the real page — one with radar traps
listed, one from a day without. Keep both: the page renders only the sections
that currently carry content, so those are two genuinely different layouts, and
an absent radar trap section must never be treated as an error.
