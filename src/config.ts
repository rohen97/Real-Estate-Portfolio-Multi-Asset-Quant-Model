export const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === '1';
export const PUBLIC_DEMO = STATIC_DEMO || import.meta.env.VITE_PUBLIC_DEMO === '1';
export const API = (import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? 'http://127.0.0.1:8001' : '/api')).replace(/\/$/, '');

export async function runCalculation(path: string, body: Record<string, number>) {
  const response = await fetch(API + path, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'The calculation could not finish. Please try again.');
  }
  return response.json();
}
