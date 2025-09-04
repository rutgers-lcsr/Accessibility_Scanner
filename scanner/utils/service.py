


from urllib.parse import urlparse
import requests

from scanner.log import log_message


def check_url(url):
    """
    Check if a URL is valid and accessible.
    """
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        response = requests.head(url, timeout=5, allow_redirects=True, verify=False)
        return response.status_code < 400
    except Exception as e:
        log_message(f"Error checking URL {url}: {e}", 'error')
        return False