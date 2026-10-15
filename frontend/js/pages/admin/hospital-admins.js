/** Hospital admins: list, edit, reset password and hand over. */

let hospitalAdminsData = [];
let activeAdminHospitalId = null;

async function renderHospitalAdmins() {
    renderDashboardShell('admin', 'hospital-admins', 'Hospital Admins', `
        <div class="page-header">
            <h1>Hospital Admins</h1>
            <p>Manage the admin account that runs each hospital.</p>
        </div>

        <div class="card glass" id="adminsCard">
            <div class="card-header"><h3>Admin Accounts</h3></div>
            <div id="adminsContent">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading admins...</span></div>
            </div>
        </div>

        <div class="modal-overlay" id="adminEditModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="adminEditTitle">Edit Admin</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeAdminEditModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="adminEditForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="adminName">Full Name</label>
                            <input type="text" id="adminName" class="form-input" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="adminEmail">Login Email</label>
                            <input type="email" id="adminEmail" class="form-input" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="adminPhone">Phone <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="text" id="adminPhone" class="form-input" />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeAdminEditModal()">Cancel</button>
                    <button class="btn btn-primary" id="adminEditBtn" onclick="submitAdminEdit()">Save Changes</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="adminPasswordModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="adminPasswordTitle">Reset Password</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeAdminPasswordModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="adminPasswordForm" class="flex flex-col gap-4">
                        <p style="font-size: var(--text-sm); color: var(--text-secondary);">
                            The admin will need this new password to sign in. Their current password stops working immediately.
                        </p>
                        <div class="form-group">
                            <label class="form-label" for="adminNewPassword">New Password</label>
                            <input type="text" id="adminNewPassword" class="form-input" minlength="6" placeholder="At least 6 characters" required />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeAdminPasswordModal()">Cancel</button>
                    <button class="btn btn-danger" id="adminPasswordBtn" onclick="submitAdminPassword()">Reset Password</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="adminReplaceModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="adminReplaceTitle">Hand Over Hospital</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeAdminReplaceModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="adminReplaceForm" class="flex flex-col gap-4">
                        <p style="font-size: var(--text-sm); color: var(--text-secondary);">
                            Creates a new admin account for this hospital. The outgoing admin is deactivated,
                            not deleted, so everything they created keeps a named author.
                        </p>
                        <div class="form-group">
                            <label class="form-label" for="newAdminName">New Admin Name</label>
                            <input type="text" id="newAdminName" class="form-input" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="newAdminEmail">Login Email</label>
                            <input type="email" id="newAdminEmail" class="form-input" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="newAdminPassword">Password</label>
                            <input type="text" id="newAdminPassword" class="form-input" minlength="6" placeholder="At least 6 characters" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="newAdminPhone">Phone <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="text" id="newAdminPhone" class="form-input" />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeAdminReplaceModal()">Cancel</button>
                    <button class="btn btn-primary" id="adminReplaceBtn" onclick="submitAdminReplace()">Hand Over</button>
                </div>
            </div>
        </div>
    `);

    await loadHospitalAdmins();
}


async function loadHospitalAdmins() {
    const content = document.getElementById('adminsContent');
    if (!content) return;

    try {
        const data = await api.get('/admin/hospital-admins');
        hospitalAdminsData = data.admins;

        if (!data.admins.length) {
            content.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔑</div>
                    <div class="empty-title">No Hospital Admins</div>
                    <div class="empty-desc">Admin accounts are created with their hospital.</div>
                    <a href="#/admin/hospitals" class="btn btn-primary" style="margin-top: var(--space-4);">Go to Hospitals</a>
                </div>
            `;
            return;
        }

        content.innerHTML = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Hospital</th>
                            <th>Admin</th>
                            <th>Login Email</th>
                            <th>Phone</th>
                            <th>Status</th>
                            <th style="text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.admins.map(a => `
                            <tr class="${a.is_active ? '' : 'row-inactive'}">
                                <td><strong>${escapeHtml(a.hospital_name || '—')}</strong></td>
                                <td>${escapeHtml(a.full_name)}</td>
                                <td style="font-size: var(--text-sm);">${escapeHtml(a.email)}</td>
                                <td style="font-size: var(--text-sm); color: var(--text-muted);">${escapeHtml(a.phone || '—')}</td>
                                <td>
                                    <span class="badge ${a.is_active ? 'badge-success' : 'badge-danger'}">
                                        ${a.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </td>
                                <td style="text-align: right;">
                                    ${a.hospital_id ? `
                                        <button class="btn btn-ghost btn-sm" onclick="openAdminEditModal('${escapeHtml(a.hospital_id)}')">Edit</button>
                                        <button class="btn btn-ghost btn-sm" onclick="openAdminPasswordModal('${escapeHtml(a.hospital_id)}')">Password</button>
                                        <button class="btn btn-ghost btn-sm" onclick="openAdminReplaceModal('${escapeHtml(a.hospital_id)}')">Hand over</button>
                                    ` : '<span style="color: var(--text-muted);">—</span>'}
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
                <div class="empty-title">Failed to load admins</div>
                <div class="empty-desc">${escapeHtml(err.message || 'Please try again.')}</div>
            </div>
        `;
    }
}


function _adminFor(hospitalId) {
    return hospitalAdminsData.find(a => a.hospital_id === hospitalId);
}


/* ── Edit ───────────────────────────────────────────────── */

function openAdminEditModal(hospitalId) {
    activeAdminHospitalId = hospitalId;
    const a = _adminFor(hospitalId);
    if (!a) return;

    document.getElementById('adminEditTitle').textContent = `Edit Admin — ${a.hospital_name || ''}`;
    document.getElementById('adminName').value = a.full_name || '';
    document.getElementById('adminEmail').value = a.email || '';
    document.getElementById('adminPhone').value = a.phone || '';
    document.getElementById('adminEditModal').classList.add('active');
}

function closeAdminEditModal() {
    document.getElementById('adminEditModal').classList.remove('active');
    activeAdminHospitalId = null;
}

async function submitAdminEdit() {
    const full_name = document.getElementById('adminName').value.trim();
    const email = document.getElementById('adminEmail').value.trim();
    const phone = document.getElementById('adminPhone').value.trim() || null;
    const btn = document.getElementById('adminEditBtn');

    if (!full_name || !email) {
        showToast('Name and email are required', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.put(`/admin/hospitals/${activeAdminHospitalId}/admin`, { full_name, email, phone });
        showToast('Admin updated', 'success');
        closeAdminEditModal();
        await loadHospitalAdmins();
    } catch (err) {
        showToast(err.message || 'Failed to update admin', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Changes';
    }
}


/* ── Reset Password ─────────────────────────────────────── */

function openAdminPasswordModal(hospitalId) {
    activeAdminHospitalId = hospitalId;
    const a = _adminFor(hospitalId);
    document.getElementById('adminPasswordForm').reset();
    document.getElementById('adminPasswordTitle').textContent =
        `Reset Password — ${a ? a.full_name : ''}`;
    document.getElementById('adminPasswordModal').classList.add('active');
}

function closeAdminPasswordModal() {
    document.getElementById('adminPasswordModal').classList.remove('active');
    activeAdminHospitalId = null;
}

async function submitAdminPassword() {
    const new_password = document.getElementById('adminNewPassword').value;
    const btn = document.getElementById('adminPasswordBtn');

    if (!new_password || new_password.length < 6) {
        showToast('Password must be at least 6 characters', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Resetting...';

    try {
        await api.patch(`/admin/hospitals/${activeAdminHospitalId}/admin/password`, { new_password });
        showToast('Password reset — share it with the admin', 'success');
        closeAdminPasswordModal();
    } catch (err) {
        showToast(err.message || 'Failed to reset password', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Reset Password';
    }
}


/* ── Hand Over ──────────────────────────────────────────── */

function openAdminReplaceModal(hospitalId) {
    activeAdminHospitalId = hospitalId;
    const a = _adminFor(hospitalId);
    document.getElementById('adminReplaceForm').reset();
    document.getElementById('adminReplaceTitle').textContent =
        `Hand Over — ${a ? (a.hospital_name || '') : ''}`;
    document.getElementById('adminReplaceModal').classList.add('active');
}

function closeAdminReplaceModal() {
    document.getElementById('adminReplaceModal').classList.remove('active');
    activeAdminHospitalId = null;
}

async function submitAdminReplace() {
    const admin_name = document.getElementById('newAdminName').value.trim();
    const admin_email = document.getElementById('newAdminEmail').value.trim();
    const admin_password = document.getElementById('newAdminPassword').value;
    const admin_phone = document.getElementById('newAdminPhone').value.trim() || null;
    const btn = document.getElementById('adminReplaceBtn');

    if (!admin_name || !admin_email || !admin_password) {
        showToast('Name, email, and password are required', 'warning');
        return;
    }
    if (admin_password.length < 6) {
        showToast('Password must be at least 6 characters', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Handing over...';

    try {
        await api.post(`/admin/hospitals/${activeAdminHospitalId}/admin`, {
            admin_name, admin_email, admin_password, admin_phone,
        });
        showToast('Hospital handed over — previous admin deactivated', 'success');
        closeAdminReplaceModal();
        await loadHospitalAdmins();
    } catch (err) {
        showToast(err.message || 'Failed to hand over', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Hand Over';
    }
}
