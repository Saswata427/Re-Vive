/** Doctor dashboard: greeting, today's schedule, caseload, risk and quick links. */

async function renderDoctorDashboard() {
    const user = api.getUser();
    const name = user?.name ? user.name.replace(/^Dr\.\s*/i, '') : 'Doctor';
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning,' : hour < 18 ? 'Good afternoon,' : 'Good evening,';

    renderDashboardShell('doctor', 'dashboard', 'Dashboard', `
        <section class="doctor-hero">
            <div class="doctor-hero-copy">
                <div class="eyebrow">Doctor dashboard</div>
                <div class="doctor-greeting">${greeting}</div>
                <h1>Dr. <span>${escapeHtml(name)}</span></h1>
                <p>Here’s an overview of your patients and today’s activity.</p>
                <div class="doctor-quote">
                    <span class="quote-mark">“</span>
                    <span>Better movement. Brighter tomorrows.</span>
                    <strong>— RE:VIVE</strong>
                </div>
            </div>
            <div class="doctor-hero-art" aria-hidden="true">
                <span class="hero-script">Healthcare<br><em>for a stronger<br>tomorrow</em></span>
            </div>

            <aside class="doctor-schedule-card" aria-labelledby="scheduleHeading">
                <div class="schedule-date" id="scheduleDate">Today</div>
                <div class="schedule-heading">
                    <span class="schedule-icon" aria-hidden="true">▣</span>
                    <strong id="scheduleHeading">Today's Schedule</strong>
                    <a href="#/doctor/appointments">View All →</a>
                </div>
                <div id="todaySchedule" class="schedule-list">
                    <div class="schedule-empty">Loading schedule...</div>
                </div>
            </aside>
        </section>

        <section class="doctor-dashboard-row">
            <div class="doctor-main-column">
                <div class="dashboard-grid doctor-stats" id="docStatsGrid">
                    <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
                    <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
                    <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
                    <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
                </div>

                <section class="card glass" id="doctorAIRiskSummary">
                    <div class="card-header doctor-section-header">
                        <div><div class="section-kicker">AI-assisted triage</div><h3>Recovery Risk Overview</h3><p>Prototype risk estimates from your patients' recent recovery signals</p></div>
                    </div>
                    <div class="ai-risk-loading"><div class="spinner"></div><span>Loading patient risk signals...</span></div>
                </section>

                <section class="card glass doctor-patients-card">
                    <div class="card-header doctor-section-header">
                        <div>
                            <div class="section-kicker">Patient management</div>
                            <h3>Recent Patients</h3>
                            <p>Your most recent patient activity</p>
                        </div>
                        <a href="#/doctor/patients" class="btn btn-ghost btn-sm">View All →</a>
                    </div>
                    <div id="recentActivity">
                        <div class="loading-overlay"><div class="spinner"></div><span>Loading activity...</span></div>
                    </div>
                </section>
            </div>

            <aside class="doctor-action-rail" aria-label="Quick actions">
                <div class="doctor-action-title">
                    <span class="action-symbol" aria-hidden="true">ϟ</span>
                    <div><h3>Quick Actions</h3><p>Get things done quickly</p></div>
                </div>
                <a href="#/doctor/patients" class="doctor-action-item"><span aria-hidden="true">👥</span><b>View My Patients</b><i aria-hidden="true">→</i></a>
                <a href="#/doctor/appointments" class="doctor-action-item"><span aria-hidden="true">📅</span><b>Schedule Appointment</b><i aria-hidden="true">→</i></a>
                <a href="#/doctor/analytics" class="doctor-action-item"><span aria-hidden="true">▥</span><b>View Analytics</b><i aria-hidden="true">→</i></a>
            </aside>
        </section>

        <section class="doctor-lower-grid">
            <section class="doctor-tools card glass">
                <div class="card-header doctor-section-header">
                    <div><div class="section-kicker">Workspace</div><h3>System Tools</h3><p>Quick access to commonly used features</p></div>
                </div>
                <div class="doctor-tool-grid">
                    <a href="#/doctor/patients" class="doctor-tool"><span aria-hidden="true">👥</span><b>Patient Management</b><i aria-hidden="true">→</i></a>
                    <a href="#/doctor/appointments" class="doctor-tool"><span aria-hidden="true">📅</span><b>Appointments</b><i aria-hidden="true">→</i></a>
                    <a href="#/doctor/analytics" class="doctor-tool"><span aria-hidden="true">▥</span><b>Caseload</b><i aria-hidden="true">→</i></a>
                </div>
            </section>

            <section class="doctor-resources card glass">
                <div class="card-header doctor-section-header">
                    <div><div class="section-kicker">Support</div><h3>Support & Resources</h3></div>
                </div>
                <a href="#/doctor/analytics" class="resource-row"><span aria-hidden="true">▣</span><b>Caseload overview</b><i aria-hidden="true">→</i></a>
                <a href="#/doctor/appointments" class="resource-row"><span aria-hidden="true">?</span><b>Appointment management</b><i aria-hidden="true">→</i></a>
                <a href="#/doctor/patients" class="resource-row"><span aria-hidden="true">●</span><b>Patient management</b><i aria-hidden="true">→</i></a>
            </section>
        </section>
    `);

    loadDoctorDashboardStats();
    loadDoctorRecentPatients();
    loadDoctorSchedule();
    loadDoctorAIRiskSummary();
}

async function loadDoctorDashboardStats() {
    try {
        const stats = await api.get('/doctor/dashboard');
        const grid = document.getElementById('docStatsGrid');
        if (!grid) return;

        const tiles = [
            ['stat-red', '🩺', 'Assigned Patients', stats.assigned_patients],
            ['stat-blue', '📝', 'Check-ins (7d)', stats.recent_checkins],
            ['stat-green', '🎯', 'Active Goals', stats.active_goals],
            ['stat-red', '📋', 'Clinical Notes', stats.total_notes],
        ];
        grid.innerHTML = tiles.map(([tone, icon, label, value]) => `
            <div class="card glass stat-card">
                <div class="stat-icon ${tone}" aria-hidden="true">${icon}</div>
                <div class="stat-label">${label}</div>
                <div class="stat-value">${Number(value) || 0}</div>
            </div>
        `).join('');
    } catch (err) {
        showToast('Failed to load dashboard statistics', 'error');
    }
}

async function loadDoctorRecentPatients() {
    try {
        const patientData = await api.get('/doctor/patients');
        const activityDiv = document.getElementById('recentActivity');
        if (!activityDiv) return;

        if (!patientData.patients.length) {
            activityDiv.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🩺</div>
                    <div class="empty-title">No Patients Assigned</div>
                    <div class="empty-desc">Ask your hospital admin to assign patients to you.</div>
                </div>`;
            return;
        }

        activityDiv.innerHTML = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr><th>Patient</th><th>Status</th><th>Last Check-in</th><th>Active Goals</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${patientData.patients.map(p => `
                            <tr>
                                <td><div class="patient-cell"><span class="patient-avatar">${escapeHtml((p.full_name || '?').split(' ').map(x=>x[0]).slice(0,2).join('').toUpperCase())}</span><div><strong>${escapeHtml(p.full_name)}</strong><small>${escapeHtml(p.email)}</small></div></div></td>
                                <td><span class="badge ${p.is_active ? 'badge-success' : 'badge-danger'}">${p.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>${p.last_checkin_date ? formatDate(p.last_checkin_date) : '—'}</td>
                                <td><span class="badge badge-warning">${Number(p.active_goals) || 0} active</span></td>
                                <td><a href="#/doctor/patients/${encodeURIComponent(p.id)}" class="btn btn-ghost btn-sm">View →</a></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
    } catch (err) {
        const activityDiv = document.getElementById('recentActivity');
        if (activityDiv) activityDiv.innerHTML = `<div class="empty-state"><div class="empty-title">Could not load patients</div><div class="empty-desc">Refresh the page to try again.</div></div>`;
    }
}

async function loadDoctorSchedule() {
    const list = document.getElementById('todaySchedule');
    const dateEl = document.getElementById('scheduleDate');
    if (!list) return;

    const now = new Date();
    if (dateEl) dateEl.textContent = now.toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric', year:'numeric'});

    try {
        const data = await api.get('/appointments?limit=200');
        const todayKey = now.toDateString();
        const appointments = (data.appointments || [])
            .filter(a => a.status !== 'cancelled' && new Date(a.date_time).toDateString() === todayKey)
            .sort((a,b) => new Date(a.date_time) - new Date(b.date_time))
            .slice(0, 3);

        if (!appointments.length) {
            list.innerHTML = `<div class="schedule-empty">No appointments scheduled for today.</div>`;
            return;
        }

        list.innerHTML = appointments.map(a => `
            <div class="schedule-item">
                <span class="schedule-dot" aria-hidden="true"></span>
                <time>${new Date(a.date_time).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'})}</time>
                <div><strong>${escapeHtml(a.reason || 'Appointment')}</strong><small>${a.patient_name ? `with ${escapeHtml(a.patient_name)}` : ''}</small></div>
            </div>
        `).join('');
    } catch (err) {
        list.innerHTML = `<div class="schedule-empty">Schedule unavailable.</div>`;
    }
}



async function loadDoctorAIRiskSummary() {
    const container = document.getElementById('doctorAIRiskSummary');
    if (!container) return;
    try {
        const data = await api.get('/doctor/patients');
        const patients = data.patients || [];
        if (!patients.length) {
            container.innerHTML = `<div class="card-header doctor-section-header"><div><div class="section-kicker">AI-assisted triage</div><h3>Recovery Risk Overview</h3><p>No assigned patients yet.</p></div></div>`;
            return;
        }
        const results = await Promise.all(patients.slice(0, 8).map(async patient => {
            try { return { patient, result: await getPatientRiskResult('doctor', patient.id) }; }
            catch { return { patient, result: null }; }
        }));
        container.innerHTML = `
            <div class="card-header doctor-section-header">
                <div><div class="section-kicker">AI-assisted triage</div><h3>Recovery Risk Overview</h3><p>Prototype risk estimates from recent recovery signals</p></div>
                <a href="#/doctor/patients" class="btn btn-ghost btn-sm">Review Patients →</a>
            </div>
            <div class="doctor-ai-risk-grid">
                ${results.map(({patient,result}) => {
                    if (!result) return `<div class="ai-risk-unavailable ai-risk-inline"><span>🧠</span><div><strong>${escapeHtml(patient.full_name)}</strong><small>AI unavailable</small></div></div>`;
                    const meta = aiRiskMeta(result.risk_category);
                    const pct = Math.round((result.recovery_risk_probability || 0) * 100);
                    return `<a class="doctor-ai-risk-mini ${escapeHtml(meta.cls)}" href="#/doctor/patients/${encodeURIComponent(patient.id)}"><div class="mini-patient"><span>${meta.icon}</span><div><strong>${escapeHtml(patient.full_name)}</strong><small>${escapeHtml(meta.label)}</small></div></div><b>${pct}%</b></a>`;
                }).join('')}
            </div>`;
    } catch (err) {
        container.innerHTML = `<div class="ai-risk-unavailable"><span>🧠</span><div><strong>Recovery Risk AI is unavailable</strong><small>Start the AI service on port 8010 to enable risk estimates.</small></div></div>`;
    }
}
