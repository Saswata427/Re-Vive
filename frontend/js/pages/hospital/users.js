/** Hospital users: doctors, patients and guardians, with add, edit and status. */

let hospitalUsersData = [];
let currentRoleFilter = null;

async function renderHospitalUsers() {
    renderDashboardShell('hospital', 'users', 'Manage Users', `
        <div class="page-header flex justify-between items-center">
            <div>
                <h1>Manage Users</h1>
                <p>Add and manage doctors, patients, and guardians</p>
            </div>
            <button class="btn btn-primary" onclick="openUserModal()">
                + Add User
            </button>
        </div>

        <div class="tabs-bar" style="margin-bottom: var(--space-5);">
            <button class="tab-btn active" data-role="" onclick="filterUsersByRole(this, '')">All Users</button>
            <button class="tab-btn" data-role="doctor" onclick="filterUsersByRole(this, 'doctor')">Doctors</button>
            <button class="tab-btn" data-role="patient" onclick="filterUsersByRole(this, 'patient')">Patients</button>
            <button class="tab-btn" data-role="guardian" onclick="filterUsersByRole(this, 'guardian')">Guardians</button>
        </div>

        <div class="card glass" id="usersTableCard">
            <div class="loading-overlay" id="usersLoading">
                <div class="spinner"></div>
                <span>Loading users...</span>
            </div>
            <div id="usersContent" style="display: none;"></div>
        </div>

        <div class="modal-overlay" id="patientProfileModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="patientProfileTitle">Clinical Profile</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closePatientProfileModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="patientProfileForm" class="flex flex-col gap-4">
                        <input type="hidden" id="profilePatientId" value="" />
                        <div class="form-group">
                            <label class="form-label" for="hProfCondition">Primary Condition</label>
                            <input type="text" id="hProfCondition" class="form-input" placeholder="e.g., Alcohol use disorder" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hProfTherapy">Therapy Program</label>
                            <input type="text" id="hProfTherapy" class="form-input" placeholder="e.g., Outpatient CBT, 12-step" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hProfStart">Program Start Date</label>
                            <input type="date" id="hProfStart" class="form-input" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hProfSobriety">Sobriety Date <span style="color: var(--text-muted);">(drives the abstinence counter)</span></label>
                            <input type="date" id="hProfSobriety" class="form-input" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hProfEmergency">Emergency Contact</label>
                            <input type="text" id="hProfEmergency" class="form-input" placeholder="Name and phone number" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hProfNotes">Medical Notes</label>
                            <textarea id="hProfNotes" class="form-input" rows="4" placeholder="Background, history, considerations..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closePatientProfileModal()">Cancel</button>
                    <button class="btn btn-primary" id="patientProfileSubmitBtn" onclick="submitPatientProfile()">Save Profile</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="userModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="userModalTitle">Add User</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeUserModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="userForm" class="flex flex-col gap-4">
                        <input type="hidden" id="editUserId" value="" />

                        <div class="form-group" id="roleSelectGroup">
                            <label class="form-label" for="userRole">Role</label>
                            <select id="userRole" class="form-input" required>
                                <option value="">Select role...</option>
                                <option value="doctor">Doctor</option>
                                <option value="patient">Patient</option>
                                <option value="guardian">Guardian</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="userName">Full Name</label>
                            <input type="text" id="userName" class="form-input" placeholder="John Doe" required />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="userEmail">Email</label>
                            <input type="email" id="userEmail" class="form-input" placeholder="user@hospital.com" required />
                        </div>

                        <div class="form-group" id="passwordGroup">
                            <label class="form-label" for="userPassword">Password</label>
                            <input type="password" id="userPassword" class="form-input" placeholder="Min 6 characters" required minlength="6" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="userPhone">Phone <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="tel" id="userPhone" class="form-input" placeholder="+1 234 567 890" />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeUserModal()">Cancel</button>
                    <button class="btn btn-primary" id="userSubmitBtn" onclick="submitUserForm()">Create User</button>
                </div>
            </div>
        </div>
    `);

    currentRoleFilter = null;
    await loadHospitalUsers();
}


async function loadHospitalUsers(roleFilter) {
    try {
        const endpoint = roleFilter ? `/hospital/users?role=${roleFilter}` : '/hospital/users';
        const data = await api.get(endpoint);
        hospitalUsersData = data.users;
        renderUsersTable(hospitalUsersData);
    } catch (err) {
        showToast('Failed to load users', 'error');
    }
}


function filterUsersByRole(btn, role) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    currentRoleFilter = role || null;

    const loading = document.getElementById('usersLoading');
    const content = document.getElementById('usersContent');
    if (loading) loading.style.display = 'flex';
    if (content) content.style.display = 'none';

    loadHospitalUsers(currentRoleFilter);
}


const ROLE_BADGES = {
    doctor: { label: 'Doctor', class: 'badge-primary', icon: '🩺' },
    patient: { label: 'Patient', class: 'badge-info', icon: '🧑' },
    guardian: { label: 'Guardian', class: 'badge-warning', icon: '👥' },
};


function renderUsersTable(users) {
    const loading = document.getElementById('usersLoading');
    const content = document.getElementById('usersContent');
    if (loading) loading.style.display = 'none';
    if (!content) return;
    content.style.display = 'block';

    if (users.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👤</div>
                <div class="empty-title">No Users Found</div>
                <div class="empty-desc">Add your first user to get started.</div>
                <button class="btn btn-primary" onclick="openUserModal()" style="margin-top: var(--space-4);">+ Add User</button>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Phone</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${users.map(u => {
                        const rb = ROLE_BADGES[u.role] || { label: u.role, class: '', icon: '' };
                        return `
                            <tr>
                                <td>
                                    <div style="font-weight: 500;">${escapeHtml(u.full_name)}</div>
                                </td>
                                <td style="font-size: var(--text-sm);">${escapeHtml(u.email)}</td>
                                <td>
                                    <span class="badge ${escapeHtml(rb.class)}">
                                        ${rb.icon} ${rb.label}
                                    </span>
                                </td>
                                <td style="font-size: var(--text-sm); color: var(--text-muted);">${escapeHtml(u.phone || '—')}</td>
                                <td>
                                    <span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">
                                        ${u.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </td>
                                <td>
                                    <div class="flex gap-2">
                                        <button class="btn btn-ghost btn-sm" onclick="openEditUser('${escapeHtml(u.id)}')" title="Edit">
                                            Edit
                                        </button>
                                        ${u.role === 'patient' ? `
                                            <button class="btn btn-ghost btn-sm" onclick="openPatientProfileModal('${escapeHtml(u.id)}')" title="Clinical profile">
                                                Profile
                                            </button>
                                        ` : ''}
                                        <button class="btn btn-ghost btn-sm ${u.is_active ? 'text-danger' : 'text-success'}"
                                                onclick="toggleUserStatus('${u.id}', ${!u.is_active})"
                                                title="${u.is_active ? 'Deactivate' : 'Activate'}">
                                            ${u.is_active ? 'Deactivate' : 'Activate'}
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}


/* ── Modal Controls ─────────────────────────────────────── */

function openUserModal() {
    document.getElementById('userModal').classList.add('active');
    document.getElementById('userModalTitle').textContent = 'Add User';
    document.getElementById('userSubmitBtn').textContent = 'Create User';
    document.getElementById('editUserId').value = '';
    document.getElementById('roleSelectGroup').style.display = 'block';
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('userForm').reset();
}

function openEditUser(id) {
    const user = hospitalUsersData.find(u => u.id === id);
    if (!user) return;

    document.getElementById('userModal').classList.add('active');
    document.getElementById('userModalTitle').textContent = 'Edit User';
    document.getElementById('userSubmitBtn').textContent = 'Save Changes';
    document.getElementById('editUserId').value = id;
    document.getElementById('roleSelectGroup').style.display = 'none';
    document.getElementById('passwordGroup').style.display = 'none';

    document.getElementById('userName').value = user.full_name;
    document.getElementById('userEmail').value = user.email;
    document.getElementById('userPhone').value = user.phone || '';
}

function closeUserModal() {
    document.getElementById('userModal').classList.remove('active');
}


async function submitUserForm() {
    const editId = document.getElementById('editUserId').value;
    const btn = document.getElementById('userSubmitBtn');

    const full_name = document.getElementById('userName').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    const phone = document.getElementById('userPhone').value.trim() || null;

    if (!full_name || !email) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        if (editId) {
            await api.put(`/hospital/users/${editId}`, { full_name, email, phone });
            showToast('User updated successfully', 'success');
        } else {
            const role = document.getElementById('userRole').value;
            const password = document.getElementById('userPassword').value;

            if (!role) {
                showToast('Please select a role', 'warning');
                btn.disabled = false;
                btn.textContent = 'Create User';
                return;
            }

            if (!password || password.length < 6) {
                showToast('Password must be at least 6 characters', 'warning');
                btn.disabled = false;
                btn.textContent = 'Create User';
                return;
            }

            await api.post('/hospital/users', { role, full_name, email, password, phone });
            showToast('User created successfully', 'success');
        }

        closeUserModal();
        await loadHospitalUsers(currentRoleFilter);
    } catch (err) {
        showToast(err.message || 'Failed to save user', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = editId ? 'Save Changes' : 'Create User';
    }
}


async function toggleUserStatus(id, newStatus) {
    const action = newStatus ? 'activate' : 'deactivate';
    if (!confirm(`Are you sure you want to ${action} this user?`)) return;

    try {
        await api.patch(`/hospital/users/${id}/status`, { is_active: newStatus });
        showToast(`User ${action}d successfully`, 'success');
        await loadHospitalUsers(currentRoleFilter);
    } catch (err) {
        showToast(err.message || `Failed to ${action} user`, 'error');
    }
}


/* ── Patient Clinical Profile Modal ──────────── */

async function openPatientProfileModal(patientId) {
    const modal = document.getElementById('patientProfileModal');
    if (!modal) return;

    // Looked up by ID, not passed in the onclick, so a quote in a name can't break out.
    const patient = hospitalUsersData.find(u => u.id === patientId);
    const patientName = patient ? patient.full_name : 'Patient';

    document.getElementById('patientProfileForm').reset();
    document.getElementById('profilePatientId').value = patientId;
    document.getElementById('patientProfileTitle').textContent = `Clinical Profile \u2014 ${patientName}`;
    modal.classList.add('active');

    // Load whatever is already on file
    try {
        const p = await api.get(`/hospital/patients/${patientId}/profile`);
        document.getElementById('hProfCondition').value = p.primary_condition || '';
        document.getElementById('hProfTherapy').value = p.therapy_program || '';
        document.getElementById('hProfStart').value = (p.program_start_date || '').slice(0, 10);
        document.getElementById('hProfSobriety').value = (p.sobriety_date || '').slice(0, 10);
        document.getElementById('hProfEmergency').value = p.emergency_contact || '';
        document.getElementById('hProfNotes').value = p.medical_notes || '';
    } catch (err) {
        showToast(err.message || 'Failed to load profile', 'error');
    }
}

function closePatientProfileModal() {
    document.getElementById('patientProfileModal').classList.remove('active');
}

async function submitPatientProfile() {
    const patientId = document.getElementById('profilePatientId').value;
    const btn = document.getElementById('patientProfileSubmitBtn');

    const payload = {
        primary_condition: document.getElementById('hProfCondition').value.trim() || null,
        therapy_program: document.getElementById('hProfTherapy').value.trim() || null,
        program_start_date: document.getElementById('hProfStart').value || null,
        sobriety_date: document.getElementById('hProfSobriety').value || null,
        emergency_contact: document.getElementById('hProfEmergency').value.trim() || null,
        medical_notes: document.getElementById('hProfNotes').value.trim() || null,
    };

    if (Object.values(payload).every(v => v === null)) {
        showToast('Fill in at least one field', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.put(`/hospital/patients/${patientId}/profile`, payload);
        showToast('Clinical profile saved', 'success');
        closePatientProfileModal();
    } catch (err) {
        showToast(err.message || 'Failed to save profile', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Profile';
    }
}
