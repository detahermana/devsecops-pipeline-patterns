// Minimal entry point so the pipeline's frontend build and lint steps have
// something real to run against.

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`health check failed: ${res.status}`);
  }
  return res.json();
}

export function formatItem(item) {
  return `${item.id}: ${item.name}`;
}
