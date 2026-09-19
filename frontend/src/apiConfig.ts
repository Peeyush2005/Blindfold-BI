const defaultUrl =
  typeof window !== 'undefined' && window.location.hostname.includes('azurestaticapps.net')
    ? 'https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io'
    : '';

export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL || defaultUrl).replace(/\/$/, '');

export function apiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}
