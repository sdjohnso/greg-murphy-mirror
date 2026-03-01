# Greg Murphy Congressional Mirror

A public data mirror of Rep. Greg Murphy's (NC-03) congressional activity, providing transparent civic access to voting records, sponsored legislation, and performance metrics.

## Key Metrics

| Metric | Value |
|--------|-------|
| **Participation Rate** | 84.6% |
| **Party Alignment** | 95.2% |
| **Bipartisan Votes** | 67 |
| **Bills Sponsored** | 117 |
| **Bills Cosponsored** | 817 |

**Live Dashboard**: [sdjohnso.github.io/greg-murphy-mirror](https://sdjohnso.github.io/greg-murphy-mirror)

**RSS Feed**: [Subscribe to vote updates](https://sdjohnso.github.io/greg-murphy-mirror/feeds/votes.xml)

## Representative Profile

- **Name**: Gregory F. Murphy, M.D.
- **District**: North Carolina's 3rd Congressional District
- **Party**: Republican
- **Serving Since**: September 2019
- **BioguideId**: M001210

## Data Available

### Voting Records
- **1,681 House floor votes** (118th-119th Congress)
- Murphy's position on each vote (Yea/Nay/Not Voting)
- Party alignment analysis (voted with/against Republican majority)
- Votes grouped by bill for multi-stage analysis

### Legislation
- **117 sponsored bills** with status and latest action
- **817 cosponsored bills** across 4 Congresses
- Breakdown by Congress and policy area

### Analysis
- **Consistency analysis**: Bills where Murphy voted differently at different stages
- **Bipartisan votes**: Times he broke with party majority
- **Bills with multiple votes**: Amendments, recommit motions, final passage

## Directory Structure

```
greg-murphy-mirror/
├── raw/                    # Raw API responses
│   ├── member/             # Member profile
│   ├── votes/              # Roll call votes by Congress/year
│   ├── sponsored/          # Sponsored legislation
│   └── cosponsored/        # Cosponsored legislation
├── processed/              # Transformed data
│   ├── votes/              # Consolidated votes with Murphy's positions
│   ├── metrics.json        # Performance statistics
│   └── consistency.json    # Voting consistency analysis
├── docs/                   # Human-readable markdown
│   ├── index.md            # Dashboard
│   ├── votes/              # Voting record pages
│   └── legislation/        # Legislation pages
└── scripts/                # Update scripts
```

## Usage

### View Documentation

Browse the [docs/](docs/) directory on GitHub for formatted summaries:
- [Dashboard](docs/index.md)
- [Voting Record](docs/votes/index.md)
- [Recent Votes](docs/votes/recent.md)
- [Sponsored Legislation](docs/legislation/sponsored.md)

### Raw Data Access

Access JSON data directly via GitHub raw URLs:

```bash
# Member profile
curl https://raw.githubusercontent.com/sdjohnso/greg-murphy-mirror/main/raw/member/profile.json

# All votes with Murphy's positions
curl https://raw.githubusercontent.com/sdjohnso/greg-murphy-mirror/main/processed/votes/all_votes.json

# Performance metrics
curl https://raw.githubusercontent.com/sdjohnso/greg-murphy-mirror/main/processed/metrics.json
```

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/sdjohnso/greg-murphy-mirror.git
   cd greg-murphy-mirror
   ```

2. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Get a Congress.gov API key at [api.congress.gov](https://api.congress.gov)

4. Create `.env` file:
   ```bash
   echo 'CONGRESS_API_KEY=your_key_here' > .env
   ```

5. Run the update script:
   ```bash
   python scripts/update_mirror.py full   # Full update
   python scripts/update_mirror.py daily  # Daily update (votes only)
   ```

## Data Sources

- **Congress.gov API**: Member profile, sponsored/cosponsored legislation
- **House Clerk XML**: Individual vote positions from official roll call records

## Update Schedule

Data is updated daily at 6 AM EST via GitHub Actions. Manual updates can be triggered from the Actions tab.

## License

Data sourced from Congress.gov is in the public domain. This repository's code is available under the MIT License.
