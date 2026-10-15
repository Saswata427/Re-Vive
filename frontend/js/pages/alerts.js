/** Full alert history, shared by the patient and guardian portals. */

let alertsFilter = 'all';
let alertsPageRole = 'patient';

async function renderAlertsPage(role) {
    alertsPageRole = role;
    alertsFilter = 'all';

    renderDashboardShell(role, 'alerts', 'Alerts', `
        <div class="page-header">
            <h1>Alerts</h1>
            <p>${role === 'guardian'
                ? "Clinical alerts raised about your linked patient."
                : "Clinical alerts raised about your recovery."}</p>
        </div>

        <div class="card glass">
            <div class="card-header">
                <h3>Alert History</h3>
                <div class="flex gap-2 items-center">
                    <select id="alertsFilter" class="form-input" style="width: auto;" onchange="filterAlertsPage(this.value)">
                        <option value="all">All alerts</option>
                        <option value="unread">Unread only</option>
                    </select>
                    <button class="btn btn-secondary btn-sm" onclick="markAllOnAlertsPage()">Mark all read</button>
                </div>
            </div>
            <div id="alertsPageList">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading alerts...</span></div>
            </div>
        </div>
    `);

    await loadAlertsPage();
}


async function loadAlertsPage() {
    const list = document.getElementById('alertsPageList');
    if (!list) return;

    const query = alertsFilter === 'unread' ? '?unread_only=true&limit=100' : '?limit=100';

    try {
        const data = await api.get(`/alerts${query}`);
        _paintBadge(data.unread);

        if (!data.alerts.length) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔕</div>
                    <div class="empty-title">${alertsFilter === 'unread' ? 'Nothing Unread' : 'No Alerts'}</div>
                    <div class="empty-desc">${alertsFilter === 'unread'
                        ? 'Every alert has been read.'
                        : 'Clinical alerts will appear here as they are raised.'}</div>
                </div>
            `;
            return;
        }

        list.innerHTML = `
            <div class="alerts-page-list">
                ${data.alerts.map(a => {
                    const cfg = ALERT_CONFIG[a.alert_type] || { icon: '🔔', label: a.alert_type };
                    const sev = SEVERITY_CONFIG[a.severity] || SEVERITY_CONFIG.low;
                    return `
                        <div class="alerts-page-item ${a.is_read ? '' : 'unread'}">
                            <div class="alerts-page-icon" style="color: ${escapeHtml(sev.color)};">${escapeHtml(cfg.icon)}</div>
                            <div class="alerts-page-body">
                                <div class="alerts-page-top">
                                    <span class="badge ${escapeHtml(sev.badge)}">${escapeHtml(cfg.label)}</span>
                                    <span class="alerts-page-time">${formatRelativeTime(a.created_at)}</span>
                                </div>
                                <div class="alerts-page-message">${escapeHtml(a.message)}</div>
                                ${a.patient_name ? `<div class="alerts-page-meta">${escapeHtml(a.patient_name)}</div>` : ''}
                            </div>
                            ${a.is_read
                                ? '<span class="alerts-page-read">Read</span>'
                                : `<button class="btn btn-ghost btn-sm" onclick="markOneOnAlertsPage('${escapeHtml(a.id)}')">Mark read</button>`}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (err) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Failed to load alerts</div>
                <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
    }
}


function filterAlertsPage(value) {
    alertsFilter = value;
    loadAlertsPage();
}


async function markOneOnAlertsPage(alertId) {
    try {
        await api.patch(`/alerts/${alertId}/read`);
        await loadAlertsPage();
    } catch (err) {
        showToast(err.message || 'Failed to update alert', 'error');
    }
}


async function markAllOnAlertsPage() {
    try {
        const result = await api.patch('/alerts/read-all');
        if (result.updated > 0) {
            showToast(`${result.updated} alert(s) marked as read`, 'success');
        }
        await loadAlertsPage();
    } catch (err) {
        showToast(err.message || 'Failed to mark alerts as read', 'error');
    }
}
