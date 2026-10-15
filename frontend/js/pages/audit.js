/** Audit trail: platform-wide for admins, own hospital for hospital admins. */

let auditRole = 'admin';
let auditSkip = 0;
let auditTotal = 0;
const AUDIT_PAGE_SIZE = 50;

const AUDIT_ACTOR_BADGES = {
    admin: 'badge-primary',
    hospital: 'badge-info',
    doctor: 'badge-success',
    patient: 'badge-warning',
    guardian: 'badge-warning',
};


async function renderAuditPage(role) {
    auditRole = role;
    auditSkip = 0;

    renderDashboardShell(role, 'audit', 'Audit Trail', `
        <div class="page-header">
            <h1>Audit Trail</h1>
            <p>${role === 'admin'
                ? 'Every recorded action across the platform.'
                : "Actions taken by your hospital's users."}</p>
        </div>

        <div class="card glass">
            <div class="card-header">
                <h3>Recorded Actions</h3>
                <span class="badge badge-info" id="auditCount">—</span>
            </div>

            <div class="audit-filters">
                <div class="form-group">
                    <label class="form-label" for="auditAction">Action</label>
                    <select id="auditAction" class="form-input" onchange="applyAuditFilters()">
                        <option value="">All actions</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="auditResource">Resource</label>
                    <select id="auditResource" class="form-input" onchange="applyAuditFilters()">
                        <option value="">All resources</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="auditFrom">From</label>
                    <input type="date" id="auditFrom" class="form-input" onchange="applyAuditFilters()" />
                </div>
                <div class="form-group">
                    <label class="form-label" for="auditTo">To</label>
                    <input type="date" id="auditTo" class="form-input" onchange="applyAuditFilters()" />
                </div>
                <button class="btn btn-secondary btn-sm" onclick="clearAuditFilters()">Clear</button>
            </div>

            <div id="auditContent">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading trail...</span></div>
            </div>

            <div class="audit-pager" id="auditPager" hidden>
                <button class="btn btn-secondary btn-sm" id="auditPrev" onclick="auditPage(-1)">← Newer</button>
                <span class="audit-range" id="auditRange"></span>
                <button class="btn btn-secondary btn-sm" id="auditNext" onclick="auditPage(1)">Older →</button>
            </div>
        </div>
    `);

    await Promise.all([_loadAuditFacets(), loadAuditLogs()]);
}


function _auditBase() {
    return auditRole === 'admin' ? '/admin/audit-logs' : '/hospital/audit-logs';
}


async function _loadAuditFacets() {
    try {
        const facets = await api.get(`${_auditBase()}/facets`);

        const actionSel = document.getElementById('auditAction');
        if (actionSel) {
            actionSel.innerHTML = '<option value="">All actions</option>' +
                facets.actions.map(a =>
                    `<option value="${a}">${a.replace(/_/g, ' ')}</option>`).join('');
        }

        const resSel = document.getElementById('auditResource');
        if (resSel) {
            resSel.innerHTML = '<option value="">All resources</option>' +
                facets.resource_types.map(r =>
                    `<option value="${r}">${r.replace(/_/g, ' ')}</option>`).join('');
        }
    } catch (err) {
        // Filters are a convenience — the trail still lists without them
    }
}


function _auditQuery() {
    const params = new URLSearchParams();
    const action = document.getElementById('auditAction')?.value;
    const resource = document.getElementById('auditResource')?.value;
    const from = document.getElementById('auditFrom')?.value;
    const to = document.getElementById('auditTo')?.value;

    if (action) params.set('action', action);
    if (resource) params.set('resource_type', resource);
    if (from) params.set('date_from', from);
    if (to) params.set('date_to', to);
    params.set('limit', AUDIT_PAGE_SIZE);
    params.set('skip', auditSkip);

    return params.toString();
}


async function loadAuditLogs() {
    const content = document.getElementById('auditContent');
    if (!content) return;

    try {
        const data = await api.get(`${_auditBase()}?${_auditQuery()}`);
        auditTotal = data.total;

        const countEl = document.getElementById('auditCount');
        if (countEl) countEl.textContent = `${data.total} entr${data.total === 1 ? 'y' : 'ies'}`;

        _renderAuditPager(data);

        if (!data.logs.length) {
            content.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📜</div>
                    <div class="empty-title">No Matching Entries</div>
                    <div class="empty-desc">${auditSkip > 0 || _auditQuery().length > 30
                        ? 'Try widening the filters.'
                        : 'Actions will be recorded here as people use the platform.'}</div>
                </div>
            `;
            return;
        }

        content.innerHTML = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>When</th>
                            <th>Actor</th>
                            <th>Action</th>
                            <th>Resource</th>
                            <th>Details</th>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.logs.map(l => `
                            <tr>
                                <td style="white-space: nowrap; font-size: var(--text-xs);">
                                    ${formatDateTime(l.created_at)}
                                </td>
                                <td>
                                    <div style="font-weight: 500;">${escapeHtml(l.actor_name || '—')}</div>
                                    ${l.actor_role ? `<span class="badge ${escapeHtml(AUDIT_ACTOR_BADGES[l.actor_role] || '')}" style="margin-top: 2px;">${escapeHtml(l.actor_role)}</span>` : ''}
                                </td>
                                <td><code class="audit-action">${l.action.replace(/_/g, ' ')}</code></td>
                                <td style="font-size: var(--text-xs); color: var(--text-secondary);">
                                    ${escapeHtml(l.resource_type || '—')}
                                </td>
                                <td class="audit-details">${_auditDetails(l.details)}</td>
                                <td style="font-size: var(--text-xs); color: var(--text-muted);">
                                    ${escapeHtml(l.ip_address || '—')}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Failed to load the trail</div>
                <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
    }
}




function _auditDetails(details) {
    if (!details || Object.keys(details).length === 0) return '—';
    return Object.entries(details)
        .map(([k, v]) => {
            const value = Array.isArray(v) ? v.join(', ') : String(v);
            return `<span class="audit-detail-pair"><b>${k.replace(/_/g, ' ')}</b> ${value}</span>`;
        })
        .join('');
}


function _renderAuditPager(data) {
    const pager = document.getElementById('auditPager');
    if (!pager) return;

    if (data.total <= AUDIT_PAGE_SIZE) {
        pager.hidden = true;
        return;
    }
    pager.hidden = false;

    const first = data.total === 0 ? 0 : auditSkip + 1;
    const last = Math.min(auditSkip + AUDIT_PAGE_SIZE, data.total);
    document.getElementById('auditRange').textContent = `${first}–${last} of ${data.total}`;
    document.getElementById('auditPrev').disabled = auditSkip === 0;
    document.getElementById('auditNext').disabled = last >= data.total;
}


function auditPage(direction) {
    const next = auditSkip + direction * AUDIT_PAGE_SIZE;
    if (next < 0 || next >= auditTotal) return;
    auditSkip = next;
    loadAuditLogs();
}


function applyAuditFilters() {
    auditSkip = 0;
    loadAuditLogs();
}


function clearAuditFilters() {
    ['auditAction', 'auditResource', 'auditFrom', 'auditTo'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    applyAuditFilters();
}
