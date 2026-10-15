/** API client: adds the token, and on a 401 renews the session once and retries. */

const API_BASE = '/api';
const TOKEN_KEY = 'revive_token';
const REFRESH_KEY = 'revive_refresh';
const USER_KEY = 'revive_user';

class ApiClient {
    constructor() {
        this.baseURL = API_BASE;
        // The refresh in progress, shared so parallel 401s trigger only one.
        this._refreshInFlight = null;
    }

    /* ── Storage ─────────────────────────────────────────── */
    /* Storage can throw in private windows, so every access is guarded. */

    _read(key) {
        try {
            return localStorage.getItem(key);
        } catch (err) {
            return null;
        }
    }

    _write(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (err) {
            // Session works for this page load; it just will not be remembered.
        }
    }

    _remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (err) {
            /* nothing to do */
        }
    }

    getToken() { return this._read(TOKEN_KEY); }

    getRefreshToken() { return this._read(REFRESH_KEY); }

    /** Save the tokens from a sign-in or refresh. */
    storeSession(data) {
        if (data.access_token) this._write(TOKEN_KEY, data.access_token);
        if (data.refresh_token) this._write(REFRESH_KEY, data.refresh_token);
        if (data.user_id) {
            this._write(USER_KEY, JSON.stringify({
                id: data.user_id,
                role: data.role,
                name: data.full_name,
            }));
        }
    }

    /** Request headers, with the token when asked for. */
    getHeaders(includeAuth = true) {
        const headers = { 'Content-Type': 'application/json' };
        if (includeAuth) {
            const token = this.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        return headers;
    }

    /** Swap the refresh token for a new pair, one at a time: two at once look like theft and end every session. */
    async _refreshSession() {
        if (this._refreshInFlight) return this._refreshInFlight;

        const refreshToken = this.getRefreshToken();
        if (!refreshToken) return false;

        this._refreshInFlight = (async () => {
            try {
                const response = await fetch(`${this.baseURL}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });
                if (!response.ok) return false;
                this.storeSession(await response.json());
                return true;
            } catch (err) {
                return false;
            }
        })();

        try {
            return await this._refreshInFlight;
        } finally {
            this._refreshInFlight = null;
        }
    }

    /** Send a request; on a 401, renew once and retry before sending the user to sign in. */
    async request(method, endpoint, data = null, includeAuth = true, isRetry = false) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: this.getHeaders(includeAuth),
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        let response;
        try {
            response = await fetch(url, options);
        } catch (err) {
            throw new ApiError('Network error. Check your connection and try again.', 0);
        }

        // A non-JSON reply is still a server answer, so report it by its status.
        let result = null;
        try {
            result = await response.json();
        } catch (err) {
            result = null;
        }

        if (response.ok) return result;

        if (response.status === 401 && includeAuth && !isRetry) {
            // Never try to refresh the refresh call itself.
            if (endpoint !== '/auth/refresh' && await this._refreshSession()) {
                return this.request(method, endpoint, data, includeAuth, true);
            }
            this.clearAuth();
            window.location.hash = '#/login';
        }

        throw new ApiError(this._errorMessage(result, response.status), response.status);
    }

    /** Turn any error body, including a 422 field list, into one sentence. */
    _errorMessage(result, status) {
        const detail = result && result.detail;
        if (typeof detail === 'string' && detail) return detail;
        if (Array.isArray(detail) && detail.length) {
            return detail.map(d => {
                const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : '';
                return field ? `${field}: ${d.msg}` : d.msg;
            }).join('; ');
        }
        if (status >= 500) return `The server hit an error (${status}). Try again in a moment.`;
        return `Request failed (${status}).`;
    }

    // Convenience methods
    get(endpoint) { return this.request('GET', endpoint); }
    post(endpoint, data) { return this.request('POST', endpoint, data); }
    put(endpoint, data) { return this.request('PUT', endpoint, data); }
    patch(endpoint, data) { return this.request('PATCH', endpoint, data); }
    delete(endpoint) { return this.request('DELETE', endpoint); }

    /** Sign in and store the session. */
    async login(email, password) {
        const data = await this.request('POST', '/auth/login', {
            email,
            password,
            device_label: this._deviceLabel(),
        }, false);
        this.storeSession(data);
        return data;
    }

    /** A short browser name, so a user can tell their sessions apart. */
    _deviceLabel() {
        const ua = navigator.userAgent || '';
        const browser = /Edg\//.test(ua) ? 'Edge'
            : /Chrome\//.test(ua) ? 'Chrome'
            : /Firefox\//.test(ua) ? 'Firefox'
            : /Safari\//.test(ua) ? 'Safari'
            : 'Browser';
        const platform = /Android/.test(ua) ? 'Android'
            : /iPhone|iPad/.test(ua) ? 'iOS'
            : /Mac OS/.test(ua) ? 'macOS'
            : /Windows/.test(ua) ? 'Windows'
            : '';
        return platform ? `${browser} on ${platform}` : browser;
    }

    /** Revoke the session on the server, then clear it here, even if the network fails. */
    async logout() {
        const refreshToken = this.getRefreshToken();
        if (refreshToken) {
            try {
                await fetch(`${this.baseURL}/auth/logout`, {
                    method: 'POST',
                    headers: this.getHeaders(true),
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });
            } catch (err) {
                /* revoke on a best-effort basis */
            }
        }
        this.clearAuth();
    }

    /** The signed-in user. */
    async getMe() {
        return this.request('GET', '/auth/me');
    }

    /** Forget the stored session. */
    clearAuth() {
        this._remove(TOKEN_KEY);
        this._remove(REFRESH_KEY);
        this._remove(USER_KEY);
    }

    /** Whether someone is signed in. */
    isAuthenticated() {
        return !!this.getToken();
    }

    /** The stored user. */
    getUser() {
        const user = this._read(USER_KEY);
        if (!user) return null;
        try {
            return JSON.parse(user);
        } catch (err) {
            return null;
        }
    }
}

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

const api = new ApiClient();
