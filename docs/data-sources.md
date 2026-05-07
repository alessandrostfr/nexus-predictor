# Data sources and confidence

Nexus Predictor uses editable local JSON files as the MVP source of truth.

## Source folders

```txt
backend/app/data/editions/
backend/app/data/artists/
backend/app/data/venue/
backend/app/data/predictions/
backend/app/data/timetables/
data-research/sources/
```

## Historical editions

Edition JSON files store dates, venue, duration, stage count, lineup and attendance ranges. Some attendance values are seed estimates rather than official confirmed figures, so each object includes confidence and notes.

## Artist data

The artist index is built from the lineups. Enriched profiles are cached locally in `enriched_artists.json`. Spotify, Last.fm and MusicBrainz integrations are prepared but optional.

## Genre data

`genre_overrides.json` contains the MVP hard-dance taxonomy, keyword rules and manual overrides. Manual overrides win over automatic rules.

## Venue and rooms

`fabrik_rooms.json` stores room names, slugs and capacity ranges. Public capacity information can vary by configuration, so values remain editable and should be treated as estimates unless an official source confirms a setup.

## Timetable data

`backend/app/data/timetables/2026.json` defines the expected import structure. Until official 2026 slots are available, the UI and API label room pressure as a theoretical simulation.

## Source notes

`data-research/sources/block_01_sources.md` lists the public sources used during the research blocks. Add new sources there with URL, supported data, capture date, confidence and ambiguity notes.
