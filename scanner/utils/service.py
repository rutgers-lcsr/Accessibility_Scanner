


from urllib.parse import urlparse
import requests

from scanner.log import log_message
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_url(url:str) -> bool:
    """
    Check if a URL is valid and accessible.
    """
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        log_message(f"Checking URL accessibility: {url}", 'info')
        response = requests.get(url, timeout=10, allow_redirects=True, verify=False)
        return response.status_code < 400
    except Exception as e:
        log_message(f"Error checking URL {url}: {e}", 'error')
        return False