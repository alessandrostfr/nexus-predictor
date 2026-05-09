"""Official API probe collectors for V3.4-B.

These collectors are intentionally small and conservative. They make real calls
only when explicitly executed by scripts/endpoints, never from pytest. Each
collector returns raw evidence and normalized metric candidates without leaking
credentials or pretending that a probe is a trained ML model.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.collectors.contracts import CollectorContract, CollectorStatus
from app.collectors.registry import COLLECTOR_REGISTRY
from app.collectors.security import redact_payload
from app.core.config import settings


SPOTIFY_FULL_METRICS_SCHEMA_REVISION = "v3.4-b-spotify-full-metrics-v2"


@dataclass(frozen=True)
class ArtistProbeTarget:
    """Minimal canonical artist fields required by external probes."""

    canonical_artist_key: str
    display_name: str
    normalized_name: str | None = None
    source_artist_slug: str | None = None


@dataclass(frozen=True)
class ProbeMetricCandidate:
    """Normalized metric candidate emitted by an official API probe."""

    metric_key: str
    value_type: str = "numeric"
    metric_value_numeric: float | None = None
    metric_value_text: str | None = None
    metric_unit: str | None = None
    confidence: str = "medium"
    feature_candidate: bool = True
    is_diagnostic_only: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class OfficialProbeResult:
    """Collector result ready to be persisted or returned as a dry response."""

    source_key: str
    collector_key: str
    canonical_artist_key: str
    status: str
    confidence: str = "medium"
    source_url: str | None = None
    external_id: str | None = None
    profile_name: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    normalized_hint_payload: dict[str, Any] = field(default_factory=dict)
    metrics: list[ProbeMetricCandidate] = field(default_factory=list)
    profile_candidate_count: int = 0
    safe_error_message: str | None = None
    http_status: int | None = None
    quota_cost_estimated: float | None = None


class OfficialAPICollector:
    """Base class for a source-specific official API collector."""

    source_key: str = ""

    def __init__(self, timeout_seconds: float | None = None) -> None:
        self.timeout_seconds = timeout_seconds or settings.EXTERNAL_TIMEOUT_SECONDS
        self.contract = _contract_by_source(self.source_key)

    def configured(self) -> bool:
        """Return whether this collector can make a real external call now."""
        return all(_safe_setting(name) for name in self.contract.credential_env_vars)

    def not_configured_result(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Return a safe result when required credentials are missing."""
        return OfficialProbeResult(
            source_key=self.contract.source_key,
            collector_key=self.contract.collector_key,
            canonical_artist_key=artist.canonical_artist_key,
            status=CollectorStatus.NOT_CONFIGURED.value,
            confidence=self.contract.confidence,
            safe_error_message="Required credentials are missing; configure env vars before real probes.",
        )

    def probe_artist(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Probe one artist. Subclasses implement source-specific logic."""
        raise NotImplementedError

    def _get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Run a controlled GET request and return JSON payload plus status."""
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=headers, params=params)
            status_code = response.status_code
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Official API response was not a JSON object.")
        return payload, status_code


class SpotifyOfficialCollector(OfficialAPICollector):
    """Official Spotify artist profile probe using Client Credentials."""

    source_key = "spotify_web_api"

    def _access_token(self) -> str:
        """Request a client-credentials token without exposing secrets."""
        client_id = settings.SPOTIFY_CLIENT_ID or ""
        client_secret = settings.SPOTIFY_CLIENT_SECRET or ""
        token = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        headers = {"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(settings.SPOTIFY_TOKEN_URL, headers=headers, data={"grant_type": "client_credentials"})
            response.raise_for_status()
            payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise ValueError("Spotify token response did not include access_token.")
        return str(access_token)

    def probe_artist(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Search Spotify for an artist and return profile metrics."""
        if not self.configured():
            return self.not_configured_result(artist)
        try:
            token = self._access_token()
            payload, status_code = self._get_json(
                f"{settings.SPOTIFY_API_BASE_URL}/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": artist.display_name, "type": "artist", "limit": 1, "market": settings.SPOTIFY_DEFAULT_MARKET},
            )
            items = payload.get("artists", {}).get("items", []) if isinstance(payload.get("artists"), dict) else []
            if not items:
                return OfficialProbeResult(
                    source_key=self.source_key,
                    collector_key=self.contract.collector_key,
                    canonical_artist_key=artist.canonical_artist_key,
                    status=CollectorStatus.NOT_FOUND.value,
                    confidence="medium",
                    raw_payload={"query": artist.display_name, "result_count": 0},
                    http_status=status_code,
                    quota_cost_estimated=1,
                )
            # The search endpoint may return a simplified artist object in some
            # Spotify responses. V3.4-B needs the complete official artist
            # contract, so we immediately enrich the selected candidate through
            # GET /artists/{id}. This is still an official API call and remains
            # quota-light compared with YouTube search.
            profile = items[0]
            spotify_id = profile.get("id")
            artist_detail_payload: dict[str, Any] = {}
            top_tracks_payload: dict[str, Any] = {}
            top_tracks_error: str | None = None

            if spotify_id:
                artist_detail_payload, _ = self._get_json(
                    f"{settings.SPOTIFY_API_BASE_URL}/artists/{spotify_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if artist_detail_payload.get("id"):
                    profile = {**profile, **artist_detail_payload}

                try:
                    top_tracks_payload, _ = self._get_json(
                        f"{settings.SPOTIFY_API_BASE_URL}/artists/{spotify_id}/top-tracks",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"market": settings.SPOTIFY_DEFAULT_MARKET},
                    )
                except Exception as exc:  # noqa: BLE001 - top tracks are useful but should not break artist profile ingestion.
                    top_tracks_error = f"{exc.__class__.__name__}: top-track probe failed safely."

            followers = (profile.get("followers") or {}).get("total")
            popularity = profile.get("popularity")
            genres = profile.get("genres") or []
            spotify_url = (profile.get("external_urls") or {}).get("spotify")
            images = profile.get("images") or []
            image_url = images[0].get("url") if images and isinstance(images[0], dict) else None
            tracks = top_tracks_payload.get("tracks") if isinstance(top_tracks_payload.get("tracks"), list) else []
            track_names = [str(track.get("name")) for track in tracks if isinstance(track, dict) and track.get("name")]
            track_ids = [str(track.get("id")) for track in tracks if isinstance(track, dict) and track.get("id")]
            track_popularities = [float(track.get("popularity")) for track in tracks if isinstance(track, dict) and track.get("popularity") is not None]
            avg_track_popularity = sum(track_popularities) / len(track_popularities) if track_popularities else None
            max_track_popularity = max(track_popularities) if track_popularities else None

            # Spotify has progressively reduced some public Web API fields.
            # V3.4-B must persist the metrics when the official API returns them,
            # but it must not invent followers, popularity, genres or exact plays
            # when Spotify no longer exposes those fields for a given app/artist.
            unavailable_metric_keys: list[str] = []
            if followers is None:
                unavailable_metric_keys.append("spotify_followers_total")
            if popularity is None:
                unavailable_metric_keys.append("spotify_popularity_score")
            if not genres:
                unavailable_metric_keys.append("spotify_genres")
            if tracks and not track_popularities:
                unavailable_metric_keys.extend(
                    [
                        "spotify_top_track_popularity_avg",
                        "spotify_top_track_popularity_max",
                        "spotify_top_track_popularity_scores",
                    ]
                )

            spotify_core_metrics_available = followers is not None and popularity is not None
            status = CollectorStatus.SUCCEEDED.value if spotify_core_metrics_available else CollectorStatus.PARTIAL.value
            safe_error_message = None
            if not spotify_core_metrics_available:
                safe_error_message = (
                    "Spotify official API response did not expose followers and/or popularity. "
                    "The probe persisted only fields returned by Spotify; no values were invented."
                )

            raw_payload = {
                "schema_revision": SPOTIFY_FULL_METRICS_SCHEMA_REVISION,
                "query": artist.display_name,
                "selected_profile": profile,
                "artist_detail": artist_detail_payload,
                "top_tracks": top_tracks_payload,
                "top_tracks_error": top_tracks_error,
                "field_presence": {
                    "followers": followers is not None,
                    "popularity": popularity is not None,
                    "genres": bool(genres),
                    "top_tracks": bool(tracks),
                    "top_track_popularity": bool(track_popularities),
                },
                "unavailable_metric_keys": unavailable_metric_keys,
                "official_api_limitation": (
                    "Spotify Web API does not expose exact track play counts or monthly listeners. "
                    "Some public artist and track popularity fields may also be absent or deprecated depending on current API policy."
                ),
                "secret_safety": "spotify token intentionally not stored",
            }
            metrics = [
                ProbeMetricCandidate("spotify_followers_total", metric_value_numeric=float(followers), metric_unit="followers", confidence="high") if followers is not None else None,
                ProbeMetricCandidate("spotify_popularity_score", metric_value_numeric=float(popularity), metric_unit="spotify_0_100", confidence="high") if popularity is not None else None,
                ProbeMetricCandidate("spotify_genres", value_type="text", metric_value_text=", ".join(genres), confidence="high", feature_candidate=False, notes="Genre text is evidence; encoding belongs to feature engineering.") if genres else None,
                ProbeMetricCandidate("spotify_artist_url", value_type="url", metric_value_text=spotify_url, confidence="high", feature_candidate=False) if spotify_url else None,
                ProbeMetricCandidate("spotify_image_url", value_type="url", metric_value_text=image_url, confidence="high", feature_candidate=False) if image_url else None,
                ProbeMetricCandidate("spotify_external_id", value_type="text", metric_value_text=str(profile.get("id")), confidence="high", feature_candidate=False) if profile.get("id") else None,
                ProbeMetricCandidate("spotify_top_tracks_count", metric_value_numeric=float(len(tracks)), metric_unit="tracks", confidence="high", feature_candidate=False, notes="Official API top-track evidence; not a play-count metric.") if tracks else None,
                ProbeMetricCandidate("spotify_top_track_popularity_avg", metric_value_numeric=avg_track_popularity, metric_unit="spotify_0_100", confidence="high", notes="Official Spotify track popularity average. This is not exact plays.") if avg_track_popularity is not None else None,
                ProbeMetricCandidate("spotify_top_track_popularity_max", metric_value_numeric=max_track_popularity, metric_unit="spotify_0_100", confidence="high", notes="Official Spotify maximum top-track popularity. This is not exact plays.") if max_track_popularity is not None else None,
                ProbeMetricCandidate("spotify_top_track_names", value_type="text", metric_value_text=", ".join(track_names[:10]), confidence="high", feature_candidate=False) if track_names else None,
                ProbeMetricCandidate("spotify_top_track_ids", value_type="text", metric_value_text=", ".join(track_ids[:10]), confidence="high", feature_candidate=False) if track_ids else None,
                ProbeMetricCandidate("spotify_top_track_popularity_scores", value_type="text", metric_value_text=", ".join(str(int(score)) for score in track_popularities[:10]), confidence="high", feature_candidate=False) if track_popularities else None,
            ]
            returned_metric_keys = [metric.metric_key for metric in metrics if metric is not None]
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=status,
                confidence="high" if status == CollectorStatus.SUCCEEDED.value else "medium",
                source_url=spotify_url,
                external_id=profile.get("id"),
                profile_name=profile.get("name"),
                raw_payload=redact_payload(raw_payload),
                normalized_hint_payload={
                    "schema_revision": SPOTIFY_FULL_METRICS_SCHEMA_REVISION,
                    "metric_keys": returned_metric_keys,
                    "unavailable_metric_keys": unavailable_metric_keys,
                    "field_presence": raw_payload["field_presence"],
                    "official_api_limitation": (
                        "Exact Spotify track play counts and monthly listeners are not exposed by the official Web API. "
                        "If followers, artist popularity, genres or track popularity are absent, Nexus stores the absence as a limitation instead of inventing values."
                    ),
                    "top_tracks_error": top_tracks_error,
                },
                metrics=[metric for metric in metrics if metric is not None],
                profile_candidate_count=1,
                safe_error_message=safe_error_message,
                http_status=status_code,
                quota_cost_estimated=3 if spotify_id else 1,
            )
        except httpx.HTTPStatusError as exc:
            return _http_error_result(self, artist, exc)
        except Exception as exc:  # noqa: BLE001 - convert any API/probe issue into safe status.
            return _safe_error_result(self, artist, exc)


class LastFmOfficialCollector(OfficialAPICollector):
    """Official Last.fm artist profile probe."""

    source_key = "lastfm_api"

    def probe_artist(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Read Last.fm artist info and normalize listeners/playcount/tags."""
        if not self.configured():
            return self.not_configured_result(artist)
        try:
            payload, status_code = self._get_json(
                settings.LASTFM_API_BASE_URL,
                headers={"User-Agent": settings.LASTFM_USER_AGENT},
                params={"method": "artist.getinfo", "artist": artist.display_name, "api_key": settings.LASTFM_API_KEY, "format": "json"},
            )
            info = payload.get("artist") if isinstance(payload.get("artist"), dict) else None
            if not info:
                return OfficialProbeResult(
                    source_key=self.source_key,
                    collector_key=self.contract.collector_key,
                    canonical_artist_key=artist.canonical_artist_key,
                    status=CollectorStatus.NOT_FOUND.value,
                    confidence="medium",
                    raw_payload=redact_payload(payload),
                    http_status=status_code,
                    quota_cost_estimated=1,
                )
            stats = info.get("stats") or {}
            listeners = _to_float(stats.get("listeners"))
            playcount = _to_float(stats.get("playcount"))
            tags = info.get("tags", {}).get("tag", []) if isinstance(info.get("tags"), dict) else []
            tag_names = [str(tag.get("name")) for tag in tags if isinstance(tag, dict) and tag.get("name")]
            bio_available = bool((info.get("bio") or {}).get("summary")) if isinstance(info.get("bio"), dict) else False
            url = info.get("url")
            metrics = [
                ProbeMetricCandidate("lastfm_listeners_total", metric_value_numeric=listeners, metric_unit="listeners", confidence="medium") if listeners is not None else None,
                ProbeMetricCandidate("lastfm_playcount_total", metric_value_numeric=playcount, metric_unit="plays", confidence="medium") if playcount is not None else None,
                ProbeMetricCandidate("lastfm_tags", value_type="text", metric_value_text=", ".join(tag_names), confidence="medium", feature_candidate=False) if tag_names else None,
                ProbeMetricCandidate("lastfm_bio_available", value_type="boolean", metric_value_numeric=1.0 if bio_available else 0.0, metric_unit="boolean", confidence="medium", feature_candidate=False, is_diagnostic_only=True) if bio_available else None,
                ProbeMetricCandidate("lastfm_url", value_type="url", metric_value_text=str(url), confidence="medium", feature_candidate=False) if url else None,
            ]
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=CollectorStatus.SUCCEEDED.value,
                confidence="medium",
                source_url=url,
                profile_name=info.get("name"),
                raw_payload=redact_payload({"query": artist.display_name, "artist": info}),
                normalized_hint_payload={"metric_keys": [metric.metric_key for metric in metrics if metric is not None]},
                metrics=[metric for metric in metrics if metric is not None],
                profile_candidate_count=1,
                http_status=status_code,
                quota_cost_estimated=1,
            )
        except httpx.HTTPStatusError as exc:
            return _http_error_result(self, artist, exc)
        except Exception as exc:  # noqa: BLE001
            return _safe_error_result(self, artist, exc)


class MusicBrainzOfficialCollector(OfficialAPICollector):
    """Official MusicBrainz probe for identity metadata candidates.

    MusicBrainz is a public official API, but it is stricter than the other
    sources in this block: it requires a meaningful User-Agent and asks clients
    not to exceed roughly one request per second. The collector therefore has a
    small process-local rate limiter plus retry/backoff for transient network
    errors. Tests still remain offline; these protections only run when a real
    V3.4-B probe is explicitly requested.
    """

    source_key = "musicbrainz_api"
    _last_request_monotonic: float = 0.0
    _min_delay_seconds: float = 1.15
    _max_attempts: int = 3
    _backoff_seconds: tuple[float, ...] = (1.0, 2.0)

    def configured(self) -> bool:
        """MusicBrainz does not need a key, but a User-Agent is mandatory."""
        return bool(str(settings.MUSICBRAINZ_USER_AGENT or "").strip())

    def probe_artist(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Search MusicBrainz and persist the best candidate as review evidence."""
        if not self.configured():
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=CollectorStatus.NOT_CONFIGURED.value,
                confidence="medium",
                safe_error_message="MUSICBRAINZ_USER_AGENT is required for responsible public API usage.",
            )
        try:
            payload, status_code = self._get_musicbrainz_json_with_retry(artist)
            artists = payload.get("artists") if isinstance(payload.get("artists"), list) else []
            if not artists:
                return OfficialProbeResult(
                    source_key=self.source_key,
                    collector_key=self.contract.collector_key,
                    canonical_artist_key=artist.canonical_artist_key,
                    status=CollectorStatus.NOT_FOUND.value,
                    confidence="medium",
                    raw_payload=redact_payload(payload),
                    http_status=status_code,
                    quota_cost_estimated=1,
                )
            candidate = artists[0]
            score = _to_float(candidate.get("score"))
            mbid = candidate.get("id")
            url = f"https://musicbrainz.org/artist/{mbid}" if mbid else None
            area = candidate.get("area") if isinstance(candidate.get("area"), dict) else {}
            country = candidate.get("country") or area.get("name")
            metrics = [
                ProbeMetricCandidate("musicbrainz_mbid", value_type="text", metric_value_text=str(mbid), confidence="medium", feature_candidate=False) if mbid else None,
                ProbeMetricCandidate("musicbrainz_country", value_type="text", metric_value_text=str(country), confidence="medium", feature_candidate=False) if country else None,
                ProbeMetricCandidate("musicbrainz_type", value_type="text", metric_value_text=str(candidate.get("type")), confidence="medium", feature_candidate=False) if candidate.get("type") else None,
                ProbeMetricCandidate("musicbrainz_disambiguation", value_type="text", metric_value_text=str(candidate.get("disambiguation")), confidence="medium", feature_candidate=False) if candidate.get("disambiguation") else None,
                ProbeMetricCandidate("musicbrainz_match_confidence", metric_value_numeric=score, metric_unit="musicbrainz_score", confidence="medium", feature_candidate=False, is_diagnostic_only=True) if score is not None else None,
            ]
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=CollectorStatus.PARTIAL.value,
                confidence="medium",
                source_url=url,
                external_id=mbid,
                profile_name=candidate.get("name"),
                raw_payload=redact_payload({"query": artist.display_name, "candidates": artists}),
                normalized_hint_payload={
                    "profile_candidate": True,
                    "feature_candidate_default": False,
                    "rate_limit_policy": "one_request_per_second_with_retry_backoff",
                },
                metrics=[metric for metric in metrics if metric is not None],
                profile_candidate_count=len(artists),
                http_status=status_code,
                quota_cost_estimated=1,
            )
        except httpx.HTTPStatusError as exc:
            return _http_error_result(self, artist, exc)
        except httpx.TimeoutException as exc:
            return _safe_error_result(self, artist, exc, fallback_status=CollectorStatus.TIMEOUT.value)
        except httpx.RequestError as exc:
            return _safe_error_result(self, artist, exc)
        except Exception as exc:  # noqa: BLE001
            return _safe_error_result(self, artist, exc)

    def _get_musicbrainz_json_with_retry(self, artist: ArtistProbeTarget) -> tuple[dict[str, Any], int]:
        """Call MusicBrainz with User-Agent, rate limit and retry/backoff."""
        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                self._respect_musicbrainz_rate_limit()
                return self._get_json(
                    "https://musicbrainz.org/ws/2/artist",
                    headers={
                        "User-Agent": str(settings.MUSICBRAINZ_USER_AGENT),
                        "Accept": "application/json",
                    },
                    params={"query": f'artist:"{artist.display_name}"', "fmt": "json", "limit": 5},
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                # 429 and 5xx are transient enough to retry carefully. Other
                # HTTP errors should be reported immediately as safe statuses.
                if status_code not in {429, 500, 502, 503, 504}:
                    raise
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout) as exc:
                last_error = exc

            if attempt < self._max_attempts - 1:
                time.sleep(self._backoff_seconds[min(attempt, len(self._backoff_seconds) - 1)])

        if last_error is not None:
            raise last_error
        raise RuntimeError("MusicBrainz retry loop ended without a response or error.")

    def _respect_musicbrainz_rate_limit(self) -> None:
        """Apply a conservative process-local delay before MusicBrainz calls."""
        now = time.monotonic()
        elapsed = now - MusicBrainzOfficialCollector._last_request_monotonic
        if elapsed < self._min_delay_seconds:
            time.sleep(self._min_delay_seconds - elapsed)
        MusicBrainzOfficialCollector._last_request_monotonic = time.monotonic()


class YouTubeOfficialCollector(OfficialAPICollector):
    """Quota-aware YouTube Data API probe.

    Channel matching is ambiguous, so metrics are not feature candidates yet.
    """

    source_key = "youtube_data_api"

    def probe_artist(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Search YouTube channels and optionally read public statistics."""
        if not self.configured():
            return self.not_configured_result(artist)
        try:
            search_payload, status_code = self._get_json(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": f"{artist.display_name} official",
                    "type": "channel",
                    "maxResults": 1,
                    "key": settings.YOUTUBE_API_KEY,
                },
            )
            items = search_payload.get("items") if isinstance(search_payload.get("items"), list) else []
            if not items:
                return OfficialProbeResult(
                    source_key=self.source_key,
                    collector_key=self.contract.collector_key,
                    canonical_artist_key=artist.canonical_artist_key,
                    status=CollectorStatus.NOT_FOUND.value,
                    raw_payload=redact_payload({"query": artist.display_name, "result_count": 0}),
                    http_status=status_code,
                    quota_cost_estimated=100,
                )
            channel_id = ((items[0].get("id") or {}).get("channelId")) if isinstance(items[0].get("id"), dict) else None
            channel_title = (items[0].get("snippet") or {}).get("channelTitle") if isinstance(items[0].get("snippet"), dict) else None
            stats_payload: dict[str, Any] = {}
            if channel_id:
                stats_payload, _ = self._get_json(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "snippet,statistics", "id": channel_id, "key": settings.YOUTUBE_API_KEY},
                )
            channel = (stats_payload.get("items") or [{}])[0] if isinstance(stats_payload.get("items"), list) else {}
            statistics = channel.get("statistics") if isinstance(channel.get("statistics"), dict) else {}
            snippet = channel.get("snippet") if isinstance(channel.get("snippet"), dict) else {}
            subscribers = _to_float(statistics.get("subscriberCount"))
            views = _to_float(statistics.get("viewCount"))
            video_count = _to_float(statistics.get("videoCount"))
            custom_url = snippet.get("customUrl")
            channel_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else None
            metrics = [
                ProbeMetricCandidate("youtube_channel_subscribers_total", metric_value_numeric=subscribers, metric_unit="subscribers", confidence="low", feature_candidate=False) if subscribers is not None else None,
                ProbeMetricCandidate("youtube_channel_views_total", metric_value_numeric=views, metric_unit="views", confidence="low", feature_candidate=False) if views is not None else None,
                ProbeMetricCandidate("youtube_channel_video_count", metric_value_numeric=video_count, metric_unit="videos", confidence="low", feature_candidate=False) if video_count is not None else None,
                ProbeMetricCandidate("youtube_channel_url", value_type="url", metric_value_text=channel_url, confidence="low", feature_candidate=False) if channel_url else None,
            ]
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=CollectorStatus.PARTIAL.value,
                confidence="low",
                source_url=channel_url,
                external_id=channel_id,
                profile_name=channel_title or snippet.get("title") or custom_url,
                raw_payload=redact_payload({"query": artist.display_name, "search": search_payload, "channel": stats_payload}),
                normalized_hint_payload={"requires_manual_review": True, "feature_candidate_default": False},
                metrics=[metric for metric in metrics if metric is not None],
                profile_candidate_count=1,
                http_status=status_code,
                quota_cost_estimated=101,
            )
        except httpx.HTTPStatusError as exc:
            return _http_error_result(self, artist, exc, quota_cost_estimated=100)
        except Exception as exc:  # noqa: BLE001
            return _safe_error_result(self, artist, exc)


class SoundCloudOfficialProbe(OfficialAPICollector):
    """Conservative SoundCloud official access probe.

    This collector is intentionally honest: it documents whether official access
    appears usable and does not block V3.4 when credentials/access are missing.
    """

    source_key = "soundcloud_public_api"

    def probe_artist(self, artist: ArtistProbeTarget) -> OfficialProbeResult:
        """Attempt a minimal official/public API probe when credentials exist."""
        if not self.configured():
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=CollectorStatus.ACCESS_UNCONFIRMED.value,
                confidence="medium",
                safe_error_message="SoundCloud official credentials/access are not configured. Fallback remains V3.4-C yt-dlp metadata-only plus manual review.",
            )
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(
                    "https://api.soundcloud.com/users",
                    params={"q": artist.display_name, "limit": 1, "client_id": settings.SOUNDCLOUD_CLIENT_ID},
                )
                status_code = response.status_code
                response.raise_for_status()
                payload = response.json()
            users = payload.get("collection") if isinstance(payload, dict) and isinstance(payload.get("collection"), list) else payload if isinstance(payload, list) else []
            selected = users[0] if users and isinstance(users[0], dict) else {}
            if not selected:
                return OfficialProbeResult(
                    source_key=self.source_key,
                    collector_key=self.contract.collector_key,
                    canonical_artist_key=artist.canonical_artist_key,
                    status=CollectorStatus.NOT_FOUND.value,
                    raw_payload=redact_payload({"query": artist.display_name, "response_shape": list(payload.keys())}),
                    http_status=status_code,
                    quota_cost_estimated=1,
                )
            profile_url = selected.get("permalink_url")
            followers = _to_float(selected.get("followers_count"))
            track_count = _to_float(selected.get("track_count"))
            metrics = [
                ProbeMetricCandidate("soundcloud_followers_total", metric_value_numeric=followers, metric_unit="followers", confidence="low", feature_candidate=False) if followers is not None else None,
                ProbeMetricCandidate("soundcloud_tracks_count", metric_value_numeric=track_count, metric_unit="tracks", confidence="low", feature_candidate=False) if track_count is not None else None,
                ProbeMetricCandidate("soundcloud_profile_url", value_type="url", metric_value_text=profile_url, confidence="low", feature_candidate=False) if profile_url else None,
            ]
            return OfficialProbeResult(
                source_key=self.source_key,
                collector_key=self.contract.collector_key,
                canonical_artist_key=artist.canonical_artist_key,
                status=CollectorStatus.PARTIAL.value,
                confidence="low",
                source_url=profile_url,
                external_id=str(selected.get("id")) if selected.get("id") else None,
                profile_name=selected.get("username"),
                raw_payload=redact_payload({"query": artist.display_name, "selected_user": selected}),
                normalized_hint_payload={"requires_manual_review": True, "fallback": "yt_dlp_metadata_only_in_v3_4_c"},
                metrics=[metric for metric in metrics if metric is not None],
                profile_candidate_count=1,
                http_status=status_code,
                quota_cost_estimated=1,
            )
        except httpx.HTTPStatusError as exc:
            return _http_error_result(self, artist, exc, fallback_status=CollectorStatus.ACCESS_UNAVAILABLE.value)
        except Exception as exc:  # noqa: BLE001
            return _safe_error_result(self, artist, exc, fallback_status=CollectorStatus.ACCESS_UNAVAILABLE.value)


def official_collector_for_source(source_key: str) -> OfficialAPICollector:
    """Return the official collector implementation for a source key."""
    mapping: dict[str, type[OfficialAPICollector]] = {
        "spotify_web_api": SpotifyOfficialCollector,
        "lastfm_api": LastFmOfficialCollector,
        "musicbrainz_api": MusicBrainzOfficialCollector,
        "youtube_data_api": YouTubeOfficialCollector,
        "soundcloud_public_api": SoundCloudOfficialProbe,
    }
    if source_key not in mapping:
        raise KeyError(f"No official API collector exists for source {source_key}.")
    return mapping[source_key]()


def official_source_keys() -> list[str]:
    """Return source keys handled by V3.4-B official API probes."""
    return ["spotify_web_api", "lastfm_api", "musicbrainz_api", "youtube_data_api", "soundcloud_public_api"]


def _contract_by_source(source_key: str) -> CollectorContract:
    """Find a collector contract by source key."""
    for contract in COLLECTOR_REGISTRY:
        if contract.source_key == source_key:
            return contract
    raise KeyError(f"Unknown collector source: {source_key}")


def _safe_setting(name: str) -> str | None:
    """Read one Settings value without creating dynamic secret output."""
    value = getattr(settings, name, None)
    return str(value) if value not in (None, "") else None


def _to_float(value: Any) -> float | None:
    """Best-effort conversion for numeric strings returned by APIs."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _http_error_result(
    collector: OfficialAPICollector,
    artist: ArtistProbeTarget,
    exc: httpx.HTTPStatusError,
    *,
    fallback_status: str = CollectorStatus.FAILED.value,
    quota_cost_estimated: float | None = None,
) -> OfficialProbeResult:
    """Convert HTTP errors into safe probe results."""
    status_code = exc.response.status_code if exc.response is not None else None
    status = fallback_status
    if status_code == 401 or status_code == 403:
        status = CollectorStatus.INVALID_CREDENTIALS.value if fallback_status == CollectorStatus.FAILED.value else fallback_status
    elif status_code == 404:
        status = CollectorStatus.NOT_FOUND.value
    elif status_code == 429:
        status = CollectorStatus.RATE_LIMITED.value
    return OfficialProbeResult(
        source_key=collector.source_key,
        collector_key=collector.contract.collector_key,
        canonical_artist_key=artist.canonical_artist_key,
        status=status,
        confidence=collector.contract.confidence,
        safe_error_message=f"Official API returned HTTP {status_code}; response body was not stored.",
        http_status=status_code,
        quota_cost_estimated=quota_cost_estimated,
    )


def _safe_error_result(
    collector: OfficialAPICollector,
    artist: ArtistProbeTarget,
    exc: Exception,
    *,
    fallback_status: str = CollectorStatus.FAILED.value,
) -> OfficialProbeResult:
    """Convert arbitrary exceptions into safe, non-secret results."""
    return OfficialProbeResult(
        source_key=collector.source_key,
        collector_key=collector.contract.collector_key,
        canonical_artist_key=artist.canonical_artist_key,
        status=fallback_status,
        confidence=collector.contract.confidence,
        safe_error_message=f"{exc.__class__.__name__}: probe failed safely without storing secrets.",
    )