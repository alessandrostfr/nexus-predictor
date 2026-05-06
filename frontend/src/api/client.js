// Central API client helpers for the React app.
// The frontend talks only to this file, so endpoints stay easy to maintain.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api';

// Build a URL with optional query params while keeping empty values out.
function buildUrl(path, params = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

// Shared fetch wrapper with consistent error messages for the UI.
async function request(path, params) {
  const response = await fetch(buildUrl(path, params));

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Lightweight health check used by the shell connection banner.
export async function getHealthStatus() {
  return request('/health');
}

// Edition list powers the shell year chips and validates historical data loading.
export async function getEditions() {
  return request('/editions');
}

// Venue metadata is used only as a shell preview in Block 6.
export async function getFabrikVenue() {
  return request('/venue/fabrik');
}

// Genre list validates that the Block 4 classifier is reachable from React.
export async function getGenres() {
  return request('/genres');
}

// Prediction endpoint validates that Block 5 can feed frontend cards.
export async function getEditionPrediction(year, artistLimit = 6) {
  return request(`/predictions/${year}`, { artist_limit: artistLimit });
}

// Artist demand list is prepared for Block 7, but kept centralized now.
export async function getArtistPredictions(year, params = {}) {
  return request(`/predictions/${year}/artists`, params);
}
