"""Minimal, bounded browser/web access for Zoey.

This module deliberately provides only two capabilities:
- open_url: open an HTTP(S) URL in the user's default browser.
- fetch_url: bounded HTTP(S) text retrieval with no cookies or JavaScript.
"""

from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)


DEFAULT_MAX_CHARS = 8000
MAX_MAX_CHARS = 8000
MAX_RESPONSE_BYTES = 65536
REQUEST_TIMEOUT = 10
MAX_REDIRECTS = 3
_ALLOWED_SCHEMES = {"http", "https"}


class _RedirectLimitError(Exception):
    pass


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _BoundedHTTPClient:
    def __init__(self, max_redirects=MAX_REDIRECTS):
        self.max_redirects = max_redirects

    def fetch(self, request):
        current = request.full_url
        redirects = 0
        opener = build_opener(_NoRedirectHandler())

        while True:
            request = Request(
                current,
                headers={"User-Agent": "Zoey/10.5"},
                method="GET",
            )

            try:
                response = opener.open(request, timeout=REQUEST_TIMEOUT)
            except Exception as error:
                # urllib may expose an HTTPError for redirects when the
                # redirect handler declines the redirect. It still carries
                # the Location header and status, so handle it uniformly.
                status = getattr(error, "code", None)
                location = getattr(error, "headers", {}).get("Location") if getattr(error, "headers", None) else None
                if status not in (301, 302, 303, 307, 308) or not location:
                    raise
                response = error

            status = getattr(response, "status", None) or getattr(response, "code", None)
            location = response.headers.get("Location")

            if status in (301, 302, 303, 307, 308) and location:
                response.close()
                if redirects >= self.max_redirects:
                    raise _RedirectLimitError("Too many redirects.")
                target = urljoin(current, location)
                _validate_url(target)
                redirects += 1
                current = target
                continue

            return response


def _validate_url(url):
    if not isinstance(url, str):
        raise ValueError("url must be a string.")

    url = url.strip()
    if not url:
        raise ValueError("url cannot be empty.")
    if any(char.isspace() for char in url):
        raise ValueError("url cannot contain whitespace.")
    if "\x00" in url:
        raise ValueError("url contains an invalid null byte.")

    parsed = urlsplit(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError("Only http:// and https:// URLs are allowed.")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("URL must include a valid host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs with embedded credentials are not allowed.")

    return url


def open_url(url: str):
    """Open an HTTP(S) URL in the user's default browser."""
    from webbrowser import open as browser_open

    try:
        url = _validate_url(url)
        opened = browser_open(url)
        return {
            "success": bool(opened),
            "message": "Opened URL." if opened else "The browser did not open the URL.",
            "url": url,
        }
    except Exception as error:
        return {
            "success": False,
            "message": str(error),
        }


def fetch_url(url: str, max_chars=DEFAULT_MAX_CHARS):
    """Fetch bounded UTF-8-ish text from an HTTP(S) URL.

    No cookies, JavaScript, authentication, uploads, or arbitrary file
    downloads are supported. Response bytes and returned characters are capped.
    """
    try:
        url = _validate_url(url)

        if max_chars is None:
            max_chars = DEFAULT_MAX_CHARS
        if not isinstance(max_chars, int) or isinstance(max_chars, bool):
            raise ValueError("max_chars must be an integer.")
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than zero.")
        max_chars = min(max_chars, MAX_MAX_CHARS)

        request = Request(
            url,
            headers={"User-Agent": "Zoey/10.5"},
            method="GET",
        )
        client = _BoundedHTTPClient()

        with client.fetch(request) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > MAX_RESPONSE_BYTES:
                        raise ValueError("Response is too large.")
                except ValueError as error:
                    if str(error) == "Response is too large.":
                        raise

            chunks = []
            total = 0
            while total < MAX_RESPONSE_BYTES:
                chunk = response.read(min(8192, MAX_RESPONSE_BYTES - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)

            if total >= MAX_RESPONSE_BYTES:
                extra = response.read(1)
                if extra:
                    raise ValueError("Response is too large.")

            raw = b"".join(chunks)
            content_type = response.headers.get("Content-Type", "")
            charset = "utf-8"
            lowered = content_type.lower()
            marker = "charset="
            if marker in lowered:
                charset = lowered.split(marker, 1)[1].split(";", 1)[0].strip() or "utf-8"

            text = raw.decode(charset, errors="replace")
            return {
                "success": True,
                "url": url,
                "content": text[:max_chars],
                "truncated": len(text) > max_chars,
            }
    except Exception as error:
        return {
            "success": False,
            "message": str(error),
        }
