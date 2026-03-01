// Murphy Dashboard - Data Loading and Rendering

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
        renderRecentVotes(votes);
        renderConsistencyAlerts(consistency);
        renderLastUpdated(metrics.generated_at);
    } catch (error) {
        console.error('Failed to load data:', error);
        document.getElementById('recent-votes').innerHTML =
            '<p>Failed to load data. <a href="https://github.com/sdjohnso/greg-murphy-mirror">View on GitHub</a>.</p>';
    }
}

function renderStats(metrics) {
    const summary = metrics.summary;

    document.getElementById('stat-participation').textContent = `${summary.participation_rate}%`;
    document.getElementById('stat-alignment').textContent = `${summary.party_alignment_rate}%`;
    document.getElementById('stat-bipartisan').textContent = summary.bipartisan_votes;
    document.getElementById('stat-bills').textContent = summary.bills_sponsored;
}

function renderRecentVotes(votes) {
    // Sort by date descending and take most recent 15
    const sortedVotes = [...votes].sort((a, b) =>
        new Date(b.date) - new Date(a.date)
    ).slice(0, 15);

    const container = document.getElementById('recent-votes');
    container.removeAttribute('aria-busy');
    container.innerHTML = '';

    sortedVotes.forEach(vote => {
        const card = createVoteCard(vote);
        container.appendChild(card);
    });
}

function createVoteCard(vote) {
    const card = document.createElement('article');
    card.className = 'vote-card';

    if (vote.voted_with_party === true) {
        card.classList.add('with-party');
    } else if (vote.voted_with_party === false) {
        card.classList.add('against-party');
    }

    const billId = vote.legislation_type && vote.legislation_number
        ? `${vote.legislation_type} ${vote.legislation_number}`
        : `Roll ${vote.roll_number}`;

    const voteDate = new Date(vote.date);
    const formattedDate = voteDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });

    const murphyVoteClass = getMurphyVoteClass(vote.murphy_vote);
    const resultClass = vote.result.toLowerCase().includes('pass') ? 'result-passed' : 'result-failed';

    const partyBreakdown = formatPartyBreakdown(vote.party_totals);
    const withPartyText = vote.voted_with_party === false
        ? '<em>(Broke with party)</em>'
        : '';

    card.innerHTML = `
        <header>
            <div>
                <span class="bill-id">
                    <a href="${vote.legislation_url}" target="_blank">${billId}</a>
                </span>
                ${withPartyText}
            </div>
            <span class="vote-date">${formattedDate}</span>
        </header>
        <div>
            <span class="murphy-vote ${murphyVoteClass}">${vote.murphy_vote}</span>
            <span class="result ${resultClass}">- ${vote.result}</span>
        </div>
        <div class="party-breakdown">${partyBreakdown}</div>
    `;

    return card;
}

function getMurphyVoteClass(vote) {
    const v = vote.toLowerCase();
    if (v === 'yea' || v === 'aye') return 'yea';
    if (v === 'nay' || v === 'no') return 'nay';
    if (v === 'not voting') return 'not-voting';
    return '';
}

function formatPartyBreakdown(partyTotals) {
    if (!partyTotals || partyTotals.length === 0) return '';

    const rep = partyTotals.find(p => p.party === 'Republican');
    const dem = partyTotals.find(p => p.party === 'Democratic');

    if (!rep || !dem) return '';

    return `R: ${rep.yea}-${rep.nay} | D: ${dem.yea}-${dem.nay}`;
}

function renderConsistencyAlerts(consistency) {
    const container = document.getElementById('consistency-alerts');

    // Get recent party breaks (last 90 days)
    const ninetyDaysAgo = new Date();
    ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);

    const againstParty = consistency.against_party_votes || [];
    const recentBreaks = againstParty
        .filter(v => new Date(v.date) >= ninetyDaysAgo)
        .slice(0, 5);

    // Build summary
    const totalBreaks = consistency.against_party_count || againstParty.length;

    let html = `<p><strong>${totalBreaks} total bipartisan votes</strong> (voting against Republican majority)</p>`;

    if (recentBreaks.length === 0) {
        html += '<p class="no-alerts">No party-break votes in the past 90 days.</p>';
    } else {
        html += '<p>Recent examples:</p>';
        recentBreaks.forEach(vote => {
            const voteDate = new Date(vote.date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });

            const billId = vote.legislation_type && vote.legislation_number
                ? `${vote.legislation_type} ${vote.legislation_number}`
                : `Roll #${vote.roll_number}`;

            const clerkUrl = `https://clerk.house.gov/evs/${new Date(vote.date).getFullYear()}/roll${vote.roll_number}.xml`;

            html += `
                <div class="alert-card party-break">
                    <strong>${voteDate}:</strong> Voted <strong>${vote.murphy_vote}</strong> on
                    <a href="${clerkUrl}" target="_blank">${billId}</a>
                    - broke with Republican majority (${vote.result})
                </div>
            `;
        });
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
