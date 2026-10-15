/** Hospitals: list, add, edit, activate and deactivate. */

let hospitalsData = [];

async function renderAdminHospitals() {
    renderDashboardShell('admin', 'hospitals', 'Hospitals', `
        <div class="page-header flex justify-between items-center">
            <div>
                <h1>Hospitals</h1>
                <p>Manage hospitals on the platform</p>
            </div>
            <button class="btn btn-primary" onclick="openHospitalModal()">
                + Add Hospital
            </button>
        </div>

        <div class="card glass" id="hospitalsTableCard">
            <div class="loading-overlay" id="hospitalsLoading">
                <div class="spinner"></div>
                <span>Loading hospitals...</span>
            </div>
            <div id="hospitalsContent" style="display: none;"></div>
        </div>

        <div class="modal-overlay" id="hospitalModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="hospitalModalTitle">Add Hospital</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeHospitalModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="hospitalForm" class="flex flex-col gap-4">
                        <input type="hidden" id="editHospitalId" value="" />

                        <div class="form-group">
                            <label class="form-label" for="hospName">Hospital Name</label>
                            <input type="text" id="hospName" class="form-input" placeholder="City General Hospital" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hospAddress">Address</label>
                            <input type="text" id="hospAddress" class="form-input" placeholder="123 Main Street, City" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hospPhone">Phone</label>
                            <input type="tel" id="hospPhone" class="form-input" placeholder="+1 234 567 890" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="hospEmail">Hospital Email</label>
                            <input type="email" id="hospEmail" class="form-input" placeholder="info@hospital.com" required />
                        </div>

                        <div id="adminFields">
                            <div style="border-top: 1px solid var(--glass-border); margin: var(--space-4) 0; padding-top: var(--space-4);">
                                <h4 style="margin-bottom: var(--space-3); color: var(--text-secondary);">Hospital Admin Account</h4>
                            </div>
                            <div class="flex flex-col gap-4">
                                <div class="form-group">
                                    <label class="form-label" for="adminName">Admin Name</label>
                                    <input type="text" id="adminName" class="form-input" placeholder="John Doe" required />
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="adminEmail">Admin Email (Login)</label>
                                    <input type="email" id="adminEmail" class="form-input" placeholder="admin@hospital.com" required />
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="adminPassword">Admin Password</label>
                                    <input type="password" id="adminPassword" class="form-input" placeholder="Min 6 characters" required minlength="6" />
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeHospitalModal()">Cancel</button>
                    <button class="btn btn-primary" id="hospitalSubmitBtn" onclick="submitHospitalForm()">Create Hospital</button>
                </div>
            </div>
        </div>
    `);

    await loadHospitals();
}


async function loadHospitals() {
    try {
        const data = await api.get('/admin/hospitals');
        hospitalsData = data.hospitals;
        renderHospitalsTable(hospitalsData);
    } catch (err) {
        showToast('Failed to load hospitals', 'error');
    }
}


function renderHospitalsTable(hospitals) {
    const loading = document.getElementById('hospitalsLoading');
    const content = document.getElementById('hospitalsContent');
    if (loading) loading.style.display = 'none';
    if (!content) return;
    content.style.display = 'block';

    if (hospitals.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🏥</div>
                <div class="empty-title">No Hospitals Yet</div>
                <div class="empty-desc">Add your first hospital to get started.</div>
                <button class="btn btn-primary" onclick="openHospitalModal()" style="margin-top: var(--space-4);">+ Add Hospital</button>
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
                        <th>Contact</th>
                        <th>Admin</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${hospitals.map(h => `
                        <tr>
                            <td>
                                <div style="font-weight: 500;">${escapeHtml(h.name)}</div>
                                <div style="font-size: var(--text-xs); color: var(--text-muted); margin-top: 2px;">${escapeHtml(h.address)}</div>
                            </td>
                            <td>
                                <div style="font-size: var(--text-sm);">${escapeHtml(h.email)}</div>
                                <div style="font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(h.phone)}</div>
                            </td>
                            <td>
                                <div style="font-size: var(--text-sm);">${escapeHtml(h.admin_name || '—')}</div>
                                <div style="font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(h.admin_email || '')}</div>
                            </td>
                            <td>
                                <span class="badge ${h.is_active ? 'badge-success' : 'badge-danger'}">
                                    ${h.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </td>
                            <td>
                                <div class="flex gap-2">
                                    <button class="btn btn-ghost btn-sm" onclick="openEditHospital('${escapeHtml(h.id)}')" title="Edit">
                                        Edit
                                    </button>
                                    <button class="btn btn-ghost btn-sm ${h.is_active ? 'text-danger' : 'text-success'}" 
                                            onclick="toggleHospitalStatus('${h.id}', ${!h.is_active})" 
                                            title="${h.is_active ? 'Deactivate' : 'Activate'}">
                                        ${h.is_active ? 'Deactivate' : 'Activate'}
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}


/* ── Modal Controls ─────────────────────────────────────── */

function openHospitalModal() {
    document.getElementById('hospitalModal').classList.add('active');
    document.getElementById('hospitalModalTitle').textContent = 'Add Hospital';
    document.getElementById('hospitalSubmitBtn').textContent = 'Create Hospital';
    document.getElementById('editHospitalId').value = '';
    document.getElementById('adminFields').style.display = 'block';
    document.getElementById('hospitalForm').reset();
}

function openEditHospital(id) {
    const hospital = hospitalsData.find(h => h.id === id);
    if (!hospital) return;

    document.getElementById('hospitalModal').classList.add('active');
    document.getElementById('hospitalModalTitle').textContent = 'Edit Hospital';
    document.getElementById('hospitalSubmitBtn').textContent = 'Save Changes';
    document.getElementById('editHospitalId').value = id;
    document.getElementById('adminFields').style.display = 'none';

    document.getElementById('hospName').value = hospital.name;
    document.getElementById('hospAddress').value = hospital.address;
    document.getElementById('hospPhone').value = hospital.phone;
    document.getElementById('hospEmail').value = hospital.email;
}

function closeHospitalModal() {
    document.getElementById('hospitalModal').classList.remove('active');
}


async function submitHospitalForm() {
    const editId = document.getElementById('editHospitalId').value;
    const btn = document.getElementById('hospitalSubmitBtn');

    const name = document.getElementById('hospName').value.trim();
    const address = document.getElementById('hospAddress').value.trim();
    const phone = document.getElementById('hospPhone').value.trim();
    const email = document.getElementById('hospEmail').value.trim();

    if (!name || !address || !phone || !email) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        if (editId) {
            await api.put(`/admin/hospitals/${editId}`, { name, address, phone, email });
            showToast('Hospital updated successfully', 'success');
        } else {
            const adminName = document.getElementById('adminName').value.trim();
            const adminEmail = document.getElementById('adminEmail').value.trim();
            const adminPassword = document.getElementById('adminPassword').value;

            if (!adminName || !adminEmail || !adminPassword) {
                showToast('Please fill in admin account details', 'warning');
                btn.disabled = false;
                btn.textContent = 'Create Hospital';
                return;
            }

            if (adminPassword.length < 6) {
                showToast('Admin password must be at least 6 characters', 'warning');
                btn.disabled = false;
                btn.textContent = 'Create Hospital';
                return;
            }

            await api.post('/admin/hospitals', {
                name, address, phone, email,
                admin_name: adminName,
                admin_email: adminEmail,
                admin_password: adminPassword,
            });
            showToast('Hospital created successfully', 'success');
        }

        closeHospitalModal();
        await loadHospitals();
    } catch (err) {
        showToast(err.message || 'Failed to save hospital', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = editId ? 'Save Changes' : 'Create Hospital';
    }
}


async function toggleHospitalStatus(id, newStatus) {
    const action = newStatus ? 'activate' : 'deactivate';
    if (!confirm(`Are you sure you want to ${action} this hospital? ${!newStatus ? 'All associated users will also be deactivated.' : ''}`)) {
        return;
    }

    try {
        await api.patch(`/admin/hospitals/${id}/status`, { is_active: newStatus });
        showToast(`Hospital ${action}d successfully`, 'success');
        await loadHospitals();
    } catch (err) {
        showToast(err.message || `Failed to ${action} hospital`, 'error');
    }
}
