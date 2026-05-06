# Current roadmap position

## Active block

Block 3 - Artist enrichment.

## Methodology

- Work one complete block per macropaso whenever possible.
- Deliver a ZIP with the changed files at the end of each block.
- Do not jump outside the roadmap.
- Close every block with a Git commit.
- Report the accumulated estimated project percentage after every block.

## Current block scope

Block 3 adds the artist enrichment foundation:

- Spotify client for image, links, top tracks and latest releases when credentials are configured.
- Last.fm client for public bio, top tracks, listeners and playcount when an API key is configured.
- MusicBrainz client for aliases, country and release metadata.
- Local JSON cache at `backend/app/data/artists/enriched_artists.json`.
- Artist profile API ready for the frontend.

## Next block

Block 4 - Subgenre classification.
