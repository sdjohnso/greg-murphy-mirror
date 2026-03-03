// Murphy Dashboard - Data Loading and Rendering
// Organizes votes by date, then by bill for a timeline view

const BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? '..'
    : 'https://raw.githubusercontent.com/sdjohnso/greg-murphy-mirror/main';

// Global state for toggle
let currentView = 'recent'; // 'recent' or 'coming-up'
let scheduleData = null;

// Reusable email SVG icon to avoid duplicating inline SVG markup
const EMAIL_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>';

async function loadData() {
    try {
        // Fetch metrics first (smallest payload, drives above-the-fold stats)
        // then fire off remaining fetches in parallel
        const metricsRes = await fetch(`${BASE_URL}/processed/metrics.json`);
        const metrics = await metricsRes.json();
        renderStats(metrics);
        renderLastUpdated(metrics.generated_at);

        // Now fetch the heavier data in parallel
        const [votesRes, consistencyRes, scheduleRes] = await Promise.all([
            fetch(`${BASE_URL}/processed/votes/all_votes.json`),
            fetch(`${BASE_URL}/processed/consistency.json`),
            fetch(`${BASE_URL}/processed/schedule/weekly.json`).catch(() => null)
        ]);

        const votes = await votesRes.json();
        const consistency = await consistencyRes.json();

        // Schedule is optional - may not exist yet
        if (scheduleRes && scheduleRes.ok) {
            scheduleData = await scheduleRes.json();
        } else {
            scheduleData = { days: [] };
        }

        renderComingUp(scheduleData);
        renderVoteTimeline(votes);
        renderConsistencyAlerts(consistency);
        setupToggle();
    } catch (error) {
        console.error('Failed to load data:', error);
        document.getElementById('recent-votes').innerHTML =
            '<div class="error-message">Failed to load data. <a href="https://github.com/sdjohnso/greg-murphy-mirror">View on GitHub</a>.</div>';
    }
}

/**
 * Setup toggle button handlers
 */
function setupToggle() {
    const comingUpBtn = document.getElementById('toggle-coming-up');
    const recentBtn = document.getElementById('toggle-recent');
    const comingUpView = document.getElementById('coming-up');
    const recentView = document.getElementById('recent-votes');
    const rollingLabel = document.getElementById('rolling-label');

    comingUpBtn.addEventListener('click', () => {
        currentView = 'coming-up';
        comingUpBtn.classList.add('active');
        recentBtn.classList.remove('active');
        comingUpView.style.display = 'flex';
        recentView.style.display = 'none';
        rollingLabel.textContent = 'This week';
    });

    recentBtn.addEventListener('click', () => {
        currentView = 'recent';
        recentBtn.classList.add('active');
        comingUpBtn.classList.remove('active');
        recentView.style.display = 'flex';
        comingUpView.style.display = 'none';
        rollingLabel.textContent = '60-day rolling';
    });
}

/**
 * Render the Coming Up schedule view
 */
function renderComingUp(schedule) {
    const container = document.getElementById('coming-up');

    if (!schedule || !schedule.days || schedule.days.length === 0) {
        container.innerHTML = `
            <div class="coming-up-empty">
                <h3>No Legislation Currently Scheduled</h3>
                <p>The House floor schedule will appear here when bills are scheduled for upcoming votes.</p>
            </div>
        `;
        return;
    }

    // Build all HTML as a string, then set once (single DOM write)
    let html = '';

    schedule.days.forEach(day => {
        const dateDisplay = day.date
            ? new Date(day.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
            : '';

        html += `<div class="coming-up-day">
            <div class="coming-up-day-header">
                <span class="day-text">${day.day}${dateDisplay ? ', ' + dateDisplay : ''}</span>
                <span class="bill-count">${day.bills.length} bill${day.bills.length > 1 ? 's' : ''}</span>
            </div>`;

        day.bills.forEach(bill => {
            const procedureLabel = getProcedureLabel(bill.procedure);
            const emailSubject = encodeURIComponent(`Regarding ${bill.bill_id}`);
            const emailBody = encodeURIComponent(`Dear Rep. Murphy,\n\nI am writing regarding ${bill.bill_id}${bill.title ? ' - ' + bill.title : ''}.\n\n`);
            const mailtoLink = `mailto:greg.murphy@mail.house.gov?subject=${emailSubject}&body=${emailBody}`;

            html += `<div class="coming-up-bill">
                <div class="coming-up-bill-header">
                    <span class="coming-up-bill-id">
                        <a href="${bill.congress_url}" target="_blank" rel="noopener">${bill.bill_id}</a>
                    </span>
                    <span class="procedure-badge ${bill.procedure}">${procedureLabel}</span>
                </div>
                ${bill.title ? `<div class="coming-up-bill-title">${bill.title}</div>` : ''}
                ${bill.sponsor ? `<div class="coming-up-bill-sponsor">${bill.sponsor}</div>` : ''}
                <div class="coming-up-bill-actions">
                    <a href="${mailtoLink}"
                       class="email-rep"
                       title="Email Rep. Murphy about this bill"
                       onclick="trackEmailClick('${bill.bill_id}')">
                        ${EMAIL_SVG}
                        Contact Rep. Murphy
                    </a>
                </div>
            </div>`;
        });

        html += '</div>';
    });

    container.innerHTML = html;
}

/**
 * Get human-readable procedure label
 */
const PROCEDURE_LABELS = {
    'suspension': 'Suspension',
    'rule': 'Under Rule',
    'may_be_considered': 'May Be Considered'
};

function getProcedureLabel(procedure) {
    return PROCEDURE_LABELS[procedure] || procedure;
}

function renderStats(metrics) {
    const summary = metrics.summary;
    document.getElementById('stat-participation').textContent = `${summary.participation_rate}%`;
    document.getElementById('stat-alignment').textContent = `${summary.party_alignment_rate}%`;
    document.getElementById('stat-bipartisan').textContent = summary.bipartisan_votes;
    document.getElementById('stat-bills').textContent = summary.bills_sponsored;
}

/**
 * Groups votes by date, then by bill within each date
 * Returns structure: { dateKey: { dateFormatted, bills: { billKey: { votes: [], ... } } } }
 */
function groupVotesByDateAndBill(votes) {
    // Sort by date descending using cached timestamps
    const sorted = [...votes].sort((a, b) => {
        const ta = a._ts || (a._ts = new Date(b.date).getTime());
        const tb = b._ts || (b._ts = new Date(a.date).getTime());
        // Note: reversed for descending
        return tb - ta;
    });

    const grouped = {};
    const dateFormatOptions = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' };

    sorted.forEach(vote => {
        // Use a simple string split for dateKey instead of creating a Date object
        const dateKey = vote.date.split('T')[0];

        // Initialize date group if needed
        if (!grouped[dateKey]) {
            const voteDate = new Date(vote.date);
            grouped[dateKey] = {
                dateFormatted: voteDate.toLocaleDateString('en-US', dateFormatOptions),
                bills: {},
                voteCount: 0
            };
        }

        // Create bill key
        const billKey = vote.legislation_type && vote.legislation_number
            ? `${vote.legislation_type}-${vote.legislation_number}`
            : `roll-${vote.roll_number}`;

        // Initialize bill group if needed
        if (!grouped[dateKey].bills[billKey]) {
            grouped[dateKey].bills[billKey] = {
                displayId: vote.legislation_type && vote.legislation_number
                    ? `${vote.legislation_type} ${vote.legislation_number}`
                    : `Roll Call ${vote.roll_number}`,
                url: vote.legislation_url,
                votes: []
            };
        }

        // Add vote to bill group
        grouped[dateKey].bills[billKey].votes.push(vote);
        grouped[dateKey].voteCount++;
    });

    return grouped;
}

function renderVoteTimeline(votes) {
    // Take recent votes (last 60 days worth or ~50 votes)
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - 60);
    const cutoffTime = cutoffDate.getTime();

    const recentVotes = votes
        .filter(v => new Date(v.date).getTime() >= cutoffTime)
        .slice(0, 50);

    const grouped = groupVotesByDateAndBill(recentVotes);
    const container = document.getElementById('recent-votes');

    // Build entire timeline as HTML string for a single DOM write
    let html = '';

    Object.entries(grouped).forEach(([dateKey, dateGroup]) => {
        html += `<div class="date-group">
            <div class="date-header">
                <span class="date-text">${dateGroup.dateFormatted}</span>
                <span class="vote-count">${dateGroup.voteCount} vote${dateGroup.voteCount > 1 ? 's' : ''}</span>
            </div>`;

        Object.entries(dateGroup.bills).forEach(([billKey, billGroup]) => {
            const emailSubject = encodeURIComponent(`Regarding ${billGroup.displayId}`);
            const emailBody = encodeURIComponent(`Dear Rep. Murphy,\n\nI am writing regarding ${billGroup.displayId}.\n\n`);
            const mailtoLink = `mailto:greg.murphy@mail.house.gov?subject=${emailSubject}&body=${emailBody}`;

            html += `<div class="bill-group">
                <div class="bill-header">
                    <span class="bill-id">
                        <a href="${billGroup.url}" target="_blank" rel="noopener">${billGroup.displayId}</a>
                    </span>
                    <span class="bill-meta">
                        ${billGroup.votes.length} roll call${billGroup.votes.length > 1 ? 's' : ''}
                        <a href="${mailtoLink}"
                           class="email-rep"
                           title="Email Rep. Murphy about this bill"
                           onclick="trackEmailClick('${billGroup.displayId}')">
                            ${EMAIL_SVG}
                        </a>
                    </span>
                </div>
                <div class="vote-list">`;

            billGroup.votes.forEach(vote => {
                html += buildVoteItemHTML(vote);
            });

            html += '</div></div>';
        });

        html += '</div>';
    });

    container.innerHTML = html;
}

function buildVoteItemHTML(vote) {
    const voteBadgeClass = getVoteBadgeClass(vote.murphy_vote);
    const resultLower = vote.result.toLowerCase();
    const resultClass = resultLower.includes('pass') || resultLower.includes('agreed') ? 'passed' : 'failed';
    const partyBreakdown = formatPartyBreakdown(vote.party_totals);
    const voteType = getVoteType(resultLower);
    const againstParty = vote.voted_with_party === false;

    return `<div class="vote-item${againstParty ? ' against-party' : ''}">
        <span class="vote-badge ${voteBadgeClass}">${vote.murphy_vote}</span>
        <span class="result-badge ${resultClass}">${vote.result}</span>
        ${againstParty ? '<span class="party-break-tag">Bipartisan</span>' : ''}
        <span class="party-split">${partyBreakdown}</span>
        ${voteType ? `<span class="vote-type">${voteType}</span>` : ''}
    </div>`;
}

function getVoteBadgeClass(vote) {
    const v = vote.toLowerCase();
    if (v === 'yea' || v === 'aye') return 'yea';
    if (v === 'nay' || v === 'no') return 'nay';
    if (v === 'not voting') return 'not-voting';
    return '';
}

function getVoteType(resultLower) {
    // Accept pre-lowercased result string to avoid redundant .toLowerCase() calls
    if (resultLower.includes('motion to recommit')) return 'Motion to Recommit';
    if (resultLower.includes('previous question')) return 'Previous Question';
    if (resultLower.includes('motion to table')) return 'Motion to Table';
    if (resultLower.includes('suspend the rules')) return 'Suspension';
    if (resultLower.includes('amendment')) return 'Amendment';
    if (resultLower.includes('concur')) return 'Concurrence';
    if (resultLower.includes('conference report')) return 'Conference Report';
    if (resultLower.includes('veto')) return 'Veto Override';
    if (resultLower.includes('rule') && !resultLower.includes('suspend')) return 'Rule';
    if (resultLower.includes('passed') || resultLower.includes('agreed')) return 'Passage';
    return '';
}

function formatPartyBreakdown(partyTotals) {
    if (!partyTotals || partyTotals.length === 0) return '';

    let rep = null, dem = null;
    for (let i = 0; i < partyTotals.length; i++) {
        if (partyTotals[i].party === 'Republican') rep = partyTotals[i];
        else if (partyTotals[i].party === 'Democratic') dem = partyTotals[i];
        if (rep && dem) break;
    }

    if (!rep || !dem) return '';

    return `R ${rep.yea}-${rep.nay} | D ${dem.yea}-${dem.nay}`;
}

function renderConsistencyAlerts(consistency) {
    const container = document.getElementById('consistency-alerts');
    const totalBreaks = consistency.against_party_count ||
                       (consistency.against_party_votes ? consistency.against_party_votes.length : 0);

    // Get recent party breaks (last 90 days)
    const ninetyDaysAgo = new Date();
    ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
    const cutoffTime = ninetyDaysAgo.getTime();

    const againstParty = consistency.against_party_votes || [];
    const recentBreaks = againstParty
        .filter(v => new Date(v.date).getTime() >= cutoffTime)
        .slice(0, 5);

    let html = `
        <div class="consistency-stat">
            <span class="number">${totalBreaks}</span>
            <span class="label">times voted against Republican majority</span>
        </div>
    `;

    if (recentBreaks.length === 0) {
        html += `<p class="consistency-note">No bipartisan votes in the past 90 days.</p>`;
    } else {
        html += `<p class="consistency-note"><strong>Recent examples:</strong> `;

        const shortDateOptions = { month: 'short', day: 'numeric' };
        const examples = recentBreaks.map(vote => {
            const voteDate = new Date(vote.date).toLocaleDateString('en-US', shortDateOptions);
            const billId = vote.legislation_type && vote.legislation_number
                ? `${vote.legislation_type} ${vote.legislation_number}`
                : `Roll #${vote.roll_number}`;
            return `${voteDate} on ${billId}`;
        });

        html += examples.join(' &bull; ') + '</p>';
    }

    container.innerHTML = html;
}

function renderLastUpdated(timestamp) {
    if (!timestamp) return;

    const date = new Date(timestamp);
    const formatted = date.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    });

    document.getElementById('last-updated').textContent = `Last updated: ${formatted}`;
}

/**
 * Track email link clicks (for analytics integration)
 */
function trackEmailClick(billId) {
    // If Google Analytics is present, send event
    if (typeof gtag === 'function') {
        gtag('event', 'email_click', {
            'bill_id': billId,
            'event_category': 'engagement'
        });
    }

    // Store in localStorage for simple tracking
    try {
        const clicks = JSON.parse(localStorage.getItem('emailClicks') || '[]');
        clicks.push({ billId, timestamp: new Date().toISOString() });
        localStorage.setItem('emailClicks', JSON.stringify(clicks.slice(-100)));
    } catch (e) {
        // localStorage may be unavailable in private browsing
    }
}

// With defer attribute, DOMContentLoaded is guaranteed — call loadData directly
loadData();
