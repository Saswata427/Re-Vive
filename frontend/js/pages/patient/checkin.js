/** Daily check-in: mood, stress, sleep, cravings, medication, activity and notes. */

/* Shared config for the two 1-10 intensity sliders */
const INTENSITY_SLIDERS = {
    craving: {
        id: 'craving',
        icon: '🌊',
        title: 'Cravings',
        desc: 'How strong were your cravings today?',
        bands: [
            { max: 3, label: 'Manageable', color: 'var(--level-low)', cls: 'level-low' },
            { max: 6, label: 'Noticeable', color: 'var(--level-mid)', cls: 'level-mid' },
            { max: 8, label: 'Strong', color: 'var(--level-high)', cls: 'level-high' },
            { max: 10, label: 'Overwhelming', color: 'var(--level-extreme)', cls: 'level-extreme' },
        ],
    },
    stress: {
        id: 'stress',
        icon: '🌡️',
        title: 'Stress',
        desc: 'How stressed have you felt today?',
        bands: [
            { max: 3, label: 'Calm', color: 'var(--level-low)', cls: 'level-low' },
            { max: 6, label: 'Moderate', color: 'var(--level-mid)', cls: 'level-mid' },
            { max: 8, label: 'High', color: 'var(--level-high)', cls: 'level-high' },
            { max: 10, label: 'Severe', color: 'var(--level-extreme)', cls: 'level-extreme' },
        ],
    },
};


function _renderIntensitySlider(cfg) {
    return `
        <div class="card glass checkin-section">
            <h3 class="checkin-section-title">${escapeHtml(cfg.icon)} ${escapeHtml(cfg.title)}</h3>
            <p class="checkin-section-desc">${escapeHtml(cfg.desc)}</p>
            <div class="level-slider-container">
                <input type="range" id="${escapeHtml(cfg.id)}Slider" class="level-slider" min="1" max="10" value="3" />
                <div class="level-labels">
                    ${Array.from({ length: 10 }, (_, i) => `<span>${i + 1}</span>`).join('')}
                </div>
                <div class="level-value-display" id="${escapeHtml(cfg.id)}Display">
                    <span class="level-value-number" id="${escapeHtml(cfg.id)}Number">3</span>
                    <span class="level-value-label" id="${escapeHtml(cfg.id)}Label">${escapeHtml(cfg.bands[0].label)}</span>
                </div>
            </div>
        </div>
    `;
}


async function renderPatientCheckin() {
    const user = api.getUser();

    // Check if already submitted today
    let alreadyDone = false;
    try {
        const dash = await api.get('/patient/dashboard');
        alreadyDone = dash.today_checkin_done;
    } catch { /* proceed anyway */ }

    if (alreadyDone) {
        renderDashboardShell('patient', 'checkin', 'Daily Check-in', `
            <div class="page-header">
                <h1>Daily Check-in</h1>
                <p>Log your daily recovery data</p>
            </div>
            <div class="card glass checkin-done-banner" style="max-width: 600px; margin: var(--space-8) auto;">
                <div class="checkin-done-icon" style="font-size: 3rem;">✅</div>
                <div style="text-align: center;">
                    <h2 style="color: var(--accent-success); margin-bottom: var(--space-2);">Already Checked In!</h2>
                    <p style="color: var(--text-secondary);">You've already submitted your check-in for today. Come back tomorrow!</p>
                    <a href="#/patient/dashboard" class="btn btn-primary" style="margin-top: var(--space-5);">← Back to Dashboard</a>
                </div>
            </div>
        `);
        return;
    }

    renderDashboardShell('patient', 'checkin', 'Daily Check-in', `
        <div class="page-header">
            <h1>Daily Check-in</h1>
            <p>How are you feeling today, ${escapeHtml(user?.name || 'there')}?</p>
        </div>

        <form id="checkinForm" class="checkin-form" autocomplete="off">
            <div class="card glass checkin-section">
                <h3 class="checkin-section-title">Mood</h3>
                <p class="checkin-section-desc">How is your overall mood today?</p>
                <div class="mood-selector" id="moodSelector">
                    <button type="button" class="mood-btn" data-mood="good">
                        <span class="mood-emoji">😊</span>
                        <span class="mood-label">Good</span>
                    </button>
                    <button type="button" class="mood-btn" data-mood="neutral">
                        <span class="mood-emoji">😐</span>
                        <span class="mood-label">Neutral</span>
                    </button>
                    <button type="button" class="mood-btn" data-mood="poor">
                        <span class="mood-emoji">😔</span>
                        <span class="mood-label">Difficult</span>
                    </button>
                </div>
                <input type="hidden" id="moodInput" value="" />
            </div>

            ${_renderIntensitySlider(INTENSITY_SLIDERS.craving)}
            ${_renderIntensitySlider(INTENSITY_SLIDERS.stress)}

            <div class="card glass checkin-section">
                <h3 class="checkin-section-title">Sleep</h3>
                <p class="checkin-section-desc">How many hours did you sleep last night?</p>
                <div class="sleep-input-container">
                    <button type="button" class="sleep-btn" id="sleepMinus">−</button>
                    <div class="sleep-value">
                        <span id="sleepNumber">7.0</span>
                        <span class="sleep-unit">hours</span>
                    </div>
                    <button type="button" class="sleep-btn" id="sleepPlus">+</button>
                </div>
                <input type="hidden" id="sleepInput" value="7.0" />
            </div>

            <div class="card glass checkin-section">
                <h3 class="checkin-section-title">Medication</h3>
                <p class="checkin-section-desc">Did you take all prescribed medications today?</p>
                <div class="medication-toggle" id="medToggle">
                    <button type="button" class="med-btn" data-med="true">
                        <span class="med-icon">✓</span>
                        <span>Yes, all taken</span>
                    </button>
                    <button type="button" class="med-btn" data-med="false">
                        <span class="med-icon">✕</span>
                        <span>No / Partially</span>
                    </button>
                </div>
                <input type="hidden" id="medInput" value="" />
            </div>

            <div class="card glass checkin-section">
                <h3 class="checkin-section-title">Physical Activity</h3>
                <p class="checkin-section-desc">How many minutes were you physically active today?</p>
                <div class="activity-selector" id="activitySelector">
                    <button type="button" class="activity-btn" data-minutes="0">None</button>
                    <button type="button" class="activity-btn" data-minutes="15">15 min</button>
                    <button type="button" class="activity-btn" data-minutes="30">30 min</button>
                    <button type="button" class="activity-btn" data-minutes="60">1 hour</button>
                    <button type="button" class="activity-btn" data-minutes="120">2 hours+</button>
                </div>
                <input type="hidden" id="activityInput" value="0" />
            </div>

            <div class="card glass checkin-section">
                <h3 class="checkin-section-title">Notes</h3>
                <p class="checkin-section-desc">Anything else you'd like to share with your care team?</p>
                <textarea id="checkinNotes" class="form-textarea" rows="4" placeholder="Optional notes about how you're feeling..."></textarea>
            </div>

            <div class="checkin-submit-area">
                <button type="submit" class="btn btn-primary btn-lg checkin-submit-btn" id="submitCheckin">
                    Submit Check-in
                </button>
                <a href="#/patient/dashboard" class="btn btn-ghost">Cancel</a>
            </div>
        </form>
    `);

    _initMoodSelector();
    _initIntensitySlider(INTENSITY_SLIDERS.craving);
    _initIntensitySlider(INTENSITY_SLIDERS.stress);
    _initSleepInput();
    _initMedToggle();
    _initActivitySelector();
    _initCheckinSubmit();
}


/* ── Intensity Sliders (cravings, stress) ────────────────── */

function _initIntensitySlider(cfg) {
    const slider = document.getElementById(`${cfg.id}Slider`);
    if (!slider) return;

    const update = () => {
        const val = parseInt(slider.value);
        const band = cfg.bands.find(b => val <= b.max) || cfg.bands[cfg.bands.length - 1];

        const numberEl = document.getElementById(`${cfg.id}Number`);
        const labelEl = document.getElementById(`${cfg.id}Label`);
        const displayEl = document.getElementById(`${cfg.id}Display`);

        if (numberEl) numberEl.textContent = val;
        if (labelEl) labelEl.textContent = band.label;
        if (displayEl) displayEl.className = `level-value-display ${band.cls}`;

        const pct = ((val - 1) / 9) * 100;
        slider.style.background =
            `linear-gradient(to right, ${band.color} 0%, ${band.color} ${pct}%, var(--hairline-strong) ${pct}%)`;
    };

    slider.addEventListener('input', update);
    update();
}


/* ── Mood Selector ───────────────────────────────────────── */

function _initMoodSelector() {
    const container = document.getElementById('moodSelector');
    const input = document.getElementById('moodInput');
    if (!container || !input) return;

    container.querySelectorAll('.mood-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            input.value = btn.dataset.mood;
        });
    });
}


/* ── Sleep Input ─────────────────────────────────────────── */

function _initSleepInput() {
    const minus = document.getElementById('sleepMinus');
    const plus = document.getElementById('sleepPlus');
    const display = document.getElementById('sleepNumber');
    const input = document.getElementById('sleepInput');
    if (!minus || !plus || !display || !input) return;

    let val = 7.0;

    const update = () => {
        display.textContent = val.toFixed(1);
        input.value = val.toFixed(1);
    };

    minus.addEventListener('click', () => {
        if (val > 0) { val = Math.max(0, val - 0.5); update(); }
    });

    plus.addEventListener('click', () => {
        if (val < 24) { val = Math.min(24, val + 0.5); update(); }
    });
}


/* ── Medication Toggle ───────────────────────────────────── */

function _initMedToggle() {
    const container = document.getElementById('medToggle');
    const input = document.getElementById('medInput');
    if (!container || !input) return;

    container.querySelectorAll('.med-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.med-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            input.value = btn.dataset.med;
        });
    });
}


/* ── Physical Activity Selector ──────────────────────────── */

function _initActivitySelector() {
    const container = document.getElementById('activitySelector');
    const input = document.getElementById('activityInput');
    if (!container || !input) return;

    container.querySelectorAll('.activity-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.activity-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            input.value = btn.dataset.minutes;
        });
    });
}


/* ── Form Submission ─────────────────────────────────────── */

function _initCheckinSubmit() {
    const form = document.getElementById('checkinForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('submitCheckin');

        const mood = document.getElementById('moodInput')?.value;
        const med = document.getElementById('medInput')?.value;

        if (!mood) {
            showToast('Please select your mood', 'warning');
            return;
        }
        if (med === '') {
            showToast('Please indicate if you took your medication', 'warning');
            return;
        }

        const payload = {
            mood: mood,
            craving_level: parseInt(document.getElementById('cravingSlider')?.value || '3'),
            stress_level: parseInt(document.getElementById('stressSlider')?.value || '3'),
            sleep_hours: parseFloat(document.getElementById('sleepInput')?.value || '7.0'),
            medication_taken: med === 'true',
            physical_activity_minutes: parseInt(document.getElementById('activityInput')?.value || '0'),
            notes: document.getElementById('checkinNotes')?.value?.trim() || null,
        };

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
        }

        try {
            await api.post('/patient/checkin', payload);
            try {
                const result = await getPatientRiskResult('patient');
                const meta = aiRiskMeta(result.risk_category);
                showToast(`Check-in saved. AI recovery risk: ${meta.label} (${Math.round((result.recovery_risk_probability || 0) * 100)}%).`, result.risk_category === 'HIGH' ? 'warning' : 'success');
            } catch {
                showToast('Check-in submitted successfully! 🎉', 'success');
            }
            setTimeout(() => { window.location.hash = '#/patient/dashboard'; }, 1200);
        } catch (err) {
            showToast(err.message || 'Failed to submit check-in', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Check-in';
            }
        }
    });
}
