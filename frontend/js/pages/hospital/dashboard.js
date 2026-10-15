/** Hospital dashboard: this hospital's stats. */

async function renderHospitalDashboard() {
    const user = api.getUser();

    renderDashboardShell('hospital', 'dashboard', 'Dashboard', `
        <div class="welcome-banner card glass">
            <h1>Welcome back, <span>${escapeHtml(user?.name || 'Hospital Admin')}</span></h1>
            <p>Here's an overview of your hospital.</p>
        </div>
        <div class="dashboard-grid" id="hospStatsGrid">
            <div class="card glass stat-card">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass stat-card">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass stat-card">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
            <div class="card glass stat-card">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="dashboard-grid" style="margin-top: var(--space-6);">
            <div class="card glass" style="grid-column: span 2;">
                <div style="padding: var(--space-5);">
                    <h3 style="margin-bottom: var(--space-4); color: var(--text-primary);">Quick Actions</h3>
                    <div class="flex gap-3 flex-wrap">
                        <a href="#/hospital/users" class="btn btn-primary">👨‍⚕️ Manage Users</a>
                        <a href="#/hospital/assignments" class="btn btn-secondary">Manage Assignments</a>
                    </div>
                </div>
            </div>
        </div>
    `);

    try {
        const stats = await api.get('/hospital/dashboard');
        const grid = document.getElementById('hospStatsGrid');
        if (grid) {
            grid.innerHTML = `
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-primary-rgb), 0.15); color: var(--accent-primary);">🩺</div>
                    <div class="stat-value">${escapeHtml(stats.total_doctors)}</div>
                    <div class="stat-label">Doctors</div>
                </div>
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-secondary-rgb), 0.15); color: var(--accent-secondary);">🧑</div>
                    <div class="stat-value">${escapeHtml(stats.total_patients)}</div>
                    <div class="stat-label">Patients</div>
                </div>
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-warning-rgb), 0.15); color: var(--accent-warning);">👥</div>
                    <div class="stat-value">${escapeHtml(stats.total_guardians)}</div>
                    <div class="stat-label">Guardians</div>
                </div>
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-success-rgb), 0.15); color: var(--accent-success);">✓</div>
                    <div class="stat-value">${escapeHtml(stats.active_users)}</div>
                    <div class="stat-label">Active Users</div>
                    <div style="margin-top: var(--space-2); font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(stats.total_users)} total</div>
                </div>
            `;
        }
    } catch (err) {
        showToast('Failed to load dashboard statistics', 'error');
    }
}
