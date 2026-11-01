import { isIP } from 'node:net';

const apiUrl = process.env.VITE_API_BASE_URL?.trim();

if (!apiUrl) {
  console.error('VITE_API_BASE_URL is required for a public website build; set it to the deployed HTTPS API URL ending in /api.');
  process.exit(1);
}

let parsed;
try {
  parsed = new URL(apiUrl);
} catch {
  console.error('VITE_API_BASE_URL must be an absolute HTTPS URL.');
  process.exit(1);
}

const host = parsed.hostname.toLowerCase().replace(/\.$/, '').replace(/^\[|\]$/g, '');
const ipv4Parts = host.split('.').map(Number);
const privateIpv4 = isIP(host) === 4 && (
  ipv4Parts[0] === 0 || ipv4Parts[0] === 10 || ipv4Parts[0] === 127 ||
  (ipv4Parts[0] === 169 && ipv4Parts[1] === 254) ||
  (ipv4Parts[0] === 172 && ipv4Parts[1] >= 16 && ipv4Parts[1] <= 31) ||
  (ipv4Parts[0] === 192 && ipv4Parts[1] === 168) ||
  (ipv4Parts[0] === 100 && ipv4Parts[1] >= 64 && ipv4Parts[1] <= 127)
);
const localIpv6 = isIP(host) === 6 && (host === '::' || host === '::1' || /^(fc|fd|fe[89ab])/.test(host));
const localName = host === 'localhost' ||
  /\.(localhost|local|internal|test|invalid|home|lan)$/.test(host) ||
  host === 'example.com' || host.endsWith('.example.com') ||
  host === 'example.net' || host.endsWith('.example.net') ||
  host === 'example.org' || host.endsWith('.example.org');
const path = parsed.pathname.replace(/\/+$/, '');

if (parsed.protocol !== 'https:' || privateIpv4 || localIpv6 || localName || !path.endsWith('/api')) {
  console.error('Public website builds require a deployed HTTPS API URL whose path ends in /api.');
  process.exit(1);
}

if (parsed.username || parsed.password || parsed.search || parsed.hash) {
  console.error('VITE_API_BASE_URL must not contain credentials, query parameters, or fragments.');
  process.exit(1);
}
