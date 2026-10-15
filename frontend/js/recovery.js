/** Score gauge, timeline and digital twin, shared by the patient, doctor and guardian views. */

const SCORE_BANDS = {
    strong: { color: 'var(--accent-success)', rgb: 'var(--accent-success-rgb)', icon: '🌟' },
    steady: { color: 'var(--accent-info)', rgb: 'var(--accent-info-rgb)', icon: '📈' },
    fragile: { color: 'var(--accent-warning)', rgb: 'var(--accent-warning-rgb)', icon: '⚠️' },
    at_risk: { color: 'var(--accent-danger)', rgb: 'var(--accent-danger-rgb)', icon: '🚨' },
};

const TREND_CONFIG = {
    improving: { icon: '▲', label: 'Improving', color: 'var(--accent-success)' },
    stable: { icon: '▬', label: 'Stable', color: 'var(--accent-info)' },
    declining: { icon: '▼', label: 'Declining', color: 'var(--accent-danger)' },
};

const TIMELINE_EVENT_CONFIG = {
    checkin: { icon: '📝', color: 'var(--accent-info)' },
    note: { icon: '📋', color: 'var(--accent-primary)' },
    goal: { icon: '🎯', color: 'var(--accent-success)' },
    medication: { icon: '💊', color: 'var(--accent-warning)' },
    vitals: { icon: '❤️', color: 'var(--accent-danger)' },
    appointment: { icon: '📅', color: 'var(--accent-info)' },
    intervention: { icon: '🤝', color: 'var(--accent-primary)' },
    care_plan: { icon: '🗺️', color: 'var(--accent-secondary)' },
};


/* ── Score Gauge ────────────────────────────────────────── */

/** The score gauge and its breakdown; `compact` shows just the gauge. */
function renderScoreGauge(data, options = {}) {
    const compact = options.compact === true;

    if (data.score === null || data.score === undefined) {
        return `
            <div class="score-empty">
                <div class="score-empty-icon">📊</div>
                <div class="score-empty-title">${escapeHtml(data.label || 'Not enough data')}</div>
                <div class="score-empty-desc">${escapeHtml(data.explanation || '')}</div>
            </div>
        `;
    }

    const band = SCORE_BANDS[data.band] || SCORE_BANDS.steady;
    const trend = TREND_CONFIG[data.trend];

    // Circumference of an r=52 circle, used to drive the stroke dash
    const circumference = 2 * Math.PI * 52;
    const offset = circumference * (1 - data.score / 100);

    const gauge = `
        <div class="score-gauge">
            <svg viewBox="0 0 120 120" class="score-gauge-svg" role="img"
                 aria-label="Recovery score ${escapeHtml(data.score)} out of 100">
                <circle cx="60" cy="60" r="52" class="score-gauge-track" />
                <circle cx="60" cy="60" r="52" class="score-gauge-fill"
                        style="stroke: ${band.color};
                               stroke-dasharray: ${circumference};
                               stroke-dashoffset: ${offset};" />
            </svg>
            <div class="score-gauge-center">
                <div class="score-gauge-value" style="color: ${escapeHtml(band.color)};">${escapeHtml(data.score)}</div>
                <div class="score-gauge-max">/ 100</div>
            </div>
        </div>
        <div class="score-headline">
            <div class="score-band" style="color: ${escapeHtml(band.color)};">${escapeHtml(band.icon)} ${escapeHtml(data.label)}</div>
            ${trend ? `<div class="score-trend" style="color: ${escapeHtml(trend.color)};">${escapeHtml(trend.icon)} ${escapeHtml(trend.label)}</div>` : ''}
            <div class="score-meta">${escapeHtml(data.checkins_counted)} check-ins over ${escapeHtml(data.window_days)} days</div>
        </div>
    `;

    if (compact) {
        return `<div class="score-panel score-panel-compact">${gauge}</div>`;
    }

    return `
        <div class="score-panel">
            <div class="score-panel-main">${gauge}</div>
            <div class="score-breakdown">
                <div class="score-explanation">${escapeHtml(data.explanation)}</div>
                ${data.components.map(c => `
                    <div class="score-component">
                        <div class="score-component-top">
                            <span class="score-component-label">${escapeHtml(c.label)}</span>
                            <span class="score-component-value">${escapeHtml(c.subscore)}<span class="score-component-weight">/100 · ${escapeHtml(c.weight)}% weight</span></span>
                        </div>
                        <div class="score-component-bar">
                            <div class="score-component-fill ${_componentClass(c.subscore)}"
                                 style="width: ${escapeHtml(c.subscore)}%;"></div>
                        </div>
                        <div class="score-component-detail">${escapeHtml(c.detail)}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}


function _componentClass(subscore) {
    if (subscore >= 80) return 'comp-strong';
    if (subscore >= 60) return 'comp-steady';
    if (subscore >= 40) return 'comp-fragile';
    return 'comp-weak';
}


/** Load a score into a container; the endpoint depends on the role. */
async function loadScoreInto(containerId, endpoint, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    try {
        const data = await api.get(endpoint);
        container.innerHTML = renderScoreGauge(data, options);
        return data;
    } catch (err) {
        container.innerHTML = `
            <div class="score-empty">
                <div class="score-empty-icon">⚠️</div>
                <div class="score-empty-title">Score unavailable</div>
                <div class="score-empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
        return null;
    }
}


/* ── Recovery Timeline ──────────────────────────────────── */

/** The recovery timeline, grouped by day. */
function renderRecoveryTimeline(data) {
    if (!data.entries || data.entries.length === 0) {
        return `
            <div class="empty-state">
                <div class="empty-icon">🕰️</div>
                <div class="empty-title">No Activity Yet</div>
                <div class="empty-desc">Check-ins, notes, goals, and visits will appear here day by day.</div>
            </div>
        `;
    }

    return `
        <div class="recovery-timeline">
            ${data.entries.map(entry => `
                <div class="timeline-day">
                    <div class="timeline-day-header">
                        <div class="timeline-day-date">${_timelineDate(entry.date)}</div>
                        ${entry.daily_score !== null && entry.daily_score !== undefined ? `
                            <div class="timeline-day-score ${_componentClass(entry.daily_score)}">
                                ${escapeHtml(entry.daily_score)}<span class="timeline-day-score-max">/100</span>
                            </div>
                        ` : `<div class="timeline-day-noscore">no check-in</div>`}
                    </div>
                    <div class="timeline-day-events">
                        ${entry.events.map(e => {
                            const cfg = TIMELINE_EVENT_CONFIG[e.event_type] || { icon: '•', color: 'var(--text-muted)' };
                            return `
                                <div class="timeline-event">
                                    <span class="timeline-event-icon" style="color: ${escapeHtml(cfg.color)};">${escapeHtml(cfg.icon)}</span>
                                    <div class="timeline-event-body">
                                        <div class="timeline-event-title">${escapeHtml(e.title)}</div>
                                        ${e.summary ? `<div class="timeline-event-summary">${escapeHtml(e.summary)}</div>` : ''}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}


/** Load a timeline into a container. */
async function loadTimelineInto(containerId, patientId, days = 30) {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const data = await api.get(`/clinical/patients/${patientId}/timeline?days=${days}`);
        container.innerHTML = renderRecoveryTimeline(data);
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Failed to load timeline</div>
                <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
    }
}


/* ── Digital Twin ───────────────────────────────────────── */
/** Twin state is kept per container, so a re-render keeps the chosen scenario. */

const _twinState = {};

/** Load a digital twin into a container. */
async function loadTwinInto(containerId, endpoint) {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const data = await api.get(endpoint);
        _twinState[containerId] = { data, selected: null };
        _twinRender(containerId);
    } catch (err) {
        container.innerHTML = `
            <div class="score-empty">
                <div class="score-empty-icon">⚠️</div>
                <div class="score-empty-title">Digital twin unavailable</div>
                <div class="score-empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
    }
}


function _twinSelectScenario(containerId, key) {
    const state = _twinState[containerId];
    if (!state) return;
    state.selected = state.selected === key ? null : key;
    _twinRender(containerId);
}


function _twinRender(containerId) {
    const container = document.getElementById(containerId);
    const state = _twinState[containerId];
    if (!container || !state) return;

    const data = state.data;

    if (!data.available) {
        container.innerHTML = `
            <div class="twin-disclaimer">${escapeHtml(data.disclaimer)}</div>
            <div class="score-empty">
                <div class="score-empty-icon">🧬</div>
                <div class="score-empty-title">Not enough data yet</div>
                <div class="score-empty-desc">${escapeHtml(data.reason || 'The recovery score needs more check-ins before a twin can be modelled.')}</div>
            </div>
        `;
        return;
    }

    const base = data.baseline;
    const band = SCORE_BANDS[base.band] || SCORE_BANDS.steady;
    const trend = TREND_CONFIG[base.trend];
    const selected = state.selected
        ? data.scenarios.find(s => s.key === state.selected)
        : null;

    // Baseline always, the chosen scenario on top, and "everything together" for context.
    const series = [
        { label: 'If nothing changes', color: 'var(--text-muted)', points: data.baseline_projection, dashed: true },
    ];
    if (selected) {
        series.push({ label: selected.label, color: band.color, points: selected.projection, dashed: false });
    } else if (data.combined) {
        series.push({ label: data.combined.label, color: 'var(--accent-primary)', points: data.combined.projection, dashed: false });
    }

    const slope = data.baseline_slope_per_week;
    const slopeText = slope > 0.3 ? `trending up about ${slope} points a week`
        : slope < -0.3 ? `trending down about ${Math.abs(slope)} points a week`
        : 'roughly level week to week';

    container.innerHTML = `
        <div class="twin-disclaimer">${escapeHtml(data.disclaimer)}</div>

        <div class="twin-current">
            <div class="twin-current-gauge">${renderScoreGauge(base, { compact: true })}</div>
            <div class="twin-current-stats">
                <div class="twin-stat">
                    <span class="twin-stat-label">Current state</span>
                    <span class="twin-stat-value" style="color: ${escapeHtml(band.color)};">${escapeHtml(band.icon)} ${escapeHtml(base.label)}</span>
                </div>
                ${trend ? `
                    <div class="twin-stat">
                        <span class="twin-stat-label">Recent trend</span>
                        <span class="twin-stat-value" style="color: ${escapeHtml(trend.color)};">${escapeHtml(trend.icon)} ${escapeHtml(trend.label)}</span>
                    </div>
                ` : ''}
                <div class="twin-stat">
                    <span class="twin-stat-label">No-change outlook (${escapeHtml(data.horizon_days)} days)</span>
                    <span class="twin-stat-value">${slopeText}</span>
                </div>
                ${base.abstinence_days != null ? `
                    <div class="twin-stat">
                        <span class="twin-stat-label">Days abstinent</span>
                        <span class="twin-stat-value" style="color: var(--accent-success);">${escapeHtml(base.abstinence_days)}</span>
                    </div>
                ` : ''}
            </div>
        </div>

        <div class="twin-chart-card">
            <div class="twin-chart-title">Projected recovery score — next ${escapeHtml(data.horizon_days)} days</div>
            ${_twinChart(series, data.horizon_days)}
            <div class="twin-chart-legend">
                ${series.map(s => `
                    <span class="twin-legend-item">
                        <span class="twin-legend-swatch" style="background: ${escapeHtml(s.color)}; ${s.dashed ? 'opacity: 0.55;' : ''}"></span>
                        ${escapeHtml(s.label)}
                    </span>
                `).join('')}
            </div>
        </div>

        <div class="twin-scenarios-head">
            <h4>What if one thing changed?</h4>
            <p>Each card re-runs the score with a single habit moved toward a healthy target. Select one to compare.</p>
        </div>
        <div class="twin-scenario-grid">
            ${data.scenarios.map(s => `
                <button type="button"
                        class="twin-scenario-card ${state.selected === s.key ? 'selected' : ''}"
                        onclick="_twinSelectScenario('${containerId}', '${escapeHtml(s.key)}')">
                    <div class="twin-scenario-label">${escapeHtml(s.label)}</div>
                    <div class="twin-scenario-rationale">${escapeHtml(s.rationale)}</div>
                    <div class="twin-scenario-foot">
                        <span class="twin-scenario-delta">+${escapeHtml(s.score_delta)}</span>
                        <span class="twin-scenario-score">→ ${escapeHtml(s.projected_score)}<span class="twin-scenario-score-max">/100</span></span>
                    </div>
                </button>
            `).join('')}
        </div>
        ${data.scenarios.length === 0 ? `
            <div class="score-empty-desc" style="text-align: center;">
                Every modelled habit is already at or above its healthy target — there is no what-if left to project.
            </div>
        ` : ''}

        <div class="twin-compare">
            ${selected ? `
                <div class="twin-compare-row">
                    <div class="twin-compare-col">
                        <div class="twin-compare-cap">Now</div>
                        <div class="twin-compare-score">${escapeHtml(base.score)}<span class="twin-scenario-score-max">/100</span></div>
                        <div class="twin-compare-band">${escapeHtml(base.label)}</div>
                    </div>
                    <div class="twin-compare-arrow">→</div>
                    <div class="twin-compare-col">
                        <div class="twin-compare-cap">If «${selected.label.toLowerCase()}»</div>
                        <div class="twin-compare-score" style="color: ${(SCORE_BANDS[selected.projected_band] || band).color};">
                            ${escapeHtml(selected.projected_score)}<span class="twin-scenario-score-max">/100</span>
                        </div>
                        <div class="twin-compare-band">${escapeHtml(selected.projected_label)}</div>
                    </div>
                </div>
                <div class="twin-component-move">
                    <span class="twin-component-move-name">${escapeHtml(selected.component_label)}</span>
                    <span class="twin-component-move-bar">
                        ${selected.baseline_subscore}
                        <span class="twin-component-move-arrow">→</span>
                        <strong>${escapeHtml(selected.projected_subscore)}</strong>
                        <span class="twin-scenario-score-max">/100 for this component</span>
                    </span>
                </div>
            ` : `
                <div class="twin-compare-hint">Select a scenario above to see the baseline-versus-projection comparison.</div>
            `}
        </div>
    `;
}


/** A small SVG line chart that scales to any width and works in both themes. */
function _twinChart(series, horizonDays) {
    const W = 340, H = 168;
    const padL = 30, padR = 12, padT = 12, padB = 22;
    const x = (day) => padL + (day / horizonDays) * (W - padL - padR);
    const y = (score) => (H - padB) - (score / 100) * (H - padT - padB);

    const grid = [0, 25, 50, 75, 100].map(v => `
        <line x1="${padL}" y1="${y(v)}" x2="${W - padR}" y2="${y(v)}"
              stroke="var(--glass-border)" stroke-width="1" />
        ${v % 50 === 0 ? `<text x="${padL - 6}" y="${y(v) + 3}" text-anchor="end"
              font-size="9" fill="var(--text-muted)">${v}</text>` : ''}
    `).join('');

    const lines = series.map(s => {
        const pts = s.points.map(p => `${x(p.day).toFixed(1)},${y(p.score).toFixed(1)}`).join(' ');
        const end = s.points[s.points.length - 1];
        return `
            <polyline points="${pts}" fill="none" stroke="${escapeHtml(s.color)}" stroke-width="2.5"
                      stroke-linecap="round" stroke-linejoin="round"
                      ${s.dashed ? 'stroke-dasharray="4 4"' : ''} />
            <circle cx="${x(end.day).toFixed(1)}" cy="${y(end.score).toFixed(1)}" r="3" fill="${escapeHtml(s.color)}" />
        `;
    }).join('');

    return `
        <div class="twin-chart">
            <svg viewBox="0 0 ${W} ${H}" class="twin-chart-svg" role="img"
                 aria-label="Projected recovery score over the next ${horizonDays} days">
                ${grid}
                <text x="${padL}" y="${H - 6}" font-size="9" fill="var(--text-muted)">today</text>
                <text x="${W - padR}" y="${H - 6}" text-anchor="end" font-size="9"
                      fill="var(--text-muted)">+${horizonDays}d</text>
                ${lines}
            </svg>
        </div>
    `;
}


/** A timeline date heading, with Today and Yesterday by name. */
function _timelineDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    if (isNaN(d)) return dateStr;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffDays = Math.round((today - d) / 86400000);

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';

    return d.toLocaleDateString(undefined, {
        weekday: 'short', day: 'numeric', month: 'short',
        year: d.getFullYear() === today.getFullYear() ? undefined : 'numeric',
    });
}
