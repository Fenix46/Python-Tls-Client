"""Unit tests for Session.execute_request, mocking the native cffi calls.

These tests never touch the network or the compiled tls-client library: the
``request``/``freeMemory``/``destroySession`` functions imported into
``tls_client.sessions`` are patched directly, so they run in any environment
(including CI matrices for platforms whose binary isn't exercised).

Run with:  python -m unittest discover -s tests -p "test_unit_*.py" -v
"""
import base64
import json
import unittest
from unittest.mock import patch

from tls_client import Session
from tls_client.exceptions import (
    TLSClientCertificateError,
    TLSClientConnectionError,
    TLSClientExeption,
    TLSClientProxyError,
    TLSClientTimeoutError,
)


def _fake_native_response(status=200, body="hello", headers=None, target="https://example.com/"):
    payload = {
        "id": "fake-id",
        "status": status,
        "body": body,
        "headers": headers or {"Content-Type": ["text/plain"]},
        "target": target,
    }
    return json.dumps(payload).encode("utf-8")


class _PatchedCffiTestCase(unittest.TestCase):
    """Base class that patches the three native entry points used by Session."""

    def setUp(self):
        self.request_patcher = patch("tls_client.sessions.request")
        self.free_memory_patcher = patch("tls_client.sessions.freeMemory")
        self.destroy_session_patcher = patch("tls_client.sessions.destroySession")

        self.mock_request = self.request_patcher.start()
        self.mock_free_memory = self.free_memory_patcher.start()
        self.mock_destroy_session = self.destroy_session_patcher.start()

        self.addCleanup(self.request_patcher.stop)
        self.addCleanup(self.free_memory_patcher.stop)
        self.addCleanup(self.destroy_session_patcher.stop)

        self.mock_free_memory.return_value = b'{"id": "fake-id"}'
        self.mock_destroy_session.return_value = b'{"id": "fake-id"}'

        self.session = Session(client_identifier="chrome_120")
        self.session._closed = True  # skip native destroySession in tearDown/close

    def tearDown(self):
        self.session.close()


class TestExecuteRequestSuccess(_PatchedCffiTestCase):

    def test_get_builds_response_from_native_payload(self):
        self.mock_request.return_value = _fake_native_response(status=200, body="hello world")

        response = self.session.get("https://example.com/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "hello world")
        self.assertEqual(response.url, "https://example.com/")

    def test_request_payload_includes_session_id_and_method(self):
        self.mock_request.return_value = _fake_native_response()

        self.session.post("https://example.com/submit", json={"a": 1})

        sent_bytes = self.mock_request.call_args[0][0]
        sent_payload = json.loads(sent_bytes.decode("utf-8"))
        self.assertEqual(sent_payload["sessionId"], self.session._session_id)
        self.assertEqual(sent_payload["requestMethod"], "POST")
        self.assertEqual(sent_payload["requestUrl"], "https://example.com/submit")
        self.assertEqual(sent_payload["requestBody"], '{"a": 1}')

    def test_certificate_pinning_included_when_set(self):
        self.session.certificate_pinning = {"example.com": ["sha256/AAAA..."]}
        self.mock_request.return_value = _fake_native_response()

        self.session.get("https://example.com/")

        sent_payload = json.loads(self.mock_request.call_args[0][0].decode("utf-8"))
        self.assertEqual(
            sent_payload["certificatePinningHosts"], {"example.com": ["sha256/AAAA..."]}
        )

    def test_certificate_pinning_omitted_when_not_set(self):
        self.mock_request.return_value = _fake_native_response()

        self.session.get("https://example.com/")

        sent_payload = json.loads(self.mock_request.call_args[0][0].decode("utf-8"))
        self.assertNotIn("certificatePinningHosts", sent_payload)

    def test_binary_response_decoded_from_data_uri(self):
        raw = bytes(range(250, 256)) + b"\xff\xfe"
        data_uri = "data:application/octet-stream;base64," + base64.b64encode(raw).decode()
        self.mock_request.return_value = _fake_native_response(body=data_uri)

        response = self.session.get("https://example.com/binary")

        self.assertEqual(response.content, raw)

    def test_query_params_appended_to_url(self):
        self.mock_request.return_value = _fake_native_response()

        self.session.get("https://example.com/search", params={"q": "hello world"})

        sent_payload = json.loads(self.mock_request.call_args[0][0].decode("utf-8"))
        self.assertEqual(sent_payload["requestUrl"], "https://example.com/search?q=hello+world")

    def test_proxy_dict_extracts_http_key(self):
        self.mock_request.return_value = _fake_native_response()

        self.session.get(
            "https://example.com/",
            proxy={"http": "http://user:pass@127.0.0.1:8080"},
        )

        sent_payload = json.loads(self.mock_request.call_args[0][0].decode("utf-8"))
        self.assertEqual(sent_payload["proxyUrl"], "http://user:pass@127.0.0.1:8080")


class TestExecuteRequestErrors(_PatchedCffiTestCase):

    def _fail_with(self, message):
        payload = {"id": "fake-id", "status": 0, "body": message, "headers": {}, "target": ""}
        self.mock_request.return_value = json.dumps(payload).encode("utf-8")

    def test_timeout_message_raises_timeout_error(self):
        self._fail_with("context deadline exceeded")
        with self.assertRaises(TLSClientTimeoutError):
            self.session.get("https://example.com/")

    def test_proxy_message_raises_proxy_error(self):
        self._fail_with("proxyconnect tcp: dial tcp: connection refused")
        with self.assertRaises(TLSClientProxyError):
            self.session.get("https://example.com/")

    def test_dns_message_raises_connection_error(self):
        self._fail_with("dial tcp: lookup nonexistent.invalid: no such host")
        with self.assertRaises(TLSClientConnectionError):
            self.session.get("https://example.com/")

    def test_pinning_message_raises_certificate_error(self):
        self._fail_with("certificate pinning failed for host example.com")
        with self.assertRaises(TLSClientCertificateError):
            self.session.get("https://example.com/")

    def test_unknown_message_raises_base_exception(self):
        self._fail_with("something completely unexpected happened")
        with self.assertRaises(TLSClientExeption):
            self.session.get("https://example.com/")

    def test_typed_errors_are_still_catchable_as_base_exception(self):
        self._fail_with("context deadline exceeded")
        with self.assertRaises(TLSClientExeption):
            self.session.get("https://example.com/")


class TestSessionLifecycle(_PatchedCffiTestCase):

    def test_close_marks_session_closed_and_frees_memory(self):
        self.session._closed = False
        self.session.close()

        self.assertTrue(self.session._closed)
        self.mock_destroy_session.assert_called_once()
        self.mock_free_memory.assert_called_once()

    def test_context_manager_closes_session_on_exit(self):
        self.session._closed = False
        with self.session as s:
            self.assertIs(s, self.session)
        self.assertTrue(self.session._closed)

    def test_unclosed_session_warns_on_garbage_collection(self):
        session = Session(client_identifier="chrome_120")
        session._closed = False

        with self.assertWarns(ResourceWarning):
            session.__del__()


if __name__ == "__main__":
    unittest.main()
