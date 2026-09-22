from .cookies import cookiejar_from_dict, RequestsCookieJar
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
        
        self._content = False

    def __enter__(self):
        return self

    def __repr__(self):
        return f"<Response [{self.status_code}]>"

    def json(self, **kwargs):
        """parse response body to json (dict/list)"""
        return json.loads(self.text, **kwargs)
    
    @property
    def content(self):
        """Content of the response, in bytes."""
        
        if self._content is False:
            if self._content_consumed:
                raise RuntimeError("The content for this response was already consumed")

            if self.status_code == 0:
                self._content = None
            else:
                self._content = b"".join(self.iter_content(10 * 1024)) or b""
        self._content_consumed = True
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
    response_headers = {}
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
