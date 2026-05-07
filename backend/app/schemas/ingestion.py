"""Pydantic schemas for V2.3 external ingestion."""

from pydantic import BaseModel, Field


class ExternalIngestionRunSummary(BaseModel):
    """Summary returned after an external ingestion run."""

    sources: int = Field(description="Number of source registry rows touched by the flow.")
    venue_prestige_items: int = Field(description="Number of venue/festival prestige rows upserted.")
    career_events: int = Field(description="Number of career event rows inserted during this run.")
    evidence_items: int = Field(description="Number of evidence rows inserted during this run.")
    artist_metrics: int = Field(description="Number of artist metric rows upserted.")
    skipped_unknown_artists: int = Field(description="Seed rows skipped because the artist slug does not exist.")
    warnings: list[str] = Field(default_factory=list)


class ExternalIngestionCoverage(BaseModel):
    """Coverage snapshot for V2.3 data."""

    external_sources: int
    external_evidence_items: int
    external_career_events: int
    external_artist_metrics: int
    artists_with_external_events: int
    artists_with_headliner_signals: int
    venue_prestige_items: int


class ExternalSourceProbeResult(BaseModel):
    """Best-effort URL probe result that never blocks the main ingestion run."""

    source_key: str
    source_url: str | None = None
    ok: bool
    status_code: int | None = None
    error: str | None = None
