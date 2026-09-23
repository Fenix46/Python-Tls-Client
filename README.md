# Python-TLS-Client

Advanced Python HTTP client with TLS fingerprint spoofing, built on
[bogdanfinn/tls-client](https://github.com/bogdanfinn/tls-client) and inspired
by [requests](https://github.com/psf/requests).

> **Fork notice:** this is a fork of
> [Python-Tls-Client](https://github.com/FlorianREGAZ/Python-Tls-Client) by
> Florian Zager, published on PyPI under a different name
> (`python-tls-client`) because the original name `tls-client` is already
> taken by an unrelated project. The importable module is unchanged:
> `import tls_client`.
>
> Changes on top of the original:
> - Fixed corruption of binary response bodies (protobuf, images, ...) — see [Changelog](#changelog) 1.0.2 / 1.0.3
> - Certificate pinning — see [Changelog](#changelog) 1.0.1
> - Typed exceptions, safer session lifecycle, clearer native-library load errors — see [Changelog](#changelog) (Unreleased)
> - Native binaries updated to `bogdanfinn/tls-client` v1.16.0 (Chrome 150/152, Firefox 147/148, Brave 146, HTTP/3 over SOCKS5, session ticket control, ...) — see [Changelog](#changelog) (Unreleased)

## Installation

```bash
pip install python-tls-client
```

## Quick start

The API is intentionally close to [requests](https://github.com/psf/requests),
so most of what you already know carries over directly.

```python
import tls_client

session = tls_client.Session(
    client_identifier="chrome_150",
    random_tls_extension_order=True,
)

response = session.get(
    "https://www.example.com/",
    headers={"key1": "value1"},
    proxy="http://user:password@host:port",
)

print(response.status_code, response.text)
```

Available `client_identifier` presets (see `tls_client/settings.py` for the
full, up-to-date list — kept in sync with the
[`MappedTLSClients`](https://github.com/bogdanfinn/tls-client/blob/v1.16.0/profiles/profiles.go)
map of the native library version shipped in `tls_client/dependencies/`,
currently v1.16.0):

| Browser  | Identifiers |
|----------|-------------|
| Chrome   | `chrome_103`...`chrome_112`, `chrome_116_PSK`, `chrome_116_PSK_PQ`, `chrome_117`, `chrome_120`, `chrome_124`, `chrome_130_PSK`, `chrome_131(_PSK)`, `chrome_133(_PSK)`, `chrome_144(_PSK)`, `chrome_146(_PSK)`, `chrome_150(_PSK)`, `chrome_152(_PSK)` |
| Brave    | `brave_146`, `brave_146_PSK` |
| Firefox  | `firefox_102`...`firefox_110`, `firefox_117`, `firefox_120`, `firefox_123`, `firefox_132`, `firefox_133`, `firefox_135`, `firefox_146_PSK`, `firefox_147(_PSK)`, `firefox_148` |
| Opera    | `opera_89`, `opera_90`, `opera_91` |
| Safari   | `safari_15_6_1`, `safari_16_0` |
| iOS      | `safari_ios_15_5`, `safari_ios_15_6`, `safari_ios_16_0`, `safari_ios_17_0`, `safari_ios_18_0`, `safari_ios_18_5`, `safari_ios_26_0` |
| iPadOS   | `safari_ipad_15_6` |
| Android  | `okhttp4_android_7` through `okhttp4_android_13` |

> Only `chrome_144`, `chrome_144_PSK`, `firefox_147`, `firefox_147_PSK` and
> `firefox_148` carry an HTTP/3 fingerprint matching the real browser; every
> other profile sends a minimal, non-representative SETTINGS frame if you
> end up negotiating HTTP/3. This doesn't affect the TLS or HTTP/2
> fingerprint. Use `disable_http3=True` (see below) if the HTTP/3 fingerprint
> matters and you're not using one of those five profiles.

## Releasing the session

Every `Session` holds native resources (a connection pool) in the underlying
Go library that must be released explicitly. Always use the context manager,
or call `.close()` yourself:

```python
with tls_client.Session(client_identifier="chrome_150") as session:
    response = session.get("https://www.example.com/")
# session is closed automatically here
```

If you forget, the session emits a `ResourceWarning` and does a best-effort
cleanup when it is garbage collected — but that isn't guaranteed to run
promptly (or at all), so don't rely on it in production code.

## Custom TLS fingerprint

Instead of a `client_identifier` preset, you can fully customize the TLS/HTTP2
fingerprint:

```python
import tls_client

session = tls_client.Session(
    ja3_string=(
        "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-"
        "156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0"
    ),
    h2_settings={
        "HEADER_TABLE_SIZE": 65536,
        "MAX_CONCURRENT_STREAMS": 1000,
        "INITIAL_WINDOW_SIZE": 6291456,
        "MAX_HEADER_LIST_SIZE": 262144,
    },
    h2_settings_order=[
        "HEADER_TABLE_SIZE",
        "MAX_CONCURRENT_STREAMS",
        "INITIAL_WINDOW_SIZE",
        "MAX_HEADER_LIST_SIZE",
    ],
    supported_signature_algorithms=[
        "ECDSAWithP256AndSHA256",
        "PSSWithSHA256",
        "PKCS1WithSHA256",
        "ECDSAWithP384AndSHA384",
        "PSSWithSHA384",
        "PKCS1WithSHA384",
        "PSSWithSHA512",
        "PKCS1WithSHA512",
    ],
    supported_versions=["GREASE", "1.3", "1.2"],
    key_share_curves=["GREASE", "X25519"],
    cert_compression_algo="brotli",
    pseudo_header_order=[":method", ":authority", ":scheme", ":path"],
    connection_flow=15663105,
    header_order=["accept", "user-agent", "accept-encoding", "accept-language"],
)

response = session.post(
    "https://www.example.com/",
    headers={"key1": "value1"},
    json={"key1": "key2"},
)
```

### Additional fingerprint and connection controls (v1.16.0+)

```python
import tls_client

session = tls_client.Session(
    client_identifier="chrome_150",
    # Disable TLS session ticket caching/resumption
    disable_session_tickets=True,
    # Force HTTP/2, even for a profile that would otherwise try HTTP/3
    disable_http3=True,
)
```

For a custom client (`client_identifier=None`), you can additionally set:

```python
session = tls_client.Session(
    client_identifier=None,
    ja3_string="...",
    alpn_protocols=["h2", "http/1.1"],
    alps_protocols=["h2"],
    # Required if ja3_string lists TLS extension 51764 (trust_anchors)
    trust_anchors_payload="...",
)
```

## Certificate pinning

Restrict which server certificates are accepted for given hosts by passing
their pinned public key hashes (SPKI, base64-encoded SHA-256 — the same
format used by HPKP `pin-sha256` and most certificate-pinning tooling):

```python
import tls_client

session = tls_client.Session(
    client_identifier="chrome_150",
    certificate_pinning={
        "example.com": [
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",  # backup pin
        ],
    },
)

response = session.get("https://example.com/")
```

Requests to a pinned host whose certificate doesn't match any of the given
pins raise `tls_client.TLSClientCertificateError` (see
[Error handling](#error-handling)). Including a backup pin is recommended so
rotating the leaf certificate doesn't lock you out.

## Error handling

Failures originating from the underlying Go client are raised as
`TLSClientExeption` (kept misspelled for backwards compatibility) or one of
its more specific subclasses, so you can catch broadly or narrowly:

```python
from tls_client import (
    TLSClientExeption,
    TLSClientTimeoutError,
    TLSClientProxyError,
    TLSClientConnectionError,
    TLSClientCertificateError,
)

try:
    response = session.get("https://example.com/", timeout_seconds=5)
except TLSClientTimeoutError:
    ...  # request exceeded timeout_seconds
except TLSClientProxyError:
    ...  # the configured proxy refused/rejected the connection
except TLSClientConnectionError:
    ...  # DNS, TCP, or TLS handshake failure
except TLSClientCertificateError:
    ...  # response failed certificate pinning validation
except TLSClientExeption:
    ...  # any other backend error
```

All four subclasses inherit from `TLSClientExeption`, so existing code that
only catches the base class keeps working unchanged. Classification is
best-effort pattern matching on the backend's error message (it doesn't
expose a structured error code) and falls back to the base exception when
the message doesn't match a known pattern.

## Packaging with PyInstaller / PyArmor

The compiled native library ships inside `tls_client/dependencies/` and needs
to be included explicitly when bundling with PyInstaller or PyArmor.

| Platform                | `--add-binary` argument |
|--------------------------|--------------------------|
| Linux (x86, 32-bit)      | `'{path_to_library}/tls_client/dependencies/tls-client-x86.so:tls_client/dependencies'` |
| Linux (AMD64 / x86_64)   | `'{path_to_library}/tls_client/dependencies/tls-client-amd64.so:tls_client/dependencies'` |
| macOS (Intel)            | `'{path_to_library}/tls_client/dependencies/tls-client-x86.dylib:tls_client/dependencies'` |
| macOS (Apple Silicon)    | `'{path_to_library}/tls_client/dependencies/tls-client-arm64.dylib:tls_client/dependencies'` |
| Windows (64-bit)         | `'{path_to_library}/tls_client/dependencies/tls-client-64.dll;tls_client/dependencies'` |

## Development

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_unit_*.py" -v
```

`tests/test_unit_*.py` are network-free and run in CI on every push and pull
request. `tests/test_binary_response.py` is a regression suite that hits
httpbin.org and is meant for manual local runs (`python -m pytest tests/ -v`),
not CI.

## Acknowledgements

Big shout out to [Bogdanfinn](https://github.com/bogdanfinn) for open
sourcing [tls-client](https://github.com/bogdanfinn/tls-client) in Go, and to
[FlorianREGAZ](https://github.com/FlorianREGAZ) for the original Python
wrapper this project is forked from. The syntax stays close to
[requests](https://github.com/psf/requests) since most people already know it.

## Changelog

### Unreleased
- **Breaking**: `Session`'s default `client_identifier` changed from
  `chrome_120` to `chrome_150` (matching the v1.16.0 native library's own
  default profile). `chrome_120` imitates a browser version no longer in
  circulation, which made it a distinguishing fingerprint rather than a
  neutral one; pin `client_identifier="chrome_120"` explicitly if you
  relied on the old default.
- **Added**: typed exception hierarchy (`TLSClientTimeoutError`,
  `TLSClientProxyError`, `TLSClientConnectionError`,
  `TLSClientCertificateError`), all subclasses of the existing
  `TLSClientExeption` so current `except` clauses keep working.
- **Added**: `Session` now warns (`ResourceWarning`) and best-effort
  auto-closes if garbage collected without an explicit `close()` call.
- **Fixed**: native library load failures now raise a clear `OSError`
  naming the platform, architecture, and resolved library path instead of
  a raw, hard-to-diagnose `ctypes` error.
- **Fixed**: invalid/misleading type hints in `Session.__init__` (bare
  `Optional` on `bool` parameters, `str` instead of `Optional[str]`).
- **Added**: network-free unit tests (`tests/test_unit_*.py`) and a CI
  workflow that runs them on every push and pull request.
- **Updated**: precompiled native binaries bumped from
  `bogdanfinn/tls-client` ~v1.7.x to v1.16.0. Newest previously available
  profile was `chrome_120`/`firefox_120` (obsolete browser versions by
  2026, which made the fingerprint itself a distinguishing signal). Now
  includes Chrome 150/152, Firefox 147/148, Brave 146, and 20+ other new
  profiles — see the [client identifier table](#quick-start) above. Verified
  against a live handshake (`chrome_150` against tls.peet.ws) and against
  the full existing test suite (unit tests + the httpbin-backed binary
  response regression suite) on macOS arm64.
- **Added**: `Session` parameters `alpn_protocols`, `alps_protocols`,
  `trust_anchors_payload` (custom client only), `disable_session_tickets`,
  `disable_http3`, exposing v1.16.0 request fields. All default to the
  previous behavior, so existing calls are unaffected.
- **Fixed**: `cert_compression_algo` now sends `certCompressionAlgos`
  (the v1.16.0 field name, plural/list) internally instead of the old
  singular `certCompressionAlgo`, which the new binary silently ignored.
  The public parameter itself is unchanged.
- **Fixed**: `ClientIdentifiers` type list corrected — `safari_ipad_15_6`
  was previously listed as a duplicate of `safari_ios_15_6`, making the
  real iPadOS identifier inaccessible through the type; `confirmed_android_2`
  removed as it was never a valid identifier in any checked upstream version.

### 1.0.3
- **Fixed**: on Linux, 64-bit x86 machines (`platform.machine() == "x86_64"`)
  were incorrectly matched by the `"x86" in machine()` check in `cffi.py`
  and loaded the 32-bit `tls-client-x86.so` binary instead of the 64-bit
  `tls-client-amd64.so`, causing the native library to fail to load on the
  vast majority of Linux hosts. `machine()` is now matched explicitly
  against `x86_64`/`amd64`/`AMD64` before falling back to the 32-bit binary.

### 1.0.2
- **Fixed**: binary response bodies (protobuf, images, ...) were corrupted
  by a UTF-8 `byteReplacer` (U+FFFD) inside the Go C library. Every byte
  greater than 127 that did not form a valid UTF-8 sequence was replaced by
  `EF BF BD`.
  - `sessions.py` now sends `isByteResponse: True` in the request payload
    so the backend returns the body as a base64 data-URI.
  - `response.py`'s `build_response` decodes the data-URI back to raw
    bytes for `Response.content`; `Response.text` is a UTF-8 view (with
    replacement characters for invalid sequences).
- Added `tests/test_binary_response.py` (regression suite, needs network).

### 1.0.1
- Certificate pinning.
