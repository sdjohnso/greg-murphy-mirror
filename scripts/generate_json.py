#!/usr/bin/env python3 -u
"""
Generate consolidated JSON API exports from processed congressional data.

Creates a clean, structured JSON output in api/ suitable for consumption
by other applications. This converts the same data that generates the
markdown docs into a portable JSON format.

Creates:
- api/v1/member.json          - Profile and key metrics
- api/v1/votes/summary.json   - Voting statistics
- api/v1/votes/recent.json    - Last 30 days of votes
- api/v1/votes/all.json       - Complete voting record
- api/v1/legislation.json     - Sponsored & cosponsored bills
- api/v1/consistency.json     - Voting consistency analysis
- api/v1/manifest.json        - Index of all available endpoints
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import json
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    PROJECT_ROOT,
    MEMBER_INFO,
)

API_DIR = PROJECT_ROOT / "api" / "v1"


def load_json(path: Path) -> dict | list:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def save_json(data: dict | list, path: Path):
    """Save JSON file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path}")


def generate_member_json(profile: dict, metrics: dict) -> dict:
    """Generate consolidated member profile with key metrics."""
    member = profile.get("member", {})
    participation = metrics.get("participation", {})
    alignment = metrics.get("party_alignment", {})
    summary = metrics.get("summary", {})

    return {
        "generated_at": metrics.get("generated_at"),
        "member": {
            "bioguide_id": member.get("bioguideId", MEMBER_INFO["bioguide_id"]),
            "name": member.get("directOrderName", MEMBER_INFO["name"]),
            "party": MEMBER_INFO["party"],
            "state": MEMBER_INFO["state"],
            "district": MEMBER_INFO["district"],
            "serving_since": MEMBER_INFO["serving_since"],
            "birth_year": member.get("birthYear"),
            "photo_url": member.get("depiction", {}).get("imageUrl"),
            "website": member.get("officialWebsiteUrl"),
            "office": member.get("addressInformation", {}).get("officeAddress"),
            "phone": member.get("addressInformation", {}).get("phoneNumber"),
            "congress_gov_url": "https://www.congress.gov/member/gregory-murphy/M001210",
        },
        "metrics": {
            "participation_rate": participation.get("participation_rate"),
            "total_votes": participation.get("total_votes"),
            "votes_cast": participation.get("participated"),
            "votes_missed": participation.get("not_voting"),
            "party_alignment_rate": alignment.get("alignment_rate"),
            "with_party": alignment.get("with_party"),
            "against_party": alignment.get("against_party"),
            "bipartisan_votes": alignment.get("bipartisan_votes"),
            "bills_sponsored": summary.get("bills_sponsored"),
            "bills_cosponsored": summary.get("bills_cosponsored"),
        },
    }


def generate_votes_summary_json(metrics: dict, votes: list) -> dict:
    """Generate voting statistics summary."""
    participation = metrics.get("participation", {})
    alignment = metrics.get("party_alignment", {})
    by_type = metrics.get("votes_by_type", {})

    # Count by congress
    by_congress = {}
    for vote in votes:
        congress = str(vote.get("congress", "unknown"))
        by_congress[congress] = by_congress.get(congress, 0) + 1

    # Clean up votes_by_type (remove 'recent' detail, just keep counts)
    type_summary = {}
    for leg_type, data in by_type.items():
        type_summary[leg_type if leg_type != "null" else "unclassified"] = data["count"]

    return {
        "generated_at": metrics.get("generated_at"),
        "participation": {
            "total_votes": participation.get("total_votes"),
            "participated": participation.get("participated"),
            "not_voting": participation.get("not_voting"),
            "participation_rate": participation.get("participation_rate"),
        },
        "party_alignment": {
            "with_party": alignment.get("with_party"),
            "against_party": alignment.get("against_party"),
            "alignment_rate": alignment.get("alignment_rate"),
            "bipartisan_votes": alignment.get("bipartisan_votes"),
        },
        "by_congress": by_congress,
        "by_legislation_type": type_summary,
    }


def generate_recent_votes_json(votes: list) -> dict:
    """Generate last 30 days of votes."""
    cutoff = datetime.now() - timedelta(days=30)

    recent = []
    for vote in votes:
        date_str = vote.get("date")
        if date_str:
            try:
                vote_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if vote_date.replace(tzinfo=None) > cutoff:
                    recent.append({
                        "roll_number": vote.get("roll_number"),
                        "date": vote.get("date"),
                        "congress": vote.get("congress"),
                        "legislation_type": vote.get("legislation_type"),
                        "legislation_number": vote.get("legislation_number"),
                        "legislation_url": vote.get("legislation_url"),
                        "question": vote.get("question"),
                        "result": vote.get("result"),
                        "murphy_vote": vote.get("murphy_vote"),
                        "voted_with_party": vote.get("voted_with_party"),
                    })
            except (ValueError, TypeError):
                pass

    recent.sort(key=lambda x: x.get("date", ""), reverse=True)

    return {
        "generated_at": datetime.now().isoformat(),
        "period": "last_30_days",
        "count": len(recent),
        "votes": recent,
    }


def generate_all_votes_json(votes: list) -> list:
    """Pass through all votes (already clean structure)."""
    return votes


def generate_legislation_json(sponsored: list, cosponsored: list) -> dict:
    """Generate consolidated legislation data."""
    def clean_bill(bill: dict) -> dict:
        return {
            "congress": bill.get("congress"),
            "type": bill.get("type"),
            "number": bill.get("number"),
            "title": bill.get("title"),
            "introduced_date": bill.get("introducedDate"),
            "policy_area": (bill.get("policyArea") or {}).get("name"),
            "latest_action": bill.get("latestAction", {}).get("text"),
            "latest_action_date": bill.get("latestAction", {}).get("actionDate"),
            "url": bill.get("url"),
        }

    # Group sponsored by congress
    sponsored_by_congress = {}
    for bill in sponsored:
        congress = str(bill.get("congress", "unknown"))
        sponsored_by_congress.setdefault(congress, []).append(clean_bill(bill))

    # Group cosponsored by congress
    cosponsored_by_congress = {}
    for bill in cosponsored:
        congress = str(bill.get("congress", "unknown"))
        cosponsored_by_congress.setdefault(congress, []).append(clean_bill(bill))

    return {
        "generated_at": datetime.now().isoformat(),
        "sponsored": {
            "total": len(sponsored),
            "by_congress": sponsored_by_congress,
        },
        "cosponsored": {
            "total": len(cosponsored),
            "by_congress": cosponsored_by_congress,
        },
    }


def generate_consistency_json(consistency: dict) -> dict:
    """Generate consistency analysis (pass through with clean structure)."""
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "inconsistent_bill_count": consistency.get("inconsistent_bill_count", 0),
            "against_party_count": consistency.get("against_party_count", 0),
            "voted_against_cosponsored_count": consistency.get(
                "voted_against_cosponsored_count", 0
            ),
        },
        "against_party_votes": consistency.get("against_party_votes", []),
        "inconsistent_bills": consistency.get("inconsistent_bills", {}),
        "voted_against_cosponsored": consistency.get("voted_against_cosponsored", []),
    }


def generate_manifest() -> dict:
    """Generate manifest listing all available JSON endpoints."""
    return {
        "generated_at": datetime.now().isoformat(),
        "version": "v1",
        "description": (
            "Consolidated JSON API for Rep. Greg Murphy (NC-03) congressional data. "
            "Auto-updated monthly from the greg-murphy-mirror."
        ),
        "source_repo": "https://github.com/sdjohnso/greg-murphy-mirror",
        "endpoints": {
            "member": {
                "path": "member.json",
                "description": "Member profile and key metrics",
            },
            "votes_summary": {
                "path": "votes/summary.json",
                "description": "Voting statistics and breakdowns",
            },
            "votes_recent": {
                "path": "votes/recent.json",
                "description": "Votes from the last 30 days",
            },
            "votes_all": {
                "path": "votes/all.json",
                "description": "Complete voting record with party breakdowns",
            },
            "legislation": {
                "path": "legislation.json",
                "description": "Sponsored and cosponsored bills",
            },
            "consistency": {
                "path": "consistency.json",
                "description": "Voting consistency and party alignment analysis",
            },
        },
    }


def main():
    """Generate all JSON API exports."""
    print("=" * 60)
    print("Generating JSON API Exports")
    print("=" * 60)

    # Load source data
    print("\nLoading data...")
    metrics = load_json(PROCESSED_DIR / "metrics.json")
    profile = load_json(RAW_DIR / "member" / "profile.json")
    votes = load_json(PROCESSED_DIR / "votes" / "all_votes.json")
    consistency = load_json(PROCESSED_DIR / "consistency.json")
    sponsored = load_json(RAW_DIR / "sponsored" / "bills.json")
    cosponsored = load_json(RAW_DIR / "cosponsored" / "bills.json")

    # Generate JSON exports
    print("\nGenerating JSON files...")

    save_json(generate_member_json(profile, metrics), API_DIR / "member.json")
    save_json(
        generate_votes_summary_json(metrics, votes), API_DIR / "votes" / "summary.json"
    )
    save_json(generate_recent_votes_json(votes), API_DIR / "votes" / "recent.json")
    save_json(generate_all_votes_json(votes), API_DIR / "votes" / "all.json")
    save_json(generate_legislation_json(sponsored, cosponsored), API_DIR / "legislation.json")
    save_json(generate_consistency_json(consistency), API_DIR / "consistency.json")
    save_json(generate_manifest(), API_DIR / "manifest.json")

    print("\nDone! JSON API files written to api/v1/")


if __name__ == "__main__":
    main()
