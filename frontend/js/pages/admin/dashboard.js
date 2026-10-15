/** Admin dashboard: live platform stats. */

async function renderAdminDashboard() {
    const user = api.getUser();

    renderDashboardShell('admin', 'dashboard', 'Dashboard', `
        <div class="welcome-banner card glass">
            <h1>Welcome back, <span>${escapeHtml(user?.name || 'Admin')}</span></h1>
            <p>Here's an overview of your platform.</p>
        </div>
        <div class="dashboard-grid" id="statsGrid">
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
    `);

    try {
        const stats = await api.get('/admin/stats');
        const grid = document.getElementById('statsGrid');
        if (grid) {
            grid.innerHTML = `
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-primary-rgb), 0.15); color: var(--accent-primary);">🏥</div>
                    <div class="stat-value">${escapeHtml(stats.total_hospitals)}</div>
                    <div class="stat-label">Total Hospitals</div>
                    <div style="margin-top: var(--space-2); font-size: var(--text-xs); color: var(--accent-success);">${escapeHtml(stats.active_hospitals)} active</div>
                </div>
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-success-rgb), 0.15); color: var(--accent-success);">🩺</div>
                    <div class="stat-value">${escapeHtml(stats.total_doctors)}</div>
                    <div class="stat-label">Total Doctors</div>
                </div>
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-secondary-rgb), 0.15); color: var(--accent-secondary);">🧑</div>
                    <div class="stat-value">${escapeHtml(stats.total_patients)}</div>
                    <div class="stat-label">Total Patients</div>
                </div>
                <div class="card glass stat-card">
                    <div class="stat-icon" style="background: rgba(var(--accent-info-rgb), 0.15); color: var(--accent-info);">👥</div>
                    <div class="stat-value">${escapeHtml(stats.total_users)}</div>
                    <div class="stat-label">Total Users</div>
                    <div style="margin-top: var(--space-2); font-size: var(--text-xs); color: var(--accent-warning);">${escapeHtml(stats.total_guardians)} guardians</div>
                </div>
            `;
        }
    } catch (err) {
        showToast('Failed to load statistics', 'error');
    }
}
