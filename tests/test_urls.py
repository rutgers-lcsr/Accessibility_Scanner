"""Tests for the server-side fetch guard (utils.urls.is_safe_target, check_url)."""
import socket
import types

import pytest

import scanner.utils.service as service
import utils.urls as urls


@pytest.fixture(autouse=True)
def _clear_dns_cache():
    urls._resolves_to_public.cache_clear()
    yield
    urls._resolves_to_public.cache_clear()


def _fake_getaddrinfo(address):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    return lambda host, port, **kw: [(family, socket.SOCK_STREAM, 6, "", (address, port))]


# --- literal addresses need no DNS -------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.1.2.3:5000/health",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://172.16.5.5/",
        "http://192.168.1.1/",
        "http://100.64.1.1/",
        "http://0.0.0.0/",
        "http://224.0.0.1/",
        "ftp://93.184.216.34/",
        "file:///etc/passwd",
        "not a url",
        "",
    ],
)
def test_non_public_or_non_http_targets_are_rejected(url):
    assert urls.is_safe_target(url) is False


@pytest.mark.parametrize("url", ["https://93.184.216.34/", "http://8.8.8.8:8080/path?q=1"])
def test_public_literal_addresses_are_allowed(url):
    assert urls.is_safe_target(url) is True


# --- hostnames are resolved and every address checked ------------------------------


def test_hostname_resolving_to_private_address_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("10.1.2.3"))
    assert urls.is_safe_target("https://intranet.example/") is False


def test_hostname_resolving_to_public_address_is_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    assert urls.is_safe_target("https://www.example.com/") is True


def test_hostname_with_any_private_address_is_rejected(monkeypatch):
    def mixed(host, port, **kw):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", mixed)
    assert urls.is_safe_target("https://dual.example/") is False


def test_unresolvable_hostname_is_rejected(monkeypatch):
    def fail(host, port, **kw):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    assert urls.is_safe_target("https://nope.invalid/") is False


# --- check_url follows redirects one hop at a time --------------------------------


class _Resp:
    def __init__(self, status, location=None):
        self.status_code = status
        self.headers = {"Location": location} if location else {}
        self.is_redirect = status in (301, 302, 303, 307, 308) and location is not None
        self.is_permanent_redirect = status in (301, 308) and location is not None

    def close(self):
        pass


def _requests_get(responses):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs["allow_redirects"] is False
        return responses[url]

    return fake_get, calls


def test_check_url_accepts_public_site(monkeypatch):
    fake_get, calls = _requests_get({"http://8.8.8.8/": _Resp(200)})
    monkeypatch.setattr(service.requests, "get", fake_get)
    assert service.check_url("http://8.8.8.8/") is True
    assert calls == ["http://8.8.8.8/"]


def test_check_url_rejects_error_status(monkeypatch):
    fake_get, _ = _requests_get({"http://8.8.8.8/": _Resp(503)})
    monkeypatch.setattr(service.requests, "get", fake_get)
    assert service.check_url("http://8.8.8.8/") is False


def test_check_url_follows_redirect_to_public_host(monkeypatch):
    fake_get, calls = _requests_get(
        {"http://8.8.8.8/": _Resp(301, "https://8.8.4.4/home"), "https://8.8.4.4/home": _Resp(200)}
    )
    monkeypatch.setattr(service.requests, "get", fake_get)
    assert service.check_url("http://8.8.8.8/") is True
    assert calls == ["http://8.8.8.8/", "https://8.8.4.4/home"]


def test_check_url_refuses_redirect_to_private_host(monkeypatch):
    fake_get, calls = _requests_get(
        {"http://8.8.8.8/": _Resp(302, "http://127.0.0.1:3306/"), "http://127.0.0.1:3306/": _Resp(200)}
    )
    monkeypatch.setattr(service.requests, "get", fake_get)
    assert service.check_url("http://8.8.8.8/") is False
    # the private hop is never requested
    assert calls == ["http://8.8.8.8/"]


def test_check_url_refuses_private_start(monkeypatch):
    fake_get, calls = _requests_get({})
    monkeypatch.setattr(service.requests, "get", fake_get)
    assert service.check_url("http://169.254.169.254/") is False
    assert calls == []


def test_check_url_gives_up_on_redirect_loops(monkeypatch):
    fake_get, calls = _requests_get({"http://8.8.8.8/": _Resp(302, "http://8.8.8.8/")})
    monkeypatch.setattr(service.requests, "get", fake_get)
    assert service.check_url("http://8.8.8.8/") is False
    assert len(calls) == service.MAX_REDIRECTS + 1
