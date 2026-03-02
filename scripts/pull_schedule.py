#!/usr/bin/env python3 -u
"""
Pull House weekly schedule from the Majority Leader's website.

Scrapes the upcoming floor schedule and outputs structured JSON with
bills grouped by day and categorized by procedure type (suspension vs rule).
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import (
    PROCESSED_DIR,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)

# Majority Leader weekly schedule URL
SCHEDULE_URL = "https://www.majorityleader.gov/schedule/weekly-schedule.htm"

# Current congress number
CURRENT_CONGRESS = 119


def fetch_with_retry(url: str) -> str:
    """
    Fetch URL with retry logic.

    Args:
        url: URL to fetch

    Returns:
        HTML text

    Raises:
        requests.RequestException: After all retries exhausted
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise


def parse_bill_id(text: str) -> tuple[str, str, int] | None:
    """
    Parse a bill ID like 'H.R. 6365' or 'H.J. Res. 139'.

    Args:
        text: Text containing bill ID

    Returns:
        Tuple of (formatted_id, bill_type, bill_number) or None
    """
    # Match various House bill formats
    patterns = [
        (r'H\.?\s*R\.?\s*(\d+)', 'H.R.'),  # H.R. 6365
        (r'H\.?\s*Res\.?\s*(\d+)', 'H.Res.'),  # H. Res. 123
        (r'H\.?\s*J\.?\s*Res\.?\s*(\d+)', 'H.J.Res.'),  # H.J. Res. 139
        (r'H\.?\s*Con\.?\s*Res\.?\s*(\d+)', 'H.Con.Res.'),  # H. Con. Res. 38
    ]

    for pattern, bill_type in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            bill_number = int(match.group(1))
            formatted_id = f"{bill_type} {bill_number}"
            return formatted_id, bill_type, bill_number
    return None


def get_congress_url(bill_type: str, bill_number: int) -> str:
    """
    Generate Congress.gov URL for a bill.

    Args:
        bill_type: Type like 'H.R.' or 'H.J.Res.'
        bill_number: Bill number

    Returns:
        Congress.gov URL
    """
    # Map bill types to Congress.gov URL segments
    type_map = {
        'H.R.': 'house-bill',
        'HR': 'house-bill',
        'H.RES.': 'house-resolution',
        'HRES': 'house-resolution',
        'H.J.RES.': 'house-joint-resolution',
        'HJRES': 'house-joint-resolution',
        'H.CON.RES.': 'house-concurrent-resolution',
        'HCONRES': 'house-concurrent-resolution',
    }

    # Normalize bill type
    normalized = bill_type.upper().replace(' ', '').replace('.', '')
    for key, value in type_map.items():
        if key.replace('.', '').replace(' ', '') == normalized:
            return f"https://www.congress.gov/bill/{CURRENT_CONGRESS}th-congress/{value}/{bill_number}"

    # Default to house-bill if unknown
    return f"https://www.congress.gov/bill/{CURRENT_CONGRESS}th-congress/house-bill/{bill_number}"


def parse_schedule(html: str) -> dict:
    """
    Parse the weekly schedule HTML.

    Args:
        html: Raw HTML from majorityleader.gov

    Returns:
        Structured schedule dict
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Find the main content span
    content = soup.find('span', class_='middlecopy')
    if not content:
        print("  Warning: Could not find schedule content")
        return {"days": [], "generated_at": datetime.now().isoformat(), "week_of": None}

    # Calculate the Monday of the current week for week_of
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_of = monday.strftime('%Y-%m-%d')

    # Extract bill information by finding links and their following text
    bill_info = {}
    links = content.find_all('a', href=True)

    for i, link in enumerate(links):
        link_text = link.get_text(strip=True)
        parsed = parse_bill_id(link_text)
        if not parsed:
            continue

        formatted_id, bill_type, bill_number = parsed
        title = ""
        sponsor = ""

        # Get text that follows this link until the next link or paragraph break
        # Walk through siblings after this link
        following_text = []
        for sibling in link.next_siblings:
            if sibling.name == 'a':
                break  # Stop at next link
            if hasattr(sibling, 'get_text'):
                following_text.append(sibling.get_text())
            elif isinstance(sibling, str):
                following_text.append(sibling)
            # Stop if we hit a line break followed by another bill pattern
            text_so_far = ''.join(following_text)
            if '\n' in text_so_far or '<br' in str(sibling):
                # Check if there's a sponsor pattern, if so we have complete info
                if re.search(r'\(Sponsored', text_so_far, re.IGNORECASE):
                    break

        combined_text = ''.join(following_text)

        # Extract title - text after em-dash until opening paren or end
        title_match = re.search(r'[–\-]\s*([^(]+?)(?:\s*\(|$)', combined_text)
        if title_match:
            title = title_match.group(1).strip()
            # Clean up common suffixes
            title = re.sub(r',?\s*as amended\s*$', '', title, flags=re.IGNORECASE).strip()
            # Remove trailing whitespace and non-breaking spaces
            title = title.replace('\xa0', ' ').strip()

        # Extract sponsor from parentheses
        sponsor_match = re.search(r'\(Sponsored\s+by\s+([^)]+)\)', combined_text, re.IGNORECASE)
        if sponsor_match:
            sponsor = sponsor_match.group(1).strip()
            # Clean up non-breaking spaces
            sponsor = sponsor.replace('\xa0', ' ').strip()

        bill_info[formatted_id] = {
            'bill_id': formatted_id,
            'bill_type': bill_type,
            'bill_number': bill_number,
            'title': title,
            'sponsor': sponsor,
            'congress_url': get_congress_url(bill_type, bill_number)
        }

    # Now parse the structure to get days and procedures
    text = content.get_text(separator='\n')
    lines = text.split('\n')

    days = []
    current_day = None
    current_procedure = "suspension"  # Default
    current_date = None

    # Regex patterns
    day_pattern = re.compile(r'^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),?\s*(\w+\s+\d+)?', re.IGNORECASE)
    suspension_pattern = re.compile(r'Suspension\s+of\s+the\s+Rules', re.IGNORECASE)
    rule_pattern = re.compile(r'Pursuant\s+to\s+a\s+Rule', re.IGNORECASE)
    may_be_considered_pattern = re.compile(r'may\s+be\s+considered', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for day header
        day_match = day_pattern.match(line)
        if day_match:
            if current_day and current_day.get('bills'):
                days.append(current_day)

            day_name = day_match.group(1).title()
            date_str = day_match.group(2) if day_match.group(2) else None

            # Try to parse the date
            if date_str:
                try:
                    parsed_date = datetime.strptime(f"{date_str} {today.year}", "%B %d %Y")
                    current_date = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    current_date = None

            current_day = {
                'day': day_name,
                'date': current_date,
                'bills': []
            }
            current_procedure = "suspension"
            continue

        # Check for procedure type headers
        if suspension_pattern.search(line):
            current_procedure = "suspension"
            continue

        if rule_pattern.search(line):
            current_procedure = "rule"
            continue

        if may_be_considered_pattern.search(line):
            current_procedure = "may_be_considered"
            continue

        # Check for bill references
        if current_day:
            parsed = parse_bill_id(line)
            if parsed:
                formatted_id, bill_type, bill_number = parsed

                # Get cached bill info
                if formatted_id in bill_info:
                    info = bill_info[formatted_id]
                    bill_entry = {
                        'bill_id': formatted_id,
                        'title': info['title'],
                        'procedure': current_procedure,
                        'sponsor': info['sponsor'],
                        'congress_url': info['congress_url']
                    }
                else:
                    bill_entry = {
                        'bill_id': formatted_id,
                        'title': '',
                        'procedure': current_procedure,
                        'sponsor': '',
                        'congress_url': get_congress_url(bill_type, bill_number)
                    }

                # Avoid duplicates
                existing_ids = [b['bill_id'] for b in current_day['bills']]
                if formatted_id not in existing_ids:
                    current_day['bills'].append(bill_entry)

    # Don't forget the last day
    if current_day and current_day.get('bills'):
        days.append(current_day)

    return {
        'generated_at': datetime.now().isoformat(),
        'week_of': week_of,
        'days': days
    }


def save_schedule(schedule: dict) -> Path:
    """
    Save schedule to processed directory.

    Args:
        schedule: Parsed schedule dict

    Returns:
        Path to saved file
    """
    schedule_dir = PROCESSED_DIR / "schedule"
    schedule_dir.mkdir(parents=True, exist_ok=True)

    output_path = schedule_dir / "weekly.json"
    with open(output_path, "w") as f:
        json.dump(schedule, f, indent=2)

    return output_path


def main():
    """Main entry point."""
    print("=" * 60)
    print("Pulling House Weekly Schedule")
    print("=" * 60)

    print(f"\nFetching schedule from {SCHEDULE_URL}...")
    try:
        html = fetch_with_retry(SCHEDULE_URL)
    except requests.RequestException as e:
        print(f"ERROR: Could not fetch schedule: {e}")
        # Create empty schedule on failure
        schedule = {
            'generated_at': datetime.now().isoformat(),
            'week_of': None,
            'days': [],
            'error': str(e)
        }
        output_path = save_schedule(schedule)
        print(f"  Saved empty schedule to {output_path}")
        return

    print("  Parsing schedule content...")
    schedule = parse_schedule(html)

    output_path = save_schedule(schedule)

    # Summary
    total_bills = sum(len(day['bills']) for day in schedule['days'])
    print(f"\nSummary:")
    print(f"  Week of: {schedule['week_of']}")
    print(f"  Days with legislation: {len(schedule['days'])}")
    print(f"  Total bills scheduled: {total_bills}")

    for day in schedule['days']:
        print(f"    {day['day']}: {len(day['bills'])} bills")

    print(f"\nSaved to {output_path}")
    print("\nDone!")


if __name__ == "__main__":
    main()
