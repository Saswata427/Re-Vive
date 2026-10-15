/** Doctor patients: the list, and each patient's detail with its tabs. */

let doctorPatientsData = [];
let currentPatientId = null;
let currentPatientDetail = null;
let activeDetailTab = 'checkins';


/* ═══ Patient list ═══ */

async function renderDoctorPatients() {
    currentPatientId = null;
    currentPatientDetail = null;

    renderDashboardShell('doctor', 'patients', 'My Patients', `
        <div class="page-header">
            <h1>My Patients</h1>
            <p>View and manage your assigned patients</p>
        </div>

        <div class="card glass" id="patientsCard">
            <div class="loading-overlay" id="patientsLoading">
                <div class="spinner"></div>
                <span>Loading patients...</span>
            </div>
            <div id="patientsContent" style="display: none;"></div>
        </div>
    `);

    await loadDoctorPatients();
}


async function loadDoctorPatients() {
    try {
        const data = await api.get('/doctor/patients');
        doctorPatientsData = data.patients;
        renderPatientsTable(doctorPatientsData);
    } catch (err) {
        showToast('Failed to load patients', 'error');
    }
}


function renderPatientsTable(patients) {
    const loading = document.getElementById('patientsLoading');
    const content = document.getElementById('patientsContent');
    if (loading) loading.style.display = 'none';
    if (!content) return;
    content.style.display = 'block';

    if (patients.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🩺</div>
                <div class="empty-title">No Patients Assigned</div>
                <div class="empty-desc">Ask your hospital admin to assign patients to you through the Assignments page.</div>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Patient</th>
                        <th>Contact</th>
                        <th>Status</th>
                        <th>Last Check-in</th>
                        <th>Active Goals</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${patients.map(p => `
                        <tr>
                            <td>
                                <div style="font-weight: 500;">${escapeHtml(p.full_name)}</div>
                            </td>
                            <td>
                                <div style="font-size: var(--text-sm);">${escapeHtml(p.email)}</div>
                                <div style="font-size: var(--text-xs); color: var(--text-muted);">${escapeHtml(p.phone || '—')}</div>
                            </td>
                            <td>
                                <span class="badge ${p.is_active ? 'badge-success' : 'badge-danger'}">
                                    ${p.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </td>
                            <td style="font-size: var(--text-sm); color: var(--text-secondary);">
                                ${p.last_checkin_date ? formatDate(p.last_checkin_date) : '—'}
                            </td>
                            <td>
                                <span class="badge badge-warning">${escapeHtml(p.active_goals)}</span>
                            </td>
                            <td>
                                <a href="#/doctor/patients/${escapeHtml(p.id)}" class="btn btn-primary btn-sm">View Details →</a>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}


/* ═══ Patient detail ═══ */

async function renderDoctorPatientDetail(patientId) {
    currentPatientId = patientId;
    activeDetailTab = 'checkins';

    renderDashboardShell('doctor', 'patients', 'Patient Detail', `
        <div class="page-header flex justify-between items-center">
            <div class="flex items-center gap-4">
                <a href="#/doctor/patients" class="btn btn-ghost btn-icon" title="Back to list">←</a>
                <div>
                    <h1 id="patientName">Loading...</h1>
                    <p id="patientSubtitle">Patient details</p>
                </div>
            </div>
        </div>

        <div class="card glass" id="scoreCard" style="margin-bottom: var(--space-5);">
            <div class="card-header"><h3>Recovery Score</h3></div>
            <div id="scoreGauge">
                <div class="loading-overlay"><div class="spinner"></div></div>
            </div>
        </div>

        <div class="card glass" id="doctorPatientAIRisk" style="margin-bottom: var(--space-5);">
            <div class="ai-risk-loading"><div class="spinner"></div><span>Analyzing recovery risk...</span></div>
        </div>

        <div class="card glass patient-info-card" id="patientInfoCard">
            <div class="loading-overlay" id="patientInfoLoading">
                <div class="spinner"></div>
                <span>Loading patient info...</span>
            </div>
            <div id="patientInfoContent" style="display: none;"></div>
        </div>

        <div style="margin-top: var(--space-6);">
            <div class="tabs-bar" style="margin-bottom: var(--space-5);">
                <button class="tab-btn active" id="tabCheckins" onclick="switchDetailTab('checkins', this)">Check-ins</button>
                <button class="tab-btn" id="tabNotes" onclick="switchDetailTab('notes', this)">Clinical Notes</button>
                <button class="tab-btn" id="tabGoals" onclick="switchDetailTab('goals', this)">Recovery Goals</button>
                <button class="tab-btn" id="tabMeds" onclick="switchDetailTab('medications', this)">Medications</button>
                <button class="tab-btn" id="tabVitals" onclick="switchDetailTab('vitals', this)">Vitals</button>
                <button class="tab-btn" id="tabHistory" onclick="switchDetailTab('history', this)">History</button>
                <button class="tab-btn" id="tabTimeline" onclick="switchDetailTab('timeline', this)">Timeline</button>
                <button class="tab-btn" id="tabTwin" onclick="switchDetailTab('twin', this)">Digital Twin</button>
                <button class="tab-btn" id="tabInterventions" onclick="switchDetailTab('interventions', this)">Interventions</button>
                <button class="tab-btn" id="tabPlan" onclick="switchDetailTab('plan', this)">Care Plan</button>
            </div>

            <div class="card glass" id="tabContent">
                <div class="loading-overlay">
                    <div class="spinner"></div>
                    <span>Loading...</span>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="noteModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Add Clinical Note</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeNoteModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="noteForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="noteType">Note Type</label>
                            <select id="noteType" class="form-input" required>
                                <option value="progress">Progress</option>
                                <option value="observation">Observation</option>
                                <option value="concern">Concern</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="noteContent">Content</label>
                            <textarea id="noteContent" class="form-input" placeholder="Write your clinical note..." rows="5" required></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeNoteModal()">Cancel</button>
                    <button class="btn btn-primary" id="noteSubmitBtn" onclick="submitNote()">Add Note</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="interventionModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Record Intervention</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeInterventionModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="interventionForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="ivType">What did you do?</label>
                            <select id="ivType" class="form-input" required>
                                <option value="check_in_call">Check-in call</option>
                                <option value="counselling_session">Counselling session</option>
                                <option value="therapy_referral">Therapy referral</option>
                                <option value="medication_change">Medication change</option>
                                <option value="care_plan_update">Care plan update</option>
                                <option value="escalation">Escalation</option>
                                <option value="other">• Other</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="ivAlert">Prompted by an alert? <span style="color: var(--text-muted);">(optional — links and clears it)</span></label>
                            <select id="ivAlert" class="form-input">
                                <option value="">Not prompted by an alert</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="ivDescription">Description</label>
                            <textarea id="ivDescription" class="form-input" rows="4" placeholder="What action was taken and why..." required></textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="ivFollowUp">Follow-up date <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="date" id="ivFollowUp" class="form-input" />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeInterventionModal()">Cancel</button>
                    <button class="btn btn-primary" id="ivSubmitBtn" onclick="submitIntervention()">Record</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="outcomeModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Record Outcome</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeOutcomeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="outcomeForm" class="flex flex-col gap-4">
                        <input type="hidden" id="outcomeInterventionId" value="" />
                        <div class="form-group">
                            <label class="form-label" for="outcomeStatus">Result</label>
                            <select id="outcomeStatus" class="form-input" required>
                                <option value="improved">Improved</option>
                                <option value="no_change">— No change</option>
                                <option value="worsened">Worsened</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="outcomeNotes">What happened?</label>
                            <textarea id="outcomeNotes" class="form-input" rows="4" placeholder="Observed result of the intervention..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeOutcomeModal()">Cancel</button>
                    <button class="btn btn-primary" id="outcomeSubmitBtn" onclick="submitOutcome()">Save Outcome</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="planModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 id="planModalTitle">Publish Care Plan</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closePlanModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="planForm" class="flex flex-col gap-4">
                        <p style="font-size: var(--text-sm); color: var(--text-secondary);">
                            Publishing creates a new version. The previous plan is kept in the record rather than overwritten.
                        </p>
                        <div class="form-group">
                            <label class="form-label" for="planSummary">Plan</label>
                            <textarea id="planSummary" class="form-input" rows="6" placeholder="The approach for this patient over the coming period..." required></textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Focus areas</label>
                            <div class="focus-tags" id="planFocusTags">
                                <button type="button" class="focus-tag" data-focus="craving management">Craving management</button>
                                <button type="button" class="focus-tag" data-focus="stress reduction">Stress reduction</button>
                                <button type="button" class="focus-tag" data-focus="sleep hygiene">Sleep hygiene</button>
                                <button type="button" class="focus-tag" data-focus="medication adherence">Medication adherence</button>
                                <button type="button" class="focus-tag" data-focus="therapy attendance">Therapy attendance</button>
                                <button type="button" class="focus-tag" data-focus="physical activity">Physical activity</button>
                                <button type="button" class="focus-tag" data-focus="relapse prevention">Relapse prevention</button>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="planReview">Review date <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="date" id="planReview" class="form-input" />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closePlanModal()">Cancel</button>
                    <button class="btn btn-primary" id="planSubmitBtn" onclick="submitPlan()">Publish Plan</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="profileModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Edit Clinical Profile</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeProfileModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="profileForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="profCondition">Primary Condition</label>
                            <input type="text" id="profCondition" class="form-input" placeholder="e.g., Alcohol use disorder" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="profTherapy">Therapy Program</label>
                            <input type="text" id="profTherapy" class="form-input" placeholder="e.g., Outpatient CBT, 12-step" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="profStart">Program Start Date</label>
                            <input type="date" id="profStart" class="form-input" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="profSobriety">Sobriety Date <span style="color: var(--text-muted);">(drives the abstinence counter)</span></label>
                            <input type="date" id="profSobriety" class="form-input" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="profEmergency">Emergency Contact</label>
                            <input type="text" id="profEmergency" class="form-input" placeholder="Name and phone number" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="profNotes">Medical Notes</label>
                            <textarea id="profNotes" class="form-input" rows="4" placeholder="Background, history, considerations..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeProfileModal()">Cancel</button>
                    <button class="btn btn-primary" id="profileSubmitBtn" onclick="submitProfile()">Save Profile</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="medModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Prescribe Medication</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeMedModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="medForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="medName">Medication Name</label>
                            <input type="text" id="medName" class="form-input" placeholder="e.g., Naltrexone" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="medDosage">Dosage</label>
                            <input type="text" id="medDosage" class="form-input" placeholder="e.g., 50mg" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="medFrequency">Frequency</label>
                            <input type="text" id="medFrequency" class="form-input" placeholder="e.g., Once daily" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="medStart">Start Date <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="date" id="medStart" class="form-input" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="medNotes">Notes <span style="color: var(--text-muted);">(optional)</span></label>
                            <textarea id="medNotes" class="form-input" rows="3" placeholder="Instructions, cautions..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeMedModal()">Cancel</button>
                    <button class="btn btn-primary" id="medSubmitBtn" onclick="submitMedication()">Prescribe</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="vitalsModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Record Vitals</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeVitalsModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="vitalsForm" class="flex flex-col gap-4">
                        <p style="font-size: var(--text-sm); color: var(--text-secondary);">Record at least one measurement.</p>
                        <div class="form-group">
                            <label class="form-label" for="vitBP">Blood Pressure</label>
                            <input type="text" id="vitBP" class="form-input" placeholder="e.g., 120/80" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="vitHR">Heart Rate (bpm)</label>
                            <input type="number" id="vitHR" class="form-input" min="20" max="250" placeholder="e.g., 72" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="vitTemp">Temperature (°C)</label>
                            <input type="number" id="vitTemp" class="form-input" step="0.1" min="25" max="45" placeholder="e.g., 36.8" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="vitWeight">Weight (kg)</label>
                            <input type="number" id="vitWeight" class="form-input" step="0.1" min="1" max="500" placeholder="e.g., 74.5" />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="vitNotes">Notes <span style="color: var(--text-muted);">(optional)</span></label>
                            <textarea id="vitNotes" class="form-input" rows="2"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeVitalsModal()">Cancel</button>
                    <button class="btn btn-primary" id="vitalsSubmitBtn" onclick="submitVitals()">Record</button>
                </div>
            </div>
        </div>

        <div class="modal-overlay" id="goalModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>Add Recovery Goal</h3>
                    <button class="btn btn-ghost btn-icon" onclick="closeGoalModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="goalForm" class="flex flex-col gap-4">
                        <div class="form-group">
                            <label class="form-label" for="goalTitle">Title</label>
                            <input type="text" id="goalTitle" class="form-input" placeholder="e.g., Walk 500 meters daily" required />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="goalDesc">Description <span style="color: var(--text-muted);">(optional)</span></label>
                            <textarea id="goalDesc" class="form-input" placeholder="Additional details..." rows="3"></textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="goalDate">Target Date <span style="color: var(--text-muted);">(optional)</span></label>
                            <input type="date" id="goalDate" class="form-input" />
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeGoalModal()">Cancel</button>
                    <button class="btn btn-primary" id="goalSubmitBtn" onclick="submitGoal()">Create Goal</button>
                </div>
            </div>
        </div>
    `);

    await loadPatientDetail(patientId);
}


async function loadPatientDetail(patientId) {
    try {
        currentPatientDetail = await api.get(`/doctor/patients/${patientId}`);
        renderPatientInfo(currentPatientDetail);
        document.getElementById('patientName').textContent = currentPatientDetail.full_name;
        document.getElementById('patientSubtitle').textContent = currentPatientDetail.email;
        await loadTabContent(activeDetailTab);
        loadScoreInto('scoreGauge', `/doctor/patients/${patientId}/recovery-score`);
        loadRecoveryRiskCard('doctorPatientAIRisk', 'doctor', patientId, null, { title: `${currentPatientDetail.full_name}'s Recovery Risk`, subtitle: 'AI-assisted view of recent recovery signals' });
    } catch (err) {
        showToast('Failed to load patient details', 'error');
    }
}


function renderPatientInfo(patient) {
    const loading = document.getElementById('patientInfoLoading');
    const content = document.getElementById('patientInfoContent');
    if (loading) loading.style.display = 'none';
    if (!content) return;
    content.style.display = 'block';

    content.innerHTML = `
        <div class="patient-detail-grid">
            <div class="patient-detail-item">
                <div class="detail-label">Full Name</div>
                <div class="detail-value">${escapeHtml(patient.full_name)}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Email</div>
                <div class="detail-value">${escapeHtml(patient.email)}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Phone</div>
                <div class="detail-value">${escapeHtml(patient.phone || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Status</div>
                <div class="detail-value">
                    <span class="badge ${patient.is_active ? 'badge-success' : 'badge-danger'}">
                        ${patient.is_active ? 'Active' : 'Inactive'}
                    </span>
                </div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Primary Condition</div>
                <div class="detail-value">${escapeHtml(patient.primary_condition || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Therapy Program</div>
                <div class="detail-value">${escapeHtml(patient.therapy_program || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Program Start</div>
                <div class="detail-value">${patient.program_start_date ? formatDate(patient.program_start_date) : '—'}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Days Abstinent</div>
                <div class="detail-value" style="color: var(--accent-success); font-weight: 600;">
                    ${patient.abstinence_days != null ? patient.abstinence_days : '—'}
                </div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Emergency Contact</div>
                <div class="detail-value">${escapeHtml(patient.emergency_contact || '—')}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Total Check-ins</div>
                <div class="detail-value">${escapeHtml(patient.total_checkins)}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Clinical Notes</div>
                <div class="detail-value">${escapeHtml(patient.total_notes)}</div>
            </div>
            <div class="patient-detail-item">
                <div class="detail-label">Recovery Goals</div>
                <div class="detail-value">${escapeHtml(patient.total_goals)}</div>
            </div>
        </div>
        ${patient.medical_notes ? `
            <div style="margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--glass-border);">
                <div class="detail-label" style="margin-bottom: var(--space-2);">Medical Notes</div>
                <div style="font-size: var(--text-sm); color: var(--text-secondary); line-height: 1.6; white-space: pre-wrap;">${escapeHtml(patient.medical_notes)}</div>
            </div>
        ` : ''}
        <div style="margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--glass-border); text-align: right;">
            <button class="btn btn-secondary btn-sm" onclick="openProfileModal()">Edit Clinical Profile</button>
        </div>
    `;
}


/* ── Tab Switching ──────────────────────────────────────── */

function switchDetailTab(tab, btn) {
    activeDetailTab = tab;
    document.querySelectorAll('.tabs-bar .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = `
        <div class="loading-overlay">
            <div class="spinner"></div>
            <span>Loading...</span>
        </div>
    `;

    loadTabContent(tab);
}


async function loadTabContent(tab) {
    if (!currentPatientId) return;

    switch (tab) {
        case 'checkins': await loadCheckins(); break;
        case 'notes': await loadNotes(); break;
        case 'goals': await loadGoals(); break;
        case 'medications': await loadMedications(); break;
        case 'vitals': await loadVitals(); break;
        case 'history': await loadMedicalHistory(); break;
        case 'timeline': await loadRecoveryTimelineTab(); break;
        case 'twin': await loadDigitalTwinTab(); break;
        case 'interventions': await loadInterventions(); break;
        case 'plan': await loadTreatmentPlan(); break;
    }
}


/* ── Check-ins Tab ─────────────────────────────────────── */

const MOOD_EMOJIS = {
    great: '😊', good: '🙂', okay: '😐', bad: '😟', terrible: '😩'
};

async function loadCheckins() {
    const tabContent = document.getElementById('tabContent');
    try {
        const data = await api.get(`/doctor/patients/${currentPatientId}/checkins`);

        if (data.checkins.length === 0) {
            tabContent.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📝</div>
                    <div class="empty-title">No Check-ins Yet</div>
                    <div class="empty-desc">This patient hasn't submitted any daily check-ins.</div>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Cravings</th>
                            <th>Stress</th>
                            <th>Mood</th>
                            <th>Sleep</th>
                            <th>Medication</th>
                            <th>Activity</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.checkins.map(c => `
                            <tr>
                                <td style="font-weight: 500; white-space: nowrap;">${formatDate(c.date)}</td>
                                <td>${_levelIndicator(c.craving_level)}</td>
                                <td>${_levelIndicator(c.stress_level)}</td>
                                <td>
                                    ${c.mood ? `<span class="mood-badge">${escapeHtml(MOOD_EMOJIS[c.mood] || '😐')} ${escapeHtml(c.mood)}</span>` : '—'}
                                </td>
                                <td style="font-size: var(--text-sm);">
                                    ${c.sleep_hours !== null && c.sleep_hours !== undefined ? `${c.sleep_hours}h` : '—'}
                                </td>
                                <td>
                                    ${c.medication_taken !== null && c.medication_taken !== undefined
                                        ? `<span class="badge ${c.medication_taken ? 'badge-success' : 'badge-danger'}">${c.medication_taken ? 'Taken' : 'Missed'}</span>`
                                        : '—'
                                    }
                                </td>
                                <td style="font-size: var(--text-sm);">
                                    ${c.physical_activity_minutes ? c.physical_activity_minutes + ' min' : '—'}
                                </td>
                                <td style="font-size: var(--text-sm); color: var(--text-secondary); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    ${escapeHtml(c.notes || '—')}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">Failed to load check-ins</div></div>`;
    }
}

/* ── Clinical Notes Tab ────────────────────────────────── */

const NOTE_TYPE_CONFIG = {
    progress: { label: 'Progress', class: 'badge-success', icon: '📈' },
    observation: { label: 'Observation', class: 'badge-info', icon: '🔍' },
    concern: { label: 'Concern', class: 'badge-danger', icon: '⚠️' },
};

async function loadNotes() {
    const tabContent = document.getElementById('tabContent');
    try {
        const data = await api.get(`/doctor/patients/${currentPatientId}/notes`);

        let headerHTML = `
            <div class="card-header flex justify-between items-center" style="margin-bottom: var(--space-4);">
                <h4>Clinical Notes (${escapeHtml(data.total)})</h4>
                <button class="btn btn-primary btn-sm" onclick="openNoteModal()">+ Add Note</button>
            </div>
        `;

        if (data.notes.length === 0) {
            tabContent.innerHTML = headerHTML + `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div class="empty-title">No Clinical Notes</div>
                    <div class="empty-desc">Add your first clinical note for this patient.</div>
                    <button class="btn btn-primary" onclick="openNoteModal()" style="margin-top: var(--space-4);">+ Add Note</button>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = headerHTML + `
            <div class="notes-list">
                ${data.notes.map(n => {
                    const cfg = NOTE_TYPE_CONFIG[n.note_type] || NOTE_TYPE_CONFIG.progress;
                    return `
                        <div class="note-card">
                            <div class="note-header">
                                <div class="flex items-center gap-3">
                                    <span class="badge ${escapeHtml(cfg.class)}">${escapeHtml(cfg.icon)} ${escapeHtml(cfg.label)}</span>
                                    <span class="note-author">${escapeHtml(n.doctor_name)}</span>
                                </div>
                                <span class="note-date">${formatDate(n.created_at)}</span>
                            </div>
                            <div class="note-body">${escapeHtml(n.content)}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">Failed to load notes</div></div>`;
    }
}


/* ── Recovery Goals Tab ────────────────────────────────── */

const GOAL_STATUS_CONFIG = {
    not_started: { label: 'Not Started', class: 'badge-warning', icon: '○' },
    in_progress: { label: 'In Progress', class: 'badge-info', icon: '◐' },
    completed: { label: 'Completed', class: 'badge-success', icon: '●' },
};

async function loadGoals() {
    const tabContent = document.getElementById('tabContent');
    try {
        const data = await api.get(`/doctor/patients/${currentPatientId}/goals`);

        let headerHTML = `
            <div class="card-header flex justify-between items-center" style="margin-bottom: var(--space-4);">
                <h4>Recovery Goals (${escapeHtml(data.total)})</h4>
                <button class="btn btn-primary btn-sm" onclick="openGoalModal()">+ Add Goal</button>
            </div>
        `;

        if (data.goals.length === 0) {
            tabContent.innerHTML = headerHTML + `
                <div class="empty-state">
                    <div class="empty-icon">🎯</div>
                    <div class="empty-title">No Recovery Goals</div>
                    <div class="empty-desc">Set recovery goals to track this patient's progress.</div>
                    <button class="btn btn-primary" onclick="openGoalModal()" style="margin-top: var(--space-4);">+ Add Goal</button>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = headerHTML + `
            <div class="goals-list">
                ${data.goals.map(g => {
                    const cfg = GOAL_STATUS_CONFIG[g.status] || GOAL_STATUS_CONFIG.not_started;
                    return `
                        <div class="goal-card">
                            <div class="goal-header">
                                <div class="flex items-center gap-3">
                                    <span class="goal-status-icon">${escapeHtml(cfg.icon)}</span>
                                    <div>
                                        <div class="goal-title">${escapeHtml(g.title)}</div>
                                        ${g.description ? `<div class="goal-desc">${escapeHtml(g.description)}</div>` : ''}
                                    </div>
                                </div>
                                <div class="flex items-center gap-3">
                                    ${g.target_date ? `<span class="goal-date">Target: ${formatDate(g.target_date)}</span>` : ''}
                                    <select class="form-input goal-status-select" onchange="updateGoalStatus('${escapeHtml(g.id)}', this.value)" title="Update status">
                                        <option value="not_started" ${g.status === 'not_started' ? 'selected' : ''}>○ Not Started</option>
                                        <option value="in_progress" ${g.status === 'in_progress' ? 'selected' : ''}>◐ In Progress</option>
                                        <option value="completed" ${g.status === 'completed' ? 'selected' : ''}>● Completed</option>
                                    </select>
                                </div>
                            </div>
                            ${g.notes ? `<div class="goal-notes">${escapeHtml(g.notes)}</div>` : ''}
                            <div class="goal-footer">
                                <span class="badge ${escapeHtml(cfg.class)}">${escapeHtml(cfg.label)}</span>
                                <span class="goal-meta">Created ${formatDate(g.created_at)}</span>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">Failed to load goals</div></div>`;
    }
}


/* ── Note Modal ────────────────────────────────────────── */

function openNoteModal() {
    document.getElementById('noteModal').classList.add('active');
    document.getElementById('noteForm').reset();
}

function closeNoteModal() {
    document.getElementById('noteModal').classList.remove('active');
}

async function submitNote() {
    const content = document.getElementById('noteContent').value.trim();
    const note_type = document.getElementById('noteType').value;
    const btn = document.getElementById('noteSubmitBtn');

    if (!content) {
        showToast('Please write a note', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.post(`/doctor/patients/${currentPatientId}/notes`, { content, note_type });
        showToast('Clinical note added successfully', 'success');
        closeNoteModal();
        await loadNotes();
    } catch (err) {
        showToast(err.message || 'Failed to add note', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Add Note';
    }
}


/* ── Goal Modal ────────────────────────────────────────── */

function openGoalModal() {
    document.getElementById('goalModal').classList.add('active');
    document.getElementById('goalForm').reset();
}

function closeGoalModal() {
    document.getElementById('goalModal').classList.remove('active');
}

async function submitGoal() {
    const title = document.getElementById('goalTitle').value.trim();
    const description = document.getElementById('goalDesc').value.trim() || null;
    const target_date = document.getElementById('goalDate').value || null;
    const btn = document.getElementById('goalSubmitBtn');

    if (!title) {
        showToast('Please enter a goal title', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating...';

    try {
        await api.post(`/doctor/patients/${currentPatientId}/goals`, { title, description, target_date });
        showToast('Recovery goal created successfully', 'success');
        closeGoalModal();
        await loadGoals();
    } catch (err) {
        showToast(err.message || 'Failed to create goal', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Goal';
    }
}


async function updateGoalStatus(goalId, newStatus) {
    try {
        await api.patch(`/doctor/patients/${currentPatientId}/goals/${goalId}`, { status: newStatus });
        const label = GOAL_STATUS_CONFIG[newStatus]?.label || newStatus;
        showToast(`Goal status updated to "${label}"`, 'success');
        await loadGoals();
    } catch (err) {
        showToast(err.message || 'Failed to update goal', 'error');
        await loadGoals(); // Revert select on failure
    }
}


/* ── Shared Level Indicator ─────────────────────────────── */

/** A 1–10 value as a coloured bar with its number. */
function _levelIndicator(value) {
    if (value === null || value === undefined) return '\u2014';
    return `
        <div class="level-indicator">
            <div class="level-bar">
                <div class="level-fill level-${getLevelClass(value)}" style="width: ${value * 10}%"></div>
            </div>
            <span class="level-value">${value}/10</span>
        </div>
    `;
}

function getLevelClass(level) {
    if (level <= 3) return 'low';
    if (level <= 6) return 'medium';
    return 'high';
}


/* ── Clinical Profile Modal ─────────────────────────────── */

function openProfileModal() {
    const modal = document.getElementById('profileModal');
    if (!modal) return;

    // Seed the form from the patient detail already loaded
    const p = currentPatientDetail || {};
    document.getElementById('profCondition').value = p.primary_condition || '';
    document.getElementById('profTherapy').value = p.therapy_program || '';
    document.getElementById('profStart').value = (p.program_start_date || '').slice(0, 10);
    document.getElementById('profSobriety').value = (p.sobriety_date || '').slice(0, 10);
    document.getElementById('profEmergency').value = p.emergency_contact || '';
    document.getElementById('profNotes').value = p.medical_notes || '';

    modal.classList.add('active');
}

function closeProfileModal() {
    document.getElementById('profileModal').classList.remove('active');
}

async function submitProfile() {
    const btn = document.getElementById('profileSubmitBtn');

    const payload = {
        primary_condition: document.getElementById('profCondition').value.trim() || null,
        therapy_program: document.getElementById('profTherapy').value.trim() || null,
        program_start_date: document.getElementById('profStart').value || null,
        sobriety_date: document.getElementById('profSobriety').value || null,
        emergency_contact: document.getElementById('profEmergency').value.trim() || null,
        medical_notes: document.getElementById('profNotes').value.trim() || null,
    };

    if (Object.values(payload).every(v => v === null)) {
        showToast('Fill in at least one field', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.put(`/doctor/patients/${currentPatientId}/profile`, payload);
        showToast('Clinical profile saved', 'success');
        closeProfileModal();
        await loadPatientDetail(currentPatientId);
    } catch (err) {
        showToast(err.message || 'Failed to save profile', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Profile';
    }
}


/* ── Medications Tab ────────────────────────────────────── */

async function loadMedications() {
    const tabContent = document.getElementById('tabContent');
    const headerHTML = `
        <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
            <h3>\u{1F48A} Medications</h3>
            <button class="btn btn-primary btn-sm" onclick="openMedModal()">+ Prescribe</button>
        </div>
    `;

    try {
        const data = await api.get(`/clinical/patients/${currentPatientId}/medications`);

        if (data.medications.length === 0) {
            tabContent.innerHTML = headerHTML + `
                <div class="empty-state">
                    <div class="empty-icon">\u{1F48A}</div>
                    <div class="empty-title">No Medications</div>
                    <div class="empty-desc">Prescribe this patient's first medication.</div>
                    <button class="btn btn-primary" onclick="openMedModal()" style="margin-top: var(--space-4);">+ Prescribe</button>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = headerHTML + `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Medication</th>
                            <th>Dosage</th>
                            <th>Frequency</th>
                            <th>Started</th>
                            <th>Status</th>
                            <th style="text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.medications.map(m => `
                            <tr class="${m.is_active ? '' : 'row-inactive'}">
                                <td><strong>${escapeHtml(m.name)}</strong>${m.notes ? `<div class="med-note">${escapeHtml(m.notes)}</div>` : ''}</td>
                                <td>${escapeHtml(m.dosage)}</td>
                                <td>${escapeHtml(m.frequency)}</td>
                                <td>${m.start_date ? formatDate(m.start_date) : '\u2014'}</td>
                                <td>
                                    <span class="badge ${m.is_active ? 'badge-success' : 'badge-danger'}">
                                        ${m.is_active ? '\u2713 Active' : '\u2715 Discontinued'}
                                    </span>
                                </td>
                                <td style="text-align: right;">
                                    ${m.is_active
                                        ? `<button class="btn btn-danger btn-sm" onclick="discontinueMedication('${escapeHtml(m.id)}')">Discontinue</button>`
                                        : '<span style="color: var(--text-muted);">\u2014</span>'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26A0\uFE0F</div><div class="empty-title">Failed to load medications</div></div>`;
    }
}

function openMedModal() {
    document.getElementById('medModal').classList.add('active');
    document.getElementById('medForm').reset();
}

function closeMedModal() {
    document.getElementById('medModal').classList.remove('active');
}

async function submitMedication() {
    const name = document.getElementById('medName').value.trim();
    const dosage = document.getElementById('medDosage').value.trim();
    const frequency = document.getElementById('medFrequency').value.trim();
    const start_date = document.getElementById('medStart').value || null;
    const notes = document.getElementById('medNotes').value.trim() || null;
    const btn = document.getElementById('medSubmitBtn');

    if (!name || !dosage || !frequency) {
        showToast('Name, dosage, and frequency are required', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.post(`/clinical/patients/${currentPatientId}/medications`, {
            name, dosage, frequency, start_date, notes,
        });
        showToast('Medication prescribed', 'success');
        closeMedModal();
        await loadMedications();
    } catch (err) {
        showToast(err.message || 'Failed to prescribe medication', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Prescribe';
    }
}

async function discontinueMedication(medicationId) {
    try {
        await api.patch(
            `/clinical/patients/${currentPatientId}/medications/${medicationId}`,
            { is_active: false }
        );
        showToast('Medication discontinued', 'success');
        await loadMedications();
    } catch (err) {
        showToast(err.message || 'Failed to update medication', 'error');
    }
}


/* ── Vitals Tab ─────────────────────────────────────────── */

async function loadVitals() {
    const tabContent = document.getElementById('tabContent');
    const headerHTML = `
        <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
            <h3>\u2764\uFE0F Vitals</h3>
            <button class="btn btn-primary btn-sm" onclick="openVitalsModal()">+ Record</button>
        </div>
    `;

    try {
        const data = await api.get(`/clinical/patients/${currentPatientId}/vitals`);

        if (data.vitals.length === 0) {
            tabContent.innerHTML = headerHTML + `
                <div class="empty-state">
                    <div class="empty-icon">\u2764\uFE0F</div>
                    <div class="empty-title">No Vitals Recorded</div>
                    <div class="empty-desc">Record this patient's first set of vital signs.</div>
                    <button class="btn btn-primary" onclick="openVitalsModal()" style="margin-top: var(--space-4);">+ Record</button>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = headerHTML + `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Recorded</th>
                            <th>Blood Pressure</th>
                            <th>Heart Rate</th>
                            <th>Temperature</th>
                            <th>Weight</th>
                            <th>By</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.vitals.map(v => `
                            <tr>
                                <td style="white-space: nowrap;">${formatDate(v.recorded_at)}</td>
                                <td>${escapeHtml(v.blood_pressure || '\u2014')}</td>
                                <td>${v.heart_rate != null ? v.heart_rate + ' bpm' : '\u2014'}</td>
                                <td>${v.temperature != null ? v.temperature + ' \u00B0C' : '\u2014'}</td>
                                <td>${v.weight != null ? v.weight + ' kg' : '\u2014'}</td>
                                <td style="font-size: var(--text-sm); color: var(--text-secondary);">${escapeHtml(v.recorded_by_name || '\u2014')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26A0\uFE0F</div><div class="empty-title">Failed to load vitals</div></div>`;
    }
}

function openVitalsModal() {
    document.getElementById('vitalsModal').classList.add('active');
    document.getElementById('vitalsForm').reset();
}

function closeVitalsModal() {
    document.getElementById('vitalsModal').classList.remove('active');
}

async function submitVitals() {
    const btn = document.getElementById('vitalsSubmitBtn');
    const num = (id) => {
        const raw = document.getElementById(id).value;
        return raw === '' ? null : parseFloat(raw);
    };

    const payload = {
        blood_pressure: document.getElementById('vitBP').value.trim() || null,
        heart_rate: num('vitHR'),
        temperature: num('vitTemp'),
        weight: num('vitWeight'),
        notes: document.getElementById('vitNotes').value.trim() || null,
    };

    const measurements = [payload.blood_pressure, payload.heart_rate, payload.temperature, payload.weight];
    if (measurements.every(v => v === null)) {
        showToast('Record at least one measurement', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.post(`/clinical/patients/${currentPatientId}/vitals`, payload);
        showToast('Vitals recorded', 'success');
        closeVitalsModal();
        await loadVitals();
    } catch (err) {
        showToast(err.message || 'Failed to record vitals', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Record';
    }
}


/* ── Medical History Tab ────────────────────────────────── */

const HISTORY_EVENT_CONFIG = {
    checkin: { icon: '\u{1F4DD}', color: 'var(--accent-info)' },
    note: { icon: '\u{1F4CB}', color: 'var(--accent-primary)' },
    goal: { icon: '\u{1F3AF}', color: 'var(--accent-success)' },
    medication: { icon: '\u{1F48A}', color: 'var(--accent-warning)' },
    vitals: { icon: '\u2764\uFE0F', color: 'var(--accent-danger)' },
    appointment: { icon: '\u{1F4C5}', color: 'var(--accent-info)' },
};

async function loadMedicalHistory() {
    const tabContent = document.getElementById('tabContent');

    try {
        const data = await api.get(`/clinical/patients/${currentPatientId}/history`);

        if (data.events.length === 0) {
            tabContent.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">\u{1F4DC}</div>
                    <div class="empty-title">No History Yet</div>
                    <div class="empty-desc">Check-ins, notes, goals, medications, and visits will appear here as one timeline.</div>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = `
            <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
                <h3>\u{1F4DC} Longitudinal Record</h3>
                <span class="badge badge-primary">${escapeHtml(data.total)} events</span>
            </div>
            <div class="history-timeline">
                ${data.events.map(e => {
                    const cfg = HISTORY_EVENT_CONFIG[e.event_type] || { icon: '\u2022', color: 'var(--text-muted)' };
                    return `
                        <div class="history-event">
                            <div class="history-marker" style="color: ${escapeHtml(cfg.color)};">${escapeHtml(cfg.icon)}</div>
                            <div class="history-body">
                                <div class="history-top">
                                    <span class="history-title">${escapeHtml(e.title)}</span>
                                    <span class="history-date">${e.occurred_at ? formatDate(e.occurred_at) : ''}</span>
                                </div>
                                ${e.summary ? `<div class="history-summary">${escapeHtml(e.summary)}</div>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26A0\uFE0F</div><div class="empty-title">Failed to load history</div></div>`;
    }
}


/* ── Recovery Timeline Tab ──────────────────────────────── */

async function loadRecoveryTimelineTab() {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    tabContent.innerHTML = `
        <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
            <h3>Recovery Timeline</h3>
        </div>
        <div id="doctorTimeline">
            <div class="loading-overlay"><div class="spinner"></div></div>
        </div>
    `;

    await loadTimelineInto('doctorTimeline', currentPatientId);
}


/* ── Digital Twin Tab ───────────────────────────────────── */

async function loadDigitalTwinTab() {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    tabContent.innerHTML = `
        <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
            <h3>Digital Twin</h3>
        </div>
        <div id="doctorTwin">
            <div class="loading-overlay"><div class="spinner"></div></div>
        </div>
    `;

    await loadTwinInto('doctorTwin', `/doctor/patients/${currentPatientId}/digital-twin`);
}


/* ── Interventions Tab ──────────────────────── */

const INTERVENTION_TYPE_LABELS = {
    check_in_call: { icon: '\u{1F4DE}', label: 'Check-in call' },
    counselling_session: { icon: '\u{1F5E3}\uFE0F', label: 'Counselling session' },
    therapy_referral: { icon: '\u27A1\uFE0F', label: 'Therapy referral' },
    medication_change: { icon: '\u{1F48A}', label: 'Medication change' },
    care_plan_update: { icon: '\u{1F5FA}\uFE0F', label: 'Care plan update' },
    escalation: { icon: '\u{1F6A8}', label: 'Escalation' },
    other: { icon: '\u2022', label: 'Other' },
};

const OUTCOME_CONFIG = {
    pending: { label: 'Outcome pending', cls: 'badge-warning' },
    improved: { label: '\u2713 Improved', cls: 'badge-success' },
    no_change: { label: '\u2014 No change', cls: 'badge-info' },
    worsened: { label: '\u2715 Worsened', cls: 'badge-danger' },
};

async function loadInterventions() {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    const headerHTML = (pending) => `
        <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
            <h3>\u{1F91D} Interventions</h3>
            <div class="flex items-center gap-3">
                ${pending > 0 ? `<span class="badge badge-warning">${pending} awaiting outcome</span>` : ''}
                <button class="btn btn-primary btn-sm" onclick="openInterventionModal()">+ Record</button>
            </div>
        </div>
    `;

    try {
        const data = await api.get(`/clinical/patients/${currentPatientId}/interventions`);

        if (data.interventions.length === 0) {
            tabContent.innerHTML = headerHTML(0) + `
                <div class="empty-state">
                    <div class="empty-icon">\u{1F91D}</div>
                    <div class="empty-title">No Interventions Recorded</div>
                    <div class="empty-desc">Record what you did in response to an alert or review, then log the outcome once it is known.</div>
                    <button class="btn btn-primary" onclick="openInterventionModal()" style="margin-top: var(--space-4);">+ Record Intervention</button>
                </div>
            `;
            return;
        }

        tabContent.innerHTML = headerHTML(data.pending_outcomes) + `
            <div class="intervention-list">
                ${data.interventions.map(iv => {
                    const type = INTERVENTION_TYPE_LABELS[iv.intervention_type]
                        || { icon: '\u2022', label: iv.intervention_type };
                    const outcome = OUTCOME_CONFIG[iv.outcome_status] || OUTCOME_CONFIG.pending;
                    return `
                        <div class="intervention-card ${iv.outcome_status === 'pending' ? 'pending' : ''}">
                            <div class="intervention-head">
                                <div class="flex items-center gap-3">
                                    <span class="intervention-type">${escapeHtml(type.icon)} ${escapeHtml(type.label)}</span>
                                    <span class="badge ${escapeHtml(outcome.cls)}">${escapeHtml(outcome.label)}</span>
                                </div>
                                <span class="intervention-date">${formatDate(iv.created_at)}</span>
                            </div>
                            ${iv.alert_summary ? `
                                <div class="intervention-alert">
                                    \u{1F514} Prompted by: ${escapeHtml(iv.alert_summary)}
                                </div>
                            ` : ''}
                            <div class="intervention-body">${escapeHtml(iv.description)}</div>
                            ${iv.outcome ? `
                                <div class="intervention-outcome">
                                    <span class="intervention-outcome-label">Outcome</span>
                                    ${escapeHtml(iv.outcome)}
                                </div>
                            ` : ''}
                            <div class="intervention-foot">
                                <span class="intervention-meta">
                                    ${escapeHtml(iv.doctor_name || 'Doctor')}${iv.follow_up_date ? ` \u00B7 follow up ${formatDate(iv.follow_up_date)}` : ''}
                                </span>
                                ${iv.outcome_status === 'pending'
                                    ? `<button class="btn btn-secondary btn-sm" onclick="openOutcomeModal('${escapeHtml(iv.id)}')">Record outcome</button>`
                                    : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26A0\uFE0F</div><div class="empty-title">Failed to load interventions</div></div>`;
    }
}


async function openInterventionModal() {
    const modal = document.getElementById('interventionModal');
    if (!modal) return;

    document.getElementById('interventionForm').reset();
    modal.classList.add('active');

    // Offer this patient's unread alerts so recording an action can clear one
    const select = document.getElementById('ivAlert');
    select.innerHTML = '<option value="">Not prompted by an alert</option>';
    try {
        const data = await api.get('/alerts?unread_only=true&limit=50');
        const mine = data.alerts.filter(a => a.patient_id === currentPatientId);
        mine.forEach(a => {
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = a.message.length > 70 ? a.message.slice(0, 70) + '\u2026' : a.message;
            select.appendChild(opt);
        });
    } catch (err) {
        // Alert linkage is optional — the modal still works without it
    }
}

function closeInterventionModal() {
    document.getElementById('interventionModal').classList.remove('active');
}

async function submitIntervention() {
    const intervention_type = document.getElementById('ivType').value;
    const description = document.getElementById('ivDescription').value.trim();
    const alert_id = document.getElementById('ivAlert').value || null;
    const follow_up_date = document.getElementById('ivFollowUp').value || null;
    const btn = document.getElementById('ivSubmitBtn');

    if (!description) {
        showToast('Describe what you did', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.post(`/clinical/patients/${currentPatientId}/interventions`, {
            intervention_type, description, alert_id, follow_up_date,
        });
        showToast(alert_id ? 'Intervention recorded and alert cleared' : 'Intervention recorded', 'success');
        closeInterventionModal();
        await loadInterventions();
        refreshAlertBadge();
    } catch (err) {
        showToast(err.message || 'Failed to record intervention', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Record';
    }
}


function openOutcomeModal(interventionId) {
    document.getElementById('outcomeForm').reset();
    document.getElementById('outcomeInterventionId').value = interventionId;
    document.getElementById('outcomeModal').classList.add('active');
}

function closeOutcomeModal() {
    document.getElementById('outcomeModal').classList.remove('active');
}

async function submitOutcome() {
    const id = document.getElementById('outcomeInterventionId').value;
    const outcome_status = document.getElementById('outcomeStatus').value;
    const outcome = document.getElementById('outcomeNotes').value.trim() || null;
    const btn = document.getElementById('outcomeSubmitBtn');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        await api.patch(
            `/clinical/patients/${currentPatientId}/interventions/${id}`,
            { outcome_status, outcome }
        );
        showToast('Outcome recorded', 'success');
        closeOutcomeModal();
        await loadInterventions();
    } catch (err) {
        showToast(err.message || 'Failed to record outcome', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Outcome';
    }
}


/* ── Care Plan Tab ──────────────────────────── */

let currentPlanData = null;

async function loadTreatmentPlan() {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    try {
        const data = await api.get(`/clinical/patients/${currentPatientId}/treatment-plan`);
        currentPlanData = data;

        const headerHTML = `
            <div class="card-header" style="padding: var(--space-5) var(--space-5) 0;">
                <h3>\u{1F5FA}\uFE0F Care Plan</h3>
                <div class="flex items-center gap-3">
                    ${data.total_versions > 0 ? `<span class="badge badge-info">v${data.current ? data.current.version : data.total_versions}</span>` : ''}
                    <button class="btn btn-primary btn-sm" onclick="openPlanModal()">
                        ${data.current ? 'Publish revision' : '+ Create plan'}
                    </button>
                </div>
            </div>
        `;

        if (!data.current) {
            tabContent.innerHTML = headerHTML + `
                <div class="empty-state">
                    <div class="empty-icon">\u{1F5FA}\uFE0F</div>
                    <div class="empty-title">No Care Plan Yet</div>
                    <div class="empty-desc">Set out the approach for this patient. Each revision is kept, so the record shows how care changed.</div>
                    <button class="btn btn-primary" onclick="openPlanModal()" style="margin-top: var(--space-4);">+ Create Plan</button>
                </div>
            `;
            return;
        }

        const p = data.current;
        tabContent.innerHTML = headerHTML + `
            <div style="padding: var(--space-5);">
                <div class="plan-current">
                    <div class="plan-head">
                        <span class="plan-version">Version ${escapeHtml(p.version)} \u00B7 current</span>
                        <span class="plan-meta">
                            ${escapeHtml(p.doctor_name || 'Doctor')} \u00B7 ${formatDate(p.created_at)}
                            ${p.review_date ? ` \u00B7 review ${formatDate(p.review_date)}` : ''}
                        </span>
                    </div>
                    ${p.focus_areas && p.focus_areas.length ? `
                        <div class="plan-focus">
                            ${p.focus_areas.map(f => `<span class="plan-focus-chip">${f}</span>`).join('')}
                        </div>
                    ` : ''}
                    <div class="plan-summary">${escapeHtml(p.summary)}</div>
                </div>

                ${data.history.length ? `
                    <div class="plan-history">
                        <h4 class="plan-history-title">Previous versions (${escapeHtml(data.history.length)})</h4>
                        ${data.history.map(h => `
                            <details class="plan-past">
                                <summary>
                                    <span class="plan-version">Version ${escapeHtml(h.version)}</span>
                                    <span class="plan-meta">${escapeHtml(h.doctor_name || 'Doctor')} \u00B7 ${formatDate(h.created_at)}${h.superseded_at ? ` \u2014 superseded ${formatDate(h.superseded_at)}` : ''}</span>
                                </summary>
                                ${h.focus_areas && h.focus_areas.length ? `
                                    <div class="plan-focus">
                                        ${h.focus_areas.map(f => `<span class="plan-focus-chip">${f}</span>`).join('')}
                                    </div>
                                ` : ''}
                                <div class="plan-summary">${escapeHtml(h.summary)}</div>
                            </details>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    } catch (err) {
        tabContent.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26A0\uFE0F</div><div class="empty-title">Failed to load care plan</div></div>`;
    }
}


function openPlanModal() {
    const modal = document.getElementById('planModal');
    if (!modal) return;

    document.getElementById('planForm').reset();
    document.querySelectorAll('#planFocusTags .focus-tag').forEach(t => t.classList.remove('selected'));

    const current = currentPlanData && currentPlanData.current;
    document.getElementById('planModalTitle').textContent =
        current ? `Publish Care Plan v${current.version + 1}` : 'Publish Care Plan';

    // Seed from the current plan so a revision starts from what is in force
    if (current) {
        document.getElementById('planSummary').value = current.summary || '';
        document.getElementById('planReview').value = (current.review_date || '').slice(0, 10);
        (current.focus_areas || []).forEach(f => {
            const tag = document.querySelector(`#planFocusTags .focus-tag[data-focus="${f}"]`);
            if (tag) tag.classList.add('selected');
        });
    }

    // Wire the focus tags once
    document.querySelectorAll('#planFocusTags .focus-tag').forEach(tag => {
        tag.onclick = () => tag.classList.toggle('selected');
    });

    modal.classList.add('active');
}

function closePlanModal() {
    document.getElementById('planModal').classList.remove('active');
}

async function submitPlan() {
    const summary = document.getElementById('planSummary').value.trim();
    const review_date = document.getElementById('planReview').value || null;
    const btn = document.getElementById('planSubmitBtn');

    if (!summary) {
        showToast('Write the plan before publishing', 'warning');
        return;
    }

    const focus_areas = Array.from(
        document.querySelectorAll('#planFocusTags .focus-tag.selected')
    ).map(t => t.dataset.focus);

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Publishing...';

    try {
        const plan = await api.put(
            `/clinical/patients/${currentPatientId}/treatment-plan`,
            { summary, focus_areas, review_date }
        );
        showToast(`Care plan v${plan.version} published`, 'success');
        closePlanModal();
        await loadTreatmentPlan();
    } catch (err) {
        showToast(err.message || 'Failed to publish plan', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Publish Plan';
    }
}
