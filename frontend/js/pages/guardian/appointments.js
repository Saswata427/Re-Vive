/** Guardian appointments: the linked patient's visits, read-only. */

async function renderGuardianAppointments() {
    renderDashboardShell('guardian', 'appointments', 'Appointments', `
        <div class="page-header">
            <h1>Appointments</h1>
            <p>Your linked patient's scheduled visits and history.</p>
        </div>

        <div id="gNextApptSection">
            <div class="card glass"><div class="loading-overlay"><div class="spinner"></div></div></div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header"><h3>Upcoming Appointments</h3></div>
            <div id="gUpcomingAppts">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header"><h3>Visit History</h3></div>
            <div id="gPastAppts">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>
    `);

    await loadGuardianAppointments();
}


async function loadGuardianAppointments() {
    try {
        const data = await api.get('/appointments?limit=200');
        const now = Date.now();

        const upcoming = data.appointments
            .filter(a => a.status === 'scheduled' && new Date(a.date_time).getTime() >= now)
            .sort((a, b) => new Date(a.date_time) - new Date(b.date_time));
        const past = data.appointments.filter(a => !upcoming.includes(a));

        _renderGNextAppt(upcoming[0]);
        _renderGUpcoming(upcoming);
        _renderGPast(past);
    } catch (err) {
        showToast(err.message || 'Failed to load appointments', 'error');
        _renderGNextAppt(null);
        ['gUpcomingAppts', 'gPastAppts'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">⚠️</div>
                        <div class="empty-title">Failed to load</div>
                        <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
                    </div>
                `;
            }
        });
    }
}


function _renderGNextAppt(appt) {
    const section = document.getElementById('gNextApptSection');
    if (!section) return;

    if (!appt) {
        section.innerHTML = `
            <div class="card glass">
                <div class="empty-state">
                    <div class="empty-icon">🗓️</div>
                    <div class="empty-title">No Upcoming Visits</div>
                    <div class="empty-desc">The care team will schedule the next appointment.</div>
                </div>
            </div>
        `;
        return;
    }

    section.innerHTML = `
        <div class="card glass next-appt-card">
            <div class="next-appt-badge">Next Visit</div>
            <div class="next-appt-body">
                <div class="next-appt-when">
                    <div class="next-appt-date">${formatDateTime(appt.date_time)}</div>
                    <div class="next-appt-countdown">${formatCountdown(appt.date_time)}</div>
                </div>
                <div class="next-appt-details">
                    <div class="next-appt-reason">${escapeHtml(appt.reason || 'Consultation')}</div>
                    <div class="next-appt-meta">${escapeHtml(appt.doctor_name || 'Doctor')} • ⏱️ ${escapeHtml(appt.duration_minutes)} min</div>
                    ${appt.notes ? `<div class="next-appt-notes">${escapeHtml(appt.notes)}</div>` : ''}
                </div>
            </div>
        </div>
    `;
}


function _renderGUpcoming(upcoming) {
    const list = document.getElementById('gUpcomingAppts');
    if (!list) return;

    if (!upcoming.length) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📅</div>
                <div class="empty-title">Nothing Scheduled</div>
                <div class="empty-desc">There are no upcoming appointments.</div>
            </div>
        `;
        return;
    }

    list.innerHTML = `
        <div style="padding: var(--space-4);">
            ${upcoming.map(appt => `
                <div class="appt-row">
                    <div class="appt-row-date">
                        <span class="appt-row-day">${new Date(appt.date_time).getDate()}</span>
                        <span class="appt-row-month">${new Date(appt.date_time).toLocaleString(undefined, { month: 'short' })}</span>
                    </div>
                    <div class="appt-row-info">
                        <div class="appt-row-reason">${escapeHtml(appt.reason || 'Consultation')}</div>
                        <div class="appt-row-meta">
                            ${new Date(appt.date_time).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                            • 🩺 ${escapeHtml(appt.doctor_name || 'Doctor')}
                            • ⏱️ ${appt.duration_minutes} min
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}


function _renderGPast(past) {
    const list = document.getElementById('gPastAppts');
    if (!list) return;

    if (!past.length) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🗂️</div>
                <div class="empty-title">No History Yet</div>
                <div class="empty-desc">Completed and cancelled visits will appear here.</div>
            </div>
        `;
        return;
    }

    list.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date &amp; Time</th>
                        <th>Reason</th>
                        <th>Doctor</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${past.map(appt => {
                        const cfg = APPT_STATUS_CONFIG[appt.status] || APPT_STATUS_CONFIG.scheduled;
                        return `
                            <tr>
                                <td>${formatDateTime(appt.date_time)}</td>
                                <td>${escapeHtml(appt.reason || '—')}</td>
                                <td>${escapeHtml(appt.doctor_name || '—')}</td>
                                <td><span class="badge ${escapeHtml(cfg.badge)}">${escapeHtml(cfg.icon)} ${escapeHtml(cfg.label)}</span></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}


