/** Doctor appointments: schedule, reschedule, complete and cancel. */

const APPT_STATUS_CONFIG = {
    scheduled: { label: 'Scheduled', badge: 'badge-info', icon: '📅' },
    completed: { label: 'Completed', badge: 'badge-success', icon: '✅' },
    cancelled: { label: 'Cancelled', badge: 'badge-danger', icon: '✖️' },
};

let doctorAppointments = [];
let doctorApptFilter = 'all';
let editingApptId = null;


async function renderDoctorAppointments() {
    renderDashboardShell('doctor', 'appointments', 'Appointments', `
        <div class="page-header">
            <h1>Appointments</h1>
            <p>Schedule and manage consultations with your assigned patients.</p>
        </div>

        <div class="dashboard-grid" id="apptStatsGrid">
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
            <div class="card glass stat-card"><div class="loading-overlay"><div class="spinner"></div></div></div>
        </div>

        <div class="card glass" style="margin-top: var(--space-6);">
            <div class="card-header">
                <h3>All Appointments</h3>
                <div class="flex gap-2 items-center">
                    <select id="apptStatusFilter" class="form-input" style="width: auto;" onchange="filterDoctorAppointments(this.value)">
                        <option value="all">All Statuses</option>
                        <option value="scheduled">Scheduled</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                    <button class="btn btn-primary btn-sm" onclick="openApptModal()">+ Schedule</button>
                </div>
            </div>
            <div id="apptTableContainer">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading appointments...</span></div>
            </div>
        </div>

        <div class="modal-overlay" id="apptModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="apptModalTitle">Schedule Appointment</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeApptModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="apptForm" class="flex flex-col gap-4">
                        <div class="form-group" id="apptPatientGroup">
                            <label class="form-label" for="apptPatient">Patient</label>
                            <select id="apptPatient" class="form-input" required>
                                <option value="">Loading patients...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="apptReason">Reason for Visit</label>
                            <input type="text" id="apptReason" class="form-input" placeholder="e.g., Post-surgery follow-up" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="apptDateTime">Date & Time</label>
                            <input type="datetime-local" id="apptDateTime" class="form-input" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="apptDuration">Duration (minutes)</label>
                            <select id="apptDuration" class="form-input">
                                <option value="15">15 minutes</option>
                                <option value="30" selected>30 minutes</option>
                                <option value="45">45 minutes</option>
                                <option value="60">1 hour</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="apptNotes">Notes <span style="color: var(--text-muted);">(optional)</span></label>
                            <textarea id="apptNotes" class="form-input" placeholder="Preparation instructions, context..." rows="3"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeApptModal()">Cancel</button>
                    <button class="btn btn-primary" id="apptSubmitBtn" onclick="submitAppointment()">Schedule</button>
                </div>
            </div>
        </div>
    `);

    await loadDoctorAppointments();
}


async function loadDoctorAppointments() {
    const container = document.getElementById('apptTableContainer');

    try {
        const data = await api.get('/appointments?limit=200');
        doctorAppointments = data.appointments;
        _renderApptStats(data);
        _renderApptTable();
    } catch (err) {
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <div class="empty-title">Failed to load appointments</div>
                    <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
                </div>
            `;
        }
        showToast(err.message || 'Failed to load appointments', 'error');
    }
}


function _renderApptStats(data) {
    const grid = document.getElementById('apptStatsGrid');
    if (!grid) return;

    const completed = doctorAppointments.filter(a => a.status === 'completed').length;

    grid.innerHTML = `
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-info-rgb), 0.15); color: var(--accent-info);">📅</div>
            <div class="stat-value">${escapeHtml(data.upcoming)}</div>
            <div class="stat-label">Upcoming</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-success-rgb), 0.15); color: var(--accent-success);">✅</div>
            <div class="stat-value">${completed}</div>
            <div class="stat-label">Completed</div>
        </div>
        <div class="card glass stat-card">
            <div class="stat-icon" style="background: rgba(var(--accent-primary-rgb), 0.15); color: var(--accent-primary);">📋</div>
            <div class="stat-value">${escapeHtml(data.total)}</div>
            <div class="stat-label">Total Appointments</div>
        </div>
    `;
}


function _renderApptTable() {
    const container = document.getElementById('apptTableContainer');
    if (!container) return;

    const rows = doctorApptFilter === 'all'
        ? doctorAppointments
        : doctorAppointments.filter(a => a.status === doctorApptFilter);

    if (!rows.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📅</div>
                <div class="empty-title">No Appointments</div>
                <div class="empty-desc">Schedule a consultation with one of your patients to get started.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Patient</th>
                        <th>Date & Time</th>
                        <th>Reason</th>
                        <th>Duration</th>
                        <th>Status</th>
                        <th style="text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(appt => {
                        const cfg = APPT_STATUS_CONFIG[appt.status] || APPT_STATUS_CONFIG.scheduled;
                        const isOpen = appt.status === 'scheduled';
                        return `
                            <tr>
                                <td><strong>${escapeHtml(appt.patient_name || '—')}</strong></td>
                                <td>${formatDateTime(appt.date_time)}</td>
                                <td>${escapeHtml(appt.reason || '—')}</td>
                                <td>${escapeHtml(appt.duration_minutes)} min</td>
                                <td><span class="badge ${escapeHtml(cfg.badge)}">${escapeHtml(cfg.icon)} ${escapeHtml(cfg.label)}</span></td>
                                <td style="text-align: right;">
                                    ${isOpen ? `
                                        <button class="btn btn-ghost btn-sm" onclick="openApptModal('${escapeHtml(appt.id)}')">Reschedule</button>
                                        <button class="btn btn-success btn-sm" onclick="setAppointmentStatus('${escapeHtml(appt.id)}', 'completed')">Complete</button>
                                        <button class="btn btn-danger btn-sm" onclick="setAppointmentStatus('${escapeHtml(appt.id)}', 'cancelled')">Cancel</button>
                                    ` : '<span style="color: var(--text-muted);">—</span>'}
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}


function filterDoctorAppointments(status) {
    doctorApptFilter = status;
    _renderApptTable();
}


/* ── Schedule Modal ─────────────────────────────────────── */

async function openApptModal(appointmentId = null) {
    editingApptId = appointmentId;

    const modal = document.getElementById('apptModal');
    const form = document.getElementById('apptForm');
    const title = document.getElementById('apptModalTitle');
    const submitBtn = document.getElementById('apptSubmitBtn');
    const patientGroup = document.getElementById('apptPatientGroup');

    form.reset();
    modal.classList.add('active');

    if (appointmentId) {
        // Reschedule: patient is fixed, so hide the selector
        const appt = doctorAppointments.find(a => a.id === appointmentId);
        title.textContent = 'Reschedule Appointment';
        submitBtn.textContent = 'Save Changes';
        patientGroup.hidden = true;

        if (appt) {
            document.getElementById('apptReason').value = appt.reason || '';
            document.getElementById('apptDateTime').value = toDateTimeLocal(appt.date_time);
            document.getElementById('apptDuration').value = appt.duration_minutes || 30;
            document.getElementById('apptNotes').value = appt.notes || '';
        }
        return;
    }

    title.textContent = 'Schedule Appointment';
    submitBtn.textContent = 'Schedule';
    patientGroup.hidden = false;
    document.getElementById('apptDuration').value = '30';

    await _loadPatientOptions();
}


async function _loadPatientOptions() {
    const select = document.getElementById('apptPatient');
    if (!select) return;

    try {
        const data = await api.get('/doctor/patients');
        if (!data.patients.length) {
            select.innerHTML = '<option value="">No patients assigned</option>';
            return;
        }
        select.innerHTML = '<option value="">Select a patient...</option>' +
            data.patients.map(p => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.full_name)}</option>`).join('');
    } catch (err) {
        select.innerHTML = '<option value="">Failed to load patients</option>';
        showToast(err.message || 'Failed to load patients', 'error');
    }
}


function closeApptModal() {
    document.getElementById('apptModal').classList.remove('active');
    editingApptId = null;
}


async function submitAppointment() {
    const reason = document.getElementById('apptReason').value.trim();
    const dateTimeValue = document.getElementById('apptDateTime').value;
    const duration_minutes = parseInt(document.getElementById('apptDuration').value, 10);
    const notes = document.getElementById('apptNotes').value.trim() || null;
    const btn = document.getElementById('apptSubmitBtn');

    if (!reason) {
        showToast('Please enter a reason for the visit', 'warning');
        return;
    }
    if (!dateTimeValue) {
        showToast('Please pick a date and time', 'warning');
        return;
    }

    const date_time = new Date(dateTimeValue).toISOString();
    const isEdit = !!editingApptId;
    const originalLabel = btn.textContent;

    let patient_id = null;
    if (!isEdit) {
        patient_id = document.getElementById('apptPatient').value;
        if (!patient_id) {
            showToast('Please select a patient', 'warning');
            return;
        }
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        if (isEdit) {
            await api.patch(`/appointments/${editingApptId}`, {
                date_time, duration_minutes, reason, notes,
            });
            showToast('Appointment rescheduled', 'success');
        } else {
            await api.post('/appointments', {
                patient_id, date_time, duration_minutes, reason, notes,
            });
            showToast('Appointment scheduled successfully', 'success');
        }
        closeApptModal();
        await loadDoctorAppointments();
    } catch (err) {
        showToast(err.message || 'Failed to save appointment', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalLabel;
    }
}


async function setAppointmentStatus(appointmentId, status) {
    const label = APPT_STATUS_CONFIG[status]?.label || status;

    try {
        await api.patch(`/appointments/${appointmentId}`, { status });
        showToast(`Appointment marked as ${label.toLowerCase()}`, 'success');
        await loadDoctorAppointments();
    } catch (err) {
        showToast(err.message || 'Failed to update appointment', 'error');
    }
}


/* ── Shared Date Helpers ────────────────────────────────── */



/** An ISO time in the format a datetime-local input wants. */
function toDateTimeLocal(isoString) {
    const dt = new Date(isoString);
    if (isNaN(dt)) return '';
    const pad = n => String(n).padStart(2, '0');
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`
        + `T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}
