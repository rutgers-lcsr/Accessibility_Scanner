# Standarize Url parse for all of the application
from urllib.parse import urlparse
import socket

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
