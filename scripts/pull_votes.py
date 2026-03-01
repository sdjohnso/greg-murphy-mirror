#!/usr/bin/env python3 -u
"""
Pull House roll call votes from Congress.gov API and House Clerk.

Fetches all House floor votes and extracts Greg Murphy's position from
the official House Clerk XML records.
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

from config import (
    API_KEY,
    MEMBER_ID,
    RAW_DIR,
    PROCESSED_DIR,
    CONGRESSES,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    MAX_RESULTS_PER_PAGE,
    ensure_dirs,
)

# Congress.gov house vote endpoint
HOUSE_VOTE_URL = "https://api.congress.gov/v3/house-vote"


def fetch_with_retry(url: str, params: dict = None, is_xml: bool = False):
    """
    Fetch URL with retry logic.

    Args:
        url: URL to fetch
        params: Query parameters (for JSON APIs)
        is_xml: If True, return raw text instead of JSON

    Returns:
        JSON dict or XML string

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
            return response.text if is_xml else response.json()
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise


def extract_murphy_vote(xml_text: str) -> dict | None:
    """
    Extract Greg Murphy's vote from House Clerk XML.

    Args:
        xml_text: Raw XML from clerk.house.gov

    Returns:
        Dict with vote info or None if not found
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    for recorded_vote in root.findall(".//recorded-vote"):
        legislator = recorded_vote.find("legislator")
        if legislator is not None and legislator.get("name-id") == MEMBER_ID:
            vote_elem = recorded_vote.find("vote")
            return {
                "vote": vote_elem.text if vote_elem is not None else "Unknown",
                "party": legislator.get("party"),
                "state": legislator.get("state"),
            }

    return None


def extract_party_totals(xml_text: str) -> list:
    """
    Extract party vote totals from House Clerk XML.

    Args:
        xml_text: Raw XML from clerk.house.gov

    Returns:
        List of party total dicts
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    totals = []
    for party_total in root.findall(".//totals-by-party"):
        party = party_total.find("party")
        if party is not None:
            totals.append({
                "party": party.text,
                "yea": int(party_total.find("yea-total").text or 0),
                "nay": int(party_total.find("nay-total").text or 0),
                "present": int(party_total.find("present-total").text or 0),
                "not_voting": int(party_total.find("not-voting-total").text or 0),
            })

    return totals


def fetch_all_votes() -> list:
    """
    Fetch all House votes from Congress.gov API.

    Returns:
        List of vote metadata dicts
    """
    all_votes = []
    offset = 0

    while True:
        params = {
            "api_key": API_KEY,
            "format": "json",
            "offset": offset,
            "limit": MAX_RESULTS_PER_PAGE,
        }

        print(f"  Fetching votes offset {offset}...")
        data = fetch_with_retry(HOUSE_VOTE_URL, params)
        time.sleep(REQUEST_DELAY_SECONDS)

        votes = data.get("houseRollCallVotes", [])
        if not votes:
            break

        all_votes.extend(votes)

        pagination = data.get("pagination", {})
        total = pagination.get("count", 0)

        print(f"    Got {len(votes)} votes, total so far: {len(all_votes)}/{total}")

        if offset + len(votes) >= total:
            break

        offset += MAX_RESULTS_PER_PAGE

    return all_votes


def enrich_votes(votes: list) -> list:
    """
    Enrich votes with Murphy's positions from House Clerk XML.

    Args:
        votes: List of vote metadata from Congress.gov

    Returns:
        List of enriched vote records with Murphy's position
    """
    print(f"\nEnriching {len(votes)} votes with Murphy's positions...")

    enriched_votes = []

    for i, vote in enumerate(votes):
        if (i + 1) % 25 == 0:
            print(f"  Processing vote {i + 1}/{len(votes)}...")

        # Get the XML from House Clerk for individual votes
        xml_url = vote.get("sourceDataURL")
        if not xml_url:
            continue

        try:
            xml_text = fetch_with_retry(xml_url, is_xml=True)
            time.sleep(REQUEST_DELAY_SECONDS)
        except requests.RequestException as e:
            print(f"  Warning: Could not fetch XML for roll {vote.get('rollCallNumber')}: {e}")
            continue

        # Extract Murphy's vote
        murphy_vote = extract_murphy_vote(xml_text)
        party_totals = extract_party_totals(xml_text)

        # Determine if Murphy voted with his party
        # Note: Votes can be "Yea"/"Aye" (yes) or "Nay"/"No" (no)
        voted_with_party = None
        if murphy_vote:
            vote_text = murphy_vote["vote"]
            is_yes = vote_text in ("Yea", "Aye")
            is_no = vote_text in ("Nay", "No")

            rep_total = next((p for p in party_totals if p["party"] == "Republican"), None)
            if rep_total and (is_yes or is_no):
                rep_yes = rep_total["yea"]
                rep_no = rep_total["nay"]
                rep_majority_yes = rep_yes > rep_no
                voted_with_party = (is_yes and rep_majority_yes) or (is_no and not rep_majority_yes)

        enriched_vote = {
            "congress": vote.get("congress"),
            "session": vote.get("sessionNumber"),
            "roll_number": vote.get("rollCallNumber"),
            "date": vote.get("startDate"),
            "question": vote.get("voteQuestion") if "voteQuestion" in vote else None,
            "result": vote.get("result"),
            "vote_type": vote.get("voteType"),
            "legislation_type": vote.get("legislationType"),
            "legislation_number": vote.get("legislationNumber"),
            "legislation_url": vote.get("legislationUrl"),
            "source_xml": xml_url,
            "murphy_vote": murphy_vote["vote"] if murphy_vote else "Not Found",
            "voted_with_party": voted_with_party,
            "party_totals": party_totals,
        }

        enriched_votes.append(enriched_vote)

    return enriched_votes


def save_votes(votes: list, congress: int) -> tuple[Path, Path]:
    """
    Save votes to raw and processed directories.

    Args:
        votes: List of enriched vote records
        congress: Congress number

    Returns:
        Tuple of (raw_path, processed_path)
    """
    # Group by year for raw storage
    votes_by_year = {}
    for vote in votes:
        if vote.get("date"):
            year = vote["date"][:4]
            votes_by_year.setdefault(year, []).append(vote)

    # Save raw by year
    raw_congress_dir = RAW_DIR / "votes" / str(congress)
    raw_congress_dir.mkdir(parents=True, exist_ok=True)

    for year, year_votes in votes_by_year.items():
        year_dir = raw_congress_dir / year
        year_dir.mkdir(exist_ok=True)
        raw_path = year_dir / "votes.json"
        with open(raw_path, "w") as f:
            json.dump(year_votes, f, indent=2)
        print(f"  Saved {len(year_votes)} votes to {raw_path}")

    # Save consolidated processed file
    processed_path = PROCESSED_DIR / "votes" / f"congress_{congress}.json"
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    with open(processed_path, "w") as f:
        json.dump(votes, f, indent=2)
    print(f"  Saved {len(votes)} votes to {processed_path}")

    return raw_congress_dir, processed_path


def main():
    """Main entry point."""
    print("=" * 60)
    print("Pulling House Roll Call Votes")
    print("=" * 60)

    ensure_dirs()

    # Fetch all votes at once (API doesn't filter by congress properly)
    print("\nFetching all House votes from Congress.gov...")
    all_raw_votes = fetch_all_votes()
    print(f"  Total votes fetched: {len(all_raw_votes)}")

    # Filter to target congresses
    target_votes = [v for v in all_raw_votes if v.get("congress") in CONGRESSES]
    print(f"  Votes in target congresses ({CONGRESSES}): {len(target_votes)}")

    # Enrich with Murphy's positions
    all_votes = enrich_votes(target_votes)

    # Save by congress
    for congress in CONGRESSES:
        congress_votes = [v for v in all_votes if v["congress"] == congress]
        if congress_votes:
            save_votes(congress_votes, congress)

    # Save combined all_votes.json
    all_votes_path = PROCESSED_DIR / "votes" / "all_votes.json"
    with open(all_votes_path, "w") as f:
        json.dump(all_votes, f, indent=2)
    print(f"\nSaved {len(all_votes)} total votes to {all_votes_path}")

    # Summary stats
    non_votes = ("Not Found", "Not Voting", "Present")
    murphy_votes = [v for v in all_votes if v["murphy_vote"] not in non_votes]
    with_party = [v for v in all_votes if v["voted_with_party"] is True]
    against_party = [v for v in all_votes if v["voted_with_party"] is False]

    print(f"\nSummary:")
    print(f"  Total votes: {len(all_votes)}")
    print(f"  Murphy participated: {len(murphy_votes)}")
    print(f"  Voted with party: {len(with_party)}")
    print(f"  Voted against party: {len(against_party)}")

    print("\nDone!")


if __name__ == "__main__":
    main()
