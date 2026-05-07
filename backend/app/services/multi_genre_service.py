"""V2.5 multi-genre classifier and persistence service.

This block upgrades the transparent V1-style classifier into a V2 evidence-backed
multi-genre layer. The goal is not to pretend every artist is perfectly known;
instead, every classification stores sources, confidence and review flags so
later model blocks can use the data without becoming opaque.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.paths import ARTIST_PROFILE_CACHE_PATH, GENRE_OVERRIDES_PATH, MANUAL_OVERRIDES_PATH
from app.db.models import (
    ArtistGenreModel,
    ArtistMetricModel,
    ArtistModel,
    EvidenceItemModel,
    PlatformProfileModel,
    SourceModel,
    SpotifyArtistCacheModel,
)
from app.schemas.genre import (
    ClassifiedArtistGenre,
    ClassifiedArtistGenreList,
    EditionGenreDistribution,
    GenreComparisonRecord,
    GenreComparisonResponse,
    GenreDefinition,
    GenreSeed,
    GenreSourceRecord,
    GenreTaxonomyResponse,
    MultiGenreCoverage,
    MultiGenreRebuildResult,
)
from app.services.database_seed_service import dumps_json, ensure_database_ready, loads_json
from app.services.evidence_seed_service import create_evidence, get_or_create_source, normalize_confidence, upsert_artist_metric

SPECIAL_KINDS = {"special_show", "label_show", "duo_project", "live_or_collective"}
GENRE_METRIC_PREFIX = "genre.v2."
GENRE_ARTIST_METRIC_PREFIX = "genre_v2_"
# A tiny set of ambiguous/local entries intentionally remains Unknown so the
# UI still exposes real uncertainty instead of turning every weak fallback into
# a genre claim.
FORCE_UNKNOWN_REVIEW_SLUGS = {"yeyo"}

# Parent hierarchy used for secondary chips and fallback signals. It deliberately
# stays compact: V2.6+ can refine this once room/stage/timetable evidence exists.
GENRE_PARENTS: dict[str, str | None] = {
    "Hard Dance": None,
    "Hardstyle": "Hard Dance",
    "Euphoric Hardstyle": "Hardstyle",
    "Rawstyle": "Hardstyle",
    "Xtra Raw": "Rawstyle",
    "Classic / Legacy Hardstyle": "Hardstyle",
    "Mainstage Hard Dance": "Hard Dance",
    "Freestyle / Hard Dance": "Hard Dance",
    "Hard Techno / Hard Dance": "Hard Dance",
    "Hardcore": "Hard Dance",
    "Uptempo Hardcore": "Hardcore",
    "Frenchcore": "Hardcore",
    "Industrial Hardcore": "Hardcore",
    "Terror / Speedcore": "Hardcore",
    "Happy Hardcore": "Hardcore",
    "MC / Host": "Other",
    "Unknown": None,
}

# Extra V2 hint layer used only when the previous V1 seed/keyword classifier did
# not have enough information. These are intentionally confidence-limited hints,
# not verified facts. They mostly convert known Nexus hard-dance acts away from
# Unknown while still requiring review for ambiguous cases.
V2_CURATED_HINTS: dict[str, tuple[str, str, str]] = {
    # Hardstyle / rawstyle ecosystem.
    "act-of-rage": ("Rawstyle", "medium", "Curated V2 hardstyle/rawstyle hint."),
    "adaro": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "alpha-twins": ("Classic / Legacy Hardstyle", "medium", "Curated V2 legacy hardstyle hint."),
    "code-black": ("Euphoric Hardstyle", "medium", "Curated V2 euphoric hardstyle hint."),
    "d-block": ("Euphoric Hardstyle", "medium", "D-Block entry is part of D-Block & S-Te-Fan in the dataset."),
    "d-charged": ("Euphoric Hardstyle", "medium", "Curated V2 euphoric hardstyle hint."),
    "d-fence": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "d-strub": ("Rawstyle", "low", "Low-confidence V2 rawstyle hint; needs review."),
    "deepack": ("Classic / Legacy Hardstyle", "medium", "Curated V2 legacy hardstyle hint."),
    "deetox": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "digital-punk": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "donkey-rollers": ("Classic / Legacy Hardstyle", "medium", "Curated V2 legacy hardstyle hint."),
    "hard-driver": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "keltek": ("Euphoric Hardstyle", "medium", "Curated V2 euphoric hardstyle hint."),
    "killshot": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "kronos": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "major-conspiracy": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hint."),
    "malice": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "max-enforcer": ("Euphoric Hardstyle", "medium", "Curated V2 euphoric hardstyle hint."),
    "mish": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "ncrypta": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "primeshock": ("Euphoric Hardstyle", "medium", "Curated V2 euphoric hardstyle hint."),
    "ran-d": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "reborn": ("Hardstyle", "low", "General hardstyle V2 hint; needs review."),
    "rebelion": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "rebelion-beyond-the-horizon": ("Rawstyle", "medium", "Show-level Rebelion hint."),
    "s-te-fan": ("Euphoric Hardstyle", "medium", "S-Te-Fan entry is part of D-Block & S-Te-Fan in the dataset."),
    "sound-rush": ("Euphoric Hardstyle", "medium", "Curated V2 euphoric hardstyle hint."),
    "sub-zero-project-live": ("Rawstyle", "medium", "Live show by Sub Zero Project."),
    "sub-zero-project-pres-robot-ravolution": ("Rawstyle", "medium", "Show-level Sub Zero Project hint."),
    "tatanka": ("Classic / Legacy Hardstyle", "medium", "Curated V2 legacy hardstyle hint."),
    "technoboy": ("Classic / Legacy Hardstyle", "medium", "Technoboy/TNT legacy hardstyle hint."),
    "the-gang": ("Rawstyle", "medium", "The Gang is treated as a Rooler/Sickmode show-level rawstyle project."),
    "the-gang-live": ("Rawstyle", "medium", "The Gang live show-level rawstyle project."),
    "the-straikerz": ("Xtra Raw", "medium", "Curated V2 xtra raw hint."),
    "tnt": ("Classic / Legacy Hardstyle", "medium", "TNT legacy hardstyle hint."),
    "tuneboy": ("Classic / Legacy Hardstyle", "medium", "Tuneboy/TNT legacy hardstyle hint."),
    "unresolved": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "vasto": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "vertile": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "warface": ("Rawstyle", "medium", "Curated V2 rawstyle hint."),
    "wild-motherfuckers": ("Classic / Legacy Hardstyle", "medium", "Legacy hardstyle project hint."),
    "zatox": ("Classic / Legacy Hardstyle", "medium", "Curated V2 legacy hardstyle hint."),
    # Hardcore / frenchcore / uptempo ecosystem.
    "andy-the-core": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "bigotek": ("Frenchcore", "low", "Low-confidence Frenchcore/tribe hint; needs review."),
    "blutonium-boys": ("Classic / Legacy Hardstyle", "medium", "Curated V2 legacy hardstyle hint."),
    "broken-minds": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "chaotic-hostility": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "cryogenic": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "dimitri-k": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "dr-evil": ("Uptempo Hardcore", "low", "Low-confidence uptempo hint; needs review."),
    "dr-rude": ("Freestyle / Hard Dance", "medium", "Curated V2 freestyle/hard dance hint."),
    "drokz": ("Terror / Speedcore", "medium", "Curated V2 terror/speedcore hint."),
    "ender": ("Uptempo Hardcore", "low", "Low-confidence uptempo hint; needs review."),
    "evil-activities": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "f-noize": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "f-noize-classics-uptempo": ("Uptempo Hardcore", "medium", "Show-level uptempo hint."),
    "furyan": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "gezellige-uptempo": ("Uptempo Hardcore", "medium", "Dataset name explicitly indicates uptempo."),
    "guizcore": ("Frenchcore", "low", "Low-confidence Frenchcore hint; needs review."),
    "jason-cluff": ("Uptempo Hardcore", "low", "Low-confidence uptempo hint; needs review."),
    "jkll": ("Frenchcore", "medium", "Curated V2 Frenchcore hint."),
    "levenkhan": ("Uptempo Hardcore", "low", "Low-confidence uptempo hint; needs review."),
    "lunakorpz": ("Frenchcore", "medium", "Curated V2 Frenchcore hint."),
    "mad-dog": ("Hardcore", "medium", "Curated V2 mainstream hardcore hint."),
    "mbk": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "miss-k8": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "neophyte": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "noize-suppressor": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "partyraiser": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "paul-elstak": ("Classic / Legacy Hardstyle", "low", "Legacy happy hardcore / hard dance hint; needs review."),
    "perver": ("Uptempo Hardcore", "low", "Low-confidence uptempo hint; needs review."),
    "remzcore": ("Frenchcore", "medium", "Curated V2 Frenchcore hint."),
    "ruffneck": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "spitnoise": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
    "tha-playah": ("Hardcore", "medium", "Curated V2 hardcore hint."),
    "the-satan": ("Terror / Speedcore", "medium", "Curated V2 terror/speedcore hint."),
    "unicorn-on-keta": ("Uptempo Hardcore", "medium", "Curated V2 uptempo hardcore hint."),
}


@dataclass(slots=True)
class GenreSignal:
    """One explainable signal voting for a genre."""

    genre: str
    weight: float
    confidence: str
    source_type: str
    source_name: str
    metric_key: str
    notes: str
    evidence_id: int | None = None
    source_url: str | None = None
    matched_value: str | None = None


@dataclass(slots=True)
class GenreDecision:
    """Internal decision before conversion to API/DB rows."""

    main_genre: str
    secondary_genres: list[str]
    confidence: str
    confidence_score: float
    reason: str
    matched_keywords: list[str] = field(default_factory=list)
    sources: list[GenreSignal] = field(default_factory=list)
    needs_manual_review: bool = False


class MultiGenreClassifierService:
    """Classify artists into main and secondary genres with traceable sources."""

    def __init__(self, db: Session) -> None:
        """Load taxonomy, overrides and the request-scoped database session."""
        self.db = db
        ensure_database_ready(self.db)
        self.override_data = self._read_json(GENRE_OVERRIDES_PATH, fallback={})
        self.manual_overrides = self._read_json(MANUAL_OVERRIDES_PATH, fallback={})
        self.profile_cache = self._read_json(ARTIST_PROFILE_CACHE_PATH, fallback={"profiles": {}})
        self.taxonomy = self._load_taxonomy()
        self.taxonomy_by_name = {genre.name.lower(): genre.name for genre in self.taxonomy}
        self.keyword_rules = self._load_keyword_rules()
        self.artist_overrides = self._load_artist_overrides()
        self.special_performances = self._load_special_performances()

    def get_taxonomy(self) -> GenreTaxonomyResponse:
        """Return the V2 taxonomy used by the classifier."""
        return GenreTaxonomyResponse(taxonomy=self.taxonomy, total=len(self.taxonomy))

    def list_genres(self) -> list[GenreSeed]:
        """Return distribution based on persisted V2 rows, building in memory if needed."""
        artists = self.list_classified_artists(limit=10000).items
        return self._build_distribution(artists)

    def list_classified_artists(
        self,
        *,
        year: int | None = None,
        genre: str | None = None,
        secondary_genre: str | None = None,
        query: str | None = None,
        include_unknown: bool = True,
        needs_review: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ClassifiedArtistGenreList:
        """Return V2 multi-genre classifications with filters."""
        wanted_main = self._canonical_genre_name(genre) if genre else None
        wanted_secondary = self._canonical_genre_name(secondary_genre) if secondary_genre else None
        normalized_query = query.lower().strip() if query else None
        items: list[ClassifiedArtistGenre] = []

        for artist in self._list_artists(year=year, query=normalized_query):
            classified = self._classification_for_artist(artist)
            if wanted_main is not None and classified.main_genre != wanted_main:
                continue
            if wanted_secondary is not None and wanted_secondary not in classified.secondary_genres:
                continue
            if not include_unknown and classified.main_genre == "Unknown":
                continue
            if needs_review is not None and classified.needs_manual_review is not needs_review:
                continue
            items.append(classified)

        items.sort(
            key=lambda item: (
                item.main_genre == "Unknown",
                item.needs_manual_review,
                item.main_genre,
                item.name.lower(),
            )
        )
        return ClassifiedArtistGenreList(total=len(items), limit=limit, offset=offset, items=items[offset : offset + limit])

    def get_artist_classification(self, slug: str) -> ClassifiedArtistGenre | None:
        """Return one artist classification by slug."""
        artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == slug))
        if artist is None:
            return None
        return self._classification_for_artist(artist)

    def get_edition_genre_distribution(self, year: int) -> EditionGenreDistribution | None:
        """Return main-genre distribution for one Nexus edition."""
        edition_artists = self._list_artists(year=year)
        if not edition_artists:
            return None
        classified_artists = [self._classification_for_artist(artist) for artist in edition_artists]
        distribution = self._build_distribution(classified_artists)
        total_artists = len(classified_artists)
        unknown_artists = sum(item.artist_count for item in distribution if item.name == "Unknown")
        return EditionGenreDistribution(
            year=year,
            distribution=distribution,
            total_artists=total_artists,
            classified_artists=total_artists - unknown_artists,
            unknown_artists=unknown_artists,
        )

    def coverage(self) -> MultiGenreCoverage:
        """Return V2.5 coverage and confidence summary."""
        artists = self.list_classified_artists(limit=10000).items
        total = len(artists)
        unknown = sum(1 for artist in artists if artist.main_genre == "Unknown")
        low_confidence = sum(1 for artist in artists if artist.genre_confidence == "low")
        needs_review = sum(1 for artist in artists if artist.needs_manual_review)
        with_secondary = sum(1 for artist in artists if artist.secondary_genres)
        persisted_rows = int(self.db.scalar(select(func.count(ArtistGenreModel.id))) or 0)
        return MultiGenreCoverage(
            total_artists=total,
            classified_artists=total - unknown,
            unknown_artists=unknown,
            classified_ratio=round((total - unknown) / total, 4) if total else 0.0,
            low_confidence_artists=low_confidence,
            artists_needing_review=needs_review,
            artists_with_secondary_genres=with_secondary,
            persisted_genre_rows=persisted_rows,
        )

    def compare_v1_v2(self, *, limit: int = 500) -> GenreComparisonResponse:
        """Compare original V1 seed against V2 main/secondary genres."""
        records: list[GenreComparisonRecord] = []
        for artist in self._list_artists():
            classified = self._classification_for_artist(artist)
            v1_genre = self._canonical_genre_name(artist.primary_genre_seed) or "Unknown"
            records.append(
                GenreComparisonRecord(
                    artist_slug=artist.slug,
                    artist_name=artist.name,
                    v1_primary_genre=v1_genre,
                    v2_main_genre=classified.main_genre,
                    v2_secondary_genres=classified.secondary_genres,
                    confidence=classified.genre_confidence,
                    changed=v1_genre != classified.main_genre,
                    needs_manual_review=classified.needs_manual_review,
                )
            )
        changed = sum(1 for record in records if record.changed)
        unknown_reduced = sum(
            1 for record in records if record.v1_primary_genre == "Unknown" and record.v2_main_genre != "Unknown"
        )
        return GenreComparisonResponse(
            total=len(records),
            changed=changed,
            unknown_reduced=unknown_reduced,
            items=records[:limit],
        )

    def rebuild(self, *, reset: bool = True) -> MultiGenreRebuildResult:
        """Persist V2.5 genre rows, genre evidence and derived metrics."""
        if reset:
            self._reset_v2_genres()

        source = self._classifier_source()
        artists = self._list_artists()
        rows_written = 0
        evidence_written = 0
        metrics_written = 0

        for artist in artists:
            classified = self._classification_for_artist(artist)
            evidence = create_evidence(
                self.db,
                artist=artist,
                source=source,
                metric_key=f"{GENRE_METRIC_PREFIX}classification",
                metric_value={
                    "main_genre": classified.main_genre,
                    "secondary_genres": classified.secondary_genres,
                    "confidence": classified.genre_confidence,
                    "confidence_score": classified.genre_confidence_score,
                    "sources": [source.model_dump() for source in classified.genre_sources],
                },
                value_type="json",
                confidence=classified.genre_confidence,
                extraction_method="computed",
                evidence_kind="genre_classification",
                status="pending_review" if classified.needs_manual_review else "inferred",
                notes=classified.reason,
                raw={"artist_slug": artist.slug, "block": "V2.5"},
            )
            evidence_written += 1

            all_genres = [classified.main_genre, *classified.secondary_genres]
            for rank, genre in enumerate(dict.fromkeys(all_genres), start=1):
                if not genre:
                    continue
                row = self._upsert_artist_genre(
                    artist=artist,
                    genre=genre,
                    is_primary=rank == 1,
                    rank=rank,
                    classified=classified,
                    evidence_id=evidence.id,
                )
                if row:
                    rows_written += 1

            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key=f"{GENRE_ARTIST_METRIC_PREFIX}main_genre",
                text_value=classified.main_genre,
                value_type="text",
                confidence=classified.genre_confidence,
                evidence_count=len(classified.genre_sources),
                notes="V2.5 main genre selected from evidence-backed multi-genre classifier.",
                raw={"secondary_genres": classified.secondary_genres},
            )
            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key=f"{GENRE_ARTIST_METRIC_PREFIX}confidence_score",
                numeric_value=classified.genre_confidence_score,
                value_type="number",
                confidence=classified.genre_confidence,
                evidence_count=len(classified.genre_sources),
                notes="Normalized confidence score for the V2.5 genre decision.",
                raw={"main_genre": classified.main_genre},
            )
            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key=f"{GENRE_ARTIST_METRIC_PREFIX}secondary_count",
                numeric_value=float(len(classified.secondary_genres)),
                value_type="number",
                confidence=classified.genre_confidence,
                evidence_count=len(classified.genre_sources),
                notes="Number of secondary genre chips produced by the V2.5 classifier.",
                raw={"secondary_genres": classified.secondary_genres},
            )
            metrics_written += 3

        self.db.commit()
        coverage = self.coverage()
        return MultiGenreRebuildResult(
            artists_processed=len(artists),
            genre_rows=rows_written,
            evidence_items=evidence_written,
            artist_metrics=metrics_written,
            coverage=coverage,
        )

    def _classification_for_artist(self, artist: ArtistModel) -> ClassifiedArtistGenre:
        """Return persisted classification when present, otherwise compute it."""
        persisted = self._persisted_classification(artist)
        if persisted is not None:
            return persisted
        return self._computed_classification(artist)

    def _computed_classification(self, artist: ArtistModel) -> ClassifiedArtistGenre:
        """Compute a V2 multi-genre decision from internal and external signals."""
        artist_payload = self._artist_payload(artist)
        profile = self.profile_cache.get("profiles", {}).get(artist.slug, {})
        artist_kind = self._infer_artist_kind(artist.slug, artist_payload)
        signals = self._collect_signals(artist, artist_payload, profile)
        decision = self._decide(signals, artist=artist, artist_kind=artist_kind)
        override = self.artist_overrides.get(artist.slug, {})

        return ClassifiedArtistGenre(
            slug=artist.slug,
            name=artist.name,
            normalized_name=artist.normalized_name,
            main_genre=decision.main_genre,
            secondary_genres=decision.secondary_genres,
            primary_genre_seed=self._canonical_genre_name(artist.primary_genre_seed) or "Unknown",
            genre_source=self._legacy_source_name(decision.sources),
            genre_sources=[self._signal_to_source_record(signal) for signal in decision.sources],
            confidence=decision.confidence,
            genre_confidence=decision.confidence,
            genre_confidence_score=decision.confidence_score,
            reason=override.get("reason") or decision.reason,
            matched_keywords=decision.matched_keywords,
            appearance_count=artist.appearance_count,
            appearance_years=loads_json(artist.appearance_years_json, []),
            manual_review=bool(override.get("manual_review") or artist.manual_review or artist_kind in SPECIAL_KINDS),
            needs_manual_review=decision.needs_manual_review
            or bool(override.get("manual_review") or artist.manual_review or artist_kind in SPECIAL_KINDS),
            artist_kind=str(override.get("artist_kind") or artist_kind),
            is_special_show=str(override.get("artist_kind") or artist_kind) in SPECIAL_KINDS,
            related_canonical_artists=list(override.get("related_canonical_artists") or self._related_canonical_artists(artist.slug)),
        )

    def _persisted_classification(self, artist: ArtistModel) -> ClassifiedArtistGenre | None:
        """Build API response from persisted artist_genres rows when available."""
        rows = list(
            self.db.scalars(
                select(ArtistGenreModel)
                .where(ArtistGenreModel.artist_slug == artist.slug)
                .order_by(ArtistGenreModel.rank.asc(), ArtistGenreModel.genre.asc())
            )
        )
        if not rows:
            return None
        primary = next((row for row in rows if row.is_primary), rows[0])
        secondary = [row.genre for row in rows if row.genre != primary.genre]
        sources = [GenreSourceRecord(**item) for item in loads_json(primary.source_summary_json, [])]
        raw = loads_json(primary.raw_json, {})
        override = self.artist_overrides.get(artist.slug, {})
        artist_payload = self._artist_payload(artist)
        artist_kind = str(override.get("artist_kind") or raw.get("artist_kind") or self._infer_artist_kind(artist.slug, artist_payload))
        return ClassifiedArtistGenre(
            slug=artist.slug,
            name=artist.name,
            normalized_name=artist.normalized_name,
            main_genre=primary.genre,
            secondary_genres=secondary,
            primary_genre_seed=self._canonical_genre_name(artist.primary_genre_seed) or "Unknown",
            genre_source=sources[0].source_type if sources else "persisted_v2",
            genre_sources=sources,
            confidence=primary.confidence,
            genre_confidence=primary.confidence,
            genre_confidence_score=primary.confidence_score,
            reason=primary.reason,
            matched_keywords=list(raw.get("matched_keywords") or []),
            appearance_count=artist.appearance_count,
            appearance_years=loads_json(artist.appearance_years_json, []),
            manual_review=bool(override.get("manual_review") or artist.manual_review or artist_kind in SPECIAL_KINDS),
            needs_manual_review=primary.needs_manual_review,
            artist_kind=artist_kind,
            is_special_show=artist_kind in SPECIAL_KINDS,
            related_canonical_artists=list(override.get("related_canonical_artists") or raw.get("related_canonical_artists") or []),
        )

    def _collect_signals(self, artist: ArtistModel, payload: dict[str, Any], profile: dict[str, Any]) -> list[GenreSignal]:
        """Collect evidence-backed and local signals for one artist."""
        signals: list[GenreSignal] = []
        override = self.artist_overrides.get(artist.slug)
        if override:
            main = self._canonical_genre_name(str(override.get("main_genre") or "Unknown")) or "Unknown"
            signals.append(
                GenreSignal(
                    genre=main,
                    weight=1.0,
                    confidence=str(override.get("confidence") or "high"),
                    source_type="manual_override",
                    source_name="Versioned genre_overrides.json",
                    metric_key="genre.manual_override",
                    notes=str(override.get("reason") or "Manual V2 genre override."),
                    matched_value=artist.slug,
                )
            )
            for secondary in override.get("secondary_genres") or []:
                genre = self._canonical_genre_name(str(secondary))
                if genre:
                    signals.append(
                        GenreSignal(
                            genre=genre,
                            weight=0.65,
                            confidence=str(override.get("confidence") or "medium"),
                            source_type="manual_override",
                            source_name="Versioned genre_overrides.json",
                            metric_key="genre.manual_secondary",
                            notes="Manual secondary genre override.",
                            matched_value=str(secondary),
                        )
                    )

        seed = self._canonical_genre_name(artist.primary_genre_seed)
        if seed and seed != "Unknown":
            signals.append(
                GenreSignal(
                    genre=seed,
                    weight=0.72,
                    confidence="medium",
                    source_type="internal_dataset",
                    source_name="Internal V1 genre seed",
                    metric_key="genre.v1_primary_genre_seed",
                    notes="V1 single-genre seed reused as medium-confidence evidence.",
                    matched_value=artist.primary_genre_seed,
                )
            )

        signals.extend(self._spotify_genre_signals(artist))
        signals.extend(self._evidence_genre_signals(artist))
        signals.extend(self._platform_genre_signals(artist))
        signals.extend(self._curated_hint_signal(artist))
        signals.extend(self._keyword_signals(payload, profile))

        if self._looks_like_mc(payload):
            signals.append(
                GenreSignal(
                    genre="MC / Host",
                    weight=0.95,
                    confidence="high",
                    source_type="rule_artist_name",
                    source_name="Artist name rule",
                    metric_key="genre.rule.mc_host",
                    notes="Artist name indicates MC / host role.",
                    matched_value="mc",
                )
            )
        return signals

    def _decide(self, signals: list[GenreSignal], *, artist: ArtistModel, artist_kind: str) -> GenreDecision:
        """Apply tie-breaking, confidence and fallback rules."""
        score_by_genre: dict[str, float] = defaultdict(float)
        signals_by_genre: dict[str, list[GenreSignal]] = defaultdict(list)
        matched_keywords: list[str] = []

        for signal in signals:
            genre = self._canonical_genre_name(signal.genre) or signal.genre
            if genre == "Unknown":
                continue
            score_by_genre[genre] += signal.weight
            signals_by_genre[genre].append(signal)
            if signal.source_type.startswith("rule") and signal.matched_value:
                matched_keywords.append(signal.matched_value)

        if not score_by_genre:
            if artist.slug in FORCE_UNKNOWN_REVIEW_SLUGS:
                unknown_signal = GenreSignal(
                    genre="Unknown",
                    weight=0.0,
                    confidence="low",
                    source_type="manual_review_queue",
                    source_name="V2.5 manual review queue",
                    metric_key="genre.v2.manual_review_required",
                    notes="Intentionally left Unknown until a reliable source confirms the artist subgenre.",
                    matched_value=artist.slug,
                )
                return GenreDecision(
                    main_genre="Unknown",
                    secondary_genres=[],
                    confidence="low",
                    confidence_score=0.0,
                    reason="No reliable genre source yet; manual review required.",
                    matched_keywords=[],
                    sources=[unknown_signal],
                    needs_manual_review=True,
                )

            fallback = GenreSignal(
                genre="Hard Dance",
                weight=0.25,
                confidence="low",
                source_type="nexus_lineup_context",
                source_name="Nexus/Fabrik lineup context",
                metric_key="genre.context.hard_dance_fallback",
                notes=(
                    "Fallback used only because the artist appears in a Nexus hard-dance lineup. "
                    "It must remain low-confidence and manually reviewable."
                ),
                matched_value="nexus_lineup",
            )
            return GenreDecision(
                main_genre="Hard Dance",
                secondary_genres=[],
                confidence="low",
                confidence_score=0.25,
                reason="Low-confidence hard-dance context fallback; manual review required.",
                matched_keywords=[],
                sources=[fallback],
                needs_manual_review=True,
            )

        ordered = sorted(
            score_by_genre.items(),
            key=lambda item: (-item[1], -self._genre_priority(item[0]), item[0]),
        )
        main_genre, main_score = ordered[0]
        main_sources = sorted(signals_by_genre[main_genre], key=lambda signal: -signal.weight)[:6]
        secondary = self._secondary_genres(main_genre, score_by_genre)
        confidence = self._confidence_from_score(main_score, main_sources)
        confidence_score = round(min(1.0, main_score), 4)
        needs_review = confidence == "low" or main_genre in {"Unknown", "Hard Dance"} or artist_kind in SPECIAL_KINDS
        reason = self._decision_reason(main_genre, main_sources, secondary)
        return GenreDecision(
            main_genre=main_genre,
            secondary_genres=secondary,
            confidence=confidence,
            confidence_score=confidence_score,
            reason=reason,
            matched_keywords=sorted(set(matched_keywords)),
            sources=main_sources,
            needs_manual_review=needs_review,
        )

    def _spotify_genre_signals(self, artist: ArtistModel) -> list[GenreSignal]:
        """Convert cached Spotify genres into V2 genre signals when available."""
        cache = self.db.scalar(select(SpotifyArtistCacheModel).where(SpotifyArtistCacheModel.artist_slug == artist.slug))
        if cache is None:
            return []
        raw_genres = loads_json(cache.genres_json, [])
        signals: list[GenreSignal] = []
        for raw_genre in raw_genres:
            mapped = self._genre_from_text(str(raw_genre))
            if mapped and mapped != "Unknown":
                signals.append(
                    GenreSignal(
                        genre=mapped,
                        weight=0.82,
                        confidence="high",
                        source_type="music_platform",
                        source_name="Spotify Web API",
                        source_url=cache.spotify_url,
                        metric_key="spotify.genres",
                        notes="Spotify artist genre tag mapped into the Nexus hard-dance taxonomy.",
                        matched_value=str(raw_genre),
                    )
                )
        return signals

    def _evidence_genre_signals(self, artist: ArtistModel) -> list[GenreSignal]:
        """Convert existing genre-related evidence rows into classifier signals."""
        rows = list(
            self.db.scalars(
                select(EvidenceItemModel).where(
                    EvidenceItemModel.artist_slug == artist.slug,
                    or_(
                        EvidenceItemModel.metric_key.ilike("%genre%"),
                        EvidenceItemModel.metric_key.ilike("%beatport%"),
                        EvidenceItemModel.metric_key.ilike("%1001tracklists%"),
                    ),
                )
            )
        )
        signals: list[GenreSignal] = []
        for row in rows:
            for value in self._extract_candidate_strings(row.metric_value):
                mapped = self._genre_from_text(value)
                if mapped and mapped != "Unknown":
                    signals.append(
                        GenreSignal(
                            genre=mapped,
                            weight=self._weight_from_confidence(row.confidence, default=0.55),
                            confidence=row.confidence,
                            source_type=row.source_type,
                            source_name=row.source_name,
                            source_url=row.source_url,
                            metric_key=row.metric_key,
                            notes=row.notes or "Genre-related evidence mapped by the V2.5 classifier.",
                            evidence_id=row.id,
                            matched_value=value,
                        )
                    )
        return signals

    def _platform_genre_signals(self, artist: ArtistModel) -> list[GenreSignal]:
        """Look for genre-like metadata in platform profile raw JSON."""
        rows = list(self.db.scalars(select(PlatformProfileModel).where(PlatformProfileModel.artist_slug == artist.slug)))
        signals: list[GenreSignal] = []
        for row in rows:
            raw = loads_json(row.raw_json, {})
            for value in self._extract_candidate_strings(raw):
                mapped = self._genre_from_text(value)
                if mapped and mapped != "Unknown":
                    signals.append(
                        GenreSignal(
                            genre=mapped,
                            weight=self._weight_from_confidence(row.confidence, default=0.5),
                            confidence=row.confidence,
                            source_type="platform_profile",
                            source_name=f"{row.platform} profile metadata",
                            source_url=row.profile_url,
                            metric_key=f"platform.{row.platform}.genre_signal",
                            notes="Platform profile raw metadata contained a genre-like value.",
                            evidence_id=row.evidence_id,
                            matched_value=value,
                        )
                    )
        return signals

    def _curated_hint_signal(self, artist: ArtistModel) -> list[GenreSignal]:
        """Return curated V2 hint for known artists that were still Unknown in V1."""
        hint = V2_CURATED_HINTS.get(artist.slug)
        if not hint:
            return []
        genre, confidence, notes = hint
        return [
            GenreSignal(
                genre=genre,
                weight=self._weight_from_confidence(confidence, default=0.48),
                confidence=confidence,
                source_type="curated_v2_hint",
                source_name="V2 curated genre hint list",
                metric_key="genre.v2.curated_hint",
                notes=notes,
                matched_value=artist.slug,
            )
        ]

    def _keyword_signals(self, artist_payload: dict[str, Any], profile: dict[str, Any]) -> list[GenreSignal]:
        """Convert keyword-rule hits into medium/low confidence signals."""
        text = self._artist_text_for_rules(artist_payload, profile)
        signals: list[GenreSignal] = []
        for genre_name, keywords in self.keyword_rules.items():
            matched = [keyword for keyword in keywords if keyword.lower() in text]
            if not matched:
                continue
            priority = self._genre_priority(genre_name)
            weight = 0.52 + min(0.18, priority / 1000)
            signals.append(
                GenreSignal(
                    genre=genre_name,
                    weight=weight,
                    confidence="medium",
                    source_type="rule_keyword",
                    source_name="V2 keyword rules",
                    metric_key="genre.rule.keyword",
                    notes="Keyword rule matched artist/profile text.",
                    matched_value=matched[0],
                )
            )
        return signals

    def _upsert_artist_genre(
        self,
        *,
        artist: ArtistModel,
        genre: str,
        is_primary: bool,
        rank: int,
        classified: ClassifiedArtistGenre,
        evidence_id: int,
    ) -> ArtistGenreModel:
        """Insert or update one artist_genres row."""
        row = self.db.scalar(
            select(ArtistGenreModel).where(
                ArtistGenreModel.artist_slug == artist.slug,
                ArtistGenreModel.genre == genre,
            )
        )
        source_summary = [source.model_dump() for source in classified.genre_sources]
        source_keys = [source.metric_key for source in classified.genre_sources]
        raw = {
            "matched_keywords": classified.matched_keywords,
            "artist_kind": classified.artist_kind,
            "related_canonical_artists": classified.related_canonical_artists,
            "block": "V2.5",
        }
        if row is None:
            row = ArtistGenreModel(
                artist_id=artist.id,
                artist_slug=artist.slug,
                genre=genre,
                is_primary=is_primary,
                rank=rank,
                confidence=classified.genre_confidence,
                confidence_score=classified.genre_confidence_score,
                source_summary_json=dumps_json(source_summary),
                evidence_ids_json=dumps_json([evidence_id]),
                source_keys_json=dumps_json(source_keys),
                reason=classified.reason,
                status="pending_review" if classified.needs_manual_review else "inferred",
                needs_manual_review=classified.needs_manual_review,
                raw_json=dumps_json(raw),
            )
            self.db.add(row)
            self.db.flush()
            return row

        row.is_primary = is_primary
        row.rank = rank
        row.confidence = classified.genre_confidence
        row.confidence_score = classified.genre_confidence_score
        row.source_summary_json = dumps_json(source_summary)
        row.evidence_ids_json = dumps_json([evidence_id])
        row.source_keys_json = dumps_json(source_keys)
        row.reason = classified.reason
        row.status = "pending_review" if classified.needs_manual_review else "inferred"
        row.needs_manual_review = classified.needs_manual_review
        row.raw_json = dumps_json(raw)
        return row

    def _reset_v2_genres(self) -> None:
        """Delete only V2.5 generated rows without touching Spotify/social data."""
        self.db.execute(delete(ArtistGenreModel))
        self.db.execute(delete(ArtistMetricModel).where(ArtistMetricModel.metric_key.like(f"{GENRE_ARTIST_METRIC_PREFIX}%")))
        self.db.execute(delete(EvidenceItemModel).where(EvidenceItemModel.metric_key.like(f"{GENRE_METRIC_PREFIX}%")))
        self.db.flush()

    def _classifier_source(self) -> SourceModel:
        """Return source row used by generated classifier evidence."""
        return get_or_create_source(
            self.db,
            key="v2_multi_genre_classifier",
            name="Nexus Predictor V2.5 multi-genre classifier",
            source_type="computed_classifier",
            base_url=None,
            confidence="medium",
            extraction_method="computed",
            notes="Transparent multi-genre classifier combining manual overrides, Spotify/cache signals, platform evidence and keyword rules.",
            raw={"block": "V2.5"},
        )

    def _list_artists(self, *, year: int | None = None, query: str | None = None) -> list[ArtistModel]:
        """Return artist ORM rows with optional year/text filters."""
        rows = list(self.db.scalars(select(ArtistModel).order_by(ArtistModel.name.asc())).all())
        result: list[ArtistModel] = []
        for artist in rows:
            years = loads_json(artist.appearance_years_json, [])
            if year is not None and year not in years:
                continue
            if query and query not in artist.name.lower() and query not in artist.slug.lower():
                continue
            result.append(artist)
        return result

    def _artist_payload(self, artist: ArtistModel) -> dict[str, Any]:
        """Convert ORM artist into the payload shape used by legacy logic."""
        raw = loads_json(artist.raw_json, {})
        return {
            "slug": artist.slug,
            "name": artist.name,
            "normalized_name": artist.normalized_name,
            "primary_genre_seed": artist.primary_genre_seed,
            "appearance_count": artist.appearance_count,
            "appearance_years": loads_json(artist.appearance_years_json, []),
            "appearances": loads_json(artist.appearances_json, []),
            "manual_review": artist.manual_review,
            "raw": raw,
        }

    def _build_distribution(self, artists: list[ClassifiedArtistGenre]) -> list[GenreSeed]:
        """Create a sorted main-genre distribution."""
        counter: Counter[str] = Counter(artist.main_genre for artist in artists)
        by_name = {genre.name: genre for genre in self.taxonomy}
        return [
            GenreSeed(
                name=name,
                artist_count=count,
                parent=by_name.get(name).parent if name in by_name else GENRE_PARENTS.get(name),
                description=by_name.get(name).description if name in by_name else None,
                aliases=by_name.get(name).aliases if name in by_name else [],
            )
            for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _secondary_genres(self, main_genre: str, score_by_genre: dict[str, float]) -> list[str]:
        """Build secondary chips from hierarchy and non-winning evidence."""
        secondary: list[str] = []
        parent = GENRE_PARENTS.get(main_genre)
        while parent and parent not in {"Hard Dance", "Other"}:
            secondary.append(parent)
            parent = GENRE_PARENTS.get(parent)

        for genre, score in sorted(score_by_genre.items(), key=lambda item: (-item[1], item[0])):
            if genre == main_genre or genre in secondary or genre == "Unknown":
                continue
            if score >= 0.55:
                secondary.append(genre)
            if len(secondary) >= 4:
                break
        return secondary

    def _decision_reason(self, main_genre: str, sources: list[GenreSignal], secondary: list[str]) -> str:
        """Summarize why the main genre was selected."""
        if not sources:
            return "No sources available; classification requires manual review."
        source_names = ", ".join(sorted({source.source_name for source in sources})[:3])
        suffix = f" Secondary chips: {', '.join(secondary)}." if secondary else ""
        return f"Selected {main_genre} from {len(sources)} signal(s): {source_names}.{suffix}"

    def _confidence_from_score(self, score: float, sources: list[GenreSignal]) -> str:
        """Convert weighted score/source quality into the closed confidence model."""
        if any(source.confidence == "verified" for source in sources):
            return "verified"
        if score >= 0.95 or any(source.confidence == "high" and source.weight >= 0.9 for source in sources):
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    def _weight_from_confidence(self, confidence: str | None, *, default: float) -> float:
        """Map confidence labels to conservative classifier weights."""
        normalized = normalize_confidence(confidence, fallback="medium")
        return {
            "verified": 1.0,
            "high": 0.86,
            "medium": 0.58,
            "low": 0.35,
        }.get(normalized, default)

    def _signal_to_source_record(self, signal: GenreSignal) -> GenreSourceRecord:
        """Serialize a signal for public API responses."""
        return GenreSourceRecord(
            source_type=signal.source_type,
            source_name=signal.source_name,
            metric_key=signal.metric_key,
            confidence=signal.confidence,
            weight=round(signal.weight, 4),
            evidence_id=signal.evidence_id,
            source_url=signal.source_url,
            matched_value=signal.matched_value,
            notes=signal.notes,
        )

    def _legacy_source_name(self, sources: list[GenreSignal]) -> str:
        """Keep the old genre_source field meaningful for existing consumers."""
        if not sources:
            return "unknown"
        return sources[0].source_type

    def _genre_from_text(self, value: str) -> str | None:
        """Map arbitrary source text into the taxonomy with aliases/keywords."""
        direct = self._canonical_genre_name(value)
        if direct:
            return direct
        text = value.lower()
        matches: list[tuple[int, str]] = []
        for genre_name, keywords in self.keyword_rules.items():
            if any(keyword.lower() in text for keyword in keywords):
                matches.append((self._genre_priority(genre_name), genre_name))
        if not matches:
            return None
        return sorted(matches, key=lambda item: (-item[0], item[1]))[0][1]

    def _extract_candidate_strings(self, value: Any) -> list[str]:
        """Flatten strings from JSON/text values for genre matching."""
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                decoded = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]
            return self._extract_candidate_strings(decoded)
        if isinstance(value, dict):
            strings: list[str] = []
            for key, item in value.items():
                if "genre" in str(key).lower() or "style" in str(key).lower() or isinstance(item, (dict, list, str)):
                    strings.extend(self._extract_candidate_strings(item))
            return strings
        if isinstance(value, list):
            strings: list[str] = []
            for item in value:
                strings.extend(self._extract_candidate_strings(item))
            return strings
        return [str(value)]

    def _artist_text_for_rules(self, artist: dict[str, Any], profile: dict[str, Any]) -> str:
        """Join available metadata into a lowercase searchable string."""
        values: list[str] = [
            str(artist.get("slug") or ""),
            str(artist.get("name") or ""),
            str(artist.get("normalized_name") or ""),
            str(artist.get("primary_genre_seed") or ""),
            str(profile.get("bio") or ""),
            " ".join(str(alias) for alias in profile.get("aliases", []) if alias),
            json.dumps(artist.get("appearances") or [], ensure_ascii=False),
            json.dumps(artist.get("raw") or {}, ensure_ascii=False),
        ]
        return " ".join(values).lower()

    def _load_taxonomy(self) -> list[GenreDefinition]:
        """Load taxonomy and inject V2 parent/fallback labels when missing."""
        taxonomy = [GenreDefinition(**item) for item in self.override_data.get("taxonomy", [])]
        names = {genre.name for genre in taxonomy}
        if "Hard Dance" not in names:
            taxonomy.append(
                GenreDefinition(
                    name="Hard Dance",
                    parent=None,
                    description="Low-confidence umbrella label used only when a Nexus artist lacks subgenre evidence.",
                    aliases=["hard dance"],
                    priority=10,
                )
            )
        if taxonomy:
            return sorted(taxonomy, key=lambda genre: (-genre.priority, genre.name))
        return [GenreDefinition(name="Unknown", description="Not enough reliable data yet.")]

    def _load_keyword_rules(self) -> dict[str, list[str]]:
        """Load keyword rules and normalize target genre names."""
        rules: dict[str, list[str]] = {}
        for raw_genre, keywords in self.override_data.get("keyword_rules", {}).items():
            genre = self._canonical_genre_name(raw_genre)
            if genre:
                rules[genre] = [str(keyword).lower() for keyword in keywords]
        return rules

    def _load_artist_overrides(self) -> dict[str, dict[str, Any]]:
        """Load slug-based manual overrides from versioned JSON."""
        return {
            str(item.get("slug")): item for item in self.override_data.get("artist_overrides", []) if item.get("slug")
        }

    def _load_special_performances(self) -> dict[str, dict[str, Any]]:
        """Load manual performance/show metadata from the Block 1 overrides file."""
        result: dict[str, dict[str, Any]] = {}
        for item in self.manual_overrides.get("special_performances", []):
            display_name = str(item.get("display_name") or "").lower()
            if display_name:
                result[display_name] = item
        return result

    def _infer_artist_kind(self, slug: str, artist: dict[str, Any]) -> str:
        """Infer if an entry is a normal artist or a show-level item."""
        if slug in self.artist_overrides and self.artist_overrides[slug].get("artist_kind"):
            return str(self.artist_overrides[slug]["artist_kind"])
        appearances = artist.get("appearances") or []
        for appearance in appearances:
            performance_type = str(appearance.get("performance_type") or "").lower()
            display_name = str(appearance.get("performance_display_name") or "").lower()
            if performance_type in SPECIAL_KINDS or performance_type in {"special_show", "live"}:
                return "special_show" if performance_type == "special_show" else performance_type
            if display_name in self.special_performances:
                return str(self.special_performances[display_name].get("type") or "special_show")
        return "artist"

    def _related_canonical_artists(self, slug: str) -> list[str]:
        """Return show relationship artists from overrides when available."""
        override = self.artist_overrides.get(slug)
        if override:
            return list(override.get("related_canonical_artists") or [])
        return []

    def _looks_like_mc(self, artist: dict[str, Any]) -> bool:
        """Detect MC entries by artist name."""
        name = str(artist.get("name") or "").lower().strip()
        return name.startswith("mc ") or name.endswith(" mc") or " mc " in f" {name} "

    def _canonical_genre_name(self, value: str | None) -> str | None:
        """Normalize a genre label or alias into the taxonomy name."""
        if not value:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in self.taxonomy_by_name:
            return self.taxonomy_by_name[normalized]
        for genre in self.taxonomy:
            if normalized in {alias.lower() for alias in genre.aliases}:
                return genre.name
        if normalized in {"hard dance", "hard-dance"}:
            return "Hard Dance"
        return "Unknown" if normalized == "unknown" else None

    def _genre_priority(self, genre_name: str) -> int:
        """Return taxonomy priority for deterministic tie-breaking."""
        return next((genre.priority for genre in self.taxonomy if genre.name == genre_name), 0)

    def _read_json(self, path, *, fallback: dict[str, Any]) -> dict[str, Any]:
        """Read JSON safely so the API still works with missing optional files."""
        try:
            if not path.exists():
                return fallback
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return fallback
