/** Patient progress: trends, check-in history and goal milestones. */

async function renderPatientProgress() {
    renderDashboardShell('patient', 'progress', 'My Progress', `
        <div class="page-header">
            <h1>My Progress</h1>
            <p>Visualize your recovery journey over time</p>
        </div>

        <div class="card glass" id="scoreCard" style="margin-bottom: var(--space-6);">
            <div class="card-header"><h3>Recovery Score</h3></div>
            <div id="scoreGauge">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="dashboard-grid cols-2" style="margin-bottom: var(--space-6);">
            <div class="card glass" id="cravingTrendCard">
                <div class="card-header"><h3>Craving Trend (14 days)</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass" id="stressTrendCard">
                <div class="card-header"><h3>Stress Trend (14 days)</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="dashboard-grid cols-2" style="margin-bottom: var(--space-6);">
            <div class="card glass" id="moodTrendCard">
                <div class="card-header"><h3>Mood Trend (14 days)</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass" id="sleepTrendCard">
                <div class="card-header"><h3>Sleep Trend (14 days)</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="card glass" id="goalMilestones" style="margin-bottom: var(--space-6);">
            <div class="card-header"><h3>Recovery Milestones</h3></div>
            <div class="loading-overlay"><div class="spinner"></div></div>
        </div>

        <div class="card glass" id="timelineCard" style="margin-bottom: var(--space-6);">
            <div class="card-header"><h3>Recovery Timeline</h3></div>
            <div id="recoveryTimeline">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="card glass" id="checkinHistory">
            <div class="card-header"><h3>Check-in History</h3></div>
            <div class="loading-overlay"><div class="spinner"></div><span>Loading history...</span></div>
        </div>
    `);

    try {
        const [checkinsData, goalsData] = await Promise.all([
            api.get('/patient/checkins?limit=30'),
            api.get('/patient/goals'),
        ]);

        _renderIntensityTrend(checkinsData.checkins, {
            cardId: 'cravingTrendCard', field: 'craving_level',
            title: 'Craving Trend (14 days)', emptyIcon: '🌊', label: 'craving',
        });
        _renderIntensityTrend(checkinsData.checkins, {
            cardId: 'stressTrendCard', field: 'stress_level',
            title: 'Stress Trend (14 days)', emptyIcon: '🌡️', label: 'stress',
        });
        _renderMoodTrend(checkinsData.checkins);
        _renderSleepTrend(checkinsData.checkins);
        _renderMilestones(goalsData.goals);
        _renderCheckinHistory(checkinsData.checkins);
    } catch (err) {
        showToast('Failed to load progress data', 'error');
    }

    // Score and timeline load independently of the trend charts
    loadScoreInto('scoreGauge', '/patient/recovery-score');
    const me = api.getUser();
    if (me?.id) loadTimelineInto('recoveryTimeline', me.id);
}


/* ── Intensity Trend (cravings, stress) ─────────────── */

function _renderIntensityTrend(checkins, cfg) {
    const card = document.getElementById(cfg.cardId);
    if (!card) return;

    const recent = checkins.slice(0, 14).reverse();

    if (recent.length === 0) {
        card.innerHTML = `
            <div class="card-header"><h3>${escapeHtml(cfg.title)}</h3></div>
            <div class="empty-state">
                <div class="empty-icon">${escapeHtml(cfg.emptyIcon)}</div>
                <div class="empty-title">No Data Yet</div>
                <div class="empty-desc">Start checking in daily to see your ${escapeHtml(cfg.label)} trend.</div>
            </div>
        `;
        return;
    }

    const bars = recent.map(ci => {
        const val = ci[cfg.field];
        if (val == null) return '';
        const pct = (val / 10) * 100;
        const color = val <= 3 ? 'var(--accent-success)' :
                      val <= 6 ? 'var(--accent-warning)' :
                      'var(--accent-danger)';
        const dateLabel = ci.date ? ci.date.slice(5) : '?';
        return `
            <div class="trend-bar-col" title="${escapeHtml(cfg.label)}: ${val}/10 on ${escapeHtml(ci.date)}">
                <div class="trend-bar-value">${val}</div>
                <div class="trend-bar" style="height: ${pct}%; background: ${color};"></div>
                <div class="trend-bar-label">${dateLabel}</div>
            </div>
        `;
    }).join('');

    card.innerHTML = `
        <div class="card-header"><h3>${escapeHtml(cfg.title)}</h3></div>
        <div class="trend-chart-container">
            <div class="trend-bar-chart">${bars}</div>
        </div>
    `;
}


/* ── Sleep Trend ─────────────────────────────── */

function _renderSleepTrend(checkins) {
    const card = document.getElementById('sleepTrendCard');
    if (!card) return;

    const recent = checkins.slice(0, 14).reverse();

    if (recent.length === 0) {
        card.innerHTML = `
            <div class="card-header"><h3>Sleep Trend (14 days)</h3></div>
            <div class="empty-state">
                <div class="empty-icon">😴</div>
                <div class="empty-title">No Data Yet</div>
                <div class="empty-desc">Start checking in daily to see your sleep trend.</div>
            </div>
        `;
        return;
    }

    // Scaled against a 10-hour ceiling; 7-9h reads as the healthy band
    const bars = recent.map(ci => {
        const hours = ci.sleep_hours ?? 0;
        const pct = Math.min(100, (hours / 10) * 100);
        const color = hours >= 7 && hours <= 9 ? 'var(--accent-success)' :
                      hours >= 5 ? 'var(--accent-warning)' :
                      'var(--accent-danger)';
        const dateLabel = ci.date ? ci.date.slice(5) : '?';
        return `
            <div class="trend-bar-col" title="Sleep: ${hours}h on ${escapeHtml(ci.date)}">
                <div class="trend-bar-value">${hours}</div>
                <div class="trend-bar" style="height: ${pct}%; background: ${color};"></div>
                <div class="trend-bar-label">${dateLabel}</div>
            </div>
        `;
    }).join('');

    card.innerHTML = `
        <div class="card-header"><h3>Sleep Trend (14 days)</h3></div>
        <div class="trend-chart-container">
            <div class="trend-bar-chart">${bars}</div>
        </div>
    `;
}


/* ── Mood Trend Visualization ────────────────────────────── */

function _renderMoodTrend(checkins) {
    const card = document.getElementById('moodTrendCard');
    if (!card) return;

    const recent = checkins.slice(0, 14).reverse();

    if (recent.length === 0) {
        card.innerHTML = `
            <div class="card-header"><h3>Mood Trend (14 days)</h3></div>
            <div class="empty-state">
                <div class="empty-icon">🧠</div>
                <div class="empty-title">No Data Yet</div>
                <div class="empty-desc">Start checking in daily to see your mood trend.</div>
            </div>
        `;
        return;
    }

    const moodMap = { good: { emoji: '😊', value: 3, color: 'var(--accent-success)' },
                      neutral: { emoji: '😐', value: 2, color: 'var(--accent-warning)' },
                      poor: { emoji: '😔', value: 1, color: 'var(--accent-danger)' } };

    const dots = recent.map(ci => {
        const m = moodMap[ci.mood] || moodMap.neutral;
        const pct = (m.value / 3) * 100;
        const dateLabel = ci.date ? ci.date.slice(5) : '?';
        return `
            <div class="trend-bar-col" title="Mood: ${escapeHtml(ci.mood)} on ${escapeHtml(ci.date)}">
                <div class="trend-bar-value">${escapeHtml(m.emoji)}</div>
                <div class="trend-bar" style="height: ${pct}%; background: ${escapeHtml(m.color)};"></div>
                <div class="trend-bar-label">${dateLabel}</div>
            </div>
        `;
    }).join('');

    card.innerHTML = `
        <div class="card-header"><h3>Mood Trend (14 days)</h3></div>
        <div class="trend-chart-container">
            <div class="trend-bar-chart">${dots}</div>
        </div>
    `;
}


/* ── Recovery Milestones ─────────────────────────────────── */

function _renderMilestones(goals) {
    const card = document.getElementById('goalMilestones');
    if (!card) return;

    if (!goals || goals.length === 0) {
        card.innerHTML = `
            <div class="card-header"><h3>Recovery Milestones</h3></div>
            <div class="empty-state">
                <div class="empty-icon">🎯</div>
                <div class="empty-title">No Goals Yet</div>
                <div class="empty-desc">Your doctor will set recovery milestones for you.</div>
            </div>
        `;
        return;
    }

    const completedCount = goals.filter(g => g.status === 'completed').length;
    const progressPct = goals.length > 0 ? Math.round((completedCount / goals.length) * 100) : 0;

    const goalItems = goals.map(g => {
        const isComplete = g.status === 'completed';
        const isActive = g.status === 'in_progress';
        return `
            <div class="milestone-item ${isComplete ? 'completed' : ''} ${isActive ? 'active' : ''}">
                <div class="milestone-marker">
                    ${isComplete ? '✓' : isActive ? '◑' : '○'}
                </div>
                <div class="milestone-content">
                    <span class="milestone-title">${escapeHtml(g.title)}</span>
                    ${g.target_date ? `<span class="milestone-date">${formatDateShort(g.target_date)}</span>` : ''}
                </div>
                <span class="badge ${isComplete ? 'badge-success' : isActive ? 'badge-warning' : 'badge-secondary'}">
                    ${g.status.replace('_', ' ')}
                </span>
            </div>
        `;
    }).join('');

    card.innerHTML = `
        <div class="card-header">
            <h3>Recovery Milestones</h3>
            <span class="badge badge-primary">${completedCount}/${escapeHtml(goals.length)} complete</span>
        </div>
        <div style="padding: var(--space-4);">
            <div class="progress-bar-container">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${progressPct}%;"></div>
                </div>
                <span class="progress-bar-label">${progressPct}% overall progress</span>
            </div>
            <div class="milestones-list">
                ${goalItems}
            </div>
        </div>
    `;
}


/* ── Check-in History Table ──────────────────────────────── */

function _renderCheckinHistory(checkins) {
    const container = document.getElementById('checkinHistory');
    if (!container) return;

    if (!checkins || checkins.length === 0) {
        container.innerHTML = `
            <div class="card-header"><h3>Check-in History</h3></div>
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <div class="empty-title">No Check-ins Yet</div>
                <div class="empty-desc">Your daily check-in history will appear here.</div>
            </div>
        `;
        return;
    }

    const levelColor = (v) => v == null ? 'var(--text-muted)'
        : v <= 3 ? 'var(--accent-success)' : v <= 6 ? 'var(--accent-warning)' : 'var(--accent-danger)';
    const moodEmoji = { good: '😊', neutral: '😐', poor: '😔' };

    container.innerHTML = `
        <div class="card-header"><h3>Check-in History</h3></div>
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Cravings</th>
                        <th>Stress</th>
                        <th>Mood</th>
                        <th>Sleep</th>
                        <th>Medication</th>
                        <th>Activity</th>
                    </tr>
                </thead>
                <tbody>
                    ${checkins.map(ci => `
                        <tr>
                            <td style="font-weight: 500;">${formatDateShort(ci.date) || ci.date}</td>
                            <td>
                                <span class="level-badge" style="color: ${levelColor(ci.craving_level)}; font-weight: 600;">
                                    ${ci.craving_level ?? '—'}/10
                                </span>
                            </td>
                            <td>
                                <span class="level-badge" style="color: ${levelColor(ci.stress_level)}; font-weight: 600;">
                                    ${ci.stress_level ?? '—'}/10
                                </span>
                            </td>
                            <td>${moodEmoji[ci.mood] || ci.mood} ${escapeHtml(ci.mood)}</td>
                            <td>${escapeHtml(ci.sleep_hours)}h</td>
                            <td>
                                <span class="badge ${ci.medication_taken ? 'badge-success' : 'badge-danger'}">
                                    ${ci.medication_taken ? 'Yes' : 'No'}
                                </span>
                            </td>
                            <td style="font-size: var(--text-xs); color: var(--text-secondary);">
                                ${ci.physical_activity_minutes ? ci.physical_activity_minutes + ' min' : '—'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}
