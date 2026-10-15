/** Recovery risk card. Requests go through the backend's signed-in /api/ai gateway, never straight to the AI service. */

function aiRiskMeta(category) {
    const key = String(category || '').toUpperCase();
    if (key === 'HIGH') return { icon: '🔴', cls: 'ai-risk-high', label: 'High risk' };
    if (key === 'MEDIUM') return { icon: '🟠', cls: 'ai-risk-medium', label: 'Medium risk' };
    return { icon: '🟢', cls: 'ai-risk-low', label: 'Low risk' };
}

async function recoveryAiPredict(payload) {
    return api.post('/ai/predict', payload || {});
}

function aiDaysSince(dateValue) {
    if (!dateValue) return null;
    const d = new Date(dateValue);
    if (Number.isNaN(d.getTime())) return null;
    return Math.max(0, Math.round((Date.now() - d.getTime()) / 86400000));
}

function aiMoodScore(mood) {
    return ({ good: 8, neutral: 5, poor: 2 }[String(mood || '').toLowerCase()] ?? null);
}

function aiBuildPayload({ profile = {}, checkins = [], score = null, goals = [] } = {}) {
    const recent = (checkins || []).slice(0, 7);
    const latest = recent[0] || {};
    const n = recent.length;
    const medicationRate = n ? recent.filter(c => c.medication_taken === true).length / n * 100 : null;
    const exerciseRate = n ? recent.reduce((sum, c) => sum + Math.min(Number(c.physical_activity_minutes || 0) / 30 * 100, 100), 0) / n : null;
    const checkinRate = Math.min(n / 7 * 100, 100);
    const goalGap = (goals || []).filter(g => g.status !== 'completed').length;
    const recoveryProgress = score?.score ?? null;

    return {
        days_post_procedure: aiDaysSince(profile.program_start_date),
        age: null,
        // Check-ins don't collect vitals, so leave them out and let the model fill them in.
        pain_score: null,
        temperature_c: null,
        heart_rate_bpm: null,
        systolic_bp: null,
        diastolic_bp: null,
        oxygen_saturation_pct: null,
        sleep_hours: latest.sleep_hours ?? null,
        medication_adherence_pct: medicationRate,
        exercise_adherence_pct: exerciseRate,
        daily_checkin_adherence_pct: checkinRate,
        symptom_severity: null,
        mood_score: aiMoodScore(latest.mood),
        recovery_progress_pct: recoveryProgress,
        goal_gap_count: goalGap,
    };
}

async function aiLoadPatientContext(role, patientId = null, existing = null) {
    if (role === 'guardian' && existing) {
        const profile = {
            program_start_date: existing.program_start_date,
            primary_condition: existing.primary_condition,
        };
        return {
            payload: aiBuildPayload({ profile, checkins: existing.recent_checkins || [], score: existing.recovery_score != null ? { score: existing.recovery_score } : null, goals: existing.goals || [] }),
            patientName: existing.patient_name || 'Patient',
        };
    }

    const base = role === 'doctor' ? `/doctor/patients/${patientId}` : '/patient';
    const [profile, checkins, score, goals] = await Promise.all([
        api.get(role === 'doctor' ? `${base}/profile` : '/patient/profile'),
        api.get(role === 'doctor' ? `${base}/checkins?limit=7` : '/patient/checkins?limit=7'),
        api.get(role === 'doctor' ? `${base}/recovery-score?window_days=30` : '/patient/recovery-score?window_days=30'),
        api.get(role === 'doctor' ? `${base}/goals` : '/patient/goals'),
    ]);
    return {
        payload: aiBuildPayload({ profile, checkins: checkins.checkins || [], score, goals: goals.goals || [] }),
        patientName: profile.full_name || 'Patient',
    };
}

function renderRecoveryRiskCard(containerId, result, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!result) {
        container.innerHTML = `<div class="ai-risk-empty"><span>🧠</span><div><strong>AI risk unavailable</strong><small>Complete recovery check-ins to build a risk view.</small></div></div>`;
        return;
    }
    const meta = aiRiskMeta(result.risk_category);
    const pct = Math.round(Number(result.recovery_risk_probability || 0) * 100);
    const shap = Array.isArray(result.shap) ? result.shap.filter(x => x.feature && x.feature !== 'SHAP unavailable').slice(0, 4) : [];
    const factorLabel = f => String(f || '').replaceAll('_', ' ');
    const factors = shap.length ? shap.map(x => `<span class="ai-factor ${x.impact === 'increases_risk' ? 'factor-up' : 'factor-down'}">${x.impact === 'increases_risk' ? '↑' : '↓'} ${escapeHtml(factorLabel(x.feature))}</span>`).join('') : '<span class="ai-factor">No explanation available yet</span>';
    const title = options.title || 'AI Recovery Risk';
    const subtitle = options.subtitle || 'Prototype risk estimate from recent recovery signals';
    container.innerHTML = `
        <div class="ai-risk-card ${escapeHtml(meta.cls)}">
            <div class="ai-risk-head">
                <div><div class="section-kicker">AI-ASSISTED MONITORING</div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(subtitle)}</p></div>
                <span class="ai-model-chip">XGBoost + SHAP</span>
            </div>
            <div class="ai-risk-main">
                <div class="ai-risk-badge"><span>${meta.icon}</span><div><strong>${escapeHtml(meta.label)}</strong><small>${pct}% estimated probability</small></div></div>
                <div class="ai-risk-meter"><div class="ai-risk-meter-fill" style="width:${Math.min(100,pct)}%"></div></div>
            </div>
            <div class="ai-risk-factors"><span class="ai-factor-label">Key signals</span>${factors}</div>
            <div class="ai-risk-disclaimer">Prototype decision-support only — not a diagnosis. Missing clinical vitals are not treated as measured values.</div>
        </div>`;
}

async function loadRecoveryRiskCard(containerId, role, patientId = null, existing = null, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return null;
    container.innerHTML = `<div class="ai-risk-loading"><div class="spinner"></div><span>Analyzing recent recovery signals...</span></div>`;
    try {
        const context = await aiLoadPatientContext(role, patientId, existing);
        const result = await recoveryAiPredict(context.payload);
        renderRecoveryRiskCard(containerId, result, { ...options, title: options.title || `${context.patientName}'s Recovery Risk` });
        return result;
    } catch (err) {
        container.innerHTML = `<div class="ai-risk-unavailable"><span>🧠</span><div><strong>Recovery Risk AI is unavailable</strong><small>${escapeHtml(err.message || 'Start the AI service on port 8010 and try again.')}</small></div></div>`;
        return null;
    }
}

async function getPatientRiskResult(role, patientId = null, existing = null) {
    const context = await aiLoadPatientContext(role, patientId, existing);
    return recoveryAiPredict(context.payload);
}
