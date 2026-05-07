// Frontend API client for Nexus Predictor V2.
// Keeping all contracts in this file prevents the UI from drifting away from FastAPI routes.

export type ApiResponse<T> = {
  success: boolean;
  message?: string;
  data: T;
};

export type HealthPayload = {
  status?: string;
  app_name?: string;
  version?: string;
  database_seeded?: boolean;
};

export type DemandCoverage = {
  year: number;
  total_artists: number;
  persisted_predictions: number;
  artists_with_external_metrics?: number;
  artists_with_spotify?: number;
  artists_with_social_or_platform_metrics?: number;
  artists_with_career_signals?: number;
  artists_with_historical_timetable?: number;
  fallback_predictions: number;
  average_demand_score: number;
  model_version: string;
  method: string;
  generated_at?: string;
};

export type DemandFactor = {
  key?: string;
  label?: string;
  value?: number | string;
  weight?: number;
  contribution?: number;
  explanation?: string;
};

export type DemandArtist = {
  artist_slug: string;
  artist_name: string;
  rank?: number | null;
  main_genre?: string;
  secondary_genres?: string[];
  popularity_score?: number;
  career_score?: number;
  momentum_score?: number;
  nexus_affinity_score?: number;
  demand_score?: number;
  crowd_risk?: string;
  confidence?: string;
  fallback_used?: boolean;
  evidence_count?: number;
  factors?: DemandFactor[];
  explanation?: string[];
};

export type DemandArtistList = {
  total: number;
  limit: number;
  offset: number;
  items: DemandArtist[];
};

export type EvidenceCoverage = {
  artists: number;
  artists_with_evidence: number;
  sources: number;
  evidence_items: number;
  artist_metrics: number;
  platform_profiles: number;
  social_profiles: number;
  career_events: number;
  venue_prestige_items: number;
};

export type GenreCoverage = {
  artists_total: number;
  classified_artists: number;
  unknown_artists: number;
  unknown_rate: number;
  main_genres: number;
  secondary_genre_rows: number;
  needs_manual_review: number;
};

export type ProbableCoverage = {
  year: number;
  timetable_kind: string;
  official_available: boolean;
  source_status: string;
  total_slots: number;
  total_artists?: number;
  assigned_artists?: number;
  unassigned_artists?: number;
  total_days: number;
  total_rooms: number;
  rooms?: string[];
  slots_by_day: Record<string, number>;
  slots_by_room: Record<string, number>;
  headliner_slots?: number;
  warmup_slots?: number;
  closing_slots?: number;
  average_probability_score: number;
  average_confidence_score: number;
  confidence_breakdown?: Record<string, number>;
  model_version?: string;
  method?: string;
  generated_at?: string;
};

export type OptimizedCoverage = {
  year: number;
  expected_variants: number;
  generated_variants: number;
  variant_keys: string[];
  total_slots: number;
  slots_per_variant: Record<string, number>;
  assigned_artists_per_variant: Record<string, number>;
  official_available: boolean;
  source_status: string;
  uses_ortools?: boolean;
  model_version?: string;
  method?: string;
  generated_at?: string;
};

export type OptimizedVariant = {
  year: number;
  variant_key: string;
  variant_name: string;
  variant_description: string;
  slot_count: number;
  artist_count: number;
  room_count?: number;
  total_days?: number;
  average_crowding_score: number;
  average_conflict_score: number;
  average_experience_score: number;
  average_optimization_score: number;
  max_expected_pressure_score: number;
  high_risk_slots: number;
  changed_slots_from_probable: number;
  rooms?: string[];
  slots_by_day?: Record<string, number>;
  slots_by_room?: Record<string, number>;
  model_version?: string;
  method?: string;
  solver_status: string;
  generated_at?: string;
  notes?: string[];
};

export type OptimizedComparison = {
  year: number;
  variants: OptimizedVariant[];
  recommended_by_goal: Record<string, string>;
  metric_notes: string[];
};

export type TimetableReason = {
  key?: string;
  label?: string;
  value?: string | number;
  weight?: number;
  description?: string;
};

export type TimetableSlot = {
  id?: number;
  year: number;
  variant_key?: string;
  variant_name?: string;
  event_day: string;
  festival_day?: number;
  date_label?: string;
  room_name: string;
  room_slug: string;
  room_capacity?: number | null;
  artist_slug: string;
  artist_name: string;
  artist_rank?: number | null;
  show_name?: string;
  performance_type?: string;
  main_genre?: string;
  secondary_genres?: string[];
  start_time: string;
  end_time: string;
  start_minutes?: number;
  end_minutes?: number;
  duration_minutes?: number;
  slot_order?: number;
  slot_type?: string;
  is_headliner_slot?: boolean;
  is_closing_slot?: boolean;
  is_warmup_slot?: boolean;
  is_special_show?: boolean;
  demand_score?: number;
  popularity_score?: number;
  career_score?: number;
  momentum_score?: number;
  nexus_affinity_score?: number;
  expected_pressure_score?: number;
  probability_score?: number;
  crowding_score?: number;
  conflict_score?: number;
  experience_score?: number;
  optimization_score?: number;
  crowd_risk?: string;
  confidence?: string;
  solver_status?: string;
  official_status?: string;
  is_official?: boolean;
  source_status?: string;
  reasons?: TimetableReason[];
  reason_json?: TimetableReason[];
};

export type SlotList = {
  total: number;
  limit: number;
  offset: number;
  items: TimetableSlot[];
};

export type SocialStatus = {
  lastfm?: {
    configured: boolean;
    api_base_url: string;
    top_track_limit: number;
    message: string;
  };
  manual_json_seed_exists?: boolean;
  manual_csv_seed_exists?: boolean;
  supported_social_platforms?: string[];
  supported_music_platforms?: string[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api';

function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined | null>) {
  const url = new URL(`${API_BASE_URL}${path}`);
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function request<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>) {
  const response = await fetch(buildUrl(path, params), {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  const payload = (await response.json()) as ApiResponse<T>;
  if (payload.success === false) {
    throw new Error(payload.message ?? 'The API returned an unsuccessful response.');
  }

  return payload.data;
}

export const api = {
  health: () => request<HealthPayload>('/health'),
  evidenceCoverage: () => request<EvidenceCoverage>('/evidence/coverage'),
  genreCoverage: () => request<GenreCoverage>('/genres/v2/coverage'),
  demandCoverage: (year = 2026) => request<DemandCoverage>(`/predictions/v2/${year}/coverage`),
  demandArtists: (year = 2026, limit = 100, q?: string, genre?: string) =>
    request<DemandArtistList>(`/predictions/v2/${year}/artists`, { limit, q, genre }),
  demandArtist: (year: number, slug: string) => request<DemandArtist>(`/predictions/v2/${year}/artists/${slug}`),
  probableCoverage: (year = 2026) => request<ProbableCoverage>(`/probable-timetables/${year}/coverage`),
  probableSlots: (year = 2026, limit = 240, room?: string, event_day?: string) =>
    request<SlotList>(`/probable-timetables/${year}/slots`, { limit, room, event_day }),
  optimizedCoverage: (year = 2026) => request<OptimizedCoverage>(`/optimized-timetables/${year}/coverage`),
  optimizedCompare: (year = 2026) => request<OptimizedComparison>(`/optimized-timetables/${year}/compare`),
  optimizedVariantSlots: (year: number, variantKey: string, limit = 240, room?: string, event_day?: string) =>
    request<SlotList>(`/optimized-timetables/${year}/variants/${variantKey}/slots`, { limit, room, event_day }),
  socialStatus: () => request<SocialStatus>('/social-platforms/status'),
};
