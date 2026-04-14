const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1']);
const SAME_ORIGIN_HOSTS = new Set(['flatwatch.aadharcha.in']);
const SAME_ORIGIN_SUFFIXES = ['.vercel.app'];
const LOCAL_FALLBACK_API_BASE = 'http://127.0.0.1:43104';

function shouldUseSameOriginApi(host: string): boolean {
  if (LOCAL_HOSTS.has(host)) {
    return false;
  }

  if (SAME_ORIGIN_HOSTS.has(host)) {
    return true;
  }

  return SAME_ORIGIN_SUFFIXES.some((suffix) => host.endsWith(suffix));
}

export function resolveFlatwatchApiBase(): string {
  if (typeof window !== 'undefined' && shouldUseSameOriginApi(window.location.host)) {
    return window.location.origin;
  }

  return process.env.NEXT_PUBLIC_API_URL || LOCAL_FALLBACK_API_BASE;
}
