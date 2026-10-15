/** Assign doctors to patients and link guardians. */

let assignmentsData = [];
let assignmentDoctors = [];
let assignmentPatients = [];
let assignmentGuardians = [];

async function renderHospitalAssignments() {
    renderDashboardShell('hospital', 'assignments', 'Assignments', `
        <div class="page-header">
            <h1>Assignments & Links</h1>
            <p>Assign doctors to patients and link guardians</p>
        </div>

        <div class="card glass" style="margin-bottom: var(--space-6);">
            <div class="card-header flex justify-between items-center">
                <h3>Doctor → Patient Assignments</h3>
                <button class="btn btn-primary btn-sm" onclick="openAssignModal()">+ Assign Doctor</button>
            </div>
            <div id="assignmentsLoading" class="loading-overlay">
                <div class="spinner"></div>
                <span>Loading assignments...</span>
            </div>
            <div id="assignmentsContent" style="display: none;"></div>
        </div>

        <div class="card glass">
            <div class="card-header flex justify-between items-center">
                <h3>Guardian → Patient Links</h3>
                <button class="btn btn-primary btn-sm" onclick="openGuardianLinkModal()">+ Link Guardian</button>
            </div>
            <div id="guardianLinksLoading" class="loading-overlay">
                <div class="spinner"></div>
                <span>Loading guardian links...</span>
            </div>
            <div id="guardianLinksContent" style="display: none;"></div>
        </div>

        <div class="modal-overlay" id="assignModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Assign Doctor to Patient</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeAssignModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="assignForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="assignDoctor">Doctor</label>
                            <select id="assignDoctor" class="form-input" required>
                                <option value="">Select a doctor...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="assignPatient">Patient</label>
                            <select id="assignPatient" class="form-input" required>
                                <option value="">Select a patient...</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeAssignModal()">Cancel</button>
                    <button class="btn btn-primary" id="assignSubmitBtn" onclick="submitAssignment()">Create Assignment</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="guardianLinkModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Link Guardian to Patient</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeGuardianLinkModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="guardianLinkForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="linkGuardian">Guardian</label>
                            <select id="linkGuardian" class="form-input" required>
                                <option value="">Select a guardian...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="linkPatient">Patient</label>
                            <select id="linkPatient" class="form-input" required>
                                <option value="">Select a patient...</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeGuardianLinkModal()">Cancel</button>
                    <button class="btn btn-primary" id="guardianLinkSubmitBtn" onclick="submitGuardianLink()">Link Guardian</button>
                </div>
            </div>
        </div>
    `);

    await loadAssignmentsPage();
}


async function loadAssignmentsPage() {
    try {
        const usersData = await api.get('/hospital/users');
        assignmentDoctors = usersData.users.filter(u => u.role === 'doctor' && u.is_active);
        assignmentPatients = usersData.users.filter(u => u.role === 'patient' && u.is_active);
        assignmentGuardians = usersData.users.filter(u => u.role === 'guardian' && u.is_active);

        const assignData = await api.get('/hospital/assignments');
        assignmentsData = assignData.assignments;

        renderAssignmentsTable(assignmentsData);
        renderGuardianLinksTable(assignmentGuardians, assignmentPatients);
    } catch (err) {
        showToast('Failed to load assignments data', 'error');
    }
}


function renderAssignmentsTable(assignments) {
    const loading = document.getElementById('assignmentsLoading');
    const content = document.getElementById('assignmentsContent');
    if (loading) loading.style.display = 'none';
    if (!content) return;
    content.style.display = 'block';

    if (assignments.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔗</div>
                <div class="empty-title">No Assignments Yet</div>
                <div class="empty-desc">Assign doctors to patients to get started.</div>
                <button class="btn btn-primary" onclick="openAssignModal()" style="margin-top: var(--space-4);">+ Assign Doctor</button>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Doctor</th>
                        <th>Patient</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${assignments.map(a => `
                        <tr>
                            <td>
                                <div style="font-weight: 500;">${escapeHtml(a.doctor_name)}</div>
                                <div style="font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(a.doctor_email)}</div>
                            </td>
                            <td>
                                <div style="font-weight: 500;">${escapeHtml(a.patient_name)}</div>
                                <div style="font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(a.patient_email)}</div>
                            </td>
                            <td>
                                <button class="btn btn-ghost btn-sm text-danger" onclick="removeAssignment('${escapeHtml(a.id)}')" title="Remove">
                                    Remove
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}


function renderGuardianLinksTable(guardians, patients) {
    const loading = document.getElementById('guardianLinksLoading');
    const content = document.getElementById('guardianLinksContent');
    if (loading) loading.style.display = 'none';
    if (!content) return;
    content.style.display = 'block';

    const linkedGuardians = guardians.filter(g => g.linked_patient_id);
    const patientMap = {};
    patients.forEach(p => { patientMap[p.id] = p; });

    if (linkedGuardians.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👥</div>
                <div class="empty-title">No Guardian Links Yet</div>
                <div class="empty-desc">Link guardians to patients so they can monitor recovery.</div>
                <button class="btn btn-primary" onclick="openGuardianLinkModal()" style="margin-top: var(--space-4);">+ Link Guardian</button>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Guardian</th>
                        <th>Linked Patient</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${linkedGuardians.map(g => {
                        const p = patientMap[g.linked_patient_id];
                        return `
                            <tr>
                                <td>
                                    <div style="font-weight: 500;">${escapeHtml(g.full_name)}</div>
                                    <div style="font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(g.email)}</div>
                                </td>
                                <td>
                                    <div style="font-weight: 500;">${p ? p.full_name : 'Unknown'}</div>
                                    <div style="font-size: var(--text-xs); color: var(--text-muted);">${p ? p.email : ''}</div>
                                </td>
                                <td>
                                    <button class="btn btn-ghost btn-sm text-danger" onclick="unlinkGuardian('${escapeHtml(g.id)}')" title="Unlink">
                                        Unlink
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}


/* ── Assignment Modal ───────────────────────────────────── */

function openAssignModal() {
    document.getElementById('assignModal').classList.add('active');

    const doctorSelect = document.getElementById('assignDoctor');
    doctorSelect.innerHTML = '<option value="">Select a doctor...</option>' +
        assignmentDoctors.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.full_name)} (${escapeHtml(d.email)})</option>`).join('');

    const patientSelect = document.getElementById('assignPatient');
    patientSelect.innerHTML = '<option value="">Select a patient...</option>' +
        assignmentPatients.map(p => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.full_name)} (${escapeHtml(p.email)})</option>`).join('');
}

function closeAssignModal() {
    document.getElementById('assignModal').classList.remove('active');
}


async function submitAssignment() {
    const doctor_id = document.getElementById('assignDoctor').value;
    const patient_id = document.getElementById('assignPatient').value;
    const btn = document.getElementById('assignSubmitBtn');

    if (!doctor_id || !patient_id) {
        showToast('Please select both a doctor and a patient', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Assigning...';

    try {
        await api.post('/hospital/assignments', { doctor_id, patient_id });
        showToast('Doctor assigned to patient successfully', 'success');
        closeAssignModal();
        await loadAssignmentsPage();
    } catch (err) {
        showToast(err.message || 'Failed to create assignment', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Assignment';
    }
}


async function removeAssignment(assignmentId) {
    if (!confirm('Are you sure you want to remove this assignment?')) return;

    try {
        await api.delete(`/hospital/assignments/${assignmentId}`);
        showToast('Assignment removed successfully', 'success');
        await loadAssignmentsPage();
    } catch (err) {
        showToast(err.message || 'Failed to remove assignment', 'error');
    }
}


/* ── Guardian Link Modal ────────────────────────────────── */

function openGuardianLinkModal() {
    document.getElementById('guardianLinkModal').classList.add('active');

    // Only show unlinked guardians
    const unlinked = assignmentGuardians.filter(g => !g.linked_patient_id);

    const guardianSelect = document.getElementById('linkGuardian');
    guardianSelect.innerHTML = '<option value="">Select a guardian...</option>' +
        unlinked.map(g => `<option value="${escapeHtml(g.id)}">${escapeHtml(g.full_name)} (${escapeHtml(g.email)})</option>`).join('');

    const patientSelect = document.getElementById('linkPatient');
    patientSelect.innerHTML = '<option value="">Select a patient...</option>' +
        assignmentPatients.map(p => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.full_name)} (${escapeHtml(p.email)})</option>`).join('');
}

function closeGuardianLinkModal() {
    document.getElementById('guardianLinkModal').classList.remove('active');
}


async function submitGuardianLink() {
    const guardian_id = document.getElementById('linkGuardian').value;
    const patient_id = document.getElementById('linkPatient').value;
    const btn = document.getElementById('guardianLinkSubmitBtn');

    if (!guardian_id || !patient_id) {
        showToast('Please select both a guardian and a patient', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Linking...';

    try {
        await api.post('/hospital/link-guardian', { guardian_id, patient_id });
        showToast('Guardian linked to patient successfully', 'success');
        closeGuardianLinkModal();
        await loadAssignmentsPage();
    } catch (err) {
        showToast(err.message || 'Failed to link guardian', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Link Guardian';
    }
}


async function unlinkGuardian(guardianId) {
    if (!confirm('Are you sure you want to unlink this guardian from their patient?')) return;

    try {
        await api.delete(`/hospital/unlink-guardian/${guardianId}`);
        showToast('Guardian unlinked successfully', 'success');
        await loadAssignmentsPage();
    } catch (err) {
        showToast(err.message || 'Failed to unlink guardian', 'error');
    }
}
