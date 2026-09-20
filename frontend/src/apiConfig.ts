const PRODUCTION_API_URL = 'https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io';

export const API_BASE_URL: string = (
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname.includes('azurestaticapps.net')
    ? PRODUCTION_API_URL
    : '')
).replace(/\/$/, '');

export function apiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}
