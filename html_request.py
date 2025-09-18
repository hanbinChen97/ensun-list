"""HTTP request utilities for fetching HTML content."""

from __future__ import annotations

from typing import Dict

import requests
from requests import RequestException


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.7",
}


def scrape_webpage(url: str, *, timeout: int = 15) -> Dict[str, str | bool | None]:
    """Fetch HTML content using a plain HTTP request.

    Args:
        url: Target URL to fetch.
        timeout: Request timeout in seconds.
    """

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
    except RequestException as exc:  # pragma: no cover - network exceptions vary at runtime
        return {
            "success": False,
            "content": "",
            "html": "",
            "url": url,
            "markdown": "",
            "error": str(exc),
        }

    html = response.text

    return {
        "success": True,
        "content": html,
        "html": html,
        "url": response.url,
        "markdown": "",
        "error": None,
    }


__all__ = ["scrape_webpage"]
