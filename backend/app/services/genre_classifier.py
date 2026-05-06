"""Rule-based hard dance subgenre classifier.

Block 4 intentionally uses a transparent rules + overrides approach instead of a
black-box ML model. Hard dance labels are often ambiguous in generic music APIs,
so manual overrides must win over keywords and seed values.
"""

import json
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.paths import ARTIST_PROFILE_CACHE_PATH, GENRE_OVERRIDES_PATH, MANUAL_OVERRIDES_PATH
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.genre import (
    ClassifiedArtistGenre,
    ClassifiedArtistGenreList,
    EditionGenreDistribution,
    GenreDefinition,
    GenreSeed,
    GenreTaxonomyResponse,
)

SPECIAL_KINDS = {"special_show", "label_show", "duo_project", "live_or_collective"}


class GenreClassifierService:
    """Classify artists using the MVP taxonomy, keywords and manual overrides."""

    def __init__(self, db: Session) -> None:
        """Create a repository and load local JSON classification data."""
        self.repository = SQLiteRepository(db)
        self.override_data = self._read_json(GENRE_OVERRIDES_PATH, fallback={})
        self.manual_overrides = self._read_json(MANUAL_OVERRIDES_PATH, fallback={})
        self.profile_cache = self._read_json(ARTIST_PROFILE_CACHE_PATH, fallback={"profiles": {}})
        self.taxonomy = self._load_taxonomy()
        self.taxonomy_by_name = {genre.name.lower(): genre.name for genre in self.taxonomy}
        self.keyword_rules = self._load_keyword_rules()
        self.artist_overrides = self._load_artist_overrides()
        self.special_performances = self._load_special_performances()

    def get_taxonomy(self) -> GenreTaxonomyResponse:
        """Return the closed MVP taxonomy used by the classifier."""
        return GenreTaxonomyResponse(taxonomy=self.taxonomy, total=len(self.taxonomy))

    def list_genres(self) -> list[GenreSeed]:
        """Return classified counts across all artists."""
        classified = self.list_classified_artists(limit=10000).items
        return self._build_distribution(classified)

    def list_classified_artists(
        self,
        *,
        year: int | None = None,
        genre: str | None = None,
        query: str | None = None,
        include_unknown: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> ClassifiedArtistGenreList:
        """Return classified artists with optional filters for API/frontend usage."""
        base_artists = self.repository.list_artists(year=year, query=query, limit=10000, offset=0)["items"]
        wanted_genre = self._canonical_genre_name(genre) if genre else None
        items: list[ClassifiedArtistGenre] = []

        for artist in base_artists:
            classified = self.classify_artist_payload(artist)
            if wanted_genre is not None and classified.main_genre != wanted_genre:
                continue
            if not include_unknown and classified.main_genre == "Unknown":
                continue
            items.append(classified)

        items.sort(key=lambda item: (item.main_genre == "Unknown", item.main_genre, item.name.lower()))
        return ClassifiedArtistGenreList(
            total=len(items),
            limit=limit,
            offset=offset,
            items=items[offset : offset + limit],
        )

    def get_artist_classification(self, slug: str) -> ClassifiedArtistGenre | None:
        """Return one artist classification by slug."""
        artist = self.repository.get_artist(slug)
        if artist is None:
            return None
        return self.classify_artist_payload(artist)

    def get_edition_genre_distribution(self, year: int) -> EditionGenreDistribution | None:
        """Return classified genre distribution for one Nexus edition."""
        lineup = self.repository.get_edition_lineup(year)
        if lineup is None:
            return None

        classified_artists = self.list_classified_artists(year=year, limit=10000).items
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

    def classify_artist_payload(self, artist: dict[str, Any]) -> ClassifiedArtistGenre:
        """Classify one artist dictionary from SQLiteRepository."""
        slug = str(artist.get("slug", ""))
        profile = self.profile_cache.get("profiles", {}).get(slug, {})
        base_seed = self._canonical_genre_name(str(artist.get("primary_genre_seed") or "Unknown")) or "Unknown"
        artist_kind = self._infer_artist_kind(slug, artist)

        override = self.artist_overrides.get(slug)
        if override:
            main_genre = self._canonical_genre_name(str(override.get("main_genre") or "Unknown")) or "Unknown"
            kind = str(override.get("artist_kind") or artist_kind)
            return ClassifiedArtistGenre(
                slug=slug,
                name=str(artist.get("name") or slug),
                normalized_name=str(artist.get("normalized_name") or artist.get("name") or slug),
                main_genre=main_genre,
                primary_genre_seed=base_seed,
                genre_source="manual_override",
                confidence=str(override.get("confidence") or "high"),
                reason=override.get("reason"),
                matched_keywords=[],
                appearance_count=int(artist.get("appearance_count") or 0),
                appearance_years=list(artist.get("appearance_years") or []),
                manual_review=bool(override.get("manual_review") or artist.get("manual_review") or kind in SPECIAL_KINDS),
                needs_manual_review=main_genre == "Unknown" or bool(override.get("manual_review") or False),
                artist_kind=kind,
                is_special_show=kind in SPECIAL_KINDS,
                related_canonical_artists=list(override.get("related_canonical_artists") or []),
            )

        if base_seed != "Unknown":
            return self._build_classification(
                artist,
                main_genre=base_seed,
                source="seed_genre",
                confidence="medium",
                reason="Classified from the curated artist_index primary_genre_seed.",
                matched_keywords=[],
                artist_kind=artist_kind,
            )

        text = self._artist_text_for_rules(artist, profile)
        matched_genre, matched_keywords = self._match_keyword_rules(text)
        if matched_genre:
            return self._build_classification(
                artist,
                main_genre=matched_genre,
                source="rule_keyword",
                confidence="medium",
                reason="Classified from hard dance keyword rules.",
                matched_keywords=matched_keywords,
                artist_kind=artist_kind,
            )

        if self._looks_like_mc(artist):
            return self._build_classification(
                artist,
                main_genre="MC / Host",
                source="rule_artist_name",
                confidence="high",
                reason="Artist name indicates MC / host role.",
                matched_keywords=["mc"],
                artist_kind="host",
            )

        return self._build_classification(
            artist,
            main_genre="Unknown",
            source="unknown",
            confidence="low",
            reason="No reliable genre seed, manual override or rule match yet.",
            matched_keywords=[],
            artist_kind=artist_kind,
        )

    def _build_classification(
        self,
        artist: dict[str, Any],
        *,
        main_genre: str,
        source: str,
        confidence: str,
        reason: str,
        matched_keywords: list[str],
        artist_kind: str,
    ) -> ClassifiedArtistGenre:
        """Build a Pydantic classification model from common fields."""
        manual_review = bool(artist.get("manual_review") or artist_kind in SPECIAL_KINDS)
        return ClassifiedArtistGenre(
            slug=str(artist.get("slug") or ""),
            name=str(artist.get("name") or ""),
            normalized_name=str(artist.get("normalized_name") or artist.get("name") or ""),
            main_genre=main_genre,
            primary_genre_seed=self._canonical_genre_name(str(artist.get("primary_genre_seed") or "Unknown")) or "Unknown",
            genre_source=source,
            confidence=confidence,
            reason=reason,
            matched_keywords=matched_keywords,
            appearance_count=int(artist.get("appearance_count") or 0),
            appearance_years=list(artist.get("appearance_years") or []),
            manual_review=manual_review,
            needs_manual_review=main_genre == "Unknown" or manual_review,
            artist_kind=artist_kind,
            is_special_show=artist_kind in SPECIAL_KINDS,
            related_canonical_artists=self._related_canonical_artists(str(artist.get("slug") or "")),
        )

    def _build_distribution(self, artists: list[ClassifiedArtistGenre]) -> list[GenreSeed]:
        """Create a sorted distribution from classified artists."""
        counter: Counter[str] = Counter(artist.main_genre for artist in artists)
        by_name = {genre.name: genre for genre in self.taxonomy}
        return [
            GenreSeed(
                name=name,
                artist_count=count,
                parent=by_name.get(name).parent if name in by_name else None,
                description=by_name.get(name).description if name in by_name else None,
                aliases=by_name.get(name).aliases if name in by_name else [],
            )
            for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _artist_text_for_rules(self, artist: dict[str, Any], profile: dict[str, Any]) -> str:
        """Join available local metadata into a lowercase searchable string."""
        values: list[str] = [
            str(artist.get("name") or ""),
            str(artist.get("normalized_name") or ""),
            str(artist.get("primary_genre_seed") or ""),
            str(profile.get("bio") or ""),
            " ".join(str(alias) for alias in profile.get("aliases", []) if alias),
        ]
        raw = artist.get("raw") or {}
        if isinstance(raw, dict):
            values.append(json.dumps(raw, ensure_ascii=False))
        return " ".join(values).lower()

    def _match_keyword_rules(self, text: str) -> tuple[str | None, list[str]]:
        """Find the highest-priority genre matching the input text."""
        candidates: list[tuple[int, str, list[str]]] = []
        for genre_name, keywords in self.keyword_rules.items():
            matched = [keyword for keyword in keywords if keyword.lower() in text]
            if matched:
                priority = next((genre.priority for genre in self.taxonomy if genre.name == genre_name), 0)
                candidates.append((priority, genre_name, matched))
        if not candidates:
            return None, []
        _, genre_name, matched_keywords = sorted(candidates, key=lambda item: (-item[0], item[1]))[0]
        return genre_name, matched_keywords

    def _load_taxonomy(self) -> list[GenreDefinition]:
        """Load taxonomy from genre_overrides.json."""
        taxonomy = [GenreDefinition(**item) for item in self.override_data.get("taxonomy", [])]
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
        """Load slug-based artist overrides."""
        return {
            str(item.get("slug")): item
            for item in self.override_data.get("artist_overrides", [])
            if item.get("slug")
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
        return "Unknown" if normalized == "unknown" else None

    def _read_json(self, path, *, fallback: dict[str, Any]) -> dict[str, Any]:
        """Read JSON safely so the API still works with missing optional files."""
        try:
            if not path.exists():
                return fallback
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return fallback
