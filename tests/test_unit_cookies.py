"""Unit tests for cookie handling: no network, no native library involved."""
import unittest

from tls_client.cookies import cookiejar_from_dict, extract_cookies_to_jar, merge_cookies
from tls_client.structures import CaseInsensitiveDict


class TestCookieJarFromDict(unittest.TestCase):

    def test_builds_jar_with_given_names_and_values(self):
        jar = cookiejar_from_dict({"session_id": "abc123", "theme": "dark"})

        self.assertEqual(jar.get("session_id"), "abc123")
        self.assertEqual(jar.get("theme"), "dark")

    def test_empty_dict_yields_empty_jar(self):
        jar = cookiejar_from_dict({})
        self.assertEqual(len(list(jar)), 0)


class TestMergeCookies(unittest.TestCase):

    def test_merges_dict_into_existing_jar(self):
        jar = cookiejar_from_dict({"a": "1"})
        merged = merge_cookies(jar, {"b": "2"})

        self.assertEqual(merged.get("a"), "1")
        self.assertEqual(merged.get("b"), "2")

    def test_new_value_overwrites_existing_cookie_with_same_name(self):
        jar = cookiejar_from_dict({"a": "1"})
        merged = merge_cookies(jar, {"a": "2"})

        self.assertEqual(merged.get("a"), "2")


class TestExtractCookiesToJar(unittest.TestCase):

    def test_extracts_set_cookie_header_into_jar(self):
        jar = cookiejar_from_dict({})
        response_cookie_jar = extract_cookies_to_jar(
            request_url="https://example.com/",
            request_headers=CaseInsensitiveDict({}),
            cookie_jar=jar,
            response_headers={"Set-Cookie": ["session_id=abc123; Path=/"]},
        )

        self.assertEqual(response_cookie_jar.get("session_id"), "abc123")
        # merge_cookies() inside extract_cookies_to_jar mutates the passed-in jar too
        self.assertEqual(jar.get("session_id"), "abc123")

    def test_no_set_cookie_header_yields_empty_jar(self):
        jar = cookiejar_from_dict({})
        response_cookie_jar = extract_cookies_to_jar(
            request_url="https://example.com/",
            request_headers=CaseInsensitiveDict({}),
            cookie_jar=jar,
            response_headers={},
        )

        self.assertEqual(len(list(response_cookie_jar)), 0)


if __name__ == "__main__":
    unittest.main()
