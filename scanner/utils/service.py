from urllib.parse import urljoin, urlparse
import requests

from scanner.browser.report import ACCESSIBILITY_USER_AGENT
from scanner.log import log_message
from utils.urls import is_safe_target

MAX_REDIRECTS = 5


def check_url(url: str) -> bool:
    """
    Check that a URL is well-formed, points at a public host, and responds with < 400.

    Redirects are followed by hand (at most MAX_REDIRECTS) so that every hop is checked
    with ``is_safe_target``; otherwise a public site could bounce the probe to an
    internal address.
    """

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        log_message(f"Checking URL accessibility: {url}", 'info')
        for _ in range(MAX_REDIRECTS + 1):
            if not is_safe_target(url):
                log_message(f"Refusing to probe non-public URL: {url}", 'warning')
                return False
            response = requests.get(
                url,
                timeout=10,
                allow_redirects=False,
                stream=True,
                headers={'User-Agent': ACCESSIBILITY_USER_AGENT},
            )
            try:
                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get('Location')
                    if not location:
                        return False
                    url = urljoin(url, location)
                    continue
                return response.status_code < 400
            finally:
                response.close()
        log_message(f"Too many redirects while checking URL {url}", 'warning')
        return False
    except Exception as e:
        log_message(f"Error checking URL {url}: {e}", 'error')
        return False
