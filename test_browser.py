import io
import sys
from unittest.mock import patch

from tools import browser
from core.agent_loop import ALLOWED_TOOLS, TOOLS as TOOL_DOC
from core.step_validation import validate_step
from core.tool_manager import TOOLS


def assert_false(result):
    assert result["success"] is False, result


def test_url_validation():
    for url in ("file:///C:/secret", "data:text/plain,hello", "smb://server/share", "ftp://example.com"):
        assert_false(browser.fetch_url(url))
        assert_false(browser.open_url(url))

    assert_false(browser.fetch_url("not a url"))
    assert_false(browser.fetch_url("https://user:pass@example.com"))
    assert browser._validate_url("https://example.com/path") == "https://example.com/path"


def test_open_url_is_mocked():
    with patch("webbrowser.open", return_value=True) as opened:
        result = browser.open_url("https://example.com")
    assert result["success"] is True
    opened.assert_called_once_with("https://example.com")


def test_fetch_is_bounded_and_decodes():
    class Headers(dict):
        def get_content_charset(self):
            return "utf-8"

    class Response(io.BytesIO):
        def __init__(self, data):
            super().__init__(data)
            self.headers = Headers({"Content-Type": "text/plain; charset=utf-8"})
            self.status = 200
        def __enter__(self): return self
        def __exit__(self, *args): self.close()

    with patch("tools.browser.build_opener") as build:
        class Opener:
            def open(self, *args, **kwargs):
                return Response(b"abcdefghij")
        build.return_value = Opener()
        result = browser.fetch_url("https://example.com", max_chars=5)
    assert result["success"] is True
    assert result["content"] == "abcde"
    assert result["truncated"] is True


def test_redirect_limit():
    class Headers(dict): pass
    class Response(io.BytesIO):
        def __init__(self, location):
            super().__init__(b"")
            self.headers = Headers({"Location": location})
            self.status = 302
            self.code = 302
        def close(self): super().close()

    class Opener:
        def open(self, request, timeout):
            return Response("https://example.com/loop")

    with patch("tools.browser.build_opener", return_value=Opener()):
        result = browser.fetch_url("https://example.com")
    assert_false(result)
    assert "redirect" in result["message"].lower()


def test_response_size_cap():
    class Headers(dict): pass
    class Response(io.BytesIO):
        def __init__(self):
            super().__init__(b"x" * (browser.MAX_RESPONSE_BYTES + 1))
            self.headers = Headers()
            self.status = 200
        def __enter__(self): return self
        def __exit__(self, *args): self.close()

    class Opener:
        def open(self, *args, **kwargs): return Response()

    with patch("tools.browser.build_opener", return_value=Opener()):
        result = browser.fetch_url("https://example.com")
    assert_false(result)
    assert "too large" in result["message"].lower()


def test_tool_sync_and_validation():
    assert "open_url" in TOOLS
    assert "fetch_url" in TOOLS
    assert "open_url" in ALLOWED_TOOLS
    assert "fetch_url" in ALLOWED_TOOLS
    assert "21. open_url" in TOOL_DOC
    assert "22. fetch_url" in TOOL_DOC

    valid = validate_step({"tool": "fetch_url", "arguments": {"url": "https://example.com", "max_chars": 100}})
    assert valid["valid"] is True
    invalid = validate_step({"tool": "fetch_url", "arguments": {"url": "https://example.com", "max_chars": "100"}})
    assert invalid["valid"] is False


def run():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"test_browser.py: {len(tests)} tests passed")


if __name__ == "__main__":
    run()
