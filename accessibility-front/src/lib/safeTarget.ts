// Server-only helpers for fetching user-influenced URLs. Mirrors utils/urls.is_safe_target
// on the backend: a URL may only be fetched when its host resolves to public addresses,
// and redirects are followed one hop at a time so every hop is checked.
import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';
import dns from 'dns/promises';
import net from 'net';

const blockList = new net.BlockList();
const IPV4_BLOCKED: ReadonlyArray<readonly [string, number]> = [
    ['0.0.0.0', 8], // "this" network
    ['10.0.0.0', 8],
    ['100.64.0.0', 10], // carrier-grade NAT
    ['127.0.0.0', 8],
    ['169.254.0.0', 16], // link-local, cloud metadata
    ['172.16.0.0', 12],
    ['192.0.0.0', 24],
    ['192.168.0.0', 16],
    ['224.0.0.0', 4], // multicast
    ['240.0.0.0', 4], // reserved + broadcast
];
for (const [address, prefix] of IPV4_BLOCKED) {
    blockList.addSubnet(address, prefix, 'ipv4');
}
blockList.addAddress('::', 'ipv6');
blockList.addAddress('::1', 'ipv6');
blockList.addSubnet('fc00::', 7, 'ipv6'); // unique local
blockList.addSubnet('fe80::', 10, 'ipv6'); // link-local
blockList.addSubnet('ff00::', 8, 'ipv6'); // multicast

function isPublicAddress(address: string): boolean {
    const mapped = address.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/i);
    if (mapped) {
        address = mapped[1];
    }
    const family = net.isIP(address);
    if (family === 4) return !blockList.check(address, 'ipv4');
    if (family === 6) return !blockList.check(address, 'ipv6');
    return false;
}

const CACHE_MS = 10 * 60 * 1000;
const hostCache = new Map<string, { ok: boolean; expires: number }>();

/** True when `url` is http(s) and every address its host resolves to is public. */
export async function isSafeTarget(url: string): Promise<boolean> {
    let parsed: URL;
    try {
        parsed = new URL(url);
    } catch {
        return false;
    }
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        return false;
    }
    let host = parsed.hostname;
    if (host.startsWith('[') && host.endsWith(']')) {
        host = host.slice(1, -1);
    }
    if (!host) {
        return false;
    }
    if (net.isIP(host)) {
        return isPublicAddress(host);
    }

    const cached = hostCache.get(host);
    if (cached && cached.expires > Date.now()) {
        return cached.ok;
    }
    let ok = false;
    try {
        const records = await dns.lookup(host, { all: true });
        ok = records.length > 0 && records.every((record) => isPublicAddress(record.address));
    } catch {
        ok = false;
    }
    hostCache.set(host, { ok, expires: Date.now() + CACHE_MS });
    return ok;
}

export class UnsafeTargetError extends Error {}

const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);

/**
 * GET `url`, refusing the request (and any redirect hop) whose host is not public.
 * Certificates are verified; a bad certificate surfaces as an axios error (502 upstream).
 */
export async function fetchPublicUrl(
    url: string,
    config: AxiosRequestConfig = {},
    maxRedirects = 5
): Promise<AxiosResponse> {
    for (let hop = 0; hop <= maxRedirects; hop++) {
        if (!(await isSafeTarget(url))) {
            throw new UnsafeTargetError(`Refusing to fetch non-public URL: ${url}`);
        }
        const response = await axios.get(url, {
            ...config,
            maxRedirects: 0,
            validateStatus: () => true,
        });
        const location = response.headers?.location;
        if (REDIRECT_STATUSES.has(response.status) && location) {
            url = new URL(String(location), url).href;
            continue;
        }
        return response;
    }
    throw new UnsafeTargetError(`Too many redirects: ${url}`);
}
