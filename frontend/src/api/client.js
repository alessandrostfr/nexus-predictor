// Central API client helpers for the React app.
// Block 7 consumes the backend through this single file so endpoint changes stay localized.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api';

// Build a safe URL with optional query params while skipping empty filters.
function buildUrl(path, params = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

// Shared fetch wrapper with a consistent response shape for the UI.
async function request(path, params) {
  const response = await fetch(buildUrl(path, params));

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();

  if (payload?.success === false) {
    throw new Error(payload.message ?? 'The API returned an unsuccessful response.');
  }

  return payload;
}

export async function getHealthStatus() {
  return request('/health');
}

export async function getEditions() {
  return request('/editions');
}

export async function getEdition(year) {
  return request(`/editions/${year}`);
}

export async function getEditionLineup(year) {
  return request(`/editions/${year}/lineup`);
}

export async function getFabrikVenue() {
  return request('/venue/fabrik');
}

export async function getGenres() {
  return request('/genres');
}

export async function getGenreTaxonomy() {
  return request('/genres/taxonomy');
}

export async function getEditionGenreDistribution(year) {
  return request(`/genres/editions/${year}`);
}

export async function getEditionPrediction(year, artistLimit = 12) {
  return request(`/predictions/${year}`, { artist_limit: artistLimit });
}

export async function getArtistPredictions(year, params = {}) {
  return request(`/predictions/${year}/artists`, params);
}

export async function getArtistPrediction(year, slug) {
  return request(`/predictions/${year}/artists/${slug}`);
}

export async function getArtistProfiles(params = {}) {
  return request('/artist-profiles', params);
}

export async function getArtistProfile(slug) {
  return request(`/artist-profiles/${slug}`);
}
