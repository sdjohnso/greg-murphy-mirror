#!/usr/bin/env python3
"""
Pull member profile data from Congress.gov API.

Fetches Rep. Greg Murphy's profile including:
- Basic biographical info
- Terms served
- Committee assignments
- Leadership positions
"""

import json
import time
import requests
from pathlib import Path

from config import (
    API_KEY,
    MEMBER_PROFILE_URL,
    RAW_DIR,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    MAX_RESULTS_PER_PAGE,
    ensure_dirs,
)


def fetch_with_retry(url: str, params: dict) -> dict:
    """
    Fetch URL with retry logic.

    Args:
        url: API endpoint URL
        params: Query parameters

    Returns:
        JSON response as dictionary

    Raises:
        requests.RequestException: After all retries exhausted
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise


def fetch_paginated(base_url: str, data_key: str) -> list:
    """
    Fetch all pages of a paginated endpoint.

    Args:
        base_url: API endpoint URL
        data_key: Key in response containing the list data

    Returns:
        Combined list of all records across pages
    """
    all_records = []
    offset = 0

    while True:
        params = {
            "api_key": API_KEY,
            "format": "json",
            "offset": offset,
            "limit": MAX_RESULTS_PER_PAGE,
        }

        print(f"  Fetching offset {offset}...")
        data = fetch_with_retry(base_url, params)
        time.sleep(REQUEST_DELAY_SECONDS)

        records = data.get(data_key, [])
        if not records:
            break

        all_records.extend(records)

        # Check pagination
        pagination = data.get("pagination", {})
        total = pagination.get("count", 0)

        if offset + len(records) >= total:
            break

        offset += MAX_RESULTS_PER_PAGE

    return all_records


def pull_member_profile() -> dict:
    """
    Pull full member profile from Congress.gov API.

    Returns:
        Complete member data including nested resources
    """
    ensure_dirs()

    print("Fetching member profile...")
    params = {
        "api_key": API_KEY,
        "format": "json",
    }

    data = fetch_with_retry(MEMBER_PROFILE_URL, params)
    member = data.get("member", {})

    # The member endpoint includes URLs to nested resources
    # Fetch sponsoredLegislation and cosponsoredLegislation counts are in member
    # Full lists are fetched by pull_legislation.py

    print(f"  Name: {member.get('directOrderName')}")
    print(f"  Party: {member.get('partyHistory', [{}])[0].get('partyName', 'Unknown')}")
    print(f"  State: {member.get('state')}, District {member.get('district')}")
    print(f"  Terms: {len(member.get('terms', []))}")

    # Extract committee info if available
    committees = member.get("committees", [])
    if committees:
        print(f"  Committees: {len(committees)}")

    return data


def save_profile(data: dict) -> Path:
    """
    Save member profile to raw directory.

    Args:
        data: Member profile data from API

    Returns:
        Path to saved file
    """
    output_path = RAW_DIR / "member" / "profile.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved to {output_path}")
    return output_path


def main():
    """Main entry point."""
    print("=" * 60)
    print("Pulling Greg Murphy Member Profile")
    print("=" * 60)

    data = pull_member_profile()
    save_profile(data)

    print("\nDone!")


if __name__ == "__main__":
    main()
