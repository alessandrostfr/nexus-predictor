"""Schemas for V3.3 artist identity resolution.

The contracts in this module are intentionally explicit about confidence and
feature eligibility. V3 must not use external metrics for ML features when the
profile match is still low-confidence or pending review.
"""

from pydantic import BaseModel, Field


class IdentityRebuildResult(BaseModel):
    """Counts returned after rebuilding the V3.3 identity layer."""

    artists_seen: int
    masters_created: int
    aliases_created: int
    links_created: int
    candidates_created: int
    top_artists_requiring_review: int
    feature_eligible_links: int
    minimum_feature_confidence: list[str]
    top_artist_policy: str


class IdentityCoverageResponse(BaseModel):
    """High-level identity-resolution coverage for admin/debug views."""

    block: str = "V3.3"
    ready: bool
    masters: int
    aliases: int
    links: int
    candidates: int
    pending_candidates: int
    verified_links: int
    rejected_candidates: int
    feature_eligible_links: int
    low_confidence_feature_links: int
    top_artists: int
    top_artists_requiring_review: int
    minimum_feature_confidence: list[str]
    warnings: list[str] = Field(default_factory=list)


class ArtistAliasRecord(BaseModel):
    """Alias/name variant attached to a canonical artist."""

    id: int
    alias: str
    normalized_alias: str
    alias_type: str
    source_key: str
    confidence: str
    status: str


class ArtistIdentityLinkRecord(BaseModel):
    """External/internal identity link attached to a canonical artist."""

    id: int
    platform: str
    profile_name: str | None = None
    normalized_profile_name: str | None = None
    profile_url: str | None = None
    external_id: str | None = None
    confidence: str
    confidence_score: float | None = None
    match_status: str
    match_method: str
    is_primary: bool
    is_feature_eligible: bool
    requires_manual_review: bool
    source_table: str | None = None
    source_record_id: int | None = None


class ArtistMasterSummary(BaseModel):
    """Compact canonical artist row for list views."""

    id: int
    canonical_artist_key: str
    source_artist_slug: str
    display_name: str
    normalized_name: str
    primary_genre_seed: str | None = None
    appearance_count: int
    is_2026_artist: bool
    is_top_artist: bool
    needs_manual_review: bool
    review_status: str
    feature_eligibility_status: str
    alias_count: int = 0
    link_count: int = 0
    candidate_count: int = 0


class ArtistMasterListResponse(BaseModel):
    """Paginated canonical artist list."""

    total: int
    limit: int
    offset: int
    items: list[ArtistMasterSummary]


class ArtistMasterDetail(ArtistMasterSummary):
    """Canonical artist detail with aliases and identity links."""

    aliases: list[ArtistAliasRecord]
    links: list[ArtistIdentityLinkRecord]


class ArtistIdentityCandidateRecord(BaseModel):
    """Candidate profile row for admin review."""

    id: int
    artist_master_id: int
    canonical_artist_key: str
    candidate_key: str
    platform: str
    candidate_name: str
    normalized_candidate_name: str
    candidate_url: str | None = None
    external_id: str | None = None
    match_score: float
    confidence: str
    status: str
    suggested_action: str
    match_method: str
    source_table: str | None = None
    source_record_id: int | None = None
    evidence_payload: dict[str, object]
    review_notes: str | None = None


class ArtistIdentityCandidateListResponse(BaseModel):
    """Paginated identity candidate list."""

    total: int
    limit: int
    offset: int
    items: list[ArtistIdentityCandidateRecord]


class ReviewIdentityCandidateRequest(BaseModel):
    """Payload used by the admin review endpoint."""

    decision: str = Field(description="Use 'verified' or 'rejected'.")
    reviewed_by: str = "alessandro"
    confidence: str | None = Field(default=None, description="Optional final confidence override.")
    notes: str | None = None


class ReviewIdentityCandidateResult(BaseModel):
    """Result returned after verifying or rejecting a candidate."""

    candidate: ArtistIdentityCandidateRecord
    created_link: ArtistIdentityLinkRecord | None = None
    feature_eligible: bool
    message: str


class IdentityConvention(BaseModel):
    """Allowed values and policy explanation."""

    key: str
    allowed_values: list[str]
    description: str


class IdentityConventionsResponse(BaseModel):
    """V3.3 identity-resolution policies."""

    confidence: IdentityConvention
    match_status: IdentityConvention
    candidate_status: IdentityConvention
    feature_eligibility: IdentityConvention
    minimum_feature_confidence: list[str]
    top_artist_policy: str
