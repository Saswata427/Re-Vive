/** Guardian dashboard: the linked patient's status, alerts and care team. */

async function renderGuardianDashboard() {
    const user = api.getUser();

    renderDashboardShell('guardian', 'dashboard', 'Dashboard', `
        <div class="welcome-banner card glass">
            <h1>Welcome, <span>${escapeHtml(user?.name || 'Guardian')}</span></h1>
            <p>Monitor your linked patient's recovery journey.</p>
        </div>

        <div class="dashboard-grid" id="guardianStatsGrid">
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
        </div>

        <div class="card glass" id="scoreCard" style="margin-top: var(--space-6);">
            <div class="card-header">
                <h3>Recovery Score</h3>
                <a href="#/guardian/patient" class="btn btn-ghost btn-sm">View details →</a>
            </div>
            <div id="scoreGauge">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="dashboard-grid cols-2" style="margin-top: var(--space-6);">
            <div class="card glass" id="patientInfoCard">
                <div class="card-header"><h3>Linked Patient</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass" id="careTeamCard">
                <div class="card-header"><h3>👨‍⚕️ Care Team</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>
    `);

    try {
        const data = await api.get('/guardian/dashboard');
        _renderGuardianStats(data);
        _renderPatientInfo(data);
        _renderGuardianCareTeam(data.care_team);
        if (data.patient_id) {
            loadScoreInto('scoreGauge', `/clinical/patients/${data.patient_id}/recovery-score`, { compact: true });
        }
    } catch (err) {
        showToast(err.message || 'Failed to load dashboard', 'error');
    }
}


function _renderGuardianStats(data) {
    const grid = document.getElementById('guardianStatsGrid');
    if (!grid) return;

    const moodEmoji = { good: '😊', neutral: '😐', poor: '😔' };
    const levelColor = (v) => v == null ? 'var(--text-muted)'
        : v <= 3 ? 'var(--accent-success)'
        : v <= 6 ? 'var(--accent-warning)' : 'var(--accent-danger)';

    grid.innerHTML = `
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: ${data.today_checkin_done
                ? 'rgba(var(--accent-success-rgb), 0.15)' : 'rgba(var(--accent-warning-rgb), 0.15)'}; color: ${data.today_checkin_done ? 'var(--accent-success)' : 'var(--accent-warning)'};">
                ${data.today_checkin_done ? '✓' : '○'}
            </div>
            <div class="stat-value">${data.today_checkin_done ? 'Done' : 'Pending'}</div>
            <div class="stat-label">Today's Check-in</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(255, 140, 0, 0.15); color: var(--accent-streak); font-size: 1.6rem;">
                🔥
            </div>
            <div class="stat-value">${data.abstinence_days != null ? data.abstinence_days : data.streak_days}</div>
            <div class="stat-label">${data.abstinence_days != null ? 'Days Abstinent' : 'Day Streak'}</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-primary-rgb), 0.15); color: ${levelColor(data.latest_craving_level)}; font-size: 1.4rem;">
                🌊
            </div>
            <div class="stat-value" style="color: ${levelColor(data.latest_craving_level)}">${data.latest_craving_level != null ? data.latest_craving_level + '/10' : '—'}</div>
            <div class="stat-label">Latest Craving Level</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-info-rgb), 0.15); color: var(--accent-info);">
                🎯
            </div>
            <div class="stat-value">${escapeHtml(data.active_goals)}</div>
            <div class="stat-label">Active Goals</div>
        </div>
    `;
}


function _renderPatientInfo(data) {
    const card = document.getElementById('patientInfoCard');
    if (!card) return;

    const moodEmoji = { good: 'Good', neutral: 'Neutral', poor: 'Difficult' };

    card.innerHTML = `
        <div class="card-header">
            <h3>Linked Patient</h3>
            ${data.unread_alerts > 0 ? `<span class="badge badge-danger">${escapeHtml(data.unread_alerts)} alert${data.unread_alerts > 1 ? 's' : ''}</span>` : ''}
        </div>
        <div class="guardian-patient-card">
            <div class="guardian-patient-avatar">👤</div>
            <div class="guardian-patient-info">
                <div class="guardian-patient-name">${escapeHtml(data.patient_name)}</div>
                <div class="guardian-patient-meta">${escapeHtml(data.primary_condition || 'No condition on file')}</div>
                ${data.latest_mood ? `<div class="guardian-patient-mood">${moodEmoji[data.latest_mood] || data.latest_mood}</div>` : ''}
            </div>
        </div>
        <div class="guardian-quick-stats">
            <div class="guardian-quick-stat">
                <span class="guardian-quick-label">Goals Progress</span>
                <span class="guardian-quick-value">${data.total_goals > 0 ? Math.round(((data.total_goals - data.active_goals) / data.total_goals) * 100) : 0}%</span>
            </div>
            <div class="guardian-quick-stat">
                <span class="guardian-quick-label">Total Goals</span>
                <span class="guardian-quick-value">${escapeHtml(data.total_goals)}</span>
            </div>
        </div>
        <a href="#/guardian/patient" class="btn btn-primary btn-sm" style="width: 100%; margin-top: var(--space-4); justify-content: center;">
            View Full Patient Details
        </a>
    `;
}


function _renderGuardianCareTeam(team) {
    const card = document.getElementById('careTeamCard');
    if (!card) return;

    if (!team || team.length === 0) {
        card.innerHTML = `
            <div class="card-header"><h3>👨‍⚕️ Care Team</h3></div>
            <div class="empty-state">
                <div class="empty-icon">👨‍⚕️</div>
                <div class="empty-title">No Care Team</div>
                <div class="empty-desc">The hospital admin will assign the care team.</div>
            </div>
        `;
        return;
    }

    card.innerHTML = `
        <div class="card-header"><h3>👨‍⚕️ Care Team</h3></div>
        <div style="padding: var(--space-4);">
            ${_renderContactCards(team)}
        </div>
    `;
}
