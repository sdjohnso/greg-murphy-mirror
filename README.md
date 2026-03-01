# Greg Murphy Congressional Mirror

A public data mirror of Rep. Greg Murphy's (NC-03) congressional activity, providing transparent civic access to voting records, sponsored legislation, and performance metrics.

## Overview

This repository automatically pulls data from the Congress.gov API daily and stores:

- **Raw data**: Unmodified API responses in `raw/`
- **Processed data**: Aggregated metrics and analysis in `processed/`
- **Documentation**: Human-readable summaries in `docs/`

## Representative Profile

- **Name**: Gregory F. Murphy, M.D.
- **District**: North Carolina's 3rd Congressional District
- **Party**: Republican
- **Serving Since**: September 2019
- **BioguideId**: M001210

## Data Available

### Voting Records
- All House floor votes (118th Congress onwards)
- Party alignment analysis
- Votes grouped by bill and topic

### Legislation
- 117 sponsored bills
- 817 cosponsored bills
- Bill status and progression

### Metrics
- Participation rate
- Party alignment percentage
- Bipartisan voting record
- Bill success rate

## Usage

### Raw Data Access

Access raw JSON data directly via GitHub raw URLs:

```
https://raw.githubusercontent.com/YOUR_USERNAME/greg-murphy-mirror/main/raw/member/profile.json
```

### Local Development

1. Clone the repository
2. Copy `.env.example` to `.env` and add your Congress.gov API key
3. Install dependencies: `pip install -r requirements.txt`
4. Run the update script: `python scripts/update_mirror.py full`

### Getting a Congress.gov API Key

1. Visit [api.congress.gov](https://api.congress.gov)
2. Sign up for a free API key
3. Store the key in your `.env` file as `CONGRESS_API_KEY`

## Data Sources

All data is sourced from the official [Congress.gov API](https://api.congress.gov).

## Update Schedule

Data is updated daily at 6 AM EST via GitHub Actions.

## License

Data sourced from Congress.gov is in the public domain. This repository's code is available under the MIT License.

## Contributing

Issues and pull requests are welcome. Please see the documentation in `docs/` for data schema details.
