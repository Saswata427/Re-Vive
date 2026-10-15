/** Patient dashboard: streak, today's check-in, goals and care team. */

async function renderPatientDashboard() {
    const user = api.getUser();

    renderDashboardShell('patient', 'dashboard', 'Dashboard', `
        <div class="welcome-banner card glass">
            <h1>Welcome back, <span>${escapeHtml(user?.name || 'Patient')}</span></h1>
            <p>Track your recovery journey and stay on top of your health.</p>
        </div>

        <div class="dashboard-grid" id="patientStatsGrid">
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
        </div>

        <div id="checkinCTA" style="margin-top: var(--space-6);"></div>

        <div class="card glass" id="scoreCard" style="margin-top: var(--space-6);">
            <div class="card-header">
                <h3>Recovery Score</h3>
                <a href="#/patient/progress" class="btn btn-ghost btn-sm">View breakdown →</a>
            </div>
            <div id="scoreGauge">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="dashboard-grid cols-2" style="margin-top: var(--space-6);">
            <div class="card glass" id="goalsSection">
                <div class="card-header"><h3>Recovery Goals</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass" id="careTeamSection">
                <div class="card-header"><h3>👨‍⚕️ Your Care Team</h3></div>
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>
    `);

    try {
        const data = await api.get('/patient/dashboard');
        _renderStatsCards(data);
        _renderCheckinCTA(data.today_checkin_done);
        _renderGoalsSummary(data.recent_goals, data.active_goals, data.total_goals);
        _renderCareTeam(data.care_team);
    } catch (err) {
        showToast('Failed to load dashboard', 'error');
    }

    // Score loads independently so a slow score never blocks the dashboard
    loadScoreInto('scoreGauge', '/patient/recovery-score', { compact: true });
}


function _renderStatsCards(data) {
    const grid = document.getElementById('patientStatsGrid');
    if (!grid) return;

    grid.innerHTML = `
        <div class="card glass stat-card patient-stat-streak">
            <div class="stat-icon" style="background: linear-gradient(135deg, rgba(var(--accent-streak-rgb), 0.2), rgba(var(--accent-streak-rgb), 0.28)); color: var(--accent-streak); font-size: 1.6rem;">
                🌟
            </div>
            <div class="stat-value">${data.abstinence_days != null ? data.abstinence_days : '—'}</div>
            <div class="stat-label">Days Abstinent</div>
            ${data.abstinence_days >= 30 ? '<div class="streak-badge">Milestone! 🎉</div>' : ''}
        </div>
        <div class="card glass stat-card patient-stat-streak">
            <div class="stat-icon" style="background: linear-gradient(135deg, rgba(var(--accent-streak-rgb), 0.2), rgba(var(--accent-streak-rgb), 0.28)); color: var(--accent-streak); font-size: 1.6rem;">
                🔥
            </div>
            <div class="stat-value">${escapeHtml(data.streak_days)}</div>
            <div class="stat-label">Check-in Streak</div>
            ${data.streak_days >= 7 ? '<div class="streak-badge">Amazing! 🎉</div>' : ''}
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-success-rgb), 0.15); color: var(--accent-success);">
                ${data.today_checkin_done ? '✓' : '○'}
            </div>
            <div class="stat-value">${data.today_checkin_done ? 'Done' : 'Pending'}</div>
            <div class="stat-label">Today's Check-in</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-primary-rgb), 0.15); color: var(--accent-primary);">
                🎯
            </div>
            <div class="stat-value">${escapeHtml(data.active_goals)}</div>
            <div class="stat-label">Active Goals</div>
        </div>
    `;
}


function _renderCheckinCTA(isDone) {
    const container = document.getElementById('checkinCTA');
    if (!container) return;

    if (isDone) {
        container.innerHTML = `
            <div class="card glass checkin-done-banner">
                <div class="checkin-done-icon">✅</div>
                <div>
                    <h3 style="color: var(--accent-success); margin-bottom: var(--space-1);">Check-in Complete!</h3>
                    <p style="color: var(--text-secondary); font-size: var(--text-sm);">Great job! You've logged your wellness data for today. See you tomorrow.</p>
                </div>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="card glass checkin-cta-banner">
                <div class="checkin-cta-content">
                    <div class="checkin-cta-icon pulse-glow">📝</div>
                    <div>
                        <h3 style="color: var(--text-primary); margin-bottom: var(--space-1);">Time for your daily check-in</h3>
                        <p style="color: var(--text-secondary); font-size: var(--text-sm);">Log your pain, mood, sleep, and medication to keep your care team updated.</p>
                    </div>
                </div>
                <a href="#/patient/checkin" class="btn btn-primary btn-lg checkin-cta-btn">
                    Start Check-in
                </a>
            </div>
        `;
    }
}


function _renderGoalsSummary(goals, activeCount, totalCount) {
    const section = document.getElementById('goalsSection');
    if (!section) return;

    if (!goals || goals.length === 0) {
        section.innerHTML = `
            <div class="card-header"><h3>Recovery Goals</h3></div>
            <div class="empty-state">
                <div class="empty-icon">🎯</div>
                <div class="empty-title">No Goals Yet</div>
                <div class="empty-desc">Your doctor will set recovery goals for you.</div>
            </div>
        `;
        return;
    }

    const statusIcon = { not_started: '○', in_progress: '◑', completed: '●' };
    const statusClass = { not_started: 'badge-secondary', in_progress: 'badge-warning', completed: 'badge-success' };

    section.innerHTML = `
        <div class="card-header">
            <h3>Recovery Goals</h3>
            <span class="badge badge-primary">${activeCount} active</span>
        </div>
        <div style="padding: var(--space-4);">
            ${goals.map(g => `
                <div class="goal-item">
                    <span class="goal-status-dot" style="color: ${g.status === 'completed' ? 'var(--accent-success)' : g.status === 'in_progress' ? 'var(--accent-warning)' : 'var(--text-muted)'}">
                        ${statusIcon[g.status] || '○'}
                    </span>
                    <div class="goal-info">
                        <span class="goal-title">${escapeHtml(g.title)}</span>
                        ${g.target_date ? `<span class="goal-date">${formatDateShort(g.target_date)}</span>` : ''}
                    </div>
                    <span class="badge ${escapeHtml(statusClass[g.status] || 'badge-secondary')}">${g.status.replace('_', ' ')}</span>
                </div>
            `).join('')}
            <a href="#/patient/progress" class="btn btn-ghost btn-sm" style="margin-top: var(--space-3); width: 100%; justify-content: center;">
                View All Progress →
            </a>
        </div>
    `;
}


function _renderCareTeam(team) {
    const section = document.getElementById('careTeamSection');
    if (!section) return;

    if (!team || team.length === 0) {
        section.innerHTML = `
            <div class="card-header"><h3>👨‍⚕️ Your Care Team</h3></div>
            <div class="empty-state">
                <div class="empty-icon">👨‍⚕️</div>
                <div class="empty-title">No Care Team Assigned</div>
                <div class="empty-desc">Your hospital admin will assign your care team.</div>
            </div>
        `;
        return;
    }

    const roleIcons = { doctor: '🩺', guardian: '🛡️' };

    section.innerHTML = `
        <div class="card-header"><h3>👨‍⚕️ Your Care Team</h3></div>
        <div style="padding: var(--space-4);">
            ${team.map(m => `
                <div class="care-team-card">
                    <div class="care-team-avatar">${escapeHtml(roleIcons[m.role] || '👤')}</div>
                    <div class="care-team-info">
                        <div class="care-team-name">${escapeHtml(m.full_name)}</div>
                        <div class="care-team-role">${m.role.charAt(0).toUpperCase() + m.role.slice(1)}</div>
                        ${m.email ? `<div class="care-team-contact">${escapeHtml(m.email)}</div>` : ''}
                        ${m.phone ? `<div class="care-team-contact">${escapeHtml(m.phone)}</div>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}


/* ── Utility ───────────────────────────────────────────────── */

