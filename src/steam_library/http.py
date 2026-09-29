import time

import requests
from google.auth.exceptions import GoogleAuthError

from .errors import LibraryError


def request_json(session, method: str, url: str, *, service: str, **kwargs):
    """Retry reads only. Never print response bodies, credential URLs, or auth errors."""
    attempts = 3 if method == "GET" else 1
    for attempt in range(attempts):
        try:
            response = session.request(method, url, timeout=(10, 60), **kwargs)
        except (requests.RequestException, GoogleAuthError):
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
                continue
            suffix = (
                " Check status before retrying; the write may have committed."
                if method != "GET"
                else ""
            )
            raise LibraryError(f"{service} connection/authentication failed.{suffix}") from None
        if response.status_code == 429 or 500 <= response.status_code < 600:
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
                continue
        if not 200 <= response.status_code < 300:
            suffix = " Check status before retrying." if method != "GET" else ""
            raise LibraryError(
                f"{service} returned HTTP {response.status_code}. "
                f"Check access and configuration.{suffix}"
            )
        try:
            return response.json()
        except ValueError:
            raise LibraryError(
                f"{service} returned invalid JSON; no further writes attempted."
            ) from None
    raise AssertionError("unreachable")
