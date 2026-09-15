# Standarize Url parse for all of the application
from functools import lru_cache
from urllib.parse import urlparse
import ipaddress
import socket

# Ranges that ipaddress does not flag as private but must never be fetched server-side.
_BLOCKED_NETWORKS = (
    ipaddress.ip_network("100.64.0.0/10"),  # carrier-grade NAT
)


def _is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    return not any(ip in network for network in _BLOCKED_NETWORKS)


@lru_cache(maxsize=2048)
def _resolves_to_public(hostname: str, port: int) -> bool:
    """True when every address ``hostname`` resolves to is public. Cached per process."""
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return False
    if not infos:
        return False
    return all(_is_public_address(info[4][0]) for info in infos)


def is_safe_target(url: str) -> bool:
    """True when ``url`` is http(s) and its host resolves only to public addresses.

    Checked before the API or the scanner fetches a user-supplied URL, so a website
    entry or a redirect on a scanned page cannot point the server at loopback, private,
    link-local or cloud-metadata addresses.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not hostname:
        return False
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return _resolves_to_public(hostname, port)


def is_valid_domain(domain: str) -> bool:
    """
    Check if a domain is valid
    """
    try:
        # Check if the domain can be resolved
        socket.gethostbyname(domain)
        return True
    except socket.error:
        return False


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid
    """
    try:
        result = urlparse(url)

        if not is_valid_domain(result.netloc):
            return False
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """Canonical form used for crawl de-duplication and Site lookups.

    Scheme and host are lowercased, a default port is dropped, and the fragment and
    query are removed (the crawler never follows query variants). The path is kept
    exactly as given, trailing slash included, so existing Site rows keep matching.
    """
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if ":" in host:  # bare IPv6 literal
        host = f"[{host}]"
    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    path = parsed.path or "/"
    return f"{scheme}://{host}{path}"


def get_website_url(url:str):
    """
    Returns the website URL from a given URL
    """
    parsed = urlparse(url)
    if not all([parsed.scheme, parsed.netloc]):
        raise ValueError("Invalid URL")
    return f"{parsed.scheme}://{parsed.netloc}"

def get_full_url(url:str):
    """
    Returns the full Url, url must include a schema

    Ex: https://www.example.com/example
    """
    
    parsed = urlparse(url)
    if not all([parsed.scheme, parsed.netloc]):
        raise ValueError("Invalid URL")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

def get_netloc(url:str):
    """
    Returns the netloc for a URL

    Ex: www.example.com
    """
    
    if url.startswith('http://') or url.startswith('https://'):
        parsed = urlparse(url)

        return f"{parsed.netloc}"
        
    netloc = urlparse(f"https://{url}").netloc

    return netloc

def get_site_netloc(url):
    """
    Returns the full site URL and Path from a string

    Ex: www.example.com/example
    """

    base_url = get_netloc(url)
    parsed = urlparse(url)
    return f"{base_url}{parsed.path}"
