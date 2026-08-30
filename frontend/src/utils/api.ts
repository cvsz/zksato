export function getBackendUrl(): string {
  if (process.env.NEXT_PUBLIC_BACKEND_URL && process.env.NEXT_PUBLIC_BACKEND_URL.startsWith('http')) {
    // If running in browser on zksato.zeaz.dev and backend was set to localhost, fallback to zksato-api.zeaz.dev
    if (typeof window !== 'undefined' && window.location.hostname.includes('zksato.zeaz.dev')) {
      return 'https://zksato-api.zeaz.dev';
    }
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host.includes('zksato.zeaz.dev')) {
      return 'https://zksato-api.zeaz.dev';
    }
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:9569';
    }
  }
  return 'http://localhost:9569';
}
