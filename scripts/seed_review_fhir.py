"""Idempotently seed the local HAPI FHIR R4 sandbox with AETHER fixtures."""

from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from demo.fhir.fixtures import SYNTHETIC_TAG, all_resources


def put_resource(base_url: str, resource: dict) -> int:
    """PUT one stable-id FHIR resource and return the HTTP status."""
    url = f"{base_url.rstrip('/')}/{resource['resourceType']}/{resource['id']}"
    request = Request(url, data=json.dumps(resource).encode(), method="PUT",
                      headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"})
    with urlopen(request, timeout=30) as response:
        return response.status


def seed(base_url: str) -> dict[str, int]:
    """Upsert the complete fixture set; stable logical ids make repeated runs idempotent."""
    counts = {"created_or_updated": 0, "failed": 0}
    for resource in all_resources():
        try:
            put_resource(base_url, resource)
            counts["created_or_updated"] += 1
        except (HTTPError, URLError) as exc:
            counts["failed"] += 1
            raise RuntimeError(f"FHIR seed failed for {resource['resourceType']}/{resource['id']}: {exc}") from exc
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/fhir")
    args = parser.parse_args()
    result = seed(args.base_url)
    print(json.dumps({**result, "synthetic_tag": SYNTHETIC_TAG, "idempotent": True}, indent=2))


if __name__ == "__main__":
    main()

