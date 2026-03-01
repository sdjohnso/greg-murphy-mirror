#!/usr/bin/env python3
"""
Pull sponsored and cosponsored legislation from Congress.gov API.

Fetches all bills Rep. Greg Murphy has sponsored or cosponsored.
"""

import json
import time
from pathlib import Path

import requests

from config import (
    API_KEY,
    MEMBER_SPONSORED_URL,
    MEMBER_COSPONSORED_URL,
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


def fetch_all_legislation(base_url: str, leg_type: str) -> list:
    """
    Fetch all legislation (paginated) from an endpoint.

    Args:
        base_url: API endpoint URL
        leg_type: Type of legislation ("sponsored" or "cosponsored")

    Returns:
        List of all legislation records
    """
    all_bills = []
    offset = 0

    while True:
        params = {
            "api_key": API_KEY,
            "format": "json",
            "offset": offset,
            "limit": MAX_RESULTS_PER_PAGE,
        }

        print(f"  Fetching {leg_type} offset {offset}...")
        data = fetch_with_retry(base_url, params)
        time.sleep(REQUEST_DELAY_SECONDS)

        # The key varies by endpoint
        bills = data.get("sponsoredLegislation", []) or data.get("cosponsoredLegislation", [])
        if not bills:
            break

        all_bills.extend(bills)

        pagination = data.get("pagination", {})
        total = pagination.get("count", 0)

        print(f"    Got {len(bills)} bills, total so far: {len(all_bills)}/{total}")

        if offset + len(bills) >= total:
            break

        offset += MAX_RESULTS_PER_PAGE

    return all_bills


def extract_bill_summary(bill: dict) -> dict:
    """
    Extract key fields from a bill record.

    Args:
        bill: Raw bill data from API

    Returns:
        Simplified bill summary
    """
    latest_action = bill.get("latestAction", {})

    return {
        "congress": bill.get("congress"),
        "bill_type": bill.get("type"),
        "bill_number": bill.get("number"),
        "title": bill.get("title"),
        "introduced_date": bill.get("introducedDate"),
        "latest_action_date": latest_action.get("actionDate"),
        "latest_action_text": latest_action.get("text"),
        "policy_area": bill.get("policyArea", {}).get("name") if bill.get("policyArea") else None,
        "url": bill.get("url"),
    }


def pull_sponsored() -> list:
    """
    Pull all sponsored legislation.

    Returns:
        List of sponsored bills
    """
    print("\nFetching sponsored legislation...")
    bills = fetch_all_legislation(MEMBER_SPONSORED_URL, "sponsored")
    print(f"  Total sponsored: {len(bills)}")
    return bills


def pull_cosponsored() -> list:
    """
    Pull all cosponsored legislation.

    Returns:
        List of cosponsored bills
    """
    print("\nFetching cosponsored legislation...")
    bills = fetch_all_legislation(MEMBER_COSPONSORED_URL, "cosponsored")
    print(f"  Total cosponsored: {len(bills)}")
    return bills


def save_legislation(bills: list, leg_type: str) -> Path:
    """
    Save legislation to raw directory.

    Args:
        bills: List of bill records
        leg_type: Type ("sponsored" or "cosponsored")

    Returns:
        Path to saved file
    """
    output_dir = RAW_DIR / leg_type
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "bills.json"
    with open(output_path, "w") as f:
        json.dump(bills, f, indent=2)

    print(f"  Saved to {output_path}")
    return output_path


def main():
    """Main entry point."""
    print("=" * 60)
    print("Pulling Sponsored and Cosponsored Legislation")
    print("=" * 60)

    ensure_dirs()

    # Pull sponsored
    sponsored = pull_sponsored()
    save_legislation(sponsored, "sponsored")

    # Pull cosponsored
    cosponsored = pull_cosponsored()
    save_legislation(cosponsored, "cosponsored")

    # Summary by congress
    print("\nSummary by Congress:")
    for leg_type, bills in [("Sponsored", sponsored), ("Cosponsored", cosponsored)]:
        by_congress = {}
        for bill in bills:
            congress = bill.get("congress", "Unknown")
            by_congress[congress] = by_congress.get(congress, 0) + 1

        print(f"\n  {leg_type}:")
        for congress in sorted(by_congress.keys(), reverse=True):
            print(f"    {congress}th Congress: {by_congress[congress]}")

    print("\nDone!")


if __name__ == "__main__":
    main()
