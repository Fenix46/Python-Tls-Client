"""Unit tests for Response / build_response: no network, no native library involved."""
import unittest

from tls_client.cookies import cookiejar_from_dict
from tls_client.response import Response, build_response


def _build(headers=None, body="hello", status=200):
    res = {"target": "https://example.com/", "status": status, "headers": headers, "body": body}
    return build_response(res, cookiejar_from_dict({}))


class TestResponseHeaders(unittest.TestCase):

    def test_headers_are_case_insensitive(self):
        response = _build(headers={"Content-Type": ["text/plain"]})
        self.assertEqual(response.headers["content-type"], "text/plain")

    def test_multi_value_headers_stay_lists(self):
        response = _build(headers={"Set-Cookie": ["a=1", "b=2"]})
        self.assertEqual(response.headers["set-cookie"], ["a=1", "b=2"])

    def test_null_headers_yield_empty_mapping(self):
        self.assertEqual(len(_build(headers=None).headers), 0)


class TestResponseBody(unittest.TestCase):

    def test_content_is_bytes_of_body(self):
        self.assertEqual(_build(body="hello").content, b"hello")

    def test_empty_response_has_empty_content(self):
        self.assertEqual(Response().content, b"")


class TestResponseContextManager(unittest.TestCase):

    def test_can_be_used_in_with_statement(self):
        with _build() as response:
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
