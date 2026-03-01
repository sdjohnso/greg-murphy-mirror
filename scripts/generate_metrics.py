#!/usr/bin/env python3 -u
"""
Generate performance metrics from pulled congressional data.

Computes:
- Participation rate
- Party alignment percentage
- Bipartisan vote analysis
- Bill success rate
- Votes grouped by bill
- Consistency analysis
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    CONGRESSES,
    ensure_dirs,
)


def load_json(path: Path) -> dict | list:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def save_json(data: dict | list, path: Path):
    """Save JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved to {path}")


def compute_participation_metrics(votes: list) -> dict:
    """
    Compute participation rate and breakdown.

    Args:
        votes: List of vote records

    Returns:
        Participation metrics dict
    """
    total = len(votes)
    non_votes = ("Not Found", "Not Voting", "Present")

    participated = [v for v in votes if v["murphy_vote"] not in non_votes]
    not_voting = [v for v in votes if v["murphy_vote"] == "Not Voting"]
    not_found = [v for v in votes if v["murphy_vote"] == "Not Found"]

    return {
        "total_votes": total,
        "participated": len(participated),
        "not_voting": len(not_voting),
        "not_found": len(not_found),
        "participation_rate": round(len(participated) / total * 100, 1) if total > 0 else 0,
    }


def compute_party_alignment(votes: list) -> dict:
    """
    Compute party alignment metrics.

    Args:
        votes: List of vote records

    Returns:
        Party alignment metrics dict
    """
    # Only count votes where he actually voted and we know party position
    with_party = [v for v in votes if v["voted_with_party"] is True]
    against_party = [v for v in votes if v["voted_with_party"] is False]
    calculable = with_party + against_party

    total_calculable = len(calculable)

    return {
        "with_party": len(with_party),
        "against_party": len(against_party),
        "alignment_rate": round(len(with_party) / total_calculable * 100, 1) if total_calculable > 0 else 0,
        "bipartisan_votes": len(against_party),
        "calculable_votes": total_calculable,
    }


def compute_votes_by_topic(votes: list, legislation: list) -> dict:
    """
    Group votes by policy area/topic.

    Args:
        votes: List of vote records
        legislation: List of sponsored/cosponsored bills

    Returns:
        Votes grouped by topic
    """
    # Note: Congress.gov API doesn't provide policy area in vote data
    # We'll group by legislation type for now
    by_type = defaultdict(list)

    for vote in votes:
        leg_type = vote.get("legislation_type", "Other")
        by_type[leg_type].append({
            "roll": vote["roll_number"],
            "date": vote["date"],
            "result": vote["result"],
            "murphy_vote": vote["murphy_vote"],
            "voted_with_party": vote["voted_with_party"],
        })

    return {
        leg_type: {
            "count": len(items),
            "recent": items[:5],  # Most recent 5
        }
        for leg_type, items in sorted(by_type.items(), key=lambda x: -len(x[1]))
    }


def group_votes_by_bill(votes: list) -> dict:
    """
    Group votes by bill identifier.

    Shows multiple votes on same legislation (amendments, recommit, passage).

    Args:
        votes: List of vote records

    Returns:
        Dict keyed by bill identifier with all votes
    """
    by_bill = defaultdict(list)

    for vote in votes:
        leg_type = vote.get("legislation_type")
        leg_num = vote.get("legislation_number")

        if leg_type and leg_num:
            bill_id = f"{leg_type}-{leg_num}"
            by_bill[bill_id].append({
                "roll_number": vote["roll_number"],
                "congress": vote["congress"],
                "date": vote["date"],
                "question": vote.get("question"),
                "result": vote["result"],
                "murphy_vote": vote["murphy_vote"],
                "voted_with_party": vote["voted_with_party"],
                "legislation_url": vote.get("legislation_url"),
            })

    # Analyze consistency for bills with multiple votes
    result = {}
    for bill_id, bill_votes in by_bill.items():
        if len(bill_votes) > 1:
            # Sort by date
            bill_votes.sort(key=lambda x: x["date"] or "")

            # Check consistency
            murphy_positions = [v["murphy_vote"] for v in bill_votes
                               if v["murphy_vote"] not in ("Not Voting", "Not Found", "Present")]

            # Normalize Yea/Aye and Nay/No
            normalized = []
            for pos in murphy_positions:
                if pos in ("Yea", "Aye"):
                    normalized.append("Yes")
                elif pos in ("Nay", "No"):
                    normalized.append("No")
                else:
                    normalized.append(pos)

            consistent = len(set(normalized)) <= 1

            result[bill_id] = {
                "vote_count": len(bill_votes),
                "consistent": consistent,
                "votes": bill_votes,
                "legislation_url": bill_votes[0].get("legislation_url"),
            }
        else:
            result[bill_id] = {
                "vote_count": 1,
                "consistent": True,
                "votes": bill_votes,
                "legislation_url": bill_votes[0].get("legislation_url") if bill_votes else None,
            }

    return result


def analyze_consistency(votes: list, sponsored: list, cosponsored: list) -> dict:
    """
    Find inconsistencies in voting patterns.

    Args:
        votes: List of vote records
        sponsored: List of sponsored bills
        cosponsored: List of cosponsored bills

    Returns:
        Consistency analysis dict
    """
    # Bills where Murphy voted differently at different stages
    by_bill = group_votes_by_bill(votes)
    inconsistent_bills = {
        bill_id: data
        for bill_id, data in by_bill.items()
        if not data["consistent"] and data["vote_count"] > 1
    }

    # Cosponsored bills he voted against
    cosponsored_ids = {
        f"{b.get('type')}-{b.get('number')}"
        for b in cosponsored
    }

    voted_against_cosponsored = []
    for bill_id, data in by_bill.items():
        if bill_id in cosponsored_ids:
            # Check if any vote was against
            for v in data["votes"]:
                if v["murphy_vote"] in ("Nay", "No"):
                    voted_against_cosponsored.append({
                        "bill_id": bill_id,
                        "vote": v,
                    })
                    break

    # Votes against party majority
    against_party_votes = [
        {
            "roll_number": v["roll_number"],
            "congress": v["congress"],
            "date": v["date"],
            "question": v.get("question"),
            "result": v["result"],
            "murphy_vote": v["murphy_vote"],
            "legislation_type": v.get("legislation_type"),
            "legislation_number": v.get("legislation_number"),
        }
        for v in votes if v["voted_with_party"] is False
    ]

    return {
        "inconsistent_bill_count": len(inconsistent_bills),
        "inconsistent_bills": inconsistent_bills,
        "voted_against_cosponsored_count": len(voted_against_cosponsored),
        "voted_against_cosponsored": voted_against_cosponsored,
        "against_party_count": len(against_party_votes),
        "against_party_votes": against_party_votes[:50],  # Limit output size
    }


def compute_legislation_metrics(sponsored: list, cosponsored: list) -> dict:
    """
    Compute legislation metrics.

    Args:
        sponsored: List of sponsored bills
        cosponsored: List of cosponsored bills

    Returns:
        Legislation metrics dict
    """
    # Count by Congress
    sponsored_by_congress = defaultdict(int)
    cosponsored_by_congress = defaultdict(int)

    for bill in sponsored:
        congress = bill.get("congress", "Unknown")
        sponsored_by_congress[congress] += 1

    for bill in cosponsored:
        congress = bill.get("congress", "Unknown")
        cosponsored_by_congress[congress] += 1

    # Analyze statuses
    def count_statuses(bills):
        statuses = defaultdict(int)
        for bill in bills:
            action = bill.get("latestAction", {}).get("text", "Unknown")
            # Simplify status
            if "Became Public Law" in action or "Signed by President" in action:
                statuses["Became Law"] += 1
            elif "Passed House" in action:
                statuses["Passed House"] += 1
            elif "Passed Senate" in action:
                statuses["Passed Senate"] += 1
            elif "Referred to" in action:
                statuses["In Committee"] += 1
            else:
                statuses["Other"] += 1
        return dict(statuses)

    return {
        "sponsored": {
            "total": len(sponsored),
            "by_congress": dict(sponsored_by_congress),
            "statuses": count_statuses(sponsored),
        },
        "cosponsored": {
            "total": len(cosponsored),
            "by_congress": dict(cosponsored_by_congress),
        },
    }


def generate_all_metrics():
    """Generate all metrics and save to processed directory."""
    print("=" * 60)
    print("Generating Performance Metrics")
    print("=" * 60)

    ensure_dirs()

    # Load data
    print("\nLoading data...")
    votes = load_json(PROCESSED_DIR / "votes" / "all_votes.json")
    sponsored = load_json(RAW_DIR / "sponsored" / "bills.json")
    cosponsored = load_json(RAW_DIR / "cosponsored" / "bills.json")

    print(f"  Loaded {len(votes)} votes")
    print(f"  Loaded {len(sponsored)} sponsored bills")
    print(f"  Loaded {len(cosponsored)} cosponsored bills")

    # Compute metrics
    print("\nComputing metrics...")

    participation = compute_participation_metrics(votes)
    print(f"  Participation: {participation['participation_rate']}%")

    alignment = compute_party_alignment(votes)
    print(f"  Party alignment: {alignment['alignment_rate']}%")

    by_topic = compute_votes_by_topic(votes, sponsored + cosponsored)
    print(f"  Vote categories: {len(by_topic)}")

    legislation = compute_legislation_metrics(sponsored, cosponsored)
    print(f"  Legislation: {legislation['sponsored']['total']} sponsored")

    # Compile all metrics
    metrics = {
        "generated_at": datetime.now().isoformat(),
        "participation": participation,
        "party_alignment": alignment,
        "votes_by_type": by_topic,
        "legislation": legislation,
        "summary": {
            "total_votes": participation["total_votes"],
            "participation_rate": participation["participation_rate"],
            "party_alignment_rate": alignment["alignment_rate"],
            "bipartisan_votes": alignment["bipartisan_votes"],
            "bills_sponsored": legislation["sponsored"]["total"],
            "bills_cosponsored": legislation["cosponsored"]["total"],
        },
    }

    # Save metrics
    print("\nSaving metrics...")
    save_json(metrics, PROCESSED_DIR / "metrics.json")

    # Generate by_bill grouping
    print("\nGrouping votes by bill...")
    by_bill = group_votes_by_bill(votes)
    multi_vote_bills = {k: v for k, v in by_bill.items() if v["vote_count"] > 1}
    print(f"  Bills with multiple votes: {len(multi_vote_bills)}")
    save_json(by_bill, PROCESSED_DIR / "votes" / "by_bill.json")

    # Generate consistency analysis
    print("\nAnalyzing consistency...")
    consistency = analyze_consistency(votes, sponsored, cosponsored)
    print(f"  Inconsistent bills: {consistency['inconsistent_bill_count']}")
    print(f"  Against party: {consistency['against_party_count']}")
    save_json(consistency, PROCESSED_DIR / "consistency.json")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Participation Rate: {participation['participation_rate']}%")
    print(f"  Party Alignment: {alignment['alignment_rate']}%")
    print(f"  Bipartisan Votes: {alignment['bipartisan_votes']}")
    print(f"  Sponsored Bills: {legislation['sponsored']['total']}")
    print(f"  Cosponsored Bills: {legislation['cosponsored']['total']}")
    print("\nDone!")


if __name__ == "__main__":
    generate_all_metrics()
