/** Caseload analytics: the score spread and a triage list. */

const BAND_DISPLAY = {
    strong: { label: 'Strong', color: 'var(--accent-success)', icon: '🌟' },
    steady: { label: 'Steady', color: 'var(--accent-info)', icon: '📈' },
    fragile: { label: 'Needs attention', color: 'var(--accent-warning)', icon: '⚠️' },
    at_risk: { label: 'At risk', color: 'var(--accent-danger)', icon: '🚨' },
    unscored: { label: 'Not enough data', color: 'var(--text-muted)', icon: '○' },
};


async function renderDoctorAnalytics() {
    renderDashboardShell('doctor', 'analytics', 'Caseload', `
        <div class="page-header">
            <h1>Caseload</h1>
            <p>Your whole patient list at a glance, ordered by who needs you first.</p>
        </div>

        <div class="dashboard-grid" id="caseloadStats">
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);" id="aiRiskAnalysis">
            <div class="card-header"><div><h3>AI Risk Analysis</h3><p>Recovery-risk estimates from the XGBoost + SHAP service.</p></div></div>
            <div class="ai-risk-loading"><div class="spinner"></div><span>Analyzing assigned patients...</span></div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header"><h3>Score Distribution</h3></div>
            <div id="caseloadDistribution">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header"><h3>Needs Attention</h3></div>
            <div id="caseloadTriage">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading caseload...</span></div>
            </div>
        </div>
    `);

    await loadCaseloadAnalytics();
    await loadAIRiskAnalysis();
}


async function loadCaseloadAnalytics() {
    try {
        const data = await api.get('/doctor/analytics');
        _renderCaseloadStats(data);
        _renderCaseloadDistribution(data);
        _renderCaseloadTriage(data);
    } catch (err) {
        showToast(err.message || 'Failed to load caseload', 'error');
        const triage = document.getElementById('caseloadTriage');
        if (triage) {
            triage.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <div class="empty-title">Failed to load</div>
                    <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
                </div>
            `;
        }
    }
}


function _renderCaseloadStats(data) {
    const grid = document.getElementById('caseloadStats');
    if (!grid) return;

    const avgColor = data.average_score == null ? 'var(--text-muted)'
        : data.average_score >= 80 ? 'var(--accent-success)'
        : data.average_score >= 60 ? 'var(--accent-info)'
        : data.average_score >= 40 ? 'var(--accent-warning)' : 'var(--accent-danger)';

    grid.innerHTML = `
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-primary-rgb), 0.15); color: var(--accent-primary);">🩺</div>
            <div class="stat-value">${escapeHtml(data.total_patients)}</div>
            <div class="stat-label">Patients</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-info-rgb), 0.15); color: ${avgColor};">📊</div>
            <div class="stat-value" style="color: ${avgColor};">${escapeHtml(data.average_score ?? '—')}</div>
            <div class="stat-label">Average Score</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-danger-rgb), 0.15); color: var(--accent-danger);">🔔</div>
            <div class="stat-value">${escapeHtml(data.unread_alerts)}</div>
            <div class="stat-label">Unread Alerts</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-warning-rgb), 0.15); color: var(--accent-warning);">🤝</div>
            <div class="stat-value">${escapeHtml(data.pending_outcomes)}</div>
            <div class="stat-label">Outcomes Pending</div>
        </div>
    `;
}


function _renderCaseloadDistribution(data) {
    const card = document.getElementById('caseloadDistribution');
    if (!card) return;

    if (data.total_patients === 0) {
        card.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-title">No Patients Assigned</div>
                <div class="empty-desc">Ask your hospital admin to assign patients to you.</div>
            </div>
        `;
        return;
    }

    const order = ['strong', 'steady', 'fragile', 'at_risk', 'unscored'];
    const total = data.total_patients;

    card.innerHTML = `
        <div style="padding: var(--space-5);">
            <div class="band-bar" role="img"
                 aria-label="Score distribution across ${total} patients">
                ${order.map(b => {
                    const n = data.band_counts[b] || 0;
                    if (!n) return '';
                    const cfg = BAND_DISPLAY[b];
                    const pct = (n / total) * 100;
                    return `<div class="band-seg" style="width: ${pct}%; background: ${escapeHtml(cfg.color)};"
                                 title="${escapeHtml(cfg.label)}: ${n}">${pct > 8 ? n : ''}</div>`;
                }).join('')}
            </div>
            <div class="band-legend">
                ${order.map(b => {
                    const n = data.band_counts[b] || 0;
                    const cfg = BAND_DISPLAY[b];
                    return `
                        <div class="band-legend-item ${n === 0 ? 'empty' : ''}">
                            <span class="band-swatch" style="background: ${escapeHtml(cfg.color)};"></span>
                            <span class="band-legend-label">${escapeHtml(cfg.label)}</span>
                            <span class="band-legend-count">${n}</span>
                        </div>
                    `;
                }).join('')}
            </div>
            <div class="caseload-engagement">
                <span>${escapeHtml(data.checkins_last_7_days)} check-ins in the last 7 days</span>
                ${data.engagement_rate != null
                    ? `<span class="caseload-engagement-rate">${escapeHtml(data.engagement_rate)}% of expected</span>`
                    : ''}
            </div>
        </div>
    `;
}


function _renderCaseloadTriage(data) {
    const card = document.getElementById('caseloadTriage');
    if (!card) return;

    if (!data.needs_attention.length) {
        card.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✅</div>
                <div class="empty-title">${data.total_patients ? 'Nobody Needs Attention' : 'No Patients Assigned'}</div>
                <div class="empty-desc">${data.total_patients
                    ? 'No patient is at risk, fragile, or carrying an unread alert.'
                    : 'Ask your hospital admin to assign patients to you.'}</div>
            </div>
        `;
        return;
    }

    card.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Patient</th>
                        <th>Score</th>
                        <th>Trend</th>
                        <th>Weakest Area</th>
                        <th>Abstinent</th>
                        <th>Last Check-in</th>
                        <th>Alerts</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    ${data.needs_attention.map(p => {
                        const cfg = BAND_DISPLAY[p.band || 'unscored'];
                        const trend = TREND_CONFIG[p.trend];
                        return `
                            <tr>
                                <td><strong>${escapeHtml(p.full_name)}</strong></td>
                                <td>
                                    <span style="color: ${escapeHtml(cfg.color)}; font-weight: 700;">
                                        ${p.score ?? '—'}
                                    </span>
                                    <div style="font-size: var(--text-xs); color: ${escapeHtml(cfg.color)};">${escapeHtml(cfg.label)}</div>
                                </td>
                                <td>${trend
                                    ? `<span style="color: ${escapeHtml(trend.color)};">${escapeHtml(trend.icon)} ${escapeHtml(trend.label)}</span>`
                                    : '<span style="color: var(--text-muted);">—</span>'}</td>
                                <td style="font-size: var(--text-xs); color: var(--text-secondary);">
                                    ${escapeHtml(p.weakest_area || '—')}
                                </td>
                                <td style="font-size: var(--text-sm);">
                                    ${p.abstinence_days != null ? p.abstinence_days + 'd' : '—'}
                                </td>
                                <td style="font-size: var(--text-xs); color: var(--text-secondary);">
                                    ${p.last_checkin_date ? formatDate(p.last_checkin_date) : 'never'}
                                </td>
                                <td>
                                    ${p.unread_alerts > 0
                                        ? `<span class="badge badge-danger">${escapeHtml(p.unread_alerts)}</span>`
                                        : '<span style="color: var(--text-muted);">—</span>'}
                                </td>
                                <td>
                                    <a href="#/doctor/patients/${escapeHtml(p.patient_id)}" class="btn btn-primary btn-sm">Open →</a>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}


async function loadAIRiskAnalysis() {
    const container = document.getElementById('aiRiskAnalysis');
    if (!container) return;
    try {
        const data = await api.get('/doctor/patients');
        const patients = data.patients || [];
        if (!patients.length) {
            container.innerHTML = `<div class="card-header"><div><h3>AI Risk Analysis</h3><p>No assigned patients yet.</p></div></div>`;
            return;
        }
        const results = await Promise.all(patients.map(async patient => {
            try { return { patient, result: await getPatientRiskResult('doctor', patient.id) }; }
            catch (error) { return { patient, result: null, error }; }
        }));
        const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
        results.forEach(x => { if (x.result?.risk_category) counts[x.result.risk_category]++; });
        container.innerHTML = `
            <div class="card-header"><div><h3>AI Risk Analysis</h3><p>Current prototype estimates for ${escapeHtml(patients.length)} assigned patient${patients.length === 1 ? '' : 's'}.</p></div><span class="ai-model-chip">XGBoost + SHAP</span></div>
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:0 var(--space-5) var(--space-5);">
                ${[['HIGH','🔴'],['MEDIUM','🟠'],['LOW','🟢']].map(([key,icon]) => `<div class="card glass" style="padding:14px;"><div style="font-size:20px;">${icon}</div><strong>${Number(counts[key]) || 0}</strong><div style="font-size:11px;color:var(--text-secondary);">${key} risk</div></div>`).join('')}
            </div>
            <div class="table-container">
                <table class="data-table"><thead><tr><th>Patient</th><th>AI Risk</th><th>Probability</th><th>Key Signals</th><th></th></tr></thead><tbody>
                ${results.map(({patient,result}) => {
                    if (!result) return `<tr><td><strong>${escapeHtml(patient.full_name)}</strong></td><td colspan="3"><span style="color:var(--text-muted);">AI unavailable</span></td><td><a href="#/doctor/patients/${escapeHtml(patient.id)}" class="btn btn-primary btn-sm">Open →</a></td></tr>`;
                    const meta = aiRiskMeta(result.risk_category);
                    const pct = Math.round((result.recovery_risk_probability || 0) * 100);
                    const shap = (result.shap || []).filter(x => x.feature && x.feature !== 'SHAP unavailable').slice(0, 2).map(x => `${x.impact === 'increases_risk' ? '↑' : '↓'} ${String(x.feature).replaceAll('_',' ')}`).join(' · ');
                    return `<tr><td><strong>${escapeHtml(patient.full_name)}</strong></td><td><span class="ai-factor ${result.risk_category === 'HIGH' ? 'factor-up' : result.risk_category === 'LOW' ? 'factor-down' : ''}">${meta.icon} ${escapeHtml(meta.label)}</span></td><td>${pct}%</td><td style="font-size:11px;color:var(--text-secondary);">${escapeHtml(shap || 'No explanation available yet')}</td><td><a href="#/doctor/patients/${escapeHtml(patient.id)}" class="btn btn-primary btn-sm">Open →</a></td></tr>`;
                }).join('')}
                </tbody></table>
            </div>
            <div class="ai-risk-disclaimer" style="padding:0 var(--space-5) var(--space-5);">Prototype decision-support only — not a diagnosis. Missing clinical vitals are not treated as measured values.</div>`;
    } catch (err) {
        container.innerHTML = `<div class="ai-risk-unavailable"><span>🧠</span><div><strong>Recovery Risk AI is unavailable</strong><small>${escapeHtml(err.message || 'Start the AI service on port 8010 and try again.')}</small></div></div>`;
    }
}
