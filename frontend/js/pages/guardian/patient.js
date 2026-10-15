/** Guardian view of the patient: profile, check-ins, goals and care team. */

async function renderGuardianPatientView() {
    renderDashboardShell('guardian', 'patient', 'Patient View', `
        <div class="page-header">
            <h1>Patient Recovery Details</h1>
            <p>Read-only view of your linked patient's recovery data</p>
        </div>

        <div class="card glass" id="guardianPatientProfile" style="margin-bottom: var(--space-6);">
            <div class="card-header"><h3>Patient Profile</h3></div>
            <div class="loading-overlay"><div class="spinner"></div></div>
        </div>

        <div class="tabs-bar" id="guardianTabs" style="margin-bottom: var(--space-6);">
            <button class="tab-btn active" data-tab="checkins" onclick="_switchGuardianTab('checkins')">Recent Check-ins</button>
            <button class="tab-btn" data-tab="goals" onclick="_switchGuardianTab('goals')">Recovery Goals</button>
            <button class="tab-btn" data-tab="milestones" onclick="_switchGuardianTab('milestones')">Milestones</button>
            <button class="tab-btn" data-tab="timeline" onclick="_switchGuardianTab('timeline')">Timeline</button>
            <button class="tab-btn" data-tab="twin" onclick="_switchGuardianTab('twin')">Digital Twin</button>
        </div>

        <div id="guardianTabContent">
            <div class="card glass">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading patient data...</span></div>
            </div>
        </div>
    `);

    try {
        const data = await api.get('/guardian/patient');
        window._guardianPatientData = data;
        _renderGuardianProfile(data);
        _renderGuardianCheckins(data.recent_checkins);
    } catch (err) {
        showToast(err.message || 'Failed to load patient data', 'error');
    }
}


/* ── Tab Switching ──────────────────────────────────────── */

function _switchGuardianTab(tab) {
    document.querySelectorAll('#guardianTabs .tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    const data = window._guardianPatientData;
    if (!data) return;

    if (tab === 'checkins') {
        _renderGuardianCheckins(data.recent_checkins);
    } else if (tab === 'goals') {
        _renderGuardianGoals(data.goals);
    } else if (tab === 'milestones') {
        _renderGuardianMilestones(data);
    } else if (tab === 'timeline') {
        _renderGuardianTimeline(data);
    } else if (tab === 'twin') {
        _renderGuardianTwin(data);
    }
}


/* ── Patient Profile ────────────────────────────────────── */

function _renderGuardianProfile(data) {
    const card = document.getElementById('guardianPatientProfile');
    if (!card) return;

    card.innerHTML = `
        <div class="card-header">
            <h3>Patient Profile</h3>
            <span class="badge badge-info">${escapeHtml(data.care_team.length)} care member${data.care_team.length !== 1 ? 's' : ''}</span>
        </div>
        <div class="patient-detail-grid" style="padding: 0 var(--space-2);">
            <div class="patient-detail-item">
                <div class="detail-label">Full Name</div>
                <div class="detail-value">${escapeHtml(data.patient_name)}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Email</div>
                <div class="detail-value">${escapeHtml(data.email || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Phone</div>
                <div class="detail-value">${escapeHtml(data.phone || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Primary Condition</div>
                <div class="detail-value">${escapeHtml(data.primary_condition || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Program Start</div>
                <div class="detail-value">${data.program_start_date ? formatDate(data.program_start_date) : '—'}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Therapy Program</div>
                <div class="detail-value">${escapeHtml(data.therapy_program || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Abstinence</div>
                <div class="detail-value">${data.abstinence_days != null
                    ? data.abstinence_days + ' day' + (data.abstinence_days === 1 ? '' : 's')
                    : '—'}</div>
            </div>
        </div>
        ${data.medical_notes ? `
            <div style="margin-top: var(--space-4); padding: var(--space-4); background: var(--surface-1); border-radius: var(--glass-radius-sm);">
                <div style="font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: var(--space-2);">Medical Notes</div>
                <div style="font-size: var(--text-sm); color: var(--text-secondary); line-height: 1.6; white-space: pre-wrap;">${escapeHtml(data.medical_notes)}</div>
            </div>
        ` : ''}

        <div style="margin-top: var(--space-6); padding-top: var(--space-4); border-top: 1px solid var(--glass-border);">
            <h4 style="margin-bottom: var(--space-4); font-size: var(--text-base); color: var(--text-secondary);">👨‍⚕️ Care Team</h4>
            ${_renderContactCards(data.care_team)}
        </div>
    `;
}


/* ── Check-in History ───────────────────────────────────── */

function _renderGuardianCheckins(checkins) {
    const container = document.getElementById('guardianTabContent');
    if (!container) return;

    if (!checkins || checkins.length === 0) {
        container.innerHTML = `
            <div class="card glass">
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div class="empty-title">No Check-ins Yet</div>
                    <div class="empty-desc">Your patient hasn't submitted any check-ins yet.</div>
                </div>
            </div>
        `;
        return;
    }

    const levelColor = (v) => v == null ? 'var(--text-muted)'
        : v <= 3 ? 'var(--accent-success)' : v <= 6 ? 'var(--accent-warning)' : 'var(--accent-danger)';
    const moodEmoji = { good: '😊', neutral: '😐', poor: '😔' };

    container.innerHTML = `
        <div class="card glass">
            <div class="card-header"><h3>Recent Check-ins (Last 14 Days)</h3></div>
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
                                <td style="font-weight: 500;">${formatDate(ci.date) || ci.date}</td>
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
        </div>
    `;
}


/* ── Recovery Goals ─────────────────────────────────────── */

function _renderGuardianGoals(goals) {
    const container = document.getElementById('guardianTabContent');
    if (!container) return;

    if (!goals || goals.length === 0) {
        container.innerHTML = `
            <div class="card glass">
                <div class="empty-state">
                    <div class="empty-icon">🎯</div>
                    <div class="empty-title">No Goals Yet</div>
                    <div class="empty-desc">The doctor hasn't set any recovery goals yet.</div>
                </div>
            </div>
        `;
        return;
    }

    const completedCount = goals.filter(g => g.status === 'completed').length;
    const progressPct = goals.length > 0 ? Math.round((completedCount / goals.length) * 100) : 0;

    container.innerHTML = `
        <div class="card glass">
            <div class="card-header">
                <h3>Recovery Goals</h3>
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
                    ${goals.map(g => {
                        const isComplete = g.status === 'completed';
                        const isActive = g.status === 'in_progress';
                        return `
                            <div class="milestone-item ${isComplete ? 'completed' : ''} ${isActive ? 'active' : ''}">
                                <div class="milestone-marker">
                                    ${isComplete ? '✓' : isActive ? '◑' : '○'}
                                </div>
                                <div class="milestone-content">
                                    <span class="milestone-title">${escapeHtml(g.title)}</span>
                                    ${g.target_date ? `<span class="milestone-date">${formatDate(g.target_date)}</span>` : ''}
                                </div>
                                <span class="badge ${isComplete ? 'badge-success' : isActive ? 'badge-warning' : 'badge-secondary'}">
                                    ${g.status.replace('_', ' ')}
                                </span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        </div>
    `;
}


/* ── Utility ───────────────────────────────────────────── */



/* ── Milestones Tab ─────────────────────────── */

// Abstinence milestones in days, separate from the goals a doctor sets.
const ABSTINENCE_MILESTONES = [
    { days: 1, label: 'First Day', icon: '\u{1F331}' },
    { days: 7, label: 'One Week', icon: '\u{1F33F}' },
    { days: 30, label: 'One Month', icon: '\u{1F338}' },
    { days: 60, label: 'Two Months', icon: '\u{1F33B}' },
    { days: 90, label: 'Three Months', icon: '\u{1F333}' },
    { days: 180, label: 'Six Months', icon: '\u2B50' },
    { days: 365, label: 'One Year', icon: '\u{1F3C6}' },
];

function _renderGuardianMilestones(data) {
    const container = document.getElementById('guardianTabContent');
    if (!container) return;

    const days = data.abstinence_days;

    if (days === null || days === undefined) {
        container.innerHTML = `
            <div class="card glass">
                <div class="empty-state">
                    <div class="empty-icon">\u{1F3C6}</div>
                    <div class="empty-title">No Sobriety Date Set</div>
                    <div class="empty-desc">Milestones appear once the care team records a sobriety date on the patient's profile.</div>
                </div>
            </div>
        `;
        return;
    }

    const nextMilestone = ABSTINENCE_MILESTONES.find(m => m.days > days);
    const completedGoals = (data.goals || []).filter(g => g.status === 'completed');

    container.innerHTML = `
        <div class="card glass">
            <div class="card-header">
                <h3>\u{1F3C6} Recovery Milestones</h3>
                <span class="badge badge-primary">${days} day${days === 1 ? '' : 's'} abstinent</span>
            </div>
            <div style="padding: var(--space-5);">
                ${nextMilestone ? `
                    <div class="milestone-next">
                        <div class="milestone-next-icon">${escapeHtml(nextMilestone.icon)}</div>
                        <div class="milestone-next-body">
                            <div class="milestone-next-label">Next: ${escapeHtml(nextMilestone.label)}</div>
                            <div class="milestone-next-meta">${nextMilestone.days - days} day${nextMilestone.days - days === 1 ? '' : 's'} to go</div>
                            <div class="progress-bar-bg" style="margin-top: var(--space-3);">
                                <div class="progress-bar-fill" style="width: ${Math.round(days / nextMilestone.days * 100)}%;"></div>
                            </div>
                        </div>
                    </div>
                ` : `
                    <div class="milestone-next">
                        <div class="milestone-next-icon">\u{1F3C6}</div>
                        <div class="milestone-next-body">
                            <div class="milestone-next-label">Every milestone reached</div>
                            <div class="milestone-next-meta">Over a year of abstinence \u2014 remarkable.</div>
                        </div>
                    </div>
                `}

                <div class="milestones-list" style="margin-top: var(--space-6);">
                    ${ABSTINENCE_MILESTONES.map(m => {
                        const achieved = days >= m.days;
                        return `
                            <div class="milestone-item ${achieved ? 'completed' : ''}">
                                <div class="milestone-marker">${achieved ? '\u2713' : m.icon}</div>
                                <div class="milestone-content">
                                    <span class="milestone-title">${escapeHtml(m.label)}</span>
                                    <span class="milestone-date">${escapeHtml(m.days)} day${m.days === 1 ? '' : 's'}</span>
                                </div>
                                <span class="badge ${achieved ? 'badge-success' : 'badge-secondary'}">
                                    ${achieved ? 'Reached' : 'Upcoming'}
                                </span>
                            </div>
                        `;
                    }).join('')}
                </div>

                ${completedGoals.length > 0 ? `
                    <div style="margin-top: var(--space-6); padding-top: var(--space-5); border-top: 1px solid var(--glass-border);">
                        <h4 style="margin-bottom: var(--space-4); font-size: var(--text-base); color: var(--text-secondary);">
                            \u{1F3AF} Clinical Goals Achieved
                        </h4>
                        <div class="milestones-list">
                            ${completedGoals.map(g => `
                                <div class="milestone-item completed">
                                    <div class="milestone-marker">\u2713</div>
                                    <div class="milestone-content">
                                        <span class="milestone-title">${escapeHtml(g.title)}</span>
                                    </div>
                                    <span class="badge badge-success">Completed</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}


/* ── Timeline Tab ──────────────────────────── */

async function _renderGuardianTimeline(data) {
    const container = document.getElementById('guardianTabContent');
    if (!container) return;

    container.innerHTML = `
        <div class="card glass">
            <div class="card-header"><h3>\u{1F570}\uFE0F Recovery Timeline</h3></div>
            <div id="guardianTimeline">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>
    `;

    if (data.patient_id) {
        await loadTimelineInto('guardianTimeline', data.patient_id);
    }
}


/* ── Digital Twin Tab ───────────────────────────────────── */

async function _renderGuardianTwin(data) {
    const container = document.getElementById('guardianTabContent');
    if (!container) return;

    container.innerHTML = `
        <div class="card glass">
            <div class="card-header"><h3>\u{1F9EC} Digital Twin</h3></div>
            <div id="guardianTwin">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>
    `;

    if (data.patient_id) {
        await loadTwinInto('guardianTwin', `/clinical/patients/${data.patient_id}/digital-twin`);
    }
}
