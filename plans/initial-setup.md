# Greg Murphy Congressional Mirror - Initial Setup
**Branch:** `main`
**Created:** 2026-02-28
**Status:** In Progress - Phase 3 complete
**Next Action:** Create update_mirror.py orchestrator script (Step 4.1)
**Purpose:** Create a public data mirror of Rep. Greg Murphy's congressional activity for transparent civic access

---

## Context

Scott wants to create a public mirror of Rep. Greg Murphy's (NC-03) congressional data, modeled after the successful NCDOT transportation mirror. The mirror will:
- Pull data daily from Congress.gov API
- Store raw JSON and processed data in a Git repository
- Generate human-readable markdown summaries
- Compute performance metrics (voting alignment, participation, bill success)
- Enable downstream consumers to build on the data without API keys

Greg Murphy (bioguideId: M001210) has served since September 2019, with 117 sponsored bills and 817 cosponsored bills across four Congresses (116th-119th).

---

## Architecture

### Data Sources

| Source | Endpoint | Data |
|--------|----------|------|
| Congress.gov API | `/member/M001210` | Profile, committees, leadership |
| Congress.gov API | `/member/M001210/sponsored-legislation` | Bills he authored |
| Congress.gov API | `/member/M001210/cosponsored-legislation` | Bills he signed onto |
| Congress.gov API | `/house-roll-call-vote/{congress}` | All House votes (filter for his votes) |

### API Details
- **Base URL:** `https://api.congress.gov/v3`
- **Auth:** API key via `api_key` query parameter
- **Rate Limit:** 5,000 requests/hour
- **Format:** JSON (specify `format=json`)
- **Pagination:** `offset` and `limit` parameters (max 250 per request)

### Directory Structure

```
greg-murphy-mirror/
├── plans/                        # Plan management
│   └── initial-setup.md
├── raw/                          # Raw API responses
│   ├── member/
│   │   └── profile.json          # Member endpoint response
│   ├── votes/
│   │   ├── 118/                  # By Congress
│   │   │   ├── 2023/             # By year
│   │   │   │   └── votes.json
│   │   │   └── 2024/
│   │   └── 119/
│   ├── sponsored/
│   │   └── bills.json
│   └── cosponsored/
│       └── bills.json
├── processed/                    # Transformed/enriched data
│   ├── votes/
│   │   ├── all_votes.json        # Consolidated with his positions + party totals
│   │   ├── by_bill.json          # Grouped by bill - all votes on same legislation
│   │   ├── by_topic.json         # Categorized by policy area
│   │   └── by_result.json        # Grouped by outcome
│   ├── legislation/
│   │   ├── sponsored_summary.json
│   │   └── cosponsored_summary.json
│   ├── consistency.json          # Position changes and inconsistencies
│   └── metrics.json              # Computed performance stats
├── docs/                         # Human-readable output
│   ├── index.md                  # Dashboard/overview
│   ├── profile.md                # Bio and committees
│   ├── votes/
│   │   ├── index.md              # Vote summary
│   │   ├── 119/                  # By Congress
│   │   │   └── index.md
│   │   ├── recent.md             # Last 30 days
│   │   ├── by-bill.md            # Bills with full vote history
│   │   └── consistency.md        # Position changes, party breaks
│   └── legislation/
│       ├── sponsored.md
│       └── cosponsored.md
├── scripts/
│   ├── config.py                 # API config, paths, constants
│   ├── pull_member.py            # Fetch member profile
│   ├── pull_votes.py             # Fetch roll call votes
│   ├── pull_legislation.py       # Fetch sponsored/cosponsored
│   ├── generate_metrics.py       # Compute performance stats
│   ├── generate_docs.py          # Create markdown files
│   └── update_mirror.py          # Orchestrator script
├── .github/
│   └── workflows/
│       └── update-mirror.yml     # Daily automation
├── .gitignore
├── requirements.txt
├── README.md
└── LAST_UPDATED.md               # Auto-generated status
```

### Data Flow

```
Congress.gov API
       │
       ▼
┌─────────────────┐
│  Pull Scripts   │  (pull_member.py, pull_votes.py, pull_legislation.py)
└────────┬────────┘
         │
         ▼
    raw/*.json         ← Raw API responses preserved
         │
         ▼
┌─────────────────┐
│ generate_metrics│  (compute voting %, alignment, participation)
└────────┬────────┘
         │
         ▼
  processed/*.json     ← Enriched/aggregated data
         │
         ▼
┌─────────────────┐
│  generate_docs  │  (create markdown summaries)
└────────┬────────┘
         │
         ▼
    docs/*.md          ← Human-readable output
         │
         ▼
   Git commit/push     ← GitHub Actions automation
```

### Metrics to Compute

| Metric | Description |
|--------|-------------|
| `participation_rate` | % of votes where he voted (not "Not Voting") |
| `party_alignment` | % votes matching Republican majority |
| `bipartisan_votes` | Count/% of votes against party majority |
| `bill_success_rate` | % of sponsored bills that passed House |
| `cosponsorship_rate` | Avg cosponsors on his bills |
| `votes_by_topic` | Breakdown by policy area |
| `votes_with_outcome` | How often on winning side |

---

## Files to Modify

| File | Why It's Being Modified |
|------|------------------------|
| `scripts/config.py` | Central configuration for API, paths, constants |
| `scripts/pull_member.py` | Fetch member profile and committees |
| `scripts/pull_votes.py` | Fetch all House votes and extract Murphy's positions |
| `scripts/pull_legislation.py` | Fetch sponsored and cosponsored bills |
| `scripts/generate_metrics.py` | Compute performance statistics |
| `scripts/generate_docs.py` | Create markdown documentation |
| `scripts/update_mirror.py` | Orchestrate full update process |
| `.github/workflows/update-mirror.yml` | GitHub Actions daily automation |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Ignore patterns |
| `README.md` | Project documentation |

---

## Success Criteria

1. **Data Completeness**
   - [ ] All House roll call votes for 118th-119th Congress with Murphy's position
   - [ ] All 117 sponsored bills with status
   - [ ] All 817 cosponsored bills with status
   - [ ] Current committee assignments

2. **Automation**
   - [ ] Daily GitHub Actions workflow runs without failure
   - [ ] Changes auto-committed with timestamps
   - [ ] LAST_UPDATED.md reflects latest run

3. **Data Quality**
   - [ ] Metrics compute correctly (spot-check against Congress.gov)
   - [ ] No missing votes in date ranges covered by API
   - [ ] Bill statuses match Congress.gov

4. **Usability**
   - [ ] Raw JSON fetchable via GitHub raw URLs
   - [ ] Markdown docs render correctly on GitHub
   - [ ] README explains how to use the data

---

## Open Questions

1. **API Key Storage:** Use GitHub Secrets for Actions? Document for local dev?
   - Resolved: Yes, use `CONGRESS_API_KEY` secret in GitHub Actions

2. **Historical Depth:** Go back to 116th Congress (his full tenure) or start with current?
   - Recommendation: Start with 118th-119th (API has votes from 2023+), note limitation

3. **Vote Detail Level:** Store full vote details or just Murphy's position?
   - Recommendation: Store both - full vote in raw/, Murphy's position in processed/

4. **Update Frequency:** Daily sufficient or more frequent?
   - Recommendation: Daily at 6 AM EST (votes typically finalized by then)

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-28 | Use file-based storage (JSON + Markdown) | Matches NCDOT pattern, enables Git versioning, no database dependency |
| 2026-02-28 | BioguideId M001210 confirmed | Verified via Congress.gov |
| 2026-02-28 | Target 118th Congress onward for votes | API only has roll call votes from 2023+ |
| 2026-03-01 | Add by_bill.json grouping | Bills have multiple votes (amendments, recommit, passage); grouping shows full legislative journey |
| 2026-03-01 | Public repository | Enable anyone to access data without API keys |
| 2026-03-01 | Link to bill text, don't cache | Keep repo size manageable; bills can be 100+ pages |
| 2026-03-01 | Include party vote totals | Enable "voted with party" vs "broke with party" analysis |
| 2026-03-01 | Track position consistency | Flag when Murphy's votes on same bill differ across stages |
| 2026-03-01 | Floor votes only | Committee votes not available via API; floor votes sufficient for v1 |
| 2026-03-01 | No notifications for v1 | Silent git commits; notifications as follow-up plan |

---

## Phase 1: Project Setup

**Goal:** Establish project structure, dependencies, and configuration

### Step 1.1: Create Directory Structure
- [x] Create all directories (raw/, processed/, docs/, scripts/, .github/workflows/)
- [x] Create .gitignore
- [x] Create requirements.txt
- [x] Create initial README.md

**Resources:**
- Project root: `/Users/scottjohnson/Documents/Python-Projects/greg-murphy-mirror`

**Validation:**
- All directories exist
- `pip install -r requirements.txt` succeeds

---

### Step 1.2: Create Configuration Module
- [x] Create `scripts/config.py` with API settings
- [x] Define paths, constants, bioguide ID
- [x] Add rate limiting and retry settings

**Resources:**
- NCDOT pattern: `/Users/scottjohnson/Documents/Python-Projects/ncdot-transportation-mirror/scripts/config.py`
- Congress.gov API docs: https://api.congress.gov

**Validation:**
- Config imports without error
- API base URL and endpoints correct

---

### Step 1.3: Obtain and Configure API Key
- [x] Register at api.congress.gov
- [x] Test API key with simple request
- [x] Document key usage in README
- [x] Set up `.env` pattern for local development

**Resources:**
- API signup: https://api.congress.gov
- API key docs: https://api.data.gov/docs/api-key/

**Validation:**
- `curl "https://api.congress.gov/v3/member/M001210?api_key=YOUR_KEY"` returns data

**Next Session Prompt:**
```
I'm on branch `main`. Project structure and config are set up.
Review `plans/initial-setup.md` and continue with Phase 2, Step 2.1 (pull_member.py).
```

---

## Phase 2: Data Pull Scripts

**Goal:** Create scripts to fetch all data from Congress.gov API

### Step 2.1: Member Profile Script
- [x] Create `scripts/pull_member.py`
- [x] Fetch `/member/M001210` endpoint
- [x] Extract profile, terms, committees
- [x] Save to `raw/member/profile.json`
- [x] Add pagination for nested data
- [x] Add retry logic and rate limiting

**Resources:**
- Member endpoint docs: https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md
- NCDOT pull pattern: `ncdot-transportation-mirror/scripts/pull_stip.py`

**Validation:**
- Script runs without error
- `raw/member/profile.json` contains expected fields
- Committees list populated

---

### Step 2.2: Votes Pull Script
- [x] Create `scripts/pull_votes.py`
- [x] Fetch House roll call votes for 118th, 119th Congress
- [x] Paginate through all votes (250 per request max)
- [x] For each vote, extract Murphy's position from member votes
- [x] Save raw votes to `raw/votes/{congress}/{year}/votes.json`
- [x] Create consolidated `processed/votes/all_votes.json` with his positions

**Resources:**
- House Roll Call endpoint: https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/HouseRollCallVoteEndpoint.md
- Murphy bioguideId: M001210

**Validation:**
- Vote counts match Congress.gov
- Each vote has Murphy's position (Aye/Nay/Not Voting)
- Date ranges cover full Congress sessions

---

### Step 2.3: Legislation Pull Script
- [x] Create `scripts/pull_legislation.py`
- [x] Fetch `/member/M001210/sponsored-legislation`
- [x] Fetch `/member/M001210/cosponsored-legislation`
- [x] Paginate through all results
- [x] Save to `raw/sponsored/bills.json` and `raw/cosponsored/bills.json`
- [x] Extract key fields: bill number, title, status, date, subjects

**Resources:**
- Member legislation endpoint: part of MemberEndpoint.md
- Expected counts: 117 sponsored, 817 cosponsored

**Validation:**
- Sponsored count matches 117
- Cosponsored count matches 817
- Bill statuses include latest action

**Next Session Prompt:**
```
I'm on branch `main`. All pull scripts are complete and tested.
Review `plans/initial-setup.md` and continue with Phase 3, Step 3.1 (generate_metrics.py).
```

---

## Phase 3: Data Processing

**Goal:** Transform raw data into useful metrics and aggregations

### Step 3.1: Metrics Generation Script
- [x] Create `scripts/generate_metrics.py`
- [ ] Compute participation rate
- [ ] Compute party alignment percentage
- [ ] Compute bipartisan vote count
- [ ] Compute bill success rate
- [ ] Aggregate votes by topic/policy area
- [ ] Include party vote totals with each vote record:
  - Republican aye/nay/present/not voting counts
  - Democrat aye/nay/present/not voting counts
  - Overall result
  - Flag: `voted_with_party` (boolean)
- [ ] Group votes by bill (`processed/votes/by_bill.json`)
  - Key by bill identifier (e.g., "HR-1234")
  - Include all votes on that bill (amendments, recommit, passage)
  - Show Murphy's position at each stage
  - Include bill metadata (title, status, sponsor)
  - Link to full bill details via `legislationUrl`
  - Flag: `consistent` (boolean) - did he vote same way throughout?
  - If inconsistent, note which votes differed
- [ ] Generate consistency report (`processed/consistency.json`)
  - Bills where Murphy voted differently at different stages
  - Cosponsored bills he voted against
  - Amendments he supported but final bill he opposed (or vice versa)
- [ ] Save metrics to `processed/metrics.json`

**Resources:**
- Raw votes: `raw/votes/`
- Raw legislation: `raw/sponsored/`, `raw/cosponsored/`
- Vote fields for grouping: `legislationType`, `legislationNumber`, `voteQuestion`
- Party totals from: `votePartyTotal` in API response

**Validation:**
- Metrics JSON valid and complete
- Spot-check participation rate against manual count
- Party alignment reasonable (typically 90%+ for most members)
- by_bill.json shows multiple votes for major legislation
- consistency.json flags any inconsistent voting patterns

---

### Step 3.2: Documentation Generation Script
- [x] Create `scripts/generate_docs.py`
- [ ] Generate `docs/index.md` - overview dashboard
- [ ] Generate `docs/profile.md` - bio and committees
- [ ] Generate `docs/votes/index.md` - vote summary
- [ ] Generate `docs/votes/recent.md` - last 30 days
- [ ] Generate `docs/votes/by-bill.md` - bills with multiple votes showing full history
- [ ] Generate `docs/votes/consistency.md` - position changes and party breaks
- [ ] Generate `docs/legislation/sponsored.md`
- [ ] Generate `docs/legislation/cosponsored.md`

**Resources:**
- Processed data: `processed/`
- Raw data for details: `raw/`
- NCDOT doc generation: `ncdot-transportation-mirror/scripts/generate_markdown.py`

**Validation:**
- All markdown files render correctly on GitHub
- Links between documents work
- Data matches raw sources

**Next Session Prompt:**
```
I'm on branch `main`. Metrics and docs generation complete.
Review `plans/initial-setup.md` and continue with Phase 4, Step 4.1 (orchestrator script).
```

---

## Phase 4: Automation

**Goal:** Create orchestration and GitHub Actions for daily updates

### Step 4.1: Orchestrator Script
- [ ] Create `scripts/update_mirror.py`
- [ ] Call all pull scripts in sequence
- [ ] Call metrics generation
- [ ] Call docs generation
- [ ] Update LAST_UPDATED.md with run status
- [ ] Add command-line args for update types (full, daily)
- [ ] Add logging and error handling

**Resources:**
- NCDOT orchestrator: `ncdot-transportation-mirror/scripts/update_mirror.py`
- All scripts in `scripts/`

**Validation:**
- `python scripts/update_mirror.py full` runs end-to-end
- LAST_UPDATED.md reflects run timestamp
- All data files updated

---

### Step 4.2: GitHub Actions Workflow
- [ ] Create `.github/workflows/update-mirror.yml`
- [ ] Schedule daily at 6 AM EST (11:00 UTC)
- [ ] Set up Python environment
- [ ] Install dependencies
- [ ] Run orchestrator with API key from secrets
- [ ] Auto-commit and push changes
- [ ] Add manual dispatch option

**Resources:**
- NCDOT workflow: `ncdot-transportation-mirror/.github/workflows/update-mirror.yml`
- GitHub Actions docs

**Validation:**
- Manual dispatch works
- Commits appear with bot attribution
- Secrets properly accessed

---

### Step 4.3: Final Documentation
- [ ] Complete README.md with usage instructions
- [ ] Document data schema
- [ ] Add examples for downstream consumers
- [ ] Add contribution guidelines

**Validation:**
- README renders correctly
- Examples work when copy-pasted

**Next Session Prompt:**
```
I'm on branch `main`. Full automation is complete.
Review `plans/initial-setup.md` and verify all success criteria are met.
```

---

## Follow-Up Plans

### Public-Facing Page + RSS
**Moved to separate plan:** `plans/public-page-rss.md`

### Vote Comparison Tool
Allow comparing Murphy's votes to another representative. Would require pulling both members' data.

### Press Releases Integration
**RSS Source:** `https://murphy.house.gov/rss.xml`
- Currently returns photo galleries, not press releases
- May need to scrape press release page or find alternate source
- Congress.gov has member alerts but not full press release text
- GovInfo.gov has additional RSS feeds worth investigating

### Email/RSS Alerts
Notify subscribers when new votes are recorded.

**How notifications could work:**
1. **GitHub Actions + Email:** After daily update, if new votes detected, send email via SendGrid/SES
2. **RSS Feed Generation:** Generate `feeds/votes.xml` that RSS readers can subscribe to
3. **Webhook:** POST to a URL (Slack, Discord, Zapier) when new votes appear
4. **GitHub Watch:** Users can "Watch" the repo and get notified of commits

Congress.gov also offers native alerts:
- Member alerts when Murphy sponsors/cosponsors bills
- Congressional Record alerts for floor statements
- Sign up at: https://www.congress.gov/rss

### Historical Backfill
If Congress.gov API expands to include older votes, backfill 116th-117th Congress data.

### Performance Dashboard
Static site (GitHub Pages) with charts showing voting trends, alignment over time.

---

## Step 1 Prompt

```
I'm starting the Greg Murphy congressional mirror project.
Review `plans/initial-setup.md` and begin with Phase 1, Step 1.1 (create directory structure).
The project is at /Users/scottjohnson/Documents/Python-Projects/greg-murphy-mirror.
```
