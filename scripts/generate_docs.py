#!/usr/bin/env python3 -u
"""
Generate human-readable markdown documentation and RSS feed from processed data.

Creates:
- docs/index.md - Dashboard overview
- docs/profile.md - Bio and committees
- docs/votes/index.md - Vote summary
- docs/votes/recent.md - Last 30 days
- docs/votes/by-bill.md - Bills with multiple votes
- docs/votes/consistency.md - Position changes
- docs/legislation/sponsored.md
- docs/legislation/cosponsored.md
- docs/feeds/votes.xml - RSS feed of recent votes
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    DOCS_DIR,
    MEMBER_INFO,
    ensure_dirs,
)


def load_json(path: Path) -> dict | list:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def save_md(content: str, path: Path):
    """Save markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  Saved {path}")


def format_date(date_str: str | None, short: bool = False) -> str:
    """Format ISO date string for display."""
    if not date_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if short:
            return dt.strftime("%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except:
        return date_str[:10] if date_str else "Unknown"


def generate_index(metrics: dict, profile: dict) -> str:
    """Generate main dashboard index."""
    member = profile.get("member", {})
    summary = metrics.get("summary", {})
    participation = metrics.get("participation", {})
    alignment = metrics.get("party_alignment", {})

    return f"""# Rep. Greg Murphy Congressional Dashboard

*Data updated: {metrics.get('generated_at', 'Unknown')[:10]}*

## Representative Profile

| | |
|---|---|
| **Name** | {member.get('directOrderName', MEMBER_INFO['name'])} |
| **Party** | Republican |
| **State** | North Carolina |
| **District** | 3 |
| **Serving Since** | September 2019 |
| **Office** | {member.get('addressInformation', {}).get('officeAddress', '407 Cannon HOB')} |
| **Phone** | {member.get('addressInformation', {}).get('phoneNumber', '(202) 225-3415')} |
| **Website** | [{member.get('officialWebsiteUrl', 'murphy.house.gov')}]({member.get('officialWebsiteUrl', 'https://murphy.house.gov')}) |

## Key Metrics

| Metric | Value |
|--------|-------|
| **Participation Rate** | {participation.get('participation_rate', 0)}% |
| **Party Alignment** | {alignment.get('alignment_rate', 0)}% |
| **Bipartisan Votes** | {alignment.get('bipartisan_votes', 0)} |
| **Total Votes Cast** | {participation.get('participated', 0)} of {participation.get('total_votes', 0)} |
| **Bills Sponsored** | {summary.get('bills_sponsored', 0)} |
| **Bills Cosponsored** | {summary.get('bills_cosponsored', 0)} |

## Quick Links

- [Voting Record](votes/index.md)
- [Recent Votes](votes/recent.md)
- [Sponsored Legislation](legislation/sponsored.md)
- [Cosponsored Legislation](legislation/cosponsored.md)
- [Consistency Analysis](votes/consistency.md)

## Data Sources

All data is sourced from the official [Congress.gov API](https://api.congress.gov).
Individual vote records come from the [House Clerk](https://clerk.house.gov).

---

*This is an automated data mirror. For official information, visit [Congress.gov](https://www.congress.gov/member/gregory-murphy/M001210).*
"""


def generate_profile(profile: dict) -> str:
    """Generate profile page with bio and committees."""
    member = profile.get("member", {})
    terms = member.get("terms", [])
    party_history = member.get("partyHistory", [])

    # Format terms
    terms_md = ""
    for term in sorted(terms, key=lambda x: x.get("startYear", 0), reverse=True):
        terms_md += f"- **{term.get('congress')}th Congress** ({term.get('startYear')}-{term.get('endYear', 'Present')}): {term.get('chamber')}\n"

    return f"""# Rep. Greg Murphy - Profile

## Biographical Information

| | |
|---|---|
| **Full Name** | {member.get('directOrderName', 'Gregory F. Murphy')} |
| **Birth Year** | {member.get('birthYear', '1963')} |
| **Party** | Republican (since 2019) |
| **State** | North Carolina |
| **District** | 3rd Congressional District |

## Contact Information

- **Office**: {member.get('addressInformation', {}).get('officeAddress', '407 Cannon House Office Building')}
- **Phone**: {member.get('addressInformation', {}).get('phoneNumber', '(202) 225-3415')}
- **Website**: [{member.get('officialWebsiteUrl', 'murphy.house.gov')}]({member.get('officialWebsiteUrl', 'https://murphy.house.gov')})

## Terms Served

{terms_md}

## Links

- [Congress.gov Profile](https://www.congress.gov/member/gregory-murphy/M001210)
- [Official Photo]({member.get('depiction', {}).get('imageUrl', '')})

---

[Back to Dashboard](index.md)
"""


def generate_votes_index(metrics: dict, votes: list) -> str:
    """Generate vote summary page."""
    participation = metrics.get("participation", {})
    alignment = metrics.get("party_alignment", {})
    by_type = metrics.get("votes_by_type", {})

    # Count by congress
    by_congress = {}
    for vote in votes:
        congress = vote.get("congress", "Unknown")
        by_congress[congress] = by_congress.get(congress, 0) + 1

    type_rows = ""
    for leg_type, data in sorted(by_type.items(), key=lambda x: -x[1]["count"]):
        type_rows += f"| {leg_type} | {data['count']} |\n"

    congress_rows = ""
    for congress in sorted(by_congress.keys(), reverse=True):
        congress_rows += f"| {congress}th | {by_congress[congress]} |\n"

    return f"""# Voting Record Summary

## Overall Statistics

| Metric | Value |
|--------|-------|
| **Total Votes** | {participation.get('total_votes', 0)} |
| **Participated** | {participation.get('participated', 0)} |
| **Not Voting** | {participation.get('not_voting', 0)} |
| **Participation Rate** | {participation.get('participation_rate', 0)}% |

## Party Alignment

| Metric | Value |
|--------|-------|
| **Voted with Party** | {alignment.get('with_party', 0)} |
| **Voted Against Party** | {alignment.get('against_party', 0)} |
| **Alignment Rate** | {alignment.get('alignment_rate', 0)}% |
| **Bipartisan Votes** | {alignment.get('bipartisan_votes', 0)} |

## Votes by Congress

| Congress | Votes |
|----------|-------|
{congress_rows}

## Votes by Legislation Type

| Type | Count |
|------|-------|
{type_rows}

## More Details

- [Recent Votes (Last 30 Days)](recent.md)
- [Bills with Multiple Votes](by-bill.md)
- [Consistency Analysis](consistency.md)

---

[Back to Dashboard](../index.md)
"""


def generate_recent_votes(votes: list) -> str:
    """Generate recent votes page (last 30 days)."""
    cutoff = datetime.now() - timedelta(days=30)

    recent = []
    for vote in votes:
        date_str = vote.get("date")
        if date_str:
            try:
                vote_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if vote_date.replace(tzinfo=None) > cutoff:
                    recent.append(vote)
            except:
                pass

    recent.sort(key=lambda x: x.get("date", ""), reverse=True)

    rows = ""
    for vote in recent[:50]:  # Limit to 50
        date = format_date(vote.get("date"))
        roll = vote.get("roll_number", "?")
        result = vote.get("result", "?")
        murphy = vote.get("murphy_vote", "?")
        with_party = "Yes" if vote.get("voted_with_party") else ("No" if vote.get("voted_with_party") is False else "-")
        leg = f"{vote.get('legislation_type', '')} {vote.get('legislation_number', '')}"

        rows += f"| {date} | {roll} | {leg} | {result} | {murphy} | {with_party} |\n"

    return f"""# Recent Votes (Last 30 Days)

*{len(recent)} votes in the last 30 days*

| Date | Roll | Legislation | Result | Murphy | With Party |
|------|------|-------------|--------|--------|------------|
{rows}

---

[Back to Voting Record](index.md) | [Back to Dashboard](../index.md)
"""


def generate_by_bill(by_bill: dict) -> str:
    """Generate bills with multiple votes page."""
    multi_vote = {k: v for k, v in by_bill.items() if v["vote_count"] > 1}
    multi_vote = dict(sorted(multi_vote.items(), key=lambda x: -x[1]["vote_count"]))

    content = """# Bills with Multiple Votes

This page shows bills that received multiple votes (amendments, recommit motions, passage votes, etc.).

"""

    for bill_id, data in list(multi_vote.items())[:30]:  # Top 30
        consistent = "Consistent" if data["consistent"] else "**Inconsistent**"
        content += f"\n## {bill_id}\n\n"
        content += f"**Votes:** {data['vote_count']} | **Consistency:** {consistent}\n\n"

        if data.get("legislation_url"):
            content += f"[View on Congress.gov]({data['legislation_url']})\n\n"

        content += "| Date | Roll | Question | Result | Murphy |\n"
        content += "|------|------|----------|--------|--------|\n"

        for vote in data["votes"]:
            date = format_date(vote.get("date"))
            roll = vote.get("roll_number", "?")
            question = (vote.get("question") or "Vote")[:40]
            result = vote.get("result", "?")
            murphy = vote.get("murphy_vote", "?")
            content += f"| {date} | {roll} | {question} | {result} | {murphy} |\n"

        content += "\n"

    content += """
---

[Back to Voting Record](index.md) | [Back to Dashboard](../index.md)
"""

    return content


def generate_consistency(consistency: dict) -> str:
    """Generate consistency analysis page."""
    inconsistent = consistency.get("inconsistent_bills", {})
    against_party = consistency.get("against_party_votes", [])
    against_cosponsored = consistency.get("voted_against_cosponsored", [])

    content = f"""# Consistency Analysis

## Summary

| Metric | Count |
|--------|-------|
| Bills with Inconsistent Positions | {consistency.get('inconsistent_bill_count', 0)} |
| Votes Against Party | {consistency.get('against_party_count', 0)} |
| Cosponsored Bills Voted Against | {consistency.get('voted_against_cosponsored_count', 0)} |

## Recent Votes Against Party

| Date | Roll | Legislation | Result | Murphy Vote |
|------|------|-------------|--------|-------------|
"""

    for vote in against_party[:25]:
        date = format_date(vote.get("date"))
        roll = vote.get("roll_number", "?")
        leg = f"{vote.get('legislation_type', '')} {vote.get('legislation_number', '')}"
        result = vote.get("result", "?")
        murphy = vote.get("murphy_vote", "?")
        content += f"| {date} | {roll} | {leg} | {result} | {murphy} |\n"

    content += """

## Bills with Inconsistent Positions

These are bills where Rep. Murphy voted differently across multiple stages
(e.g., supported an amendment but opposed final passage).

"""

    for bill_id, data in list(inconsistent.items())[:15]:
        content += f"\n### {bill_id}\n\n"
        content += "| Date | Roll | Question | Murphy Vote |\n"
        content += "|------|------|----------|-------------|\n"

        for vote in data["votes"]:
            date = format_date(vote.get("date"))
            roll = vote.get("roll_number", "?")
            question = (vote.get("question") or "Vote")[:35]
            murphy = vote.get("murphy_vote", "?")
            content += f"| {date} | {roll} | {question} | {murphy} |\n"

    content += """

---

[Back to Voting Record](index.md) | [Back to Dashboard](../index.md)
"""

    return content


def generate_sponsored(sponsored: list) -> str:
    """Generate sponsored legislation page."""
    # Sort by date (newest first)
    sponsored_sorted = sorted(
        sponsored,
        key=lambda x: x.get("introducedDate", ""),
        reverse=True
    )

    # Group by congress
    by_congress = {}
    for bill in sponsored_sorted:
        congress = bill.get("congress", "Unknown")
        by_congress.setdefault(congress, []).append(bill)

    content = f"""# Sponsored Legislation

Rep. Murphy has sponsored **{len(sponsored)}** bills.

"""

    for congress in sorted(by_congress.keys(), reverse=True):
        bills = by_congress[congress]
        content += f"\n## {congress}th Congress ({len(bills)} bills)\n\n"
        content += "| Bill | Title | Introduced | Latest Action |\n"
        content += "|------|-------|------------|---------------|\n"

        for bill in bills[:30]:  # Limit per congress
            bill_num = f"{bill.get('type', '')}{bill.get('number', '')}"
            title = (bill.get("title", "No title") or "No title")[:50]
            intro = bill.get("introducedDate", "?")[:10]
            action = (bill.get("latestAction", {}).get("text", "") or "")[:40]
            url = bill.get("url", "")

            if url:
                bill_link = f"[{bill_num}]({url})"
            else:
                bill_link = bill_num

            content += f"| {bill_link} | {title} | {intro} | {action} |\n"

    content += """

---

[Back to Dashboard](../index.md)
"""

    return content


def generate_cosponsored(cosponsored: list) -> str:
    """Generate cosponsored legislation page."""
    # Group by congress
    by_congress = {}
    for bill in cosponsored:
        congress = bill.get("congress", "Unknown")
        by_congress.setdefault(congress, []).append(bill)

    content = f"""# Cosponsored Legislation

Rep. Murphy has cosponsored **{len(cosponsored)}** bills.

| Congress | Count |
|----------|-------|
"""

    for congress in sorted(by_congress.keys(), reverse=True):
        content += f"| {congress}th | {len(by_congress[congress])} |\n"

    content += "\n## Recent Cosponsored Bills\n\n"
    content += "| Bill | Title | Introduced |\n"
    content += "|------|-------|------------|\n"

    # Most recent 50
    recent = sorted(cosponsored, key=lambda x: x.get("introducedDate", ""), reverse=True)[:50]
    for bill in recent:
        bill_num = f"{bill.get('type', '')}{bill.get('number', '')}"
        title = (bill.get("title", "No title") or "No title")[:60]
        intro = bill.get("introducedDate", "?")[:10]
        url = bill.get("url", "")

        if url:
            bill_link = f"[{bill_num}]({url})"
        else:
            bill_link = bill_num

        content += f"| {bill_link} | {title} | {intro} |\n"

    content += """

---

[Back to Dashboard](../index.md)
"""

    return content


def generate_rss(votes: list) -> str:
    """Generate RSS feed for recent votes."""
    # Sort by date descending, take last 50
    sorted_votes = sorted(
        votes,
        key=lambda x: x.get("date", ""),
        reverse=True
    )[:50]

    # Build RSS XML
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = ET.SubElement(rss, "channel")

    # Channel metadata
    ET.SubElement(channel, "title").text = "Rep. Greg Murphy Voting Record"
    ET.SubElement(channel, "link").text = "https://sdjohnso.github.io/greg-murphy-mirror"
    ET.SubElement(channel, "description").text = (
        "Daily updates on how Rep. Greg Murphy (NC-03) votes in Congress"
    )
    ET.SubElement(channel, "language").text = "en-us"

    # Self-reference link for RSS readers
    atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", "https://sdjohnso.github.io/greg-murphy-mirror/feeds/votes.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Last build date
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    # Add items
    for vote in sorted_votes:
        item = ET.SubElement(channel, "item")

        # Title: "HR 1234 - Voted AYE (with party)" or similar
        bill_id = f"{vote.get('legislation_type', '')} {vote.get('legislation_number', '')}".strip()
        if not bill_id:
            bill_id = f"Roll #{vote.get('roll_number', '?')}"

        murphy_vote = vote.get("murphy_vote", "?")
        with_party = vote.get("voted_with_party")
        party_note = ""
        if with_party is True:
            party_note = " (with party)"
        elif with_party is False:
            party_note = " (BROKE WITH PARTY)"

        title = f"{bill_id}: Voted {murphy_vote}{party_note}"
        ET.SubElement(item, "title").text = title

        # Link to Congress.gov
        link = vote.get("legislation_url", "")
        if not link:
            # Fall back to House Clerk roll call
            year = vote.get("date", "")[:4]
            roll = vote.get("roll_number", "")
            link = f"https://clerk.house.gov/evs/{year}/roll{roll}.xml"
        ET.SubElement(item, "link").text = link

        # GUID (unique identifier)
        guid = ET.SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"murphy-vote-{vote.get('congress', '')}-{vote.get('roll_number', '')}"

        # Publication date (RFC 2822 format)
        date_str = vote.get("date", "")
        if date_str:
            try:
                vote_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if vote_date.tzinfo is None:
                    vote_date = vote_date.replace(tzinfo=timezone.utc)
                ET.SubElement(item, "pubDate").text = format_datetime(vote_date)
            except:
                pass

        # Description with party breakdown
        party_totals = vote.get("party_totals", [])
        rep = next((p for p in party_totals if p.get("party") == "Republican"), {})
        dem = next((p for p in party_totals if p.get("party") == "Democratic"), {})

        desc_parts = [
            f"Murphy voted {murphy_vote}.",
            f"Result: {vote.get('result', 'Unknown')}.",
        ]

        if rep:
            desc_parts.append(f"Republicans: {rep.get('yea', 0)}-{rep.get('nay', 0)}.")
        if dem:
            desc_parts.append(f"Democrats: {dem.get('yea', 0)}-{dem.get('nay', 0)}.")

        ET.SubElement(item, "description").text = " ".join(desc_parts)

    # Convert to string with proper formatting
    ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')
    xml_str = ET.tostring(rss, encoding="unicode", method="xml")

    # Add XML declaration
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


def save_xml(content: str, path: Path):
    """Save XML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  Saved {path}")


def main():
    """Generate all documentation."""
    print("=" * 60)
    print("Generating Documentation")
    print("=" * 60)

    ensure_dirs()

    # Load data
    print("\nLoading data...")
    metrics = load_json(PROCESSED_DIR / "metrics.json")
    profile = load_json(RAW_DIR / "member" / "profile.json")
    votes = load_json(PROCESSED_DIR / "votes" / "all_votes.json")
    by_bill = load_json(PROCESSED_DIR / "votes" / "by_bill.json")
    consistency = load_json(PROCESSED_DIR / "consistency.json")
    sponsored = load_json(RAW_DIR / "sponsored" / "bills.json")
    cosponsored = load_json(RAW_DIR / "cosponsored" / "bills.json")

    # Generate docs
    print("\nGenerating pages...")

    save_md(generate_index(metrics, profile), DOCS_DIR / "index.md")
    save_md(generate_profile(profile), DOCS_DIR / "profile.md")
    save_md(generate_votes_index(metrics, votes), DOCS_DIR / "votes" / "index.md")
    save_md(generate_recent_votes(votes), DOCS_DIR / "votes" / "recent.md")
    save_md(generate_by_bill(by_bill), DOCS_DIR / "votes" / "by-bill.md")
    save_md(generate_consistency(consistency), DOCS_DIR / "votes" / "consistency.md")
    save_md(generate_sponsored(sponsored), DOCS_DIR / "legislation" / "sponsored.md")
    save_md(generate_cosponsored(cosponsored), DOCS_DIR / "legislation" / "cosponsored.md")

    # Generate RSS feed
    print("\nGenerating RSS feed...")
    save_xml(generate_rss(votes), DOCS_DIR / "feeds" / "votes.xml")

    print("\nDone!")


if __name__ == "__main__":
    main()
