"""The report script's URL guard: it must also run inside the preview frame, whose
URL carries the report URL percent-encoded."""
from utils.style_generator import report_to_js


def test_report_script_accepts_the_encoded_proxy_url():
    js = report_to_js([], "https://example.com/a b/")

    assert "const wanted = `https://example.com/a b/`" in js
    assert "currentUrl.includes(wanted) || currentUrl.includes(encodeURIComponent(wanted))" in js


def test_report_script_escapes_backticks_in_the_url():
    js = report_to_js([], "https://example.com/`x`")

    assert "const wanted = `https://example.com/\\`x\\``" in js


def test_report_script_checks_the_preview_address_first():
    # The preview frame moves to the page's own path before the script runs and keeps
    # its /proxy address in __a11yPreviewUrl (previewGuard in lib/proxyRewrite.ts).
    js = report_to_js([], "https://example.com/")

    assert "const currentUrl = window.__a11yPreviewUrl || window.location.href;" in js
