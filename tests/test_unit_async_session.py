"""Unit tests for AsyncSession, mocking the native cffi calls."""
import asyncio
import json
import unittest
from unittest.mock import patch

from tls_client import AsyncSession


def _fake_native_response(status=200, body="hello"):
    return json.dumps(
        {"id": "fake-id", "status": status, "body": body, "headers": {}, "target": "https://example.com/"}
    ).encode("utf-8")


class TestAsyncSession(unittest.TestCase):

    def setUp(self):
        for name in ("request", "freeMemory", "destroySession"):
            patcher = patch(f"tls_client.sessions.{name}")
            setattr(self, f"mock_{name}", patcher.start())
            self.addCleanup(patcher.stop)
        self.mock_request.return_value = _fake_native_response()
        self.mock_destroySession.return_value = b'{"id": "fake-id"}'

    def test_get_is_awaitable_and_returns_response(self):
        async def run():
            async with AsyncSession(client_identifier="chrome_120") as session:
                return await session.get("https://example.com/")

        response = asyncio.run(run())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "hello")

    def test_concurrent_requests_share_one_session(self):
        async def run():
            async with AsyncSession(client_identifier="chrome_120") as session:
                return await asyncio.gather(*(session.get("https://example.com/") for _ in range(5)))

        responses = asyncio.run(run())

        self.assertEqual(len(responses), 5)
        self.assertEqual(self.mock_request.call_count, 5)

    def test_async_context_manager_closes_session(self):
        async def run():
            async with AsyncSession(client_identifier="chrome_120") as session:
                pass
            return session

        session = asyncio.run(run())

        self.assertTrue(session._closed)
        self.mock_destroySession.assert_called_once()


if __name__ == "__main__":
    unittest.main()
