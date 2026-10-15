/** Digital twin page; the model and charts come from recovery.js. */

async function renderPatientTwin() {
    renderDashboardShell('patient', 'twin', 'Digital Twin', `
        <div class="page-header">
            <h1>Digital Twin</h1>
            <p>Where your recovery stands today, and how the score could move if one habit changed</p>
        </div>

        <div class="card glass" id="twinCard">
            <div class="card-header"><h3>Your Recovery Model</h3></div>
            <div id="twinBody">
                <div class="loading-overlay"><div class="spinner"></div><span>Building your twin...</span></div>
            </div>
        </div>
    `);

    loadTwinInto('twinBody', '/patient/digital-twin');
}
