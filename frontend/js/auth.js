/** Welcome page, sign-in form and the redirect to each role's dashboard. */


/* ── Demo entry / welcome page ───────────────────────────── */
const DEMO_ACCOUNTS = {
    admin:    { label: 'Platform Admin', email: 'admin@revive.com', password: 'admin123', icon: '👑', color: 'primary', description: 'Manage hospitals, admins and platform activity.' },
    hospital: { label: 'Hospital Admin', email: 'hospital@test.com', password: 'Test@123', icon: '🏥', color: 'blue', description: 'Manage doctors, patients and hospital operations.' },
    doctor:   { label: 'Doctor', email: 'doctor1@test.com', password: 'Test@123', icon: '🩺', color: 'green', description: 'View patients, appointments and recovery risk.' },
    patient:  { label: 'Patient', email: 'patient1@test.com', password: 'Test@123', icon: '🧑‍🦽', color: 'purple', description: 'Track check-ins, goals, progress and care.' },
    guardian: { label: 'Guardian', email: 'guardian1@test.com', password: 'Test@123', icon: '👨‍👩‍👧', color: 'pink', description: 'Follow a patient\'s recovery and appointments.' },
};

function selectDemoRole(role) {
    try { sessionStorage.setItem('revive_demo_role', role); } catch (e) {}
    window.location.hash = '#/login';
}

function getSelectedDemoAccount() {
    let role = 'doctor';
    try { role = sessionStorage.getItem('revive_demo_role') || 'doctor'; } catch (e) {}
    return DEMO_ACCOUNTS[role] || DEMO_ACCOUNTS.doctor;
}

function initWelcomePage() {
    const app = document.getElementById('app');
    const accounts = Object.entries(DEMO_ACCOUNTS);

    const roleIcons = {
        admin: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l2.1 4.25 4.69.68-3.4 3.31.8 4.67L12 13.7l-4.19 2.2.8-4.67-3.4-3.31 4.69-.68L12 3z"/><path d="M4 18.5h16M6 21h12"/></svg>',
        hospital: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16M3 21h18"/><path d="M10 7h4M12 5v4M9 12h1M14 12h1M9 16h1M14 16h1"/></svg>',
        doctor: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4v5a4 4 0 0 0 8 0V4M6 4h4M14 4h4"/><path d="M12 13v3a4 4 0 0 0 4 4h1a4 4 0 0 0 4-4v-1"/><circle cx="19" cy="11" r="2"/><path d="M4 4v2a3 3 0 0 0 3 3"/></svg>',
        patient: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="2"/><path d="M10 8l-1 5 3 2v5M14 8l1 5-2 2M9 11H6M15 11h3"/><path d="M8 21h3M13 21h3"/></svg>',
        guardian: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="8" r="2.5"/><circle cx="16" cy="8" r="2.5"/><path d="M3.5 18a4.5 4.5 0 0 1 9 0M11.5 18a4.5 4.5 0 0 1 9 0"/><circle cx="12" cy="13" r="2"/></svg>'
    };

    app.innerHTML = `
        ${renderNavbar(null, 'welcome')}
        <div class="welcome-page">
            <div class="welcome-bg-orb welcome-bg-orb-left"></div>
            <div class="welcome-bg-orb welcome-bg-orb-right"></div>

            <main class="welcome-shell">
                <div class="welcome-hero">
                    <div class="welcome-brand-icon" aria-hidden="true"><span>✦</span></div>
                    <h1>RE:VIVE</h1>
                    <p class="welcome-platform-name">Recovery Management Platform</p>
                    <h2>Smarter Recovery. <span>Brighter Tomorrows.</span></h2>
                    <p class="welcome-subtitle">Choose a role to explore the platform with demo access.</p>
                </div>

                <div class="demo-role-grid">
                    ${accounts.map(([role, account]) => `
                        <button class="demo-role-card demo-role-${account.color}" type="button" onclick="selectDemoRole('${role}')" aria-label="Continue as ${account.label}">
                            <span class="demo-role-icon">${roleIcons[role]}</span>
                            <span class="demo-role-copy">
                                <strong>${account.label}</strong>
                                <small>${account.description}</small>
                            </span>
                            <span class="demo-credentials">
                                <span><em>Email:</em> <b>${account.email}</b></span>
                                <span><em>Password:</em> <b>${account.password}</b></span>
                            </span>
                            <span class="demo-role-continue">Continue <span aria-hidden="true">→</span></span>
                        </button>
                    `).join('')}
                </div>

                <p class="welcome-quote">“Technology for a Healthier, More Inclusive Tomorrow.”</p>

                <div class="welcome-benefits">
                    <span><i aria-hidden="true">♥</i> Better Care</span>
                    <span><i aria-hidden="true">♟</i> Stronger Support</span>
                    <span><i aria-hidden="true">⌁</i> Faster Recovery</span>
                    <span><i aria-hidden="true">♡</i> Inclusive Healthcare</span>
                </div>

                <div class="welcome-footer">RE:VIVE v1.0 <b>|</b> Secure <b>|</b> Scalable <b>|</b> Human-Centric</div>
            </main>
        </div>
    `;
}

function initLoginPage() {
    const app = document.getElementById('app');
    const demo = getSelectedDemoAccount();
    app.innerHTML = `
        ${renderNavbar(null, 'login')}
        <main class="login-page">
            <div class="login-container">
                <div class="login-card card glass">
                    <div class="login-branding">
                        <div class="brand-icon" aria-hidden="true">✦</div>
                        <h1>RE:VIVE</h1>
                        <p>Recovery Management Platform</p>
                    </div>

                    <form id="loginForm" class="login-form">
                        <div id="loginError" class="login-error" style="display: none;"></div>

                        <div class="form-group">
                            <label class="form-label" for="email">Email</label>
                            <input
                                type="email"
                                id="email"
                                class="form-input"
                                placeholder="Enter your email"
                                value="${demo.email}"
                                autocomplete="email"
                                required
                            />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="password">Password</label>
                            <input
                                type="password"
                                id="password"
                                class="form-input"
                                placeholder="Enter your password"
                                value="${demo.password}"
                                autocomplete="current-password"
                                required
                            />
                        </div>

                        <button type="submit" class="btn btn-primary btn-lg w-full" id="loginBtn">
                            Sign In
                        </button>

                        <div class="demo-login-hint">
                            <div><strong>Demo account</strong><span>${escapeHtml(demo.label)}</span></div>
                            <button type="button" onclick="window.location.hash='#/welcome'">Change role</button>
                        </div>
                    </form>

                    <div class="login-footer">
                        <p>Secured healthcare platform · RE:VIVE v1.0</p>
                    </div>
                </div>
            </div>
        </main>
    `;

    const form = document.getElementById('loginForm');
    form.addEventListener('submit', handleLogin);
}


async function handleLogin(e) {
    e.preventDefault();

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    const errorDiv = document.getElementById('loginError');

    if (!email || !password) {
        showLoginError('Please fill in all fields');
        return;
    }

    loginBtn.disabled = true;
    loginBtn.innerHTML = '<span class="spinner"></span> Signing in...';
    errorDiv.style.display = 'none';

    try {
        const data = await api.login(email, password);
        redirectToDashboard(data.role);
    } catch (error) {
        showLoginError(error.message || 'Invalid credentials');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Sign In';
    }
}


function showLoginError(message) {
    const errorDiv = document.getElementById('loginError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}


function redirectToDashboard(role) {
    const routes = {
        admin: '#/admin/dashboard',
        hospital: '#/hospital/dashboard',
        doctor: '#/doctor/dashboard',
        patient: '#/patient/dashboard',
        guardian: '#/guardian/dashboard',
    };
    window.location.hash = routes[role] || '#/login';
}


async function logout() {
    // Revoke on the server first, so signing out really ends the session.
    await api.logout();
    window.location.hash = '#/login';
}
