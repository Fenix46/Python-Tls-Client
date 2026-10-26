from .cookies import cookiejar_from_dict, RequestsCookieJar
from .exceptions import TLSClientHTTPError
from .structures import CaseInsensitiveDict

from typing import Union
import base64
import json


class Response:
    """object, which contains the response to an HTTP request."""

    def __init__(self):

        # Reference of URL the response is coming from (especially useful with redirects)
        self.url = None

        # Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        # String of responded HTTP Body.
        self.text = None

        # Case-insensitive Dictionary of Response Headers.
        self.headers = CaseInsensitiveDict()

        # A CookieJar of Cookies the server sent back.
        self.cookies = cookiejar_from_dict({})

        self._content = b""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __repr__(self):
        return f"<Response [{self.status_code}]>"

    @property
    def ok(self):
        """True if the status code is below 400."""
        return self.status_code < 400

    def raise_for_status(self):
        """Raise TLSClientHTTPError for 4xx/5xx responses."""
        if not self.ok:
            kind = "Client" if self.status_code < 500 else "Server"
            raise TLSClientHTTPError(
                f"{self.status_code} {kind} Error for url: {self.url}", response=self
            )

    def json(self, **kwargs):
        """parse response body to json (dict/list)"""
        return json.loads(self.text, **kwargs)
    
    @property
    def content(self):
        """Content of the response, in bytes."""
        return self._content


def _split_data_uri(body: str) -> bytes:
    """Decode a base64 data-URI (data:<mime>;base64,<payload>) to raw bytes.

    The Go backend (isByteResponse) returns the response body as a data-URI to
    survive the JSON envelope as raw bytes. Anything that is not a data-URI is
    returned as-is, encoded to bytes.
    """
    if isinstance(body, str) and body.startswith("data:"):
        header, _, b64 = body.partition(",")
        if ";base64" in header:
            return base64.b64decode(b64)
    if isinstance(body, str):
        return body.encode("utf-8")
    return body or b""


def build_response(res: Union[dict, list], res_cookies: RequestsCookieJar) -> Response:
    """Builds a Response object """
    response = Response()
    # Add target / url
    response.url = res["target"]
    # Add status code
    response.status_code = res["status"]
    # Add headers
    response_headers = CaseInsensitiveDict()
    if res["headers"] is not None:
        for header_key, header_value in res["headers"].items():
            if len(header_value) == 1:
                response_headers[header_key] = header_value[0]
            else:
                response_headers[header_key] = header_value
    response.headers = response_headers
    # Add cookies
    response.cookies = res_cookies
    # Add response body (raw bytes, decoded from the base64 data-URI)
    content = _split_data_uri(res["body"])
    response._content = content
    # Add response text (utf-8, replacement chars for invalid sequences)
    response.text = content.decode("utf-8", errors="replace")
    return response
