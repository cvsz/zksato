export function getBackendUrl(): string {
  // SSR inside docker: service name `api` is reachable, not localhost
  if (typeof window === 'undefined') {
    const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (envUrl && envUrl.startsWith('http')) {
      // Inside container, rewrite localhost to service name for SSR fetches
      if (envUrl.includes('localhost') || envUrl.includes('127.0.0.1')) {
        return 'http://api:9569';
      }
      return envUrl;
    }
    return 'http://api:9569';
  }
  const host = window.location.hostname;
  if (host.includes('zksato.zeaz.dev')) {
    return 'https://zksato.zeaz.dev';
  }
  if (host === 'localhost' || host === '127.0.0.1') {
    return 'http://localhost:9569';
  }
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (envUrl && envUrl.startsWith('http')) {
    return envUrl;
  }
  return 'http://localhost:9569';
}

export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const key = sessionStorage.getItem('zksato_api_key');
    if (key) {
      headers['X-API-Key'] = key;
    }
  }
  return headers;
}
