// Murphy Dashboard - Data Loading and Rendering
// Organizes votes by date, then by bill for a timeline view

const BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? '..'
    : 'https://raw.githubusercontent.com/sdjohnso/greg-murphy-mirror/main';

async function loadData() {
    try {
        const [metricsRes, votesRes, consistencyRes] = await Promise.all([
            fetch(`${BASE_URL}/processed/metrics.json`),
            fetch(`${BASE_URL}/processed/votes/all_votes.json`),
            fetch(`${BASE_URL}/processed/consistency.json`)
        ]);

        const metrics = await metricsRes.json();
        const votes = await votesRes.json();
        const consistency = await consistencyRes.json();

        renderStats(metrics);
        renderVoteTimeline(votes);
        renderConsistencyAlerts(consistency);
        renderLastUpdated(metrics.generated_at);
    } catch (error) {
        console.error('Failed to load data:', error);
        document.getElementById('recent-votes').innerHTML =
            '<div class="error-message">Failed to load data. <a href="https://github.com/sdjohnso/greg-murphy-mirror">View on GitHub</a>.</div>';
    }
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
    // Sort by date descending
    const sorted = [...votes].sort((a, b) => new Date(b.date) - new Date(a.date));

    const grouped = {};

    sorted.forEach(vote => {
        const voteDate = new Date(vote.date);
        const dateKey = voteDate.toISOString().split('T')[0]; // YYYY-MM-DD

        // Initialize date group if needed
        if (!grouped[dateKey]) {
            grouped[dateKey] = {
                dateFormatted: voteDate.toLocaleDateString('en-US', {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric'
                }),
                bills: {},
                voteCount: 0
            };
        }

        // Create bill key
        const billKey = getBillKey(vote);

        // Initialize bill group if needed
        if (!grouped[dateKey].bills[billKey]) {
            grouped[dateKey].bills[billKey] = {
                displayId: getBillDisplayId(vote),
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

function getBillKey(vote) {
    if (vote.legislation_type && vote.legislation_number) {
        return `${vote.legislation_type}-${vote.legislation_number}`;
    }
    // For procedural votes without a bill
    return `roll-${vote.roll_number}`;
}

function getBillDisplayId(vote) {
    if (vote.legislation_type && vote.legislation_number) {
        return `${vote.legislation_type} ${vote.legislation_number}`;
    }
    return `Roll Call ${vote.roll_number}`;
}

function renderVoteTimeline(votes) {
    // Take recent votes (last 60 days worth or ~50 votes)
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - 60);

    const recentVotes = votes
        .filter(v => new Date(v.date) >= cutoffDate)
        .slice(0, 50);

    const grouped = groupVotesByDateAndBill(recentVotes);
    const container = document.getElementById('recent-votes');
    container.innerHTML = '';

    // Render each date group
    Object.entries(grouped).forEach(([dateKey, dateGroup]) => {
        const dateEl = document.createElement('div');
        dateEl.className = 'date-group';

        // Date header
        dateEl.innerHTML = `
            <div class="date-header">
                <span class="date-text">${dateGroup.dateFormatted}</span>
                <span class="vote-count">${dateGroup.voteCount} vote${dateGroup.voteCount > 1 ? 's' : ''}</span>
            </div>
        `;

        // Render each bill within this date
        Object.entries(dateGroup.bills).forEach(([billKey, billGroup]) => {
            const billEl = document.createElement('div');
            billEl.className = 'bill-group';

            // Bill header
            const billHeader = document.createElement('div');
            billHeader.className = 'bill-header';
            billHeader.innerHTML = `
                <span class="bill-id">
                    <a href="${billGroup.url}" target="_blank" rel="noopener">${billGroup.displayId}</a>
                </span>
                <span class="bill-meta">${billGroup.votes.length} roll call${billGroup.votes.length > 1 ? 's' : ''}</span>
            `;
            billEl.appendChild(billHeader);

            // Vote list
            const voteList = document.createElement('div');
            voteList.className = 'vote-list';

            billGroup.votes.forEach(vote => {
                const voteItem = createVoteItem(vote);
                voteList.appendChild(voteItem);
            });

            billEl.appendChild(voteList);
            dateEl.appendChild(billEl);
        });

        container.appendChild(dateEl);
    });
}

function createVoteItem(vote) {
    const item = document.createElement('div');
    item.className = 'vote-item';

    if (vote.voted_with_party === false) {
        item.classList.add('against-party');
    }

    // Vote badge
    const voteBadgeClass = getVoteBadgeClass(vote.murphy_vote);

    // Result badge
    const resultClass = vote.result.toLowerCase().includes('pass') ||
                       vote.result.toLowerCase().includes('agreed') ? 'passed' : 'failed';

    // Party breakdown
    const partyBreakdown = formatPartyBreakdown(vote.party_totals);

    // Vote type (if available from result text)
    const voteType = getVoteType(vote);

    item.innerHTML = `
        <span class="vote-badge ${voteBadgeClass}">${vote.murphy_vote}</span>
        <span class="result-badge ${resultClass}">${vote.result}</span>
        ${vote.voted_with_party === false ? '<span class="party-break-tag">Bipartisan</span>' : ''}
        <span class="party-split">${partyBreakdown}</span>
        ${voteType ? `<span class="vote-type">${voteType}</span>` : ''}
    `;

    return item;
}

function getVoteBadgeClass(vote) {
    const v = vote.toLowerCase();
    if (v === 'yea' || v === 'aye') return 'yea';
    if (v === 'nay' || v === 'no') return 'nay';
    if (v === 'not voting') return 'not-voting';
    return '';
}

function getVoteType(vote) {
    // Extract meaningful vote context from the result field
    const result = vote.result.toLowerCase();

    if (result.includes('motion to recommit')) return 'Motion to Recommit';
    if (result.includes('previous question')) return 'Previous Question';
    if (result.includes('motion to table')) return 'Motion to Table';
    if (result.includes('suspend the rules')) return 'Suspension';
    if (result.includes('amendment')) return 'Amendment';
    if (result.includes('concur')) return 'Concurrence';
    if (result.includes('conference report')) return 'Conference Report';
    if (result.includes('veto')) return 'Veto Override';

    // Check if it's a rule vote
    if (result.includes('rule') && !result.includes('suspend')) return 'Rule';

    // Final passage is implied if none of the above
    // Only show "Passage" if the result explicitly says it
    if (result.includes('passed') || result.includes('agreed')) return 'Passage';

    // Don't show procedural vote types like "Yea-and-Nay", "Recorded Vote", etc.
    return '';
}

function formatPartyBreakdown(partyTotals) {
    if (!partyTotals || partyTotals.length === 0) return '';

    const rep = partyTotals.find(p => p.party === 'Republican');
    const dem = partyTotals.find(p => p.party === 'Democratic');

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

    const againstParty = consistency.against_party_votes || [];
    const recentBreaks = againstParty
        .filter(v => new Date(v.date) >= ninetyDaysAgo)
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

        const examples = recentBreaks.map(vote => {
            const voteDate = new Date(vote.date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
            });
            const billId = vote.legislation_type && vote.legislation_number
                ? `${vote.legislation_type} ${vote.legislation_number}`
                : `Roll #${vote.roll_number}`;
            return `${voteDate} on ${billId}`;
        });

        html += examples.join(' • ') + '</p>';
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

// Load data on page load
document.addEventListener('DOMContentLoaded', loadData);
