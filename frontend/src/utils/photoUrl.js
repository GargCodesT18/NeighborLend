const apiBaseUrl = import.meta.env?.VITE_API_BASE_URL || '/api';

function getApiOrigin(baseUrl) {
  if (!/^https?:\/\//i.test(baseUrl)) return '';
  try {
    return new URL(baseUrl).origin;
  } catch {
    return '';
  }
}

function isLocalOrPrivateHost(hostname) {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, '').replace(/\.$/, '');
  if (host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local')) return true;
  if (host === '::1' || host === '0.0.0.0') return true;

  const octets = host.split('.').map(Number);
  if (octets.length !== 4 || octets.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
    return host.includes(':')
      && (host.startsWith('fe80:') || host.startsWith('fc') || host.startsWith('fd'));
  }
  return octets[0] === 10
    || octets[0] === 127
    || octets[0] === 0
    || (octets[0] === 169 && octets[1] === 254)
    || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
    || (octets[0] === 192 && octets[1] === 168);
}

export function createPhotoUrlResolver(baseUrl = '/api') {
  const apiOrigin = getApiOrigin(baseUrl);
  return function resolvePhotoUrl(url) {
    if (typeof url !== 'string' || !url.trim()) return '';
    const value = url.trim();

    if (value.startsWith('/uploads/')) {
      return apiOrigin ? `${apiOrigin}${value}` : value;
    }

    try {
      const parsed = new URL(value);
      if (parsed.pathname.startsWith('/uploads/') && isLocalOrPrivateHost(parsed.hostname)) {
        return apiOrigin
          ? `${apiOrigin}${parsed.pathname}${parsed.search}${parsed.hash}`
          : `${parsed.pathname}${parsed.search}${parsed.hash}`;
      }
    } catch {
      return value;
    }

    // Supabase public URLs and other absolute image URLs pass through unchanged.
    return value;
  };
}

export const resolvePhotoUrl = createPhotoUrlResolver(apiBaseUrl);
