


from urllib.parse import urlparse
import requests


def check_url(url):
    """
    Check if a URL is valid and accessible.
    """
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        response = requests.head(url, timeout=5)
        return response.status_code < 400
    except Exception:
        return False