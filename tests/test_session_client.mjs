/** Runs the real api.js against a seeded server: node tests/test_session_client.mjs [url] [email] [password] */
import fs from 'node:fs';

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const EMAIL = process.argv[3] || 'patient1@test.com';
const PASSWORD = process.argv[4] || 'Test@123';

// ── browser stand-ins ────────────────────────────────────────
const store = {};
globalThis.localStorage = {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
};
globalThis.window = { location: { hash: '' } };
// Node's navigator is read-only, so the device label falls back to 'Browser'.

// count refresh calls so we can prove single-flight
let refreshCalls = 0;
const realFetch = globalThis.fetch;
globalThis.fetch = (url, opts) => {
    if (String(url).endsWith('/auth/refresh')) refreshCalls++;
    return realFetch(url, opts);
};

// load the real client, rewriting its API base to the test server
let src = fs.readFileSync(new URL('../frontend/js/api.js', import.meta.url), 'utf8');
src = src.replace("const API_BASE = '/api';", `const API_BASE = ${JSON.stringify(BASE + '/api')};`);
const { api } = await import('data:text/javascript,' + encodeURIComponent(src + '\nexport { api, ApiError };'));

let pass = 0, fail = 0;
const check = (label, cond) => {
    if (cond) { pass++; console.log('    ok  ' + label); }
    else { fail++; console.log('  FAIL  ' + label); }
};

console.log('\n[1] Login stores both tokens');
await api.login(EMAIL, PASSWORD);
check('access token stored', !!store['revive_token']);
check('refresh token stored', !!store['revive_refresh']);
check('user stored', !!store['revive_user']);
const firstRefresh = store['revive_refresh'];

console.log('\n[2] An authenticated call works');
const me = await api.getMe();
check('GET /auth/me returns the user', me.email === EMAIL);

console.log('\n[3] An expired access token is renewed transparently');
store['revive_token'] = 'expired.invalid.token';
refreshCalls = 0;
const me2 = await api.getMe();
check('request succeeded despite a dead access token', me2.email === EMAIL);
check('exactly one refresh was performed', refreshCalls === 1);
check('a NEW access token was stored', store['revive_token'] !== 'expired.invalid.token');
check('the refresh token rotated', store['revive_refresh'] !== firstRefresh);
check('user was NOT redirected to login', window.location.hash === '');

console.log('\n[4] Concurrent 401s share ONE refresh (rotation safety)');
// Two refreshes at once would look like theft and end every session.
store['revive_token'] = 'expired.invalid.token';
refreshCalls = 0;
const results = await Promise.all([api.getMe(), api.getMe(), api.getMe(), api.getMe()]);
check('all four concurrent requests succeeded', results.every(r => r.email === EMAIL));
check('exactly one refresh for four 401s (got ' + refreshCalls + ')', refreshCalls === 1);
check('session survived — still authenticated', api.isAuthenticated());
const afterConcurrent = await api.getMe();
check('session still usable afterwards', afterConcurrent.email === EMAIL);

console.log('\n[5] A dead refresh token sends the user to login');
store['revive_token'] = 'expired.invalid.token';
store['revive_refresh'] = 'not-a-real-refresh-token';
let threw = false;
try { await api.getMe(); } catch (e) { threw = true; }
check('the request failed', threw);
check('auth was cleared', !store['revive_token'] && !store['revive_refresh']);
check('redirected to login', window.location.hash === '#/login');

console.log('\n[6] Logout revokes server-side');
window.location.hash = '';
await api.login(EMAIL, PASSWORD);
const liveRefresh = store['revive_refresh'];
await api.logout();
check('local session cleared', !store['revive_token']);
const res = await realFetch(`${BASE}/api/auth/refresh`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: liveRefresh }),
});
check('revoked refresh token is rejected (401, got ' + res.status + ')', res.status === 401);

console.log(`\n  ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
