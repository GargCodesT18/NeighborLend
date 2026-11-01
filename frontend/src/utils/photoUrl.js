const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
const apiOrigin = apiBaseUrl.startsWith('http')
  ? new URL(apiBaseUrl).origin
  : '';
const LOCAL_UPLOAD_URL = /^https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?(?=\/uploads\/)/i;

export function resolvePhotoUrl(url) {
  if (typeof url !== 'string') return '';
  if (LOCAL_UPLOAD_URL.test(url)) return apiOrigin ? url.replace(LOCAL_UPLOAD_URL, apiOrigin) : url.replace(LOCAL_UPLOAD_URL, '');
  if (url.startsWith('/uploads/') && apiOrigin) return `${apiOrigin}${url}`;
  return url;
}
