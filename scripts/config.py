"""
Greg Murphy Congressional Mirror - Configuration

Contains API settings, paths, and constants for Congress.gov data pulls.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Project Paths
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"
API_DIR = PROJECT_ROOT / "api"

# =============================================================================
# Congress.gov API Configuration
# =============================================================================

API_KEY = os.getenv("CONGRESS_API_KEY")
API_BASE_URL = "https://api.congress.gov/v3"

# Member endpoint
MEMBER_ENDPOINT = f"{API_BASE_URL}/member"
MEMBER_ID = "M001210"  # Greg Murphy's BioguideId

# Full member endpoints
MEMBER_PROFILE_URL = f"{MEMBER_ENDPOINT}/{MEMBER_ID}"
MEMBER_SPONSORED_URL = f"{MEMBER_ENDPOINT}/{MEMBER_ID}/sponsored-legislation"
MEMBER_COSPONSORED_URL = f"{MEMBER_ENDPOINT}/{MEMBER_ID}/cosponsored-legislation"

# House Roll Call Votes endpoint
# Format: /house-roll-call-vote/{congress}/{session}/{rollNumber}
# For listing: /house-roll-call-vote/{congress}
VOTE_ENDPOINT = f"{API_BASE_URL}/house-roll-call-vote"

# =============================================================================
# Member Information
# =============================================================================

MEMBER_INFO = {
    "name": "Gregory F. Murphy, M.D.",
    "bioguide_id": "M001210",
    "party": "Republican",
    "state": "North Carolina",
    "district": 3,
    "serving_since": "September 2019",
}

# Congresses to fetch (API has roll call votes from 2023+)
CONGRESSES = [118, 119]

# =============================================================================
# API Settings
# =============================================================================

# Pagination
MAX_RESULTS_PER_PAGE = 250  # Congress.gov API max

# Rate limiting
REQUEST_DELAY_SECONDS = 0.5  # Seconds between requests
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# Request timeout
REQUEST_TIMEOUT_SECONDS = 30

# =============================================================================
# Helper Functions
# =============================================================================

def get_api_params(offset: int = 0, limit: int = MAX_RESULTS_PER_PAGE) -> dict:
    """
    Get standard API parameters including authentication.

    Args:
        offset: Starting record number for pagination
        limit: Number of records to return (max 250)

    Returns:
        Dictionary of query parameters
    """
    if not API_KEY:
        raise ValueError(
            "CONGRESS_API_KEY environment variable not set. "
            "Get a key at https://api.congress.gov"
        )

    return {
        "api_key": API_KEY,
        "format": "json",
        "offset": offset,
        "limit": min(limit, MAX_RESULTS_PER_PAGE),
    }


def ensure_dirs():
    """Create all required directories if they don't exist."""
    dirs = [
        RAW_DIR / "member",
        RAW_DIR / "votes",
        RAW_DIR / "sponsored",
        RAW_DIR / "cosponsored",
        PROCESSED_DIR / "votes",
        PROCESSED_DIR / "legislation",
        DOCS_DIR / "votes",
        DOCS_DIR / "legislation",
        API_DIR / "v1" / "votes",
    ]

    for congress in CONGRESSES:
        dirs.append(RAW_DIR / "votes" / str(congress))
        dirs.append(DOCS_DIR / "votes" / str(congress))

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
