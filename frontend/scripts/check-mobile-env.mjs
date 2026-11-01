import { isIP } from 'node:net';

const apiUrl = process.env.VITE_API_BASE_URL?.trim();

if (!apiUrl) {
  console.error('VITE_API_BASE_URL is required for a mobile build. Set it to the deployed HTTPS API base, for example https://api.example.com/api.');
  process.exit(1);
}

let parsed;
try {
  parsed = new URL(apiUrl);
} catch {
  console.error('VITE_API_BASE_URL must be an absolute HTTPS URL.');
  process.exit(1);
}

const hostname = parsed.hostname.toLowerCase().replace(/\.$/, '').replace(/^\[|\]$/g, '');
const apiPath = parsed.pathname.replace(/\/+$/, '');
const ipv4Parts = hostname.split('.').map(Number);
const isIpv4 = isIP(hostname) === 4;
const privateIpv4 = isIpv4 && (
  ipv4Parts[0] === 0 || ipv4Parts[0] === 10 || ipv4Parts[0] === 127 ||
  (ipv4Parts[0] === 169 && ipv4Parts[1] === 254) ||
  (ipv4Parts[0] === 172 && ipv4Parts[1] >= 16 && ipv4Parts[1] <= 31) ||
  (ipv4Parts[0] === 192 && ipv4Parts[1] === 168) ||
  (ipv4Parts[0] === 100 && ipv4Parts[1] >= 64 && ipv4Parts[1] <= 127) ||
  (ipv4Parts[0] === 192 && ipv4Parts[1] === 0 && ipv4Parts[2] === 2) ||
  (ipv4Parts[0] === 198 && [18, 19, 51].includes(ipv4Parts[1])) ||
  (ipv4Parts[0] === 203 && ipv4Parts[1] === 0 && ipv4Parts[2] === 113)
);
const ipv6Local = isIP(hostname) === 6 && (
  hostname === '::' || hostname === '::1' ||
  /^(fc|fd|fe[89ab])/.test(hostname)
);
const placeholderOrLocalDomain = hostname === 'localhost' ||
  /\.(localhost|local|internal|test|invalid|home|lan)$/.test(hostname) ||
  hostname === 'example.com' || hostname.endsWith('.example.com') ||
  hostname === 'example.net' || hostname.endsWith('.example.net') ||
  hostname === 'example.org' || hostname.endsWith('.example.org');

if (parsed.protocol !== 'https:' || privateIpv4 || ipv6Local || placeholderOrLocalDomain) {
  console.error('Mobile builds require a deployed public HTTPS API host; local, private, and example hosts are not allowed.');
  process.exit(1);
}

if (!apiPath.endsWith('/api')) {
  console.error('VITE_API_BASE_URL must end in /api so frontend requests reach the FastAPI routes.');
  process.exit(1);
}

if (parsed.username || parsed.password || parsed.search || parsed.hash) {
  console.error('VITE_API_BASE_URL must not contain credentials, query parameters, or fragments; keep API secrets on the backend.');
  process.exit(1);
}
