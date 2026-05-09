"""Offline tests for V3.4-B official API probe contracts.

These tests intentionally do not make network calls. Real API validation is done
manually through scripts/endpoints with execute_real_calls=true.
"""

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.collectors.official_apis import (
    ArtistProbeTarget,
    LastFmOfficialCollector,
    MusicBrainzOfficialCollector,
    SoundCloudOfficialProbe,
    SpotifyOfficialCollector,
    YouTubeOfficialCollector,
    official_source_keys,
)
from app.db.database import SessionLocal
from app.db.models import NormalizedMetricModel, RawSnapshotModel
from app.main import app

client = TestClient(app)


def _counts() -> tuple[int, int]:
    """Return current raw snapshot and normalized metric counts."""
    with SessionLocal() as db:
        snapshots = int(db.scalar(select(func.count()).select_from(RawSnapshotModel)) or 0)
        metrics = int(db.scalar(select(func.count()).select_from(NormalizedMetricModel)) or 0)
    return snapshots, metrics


def test_v3_4_b_credentials_endpoint_is_sanitized() -> None:
    """Credential endpoint must expose status only, never secret values."""
    response = client.get("/api/v3/external-ingestion/credentials")
    assert response.status_code == 200
    payload = response.json()["data"]

    assert payload["block"] == "V3.4-B"
    assert payload["secret_values_exposed"] is False
    source_keys = {item["source_key"] for item in payload["sources"]}
    assert set(official_source_keys()).issubset(source_keys)

    serialized = str(payload).lower()
    assert "access_token" not in serialized
    assert "bearer " not in serialized
    assert "configured" in serialized or "missing" in serialized


def test_v3_4_b_official_probe_endpoint_is_offline_by_default() -> None:
    """Default probe request should plan probes without persisting external data."""
    snapshots_before, metrics_before = _counts()

    response = client.post(
        "/api/v3/external-ingestion/official-probes",
        json={"limit": 3, "sources": ["spotify_web_api", "lastfm_api"], "execute_real_calls": False, "persist": False},
    )
    assert response.status_code == 200
    payload = response.json()["data"]

    assert payload["block"] == "V3.4-B"
    assert payload["execute_real_calls"] is False
    assert payload["persist"] is False
    assert payload["collector_run_id"] is None
    assert payload["raw_snapshots_created"] == 0
    assert payload["normalized_metrics_created"] == 0

    snapshots_after, metrics_after = _counts()
    assert snapshots_after == snapshots_before
    assert metrics_after == metrics_before


def test_v3_4_b_persist_is_ignored_without_real_calls() -> None:
    """persist=true cannot store data unless execute_real_calls=true."""
    response = client.post(
        "/api/v3/external-ingestion/official-probes",
        json={"limit": 1, "sources": ["spotify_web_api"], "execute_real_calls": False, "persist": True},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["persist"] is False
    assert "persist=true was ignored" in " ".join(payload["warnings"])


def test_v3_4_b_collector_classes_are_available() -> None:
    """The official collector implementations requested by the subroadmap exist."""
    assert SpotifyOfficialCollector.source_key == "spotify_web_api"
    assert LastFmOfficialCollector.source_key == "lastfm_api"
    assert MusicBrainzOfficialCollector.source_key == "musicbrainz_api"
    assert YouTubeOfficialCollector.source_key == "youtube_data_api"
    assert SoundCloudOfficialProbe.source_key == "soundcloud_public_api"



def test_spotify_collector_uses_artist_detail_and_top_track_popularity(monkeypatch) -> None:
    """Spotify probes must persist the full official artist metrics when available.

    The first V3.4-B implementation only exposed URL/image/external_id from
    the search result. This regression test keeps the subroadmap contract: the
    collector must enrich the candidate through GET /artists/{id} and include
    followers, artist popularity, genres and official top-track popularity
    evidence. This is still offline because _get_json is monkeypatched.
    """
    collector = SpotifyOfficialCollector()
    calls: list[str] = []

    monkeypatch.setattr(collector, "configured", lambda: True)
    monkeypatch.setattr(collector, "_access_token", lambda: "fake-token")

    def fake_get_json(url, *, headers=None, params=None):  # type: ignore[no-untyped-def]
        calls.append(url)
        if url.endswith("/search"):
            return {
                "artists": {
                    "items": [
                        {
                            "id": "spotify-artist-1",
                            "name": "Adrenalize",
                            "external_urls": {"spotify": "https://open.spotify.com/artist/spotify-artist-1"},
                        }
                    ]
                }
            }, 200
        if url.endswith("/artists/spotify-artist-1"):
            return {
                "id": "spotify-artist-1",
                "name": "Adrenalize",
                "followers": {"total": 123456},
                "popularity": 64,
                "genres": ["hardstyle", "euphoric hardstyle"],
                "images": [{"url": "https://images.example/adrenalize.jpg"}],
                "external_urls": {"spotify": "https://open.spotify.com/artist/spotify-artist-1"},
            }, 200
        if url.endswith("/artists/spotify-artist-1/top-tracks"):
            return {
                "tracks": [
                    {"id": "track-1", "name": "Track One", "popularity": 80},
                    {"id": "track-2", "name": "Track Two", "popularity": 60},
                ]
            }, 200
        raise AssertionError(f"Unexpected Spotify URL: {url}")

    monkeypatch.setattr(collector, "_get_json", fake_get_json)

    result = collector.probe_artist(
        ArtistProbeTarget(canonical_artist_key="adrenalize", display_name="Adrenalize")
    )

    metric_keys = {metric.metric_key for metric in result.metrics}
    assert result.status == "succeeded"
    assert "spotify_followers_total" in metric_keys
    assert "spotify_popularity_score" in metric_keys
    assert "spotify_genres" in metric_keys
    assert "spotify_artist_url" in metric_keys
    assert "spotify_image_url" in metric_keys
    assert "spotify_external_id" in metric_keys
    assert "spotify_top_tracks_count" in metric_keys
    assert "spotify_top_track_popularity_avg" in metric_keys
    assert "spotify_top_track_popularity_max" in metric_keys
    assert any(url.endswith("/artists/spotify-artist-1") for url in calls)
    assert any(url.endswith("/artists/spotify-artist-1/top-tracks") for url in calls)
    limitation = result.normalized_hint_payload["official_api_limitation"].lower()
    assert "play counts" in limitation
    assert "monthly listeners" in limitation
    assert "not exposed" in limitation
    assert result.normalized_hint_payload["unavailable_metric_keys"] == []


def test_spotify_collector_is_honest_when_current_api_omits_public_metrics(monkeypatch) -> None:
    """Spotify probes must not invent metrics removed or omitted by the official API.

    In current real probes, Spotify may return a valid artist profile but omit
    followers, artist popularity, genres or track popularity. The collector must
    keep the usable URL/image/external-id evidence, mark the result as partial,
    and expose unavailable_metric_keys so V3.4-B remains technically honest.
    """
    collector = SpotifyOfficialCollector()

    monkeypatch.setattr(collector, "configured", lambda: True)
    monkeypatch.setattr(collector, "_access_token", lambda: "fake-token")

    def fake_get_json(url, *, headers=None, params=None):  # type: ignore[no-untyped-def]
        if url.endswith("/search"):
            return {
                "artists": {
                    "items": [
                        {
                            "id": "spotify-artist-1",
                            "name": "Adrenalize",
                            "images": [{"url": "https://images.example/adrenalize.jpg"}],
                            "external_urls": {"spotify": "https://open.spotify.com/artist/spotify-artist-1"},
                        }
                    ]
                }
            }, 200
        if url.endswith("/artists/spotify-artist-1"):
            return {
                "id": "spotify-artist-1",
                "name": "Adrenalize",
                "images": [{"url": "https://images.example/adrenalize.jpg"}],
                "external_urls": {"spotify": "https://open.spotify.com/artist/spotify-artist-1"},
            }, 200
        if url.endswith("/artists/spotify-artist-1/top-tracks"):
            return {
                "tracks": [
                    {"id": "track-1", "name": "Track One"},
                    {"id": "track-2", "name": "Track Two"},
                ]
            }, 200
        raise AssertionError(f"Unexpected Spotify URL: {url}")

    monkeypatch.setattr(collector, "_get_json", fake_get_json)

    result = collector.probe_artist(
        ArtistProbeTarget(canonical_artist_key="adrenalize", display_name="Adrenalize")
    )

    metric_keys = {metric.metric_key for metric in result.metrics}
    unavailable = set(result.normalized_hint_payload["unavailable_metric_keys"])

    assert result.status == "partial"
    assert "spotify_artist_url" in metric_keys
    assert "spotify_image_url" in metric_keys
    assert "spotify_external_id" in metric_keys
    assert "spotify_top_tracks_count" in metric_keys
    assert "spotify_top_track_names" in metric_keys
    assert "spotify_followers_total" not in metric_keys
    assert "spotify_popularity_score" not in metric_keys
    assert "spotify_followers_total" in unavailable
    assert "spotify_popularity_score" in unavailable
    assert "spotify_genres" in unavailable
    assert "spotify_top_track_popularity_avg" in unavailable
    assert result.safe_error_message is not None
    assert "no values were invented" in result.safe_error_message


def test_musicbrainz_collector_uses_user_agent_and_retries_transient_errors(monkeypatch) -> None:
    """MusicBrainz real probes must use User-Agent and retry transient failures.

    This remains an offline test: _get_json is monkeypatched and no network call
    is made. It protects the V3.4-B contract that MusicBrainz needs stricter
    User-Agent/rate-limit/retry handling than the other APIs.
    """
    collector = MusicBrainzOfficialCollector()
    calls: list[dict] = []

    monkeypatch.setattr(collector, "configured", lambda: True)
    monkeypatch.setattr(collector, "_respect_musicbrainz_rate_limit", lambda: None)

    def fake_get_json(url, *, headers=None, params=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "headers": headers or {}, "params": params or {}})
        if len(calls) == 1:
            raise httpx.ConnectError("temporary MusicBrainz connection issue")
        return {
            "artists": [
                {
                    "id": "183b3df1-9ded-4277-ab11-a6fcb9a7cf44",
                    "name": "Adrenalize",
                    "score": "100",
                    "country": "NL",
                    "type": "Person",
                }
            ]
        }, 200

    monkeypatch.setattr(collector, "_get_json", fake_get_json)

    result = collector.probe_artist(
        ArtistProbeTarget(canonical_artist_key="adrenalize", display_name="Adrenalize")
    )

    assert result.status == "partial"
    assert result.external_id == "183b3df1-9ded-4277-ab11-a6fcb9a7cf44"
    assert len(calls) == 2
    assert calls[0]["url"] == "https://musicbrainz.org/ws/2/artist"
    assert calls[0]["headers"].get("User-Agent")
    assert calls[0]["headers"].get("Accept") == "application/json"
    assert calls[0]["params"]["fmt"] == "json"