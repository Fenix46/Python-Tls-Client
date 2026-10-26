
import re


class TLSClientExeption(IOError):
    """General error with the TLS client"""


class TLSClientTimeoutError(TLSClientExeption):
    """The request did not complete within ``timeout_seconds``."""


class TLSClientProxyError(TLSClientExeption):
    """The proxy refused the connection, timed out, or rejected the credentials."""


class TLSClientConnectionError(TLSClientExeption):
    """The connection to the target host could not be established (DNS, TCP, TLS handshake)."""


class TLSClientCertificateError(TLSClientExeption):
    """The server certificate did not match the configured certificate pin."""


# Regexes searched (case-insensitively) in the Go backend's error message
# to classify it into one of the typed exceptions above. The backend
# (bogdanfinn/tls-client) does not expose a structured error code, only this
# free-text message, so this is best-effort pattern matching kept close to
# the strings the Go client is known to emit.
_ERROR_PATTERNS = (
    # Chain verification failures (x509: ... unknown authority, expired, ...)
    # are TLS handshake failures, not pin mismatches, so they come first.
    (r"x509", TLSClientConnectionError),
    (r"certificate", TLSClientCertificateError),
    (r"\bpin(ned|ning)?\b", TLSClientCertificateError),
    (r"proxy", TLSClientProxyError),
    (r"timeout", TLSClientTimeoutError),
    (r"deadline exceeded", TLSClientTimeoutError),
    (r"no such host", TLSClientConnectionError),
    (r"connection refused", TLSClientConnectionError),
    (r"connection reset", TLSClientConnectionError),
    (r"dial tcp", TLSClientConnectionError),
    (r"\beof\b", TLSClientConnectionError),
)


def build_exception(message: str) -> TLSClientExeption:
    """Map a Go backend error message to the most specific matching exception.

    Falls back to the base ``TLSClientExeption`` when nothing matches, so
    callers that only catch the base class keep working unchanged.
    """
    lowered = (message or "").lower()
    for pattern, exception_cls in _ERROR_PATTERNS:
        if re.search(pattern, lowered):
            return exception_cls(message)
    return TLSClientExeption(message)
