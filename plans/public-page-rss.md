# Public-Facing Page + RSS Feed
**Branch:** `main`
**Created:** 2026-03-01
**Status:** Complete
**Next Action:** Verify all success criteria are met
**Purpose:** Create a shareable webpage and RSS feed so non-technical users can access Murphy's voting record

---

## Context

After the core mirror is operational (daily updates pulling from Congress.gov API), we need a human-friendly interface. The raw GitHub repo with JSON files and markdown isn't accessible to most constituents. This plan adds:

1. A simple, clean webpage hosted on GitHub Pages
2. An RSS feed people can subscribe to for vote notifications

This is intentionally minimal - not a full web app, just enough to make the data accessible.

---

## Architecture

### GitHub Pages Setup

GitHub Pages serves static files from a repo. We'll use the `/docs` folder as the source.

**URL:** `scottjohnson.github.io/greg-murphy-mirror`

### Directory Additions

```
docs/
├── index.html            # Main dashboard page (NEW)
├── assets/
│   ├── style.css         # Simple styling
│   └── app.js            # Fetch JSON, render page
├── feeds/
│   └── votes.xml         # RSS feed (NEW)
└── ... (existing markdown files)
```

### Page Content

Single-page dashboard showing:
- **Header:** Rep. Greg Murphy (NC-03) - Voting Record
- **Stats bar:** Participation %, Party Alignment %, Bipartisan Votes
- **Recent votes:** Last 10-20 votes with his position + party breakdown
- **Consistency alerts:** Any recent party breaks or position changes
- **Links:** Full data (GitHub), RSS feed, Congress.gov profile

### RSS Feed Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Rep. Greg Murphy Voting Record</title>
    <link>https://scottjohnson.github.io/greg-murphy-mirror</link>
    <description>Daily updates on how Rep. Greg Murphy (NC-03) votes in Congress</description>
    <item>
      <title>HR 1234 - Budget Act: Voted AYE (with party)</title>
      <link>https://congress.gov/bill/119/hr/1234</link>
      <pubDate>Mon, 01 Mar 2026 12:00:00 EST</pubDate>
      <description>Murphy voted AYE. Republicans: 215-5. Democrats: 10-198. Result: PASSED.</description>
    </item>
    ...
  </channel>
</rss>
```

---

## Files to Modify

| File | Why It's Being Modified |
|------|------------------------|
| `docs/index.html` | Main dashboard page |
| `docs/assets/style.css` | Page styling |
| `docs/assets/app.js` | JavaScript to load and render JSON data |
| `docs/feeds/votes.xml` | RSS feed file |
| `scripts/generate_docs.py` | Add RSS feed generation |
| `scripts/update_mirror.py` | Ensure RSS regenerates on each run |
| `README.md` | Add links to public page and RSS |

---

## Success Criteria

1. **Page Accessible**
   - [ ] GitHub Pages enabled and serving at expected URL
   - [ ] Page loads and displays current data
   - [ ] Mobile-responsive layout

2. **RSS Functional**
   - [ ] Feed validates (use W3C Feed Validator)
   - [ ] Subscribable in Feedly, NetNewsWire, or similar
   - [ ] New votes appear as new items

3. **Shareable**
   - [ ] URL is clean and memorable
   - [ ] Page looks professional enough to share publicly
   - [ ] No broken links or missing data

---

## Open Questions

1. **Styling approach:** Minimal custom CSS vs. a lightweight framework (Pico CSS, Simple.css)?
   - Recommendation: Pico CSS - classless, looks good out of the box

2. **JavaScript dependency:** Vanilla JS or a tiny library?
   - Recommendation: Vanilla JS - no build step, loads fast

3. **How many votes in RSS:** All votes or just last N?
   - Recommendation: Last 50 votes to keep feed size reasonable

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|

---

## Phase 1: GitHub Pages Setup

**Goal:** Enable GitHub Pages and create basic page structure

### Step 1.1: Enable GitHub Pages
- [x] Go to repo Settings → Pages
- [x] Set Source: Deploy from branch, main, /docs folder
- [x] Verify page is accessible at expected URL

**Resources:**
- GitHub Pages docs: https://docs.github.com/en/pages

**Validation:**
- URL returns 200, shows docs/index.md content

---

### Step 1.2: Create Dashboard Page
- [x] Create `docs/index.html` with basic structure
- [x] Add `docs/assets/style.css` with clean styling
- [x] Create `docs/assets/app.js` to fetch and render JSON
- [x] Display: stats, recent votes, consistency alerts
- [x] Add links to full repo and Congress.gov

**Resources:**
- Pico CSS: https://picocss.com
- Processed data: `processed/metrics.json`, `processed/votes/all_votes.json`

**Validation:**
- Page loads without errors
- Data displays correctly
- Responsive on mobile

**Next Session Prompt:**
```
I'm on branch `main`. GitHub Pages is enabled and dashboard page is created.
Review `plans/public-page-rss.md` and continue with Phase 2, Step 2.1 (RSS feed generation).
```

---

## Phase 2: RSS Feed

**Goal:** Generate subscribable RSS feed

### Step 2.1: Add RSS Generation to Scripts
- [x] Update `scripts/generate_docs.py` to create `docs/feeds/votes.xml`
- [x] Include last 50 votes as RSS items
- [x] Format dates as RFC 2822
- [x] Include Murphy's position, party totals, result, link to bill

**Resources:**
- RSS 2.0 spec: https://www.rssboard.org/rss-specification
- Python xml.etree for generation

**Validation:**
- Feed validates at https://validator.w3.org/feed/
- Opens correctly in RSS reader

---

### Step 2.2: Update Documentation
- [x] Add RSS link to `docs/index.html`
- [x] Add RSS autodiscovery `<link>` tag to HTML head
- [x] Update README with RSS subscription instructions

**Validation:**
- RSS readers auto-detect feed from page URL
- README instructions work

**Next Session Prompt:**
```
I'm on branch `main`. Public page and RSS feed are complete.
Verify all success criteria are met in `plans/public-page-rss.md`.
```

---

## Follow-Up Plans

### Email Newsletter
Convert RSS to email digest using Mailchimp RSS-to-Email or similar.

### Social Sharing
Add Open Graph meta tags so page previews nicely when shared on social media.

### Vote Alerts Bot
Discord/Slack bot that posts new votes automatically.

---

## Step 1 Prompt

```
Mirror is complete. Starting public page + RSS work.
Review `plans/public-page-rss.md` and begin with Phase 1, Step 1.1 (enable GitHub Pages).
```
