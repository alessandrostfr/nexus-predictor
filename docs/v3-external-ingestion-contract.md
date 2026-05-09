# V3.4 external ingestion contract

This document defines the architecture contract introduced in **V3.4-A** and expanded in **V3.4-B**.

## V3.4-B official API contract

V3.4-B introduces official API collectors:

- `SpotifyOfficialCollector`
- `LastFmOfficialCollector`
- `MusicBrainzOfficialCollector`
- `YouTubeOfficialCollector`
- `SoundCloudOfficialProbe`

All collectors must follow these rules:

- no network calls during pytest;
- no credential values returned by API endpoints;
- no API keys/tokens stored in `raw_payload`;
- raw snapshots persist only when explicitly requested;
- normalized metrics must reference `raw_snapshot_id`;
- ambiguous sources such as YouTube channel matching and MusicBrainz candidates are evidence/profile candidates before they become features.

## Metrics expected by source

Spotify may emit when the current official API response contains the fields:

- `spotify_followers_total`
- `spotify_popularity_score`
- `spotify_genres`
- `spotify_artist_url`
- `spotify_image_url`
- `spotify_external_id`

If Spotify omits/deprecates followers, artist popularity, genres or track popularity, the probe must not invent values. It must return `partial`, expose `unavailable_metric_keys`, and persist only the official fields actually returned. Exact track play counts and monthly listeners are not exposed by the official Spotify Web API.

Last.fm may emit:

- `lastfm_listeners_total`
- `lastfm_playcount_total`
- `lastfm_tags`
- `lastfm_bio_available`
- `lastfm_url`

MusicBrainz may emit:

- `musicbrainz_mbid`
- `musicbrainz_country`
- `musicbrainz_type`
- `musicbrainz_disambiguation`
- `musicbrainz_match_confidence`

YouTube may emit candidate metrics when `YOUTUBE_API_KEY` exists, but defaults to `feature_candidate=false` until review.

SoundCloud official access may be `access_unconfirmed` or `access_unavailable`; V3.4-C will prepare metadata-only fallback if official access is not viable.

## Credential states

Allowed safe credential states are:

- `configured`
- `missing`

Allowed source states include:

- `configured`
- `not_configured`
- `access_unconfirmed`
- `access_unavailable`
- `invalid_credentials`
- `rate_limited`

## ML honesty

V3.4-B does not create ML labels, trained models or predictions. It creates traceable raw evidence and normalized metric candidates for later quality gates and feature engineering.