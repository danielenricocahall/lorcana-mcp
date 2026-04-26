"""Fetch the Ravensburger Lorcana card catalog and write it to disk.

Intended to run as a scheduled GitHub Actions job, not from inside the
shipped MCP container. The Basic-auth client credential is read from the
``RAVENSBURGER_BASIC_AUTH`` environment variable so it never lives in
source. The script writes the raw catalog JSON (the same shape the
official app sees) to the path passed on the CLI.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import requests

UNITY_VERSION = "6000.0.66f2"
TOKEN_URL = "https://sso.ravensburger.de/token"
CATALOG_URL = "https://api.lorcana.ravensburger.com/v3/catalog/en"
DEFAULT_HEADERS = {"user-agent": "Lorcana/2026.2", "x-unity-version": UNITY_VERSION}

logger = logging.getLogger("fetch_cards")


def _retrieve(url: str, headers: dict[str, str], max_attempts: int = 5) -> requests.Response:
    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.debug("GET %s succeeded on attempt %d", url, attempt)
                return response
            last_error = f"status {response.status_code}"
        except (requests.exceptions.SSLError, requests.exceptions.Timeout) as exc:
            last_error = type(exc).__name__
            logger.debug("GET %s failed on attempt %d: %s", url, attempt, last_error)
    raise RuntimeError(f"GET {url} failed after {max_attempts} attempts (last error: {last_error})")


def _get_token(basic_auth: str) -> str:
    response = requests.post(
        TOKEN_URL,
        headers={
            "authorization": f"Basic {basic_auth}",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": f"UnityPlayer/{UNITY_VERSION} (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
            "x-unity-version": UNITY_VERSION,
        },
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Token request failed (status {response.status_code}): {response.text}")
    payload = response.json()
    if "access_token" not in payload or "token_type" not in payload:
        raise RuntimeError(f"Token response missing fields: {response.text}")
    return f"{payload['token_type']} {payload['access_token']}"


def fetch_catalog(basic_auth: str) -> dict[str, Any]:
    auth_header = _get_token(basic_auth)
    headers = {**DEFAULT_HEADERS, "authorization": auth_header}
    response = _retrieve(CATALOG_URL, headers=headers)
    catalog = response.json()
    if "cards" not in catalog:
        raise RuntimeError(f"Catalog response missing 'cards' field: {response.text[:500]}")
    return catalog


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if len(argv) != 2:
        print("usage: fetch_cards.py <output-path>", file=sys.stderr)
        return 2
    output_path = argv[1]

    basic_auth = os.environ.get("RAVENSBURGER_BASIC_AUTH")
    if not basic_auth:
        print("RAVENSBURGER_BASIC_AUTH environment variable is required", file=sys.stderr)
        return 2

    catalog = fetch_catalog(basic_auth)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")

    # The catalog groups cards under buckets like actions / characters / items / locations,
    # so sum across the buckets for an accurate count.
    cards_section = catalog.get("cards", {})
    if isinstance(cards_section, dict):
        total = sum(len(v) for v in cards_section.values() if isinstance(v, list))
    else:
        total = len(cards_section)
    logger.info("Wrote %d cards to %s (catalog_hash=%s)", total, output_path, catalog.get("catalog_hash"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
