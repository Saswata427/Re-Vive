/** Patient profile: their own clinical record and care team, read-only. */

async function renderPatientProfile() {
    renderDashboardShell('patient', 'profile', 'My Profile', `
        <div class="page-header">
            <h1>My Profile</h1>
            <p>Your recovery record and care team contacts.</p>
        </div>

        <div class="card glass" id="profileCard">
            <div class="loading-overlay"><div class="spinner"></div><span>Loading profile...</span></div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header"><h3>My Care Plan</h3></div>
            <div id="patientPlanCard">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header"><h3>My Medications</h3></div>
            <div id="patientMedsCard">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>
    `);

    const me = api.getUser();
    await Promise.all([
        _loadPatientProfile(),
        me?.id ? _loadPatientPlan(me.id) : Promise.resolve(),
        me?.id ? _loadPatientMeds(me.id) : Promise.resolve(),
    ]);
}


async function _loadPatientProfile() {
    const card = document.getElementById('profileCard');
    if (!card) return;

    try {
        const p = await api.get('/patient/profile');

        card.innerHTML = `
            <div class="card-header"><h3>Recovery Record</h3></div>
            <div class="patient-detail-grid">
                <div class="patient-detail-item">
                    <div class="detail-label">Full Name</div>
                    <div class="detail-value">${escapeHtml(p.full_name)}</div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Email</div>
                    <div class="detail-value">${escapeHtml(p.email)}</div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Phone</div>
                    <div class="detail-value">${escapeHtml(p.phone || '—')}</div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Primary Condition</div>
                    <div class="detail-value">${escapeHtml(p.primary_condition || '—')}</div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Therapy Program</div>
                    <div class="detail-value">${escapeHtml(p.therapy_program || '—')}</div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Program Start</div>
                    <div class="detail-value">${p.program_start_date ? formatDateShort(p.program_start_date) : '—'}</div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Days Abstinent</div>
                    <div class="detail-value" style="color: var(--accent-success); font-weight: 600;">
                        ${p.abstinence_days != null ? p.abstinence_days : '—'}
                    </div>
                </div>
                <div class="patient-detail-item">
                    <div class="detail-label">Emergency Contact</div>
                    <div class="detail-value">${escapeHtml(p.emergency_contact || '—')}</div>
                </div>
            </div>

            <div style="margin-top: var(--space-6); padding-top: var(--space-5); border-top: 1px solid var(--glass-border);">
                <h4 style="margin-bottom: var(--space-4); font-size: var(--text-base); color: var(--text-secondary);">👨‍⚕️ Care Team</h4>
                ${_renderContactCards([p.assigned_doctor, p.guardian].filter(Boolean))}
            </div>
        `;
    } catch (err) {
        card.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Failed to load profile</div>
                <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
    }
}


async function _loadPatientPlan(patientId) {
    const card = document.getElementById('patientPlanCard');
    if (!card) return;

    try {
        const data = await api.get(`/clinical/patients/${patientId}/treatment-plan`);

        if (!data.current) {
            card.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🗺️</div>
                    <div class="empty-title">No Care Plan Yet</div>
                    <div class="empty-desc">Your doctor will set out your recovery plan here.</div>
                </div>
            `;
            return;
        }

        const p = data.current;
        card.innerHTML = `
            <div style="padding: var(--space-5);">
                <div class="plan-current">
                    <div class="plan-head">
                        <span class="plan-version">Your current plan</span>
                        <span class="plan-meta">
                            ${escapeHtml(p.doctor_name || 'Your doctor')} · ${formatDateShort(p.created_at)}
                            ${p.review_date ? ` · review ${formatDateShort(p.review_date)}` : ''}
                        </span>
                    </div>
                    ${p.focus_areas && p.focus_areas.length ? `
                        <div class="plan-focus">
                            ${p.focus_areas.map(f => `<span class="plan-focus-chip">${f}</span>`).join('')}
                        </div>
                    ` : ''}
                    <div class="plan-summary">${escapeHtml(p.summary)}</div>
                </div>
            </div>
        `;
    } catch (err) {
        card.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Failed to load care plan</div>
            </div>
        `;
    }
}


async function _loadPatientMeds(patientId) {
    const card = document.getElementById('patientMedsCard');
    if (!card) return;

    try {
        const data = await api.get(`/clinical/patients/${patientId}/medications`);
        const active = data.medications.filter(m => m.is_active);

        if (!active.length) {
            card.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💊</div>
                    <div class="empty-title">No Active Medications</div>
                    <div class="empty-desc">Prescriptions from your doctor will appear here.</div>
                </div>
            `;
            return;
        }

        card.innerHTML = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr><th>Medication</th><th>Dosage</th><th>Frequency</th><th>Instructions</th></tr>
                    </thead>
                    <tbody>
                        ${active.map(m => `
                            <tr>
                                <td><strong>${escapeHtml(m.name)}</strong></td>
                                <td>${escapeHtml(m.dosage)}</td>
                                <td>${escapeHtml(m.frequency)}</td>
                                <td style="font-size: var(--text-xs); color: var(--text-secondary);">${escapeHtml(m.notes || '—')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        card.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Failed to load medications</div>
            </div>
        `;
    }
}
