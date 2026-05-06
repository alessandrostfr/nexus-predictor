// Central API client helpers for the React app.
// Keeping fetch logic here avoids duplicating URLs across components.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api';

export async function getHealthStatus() {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error('The backend health check failed.');
  }

  return response.json();
}

export async function getEditions() {
  const response = await fetch(`${API_BASE_URL}/editions`);

  if (!response.ok) {
    throw new Error('The editions endpoint failed.');
  }

  return response.json();
}
