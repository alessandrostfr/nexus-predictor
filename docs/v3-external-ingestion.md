# V3.4 external ingestion — operational notes

V3.4 is the data factory for future ML blocks. It does not train models and does not replace V2 predictions yet.

## Current macropaso

**V3.4-B — Configuración, credenciales y probes oficiales**

V3.4-A created the offline collector architecture. V3.4-B now adds official API credential diagnostics and controlled probes for Spotify, Last.fm, MusicBrainz, YouTube and SoundCloud.

## API endpoints available after V3.4-B

V3.4-A endpoints remain:

- `GET /api/v3/external-ingestion/architecture`
- `GET /api/v3/external-ingestion/sources`
- `GET /api/v3/external-ingestion/tools`
- `POST /api/v3/external-ingestion/dry-run`

V3.4-B adds:

- `GET /api/v3/external-ingestion/credentials`
- `POST /api/v3/external-ingestion/official-probes`

## Offline by default

`official-probes` does not make external calls unless this flag is true:


## Spotify current API limitation

Real Spotify probes may return URL/image/external-id while omitting followers, artist popularity, genres or track popularity. That is handled as a `partial` official probe with `unavailable_metric_keys`; the system must not invent missing values.
