# V3.4-B official API setup

This document explains how to configure official API credentials for V3.4-B probes. Never commit `backend/.env`.

## Spotify

Expected variables:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

Spotify is used through the Client Credentials flow for public artist metadata.

## Last.fm

Expected variable:

```env
LASTFM_API_KEY=
```

Last.fm is used for listeners, playcount, tags and bio availability when coverage exists.

## MusicBrainz

Expected variable:

```env
MUSICBRAINZ_USER_AGENT=NexusPredictorV3/0.1 (local educational ML project; contact: your-email@example.com)
```

MusicBrainz does not need an API key, but it does require responsible use with a descriptive User-Agent and strict rate limiting.

## YouTube Data API v3

Expected variable:

```env
YOUTUBE_API_KEY=
```

Setup steps:

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable **YouTube Data API v3**.
4. Create an API key.
5. Restrict the key where possible.
6. Paste it into `backend/.env` only.
7. Use V3.4-B probes with a low `limit` because search endpoints consume quota.

## SoundCloud official access

Expected variables if access is available:

```env
SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
```

SoundCloud remains priority for the niche, but official API access may be limited. If access is unavailable or unconfirmed, V3.4-B records that honestly and V3.4-C prepares the approved `yt-dlp` metadata-only fallback plus manual review.

## Safety rules

- Do not print secret values.
- Do not paste `.env` into ChatGPT.
- Do not commit `.env`.
- Only `.env.example` belongs in Git.
- Prefer `limit=5` for manual probes.
