"""Regression test for the binary response corruption bug.

The Go backend (C library) used to mangle bytes > 127 in response bodies via a
UTF-8 byteReplacer (U+FFFD), corrupting binary payloads (protobuf, images, ...).

The fix sets ``isByteResponse: True`` on the request payload so the backend
returns the body as a base64 data-URI, which ``response.py`` decodes back to
raw bytes.

Run with:  python -m pytest tests/ -v
           (or:  python tests/test_binary_response.py)
"""
import base64
import unittest

from tls_client import Session


def _unescape_httpbin_data(d: str) -> bytes:
    """httpbin /post echoes a binary body as a data-URI inside the JSON.

    Text bodies come back as plain strings.
    """
    if isinstance(d, str) and d.startswith("data:"):
        return base64.b64decode(d.split(",", 1)[1])
    return d.encode("utf-8")


class TestBinaryResponse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.session = Session(client_identifier="okhttp4_android_12")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def test_get_binary_png(self):
        """GET a PNG: magic bytes and length must be intact, no U+FFFD."""
        r = self.session.get("https://httpbin.org/image/png")
        content = r.content
        self.assertEqual(r.status_code, 200)
        self.assertEqual(content[:4], b"\x89PNG")
        self.assertEqual(len(content), 8090)
        self.assertEqual(content.count(b"\xef\xbf\xbd"), 0)

    def test_get_json(self):
        r = self.session.get("https://httpbin.org/get?nome=Mario")
        self.assertEqual(r.json()["args"], {"nome": "Mario"})

    def test_post_binary_roundtrip(self):
        """POST 1024 bytes covering 0x00-0xFF: must roundtrip exactly."""
        payload = bytes(range(256)) * 4
        r = self.session.post(
            "https://httpbin.org/post",
            data=payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        echoed = _unescape_httpbin_data(r.json()["data"])
        self.assertEqual(echoed, payload)

    def test_post_protobuf_like(self):
        """POST a protobuf-like binary with multi-byte UTF-8 + high bytes."""
        proto_like = bytes.fromhex("0a" + "c3a9" * 50 + "12" + "ff" * 100)
        r = self.session.post(
            "https://httpbin.org/post",
            data=proto_like,
            headers={"Content-Type": "application/protobuf"},
        )
        self.assertEqual(_unescape_httpbin_data(r.json()["data"]), proto_like)

    def test_post_json(self):
        r = self.session.post("https://httpbin.org/post", json={"token": "abc123", "n": 42})
        self.assertEqual(r.json()["json"], {"token": "abc123", "n": 42})

    def test_text_attribute_is_str(self):
        r = self.session.get("https://httpbin.org/image/png")
        self.assertIsInstance(r.text, str)


if __name__ == "__main__":
    unittest.main()
