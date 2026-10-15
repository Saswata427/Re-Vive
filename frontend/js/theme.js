/** Theme switch: system, light or dark. index.html applies the saved one before the CSS loads. */

const THEME_KEY = 'revive_theme';
const THEME_ORDER = ['system', 'light', 'dark'];

const THEME_META = {
    system: {
        label: 'System theme',
        icon: '<circle cx="12" cy="12" r="8"/><path d="M12 4v16"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" stroke="none"/>',
    },
    light: {
        label: 'Light theme',
        icon: '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4"/>',
    },
    dark: {
        label: 'Dark theme',
        icon: '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>',
    },
};


/** The saved theme, or 'system' (reading storage can throw). */
function getTheme() {
    try {
        const stored = localStorage.getItem(THEME_KEY);
        return THEME_ORDER.includes(stored) ? stored : 'system';
    } catch (err) {
        return 'system';
    }
}


/** Apply and save a theme; 'system' hands back to the OS setting. */
function setTheme(theme) {
    if (!THEME_ORDER.includes(theme)) theme = 'system';

    if (theme === 'system') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }

    try {
        localStorage.setItem(THEME_KEY, theme);
    } catch (err) {
        // Storage is blocked: the theme applies now but won't be remembered.
    }

    refreshThemeToggle();
    return theme;
}


/** The header theme button and its menu. */
function renderThemeToggle() {
    const theme = getTheme();
    const labels = { system: 'System', light: 'Light', dark: 'Dark' };
    return `
        <div class="theme-picker" id="themePicker" onclick="event.stopPropagation()">
            <button class="theme-picker-button" type="button" aria-haspopup="true" aria-expanded="false" aria-label="Theme: ${escapeHtml(labels[theme])}"
                    onclick="toggleThemePicker(event)" title="Choose theme">
                <span class="theme-picker-icon" aria-hidden="true"><svg viewBox="0 0 24 24">${THEME_META[theme].icon}</svg></span>
                <span class="theme-picker-label">${escapeHtml(labels[theme])}</span>
                <span class="theme-picker-chevron" aria-hidden="true">⌄</span>
            </button>
            <div class="theme-picker-menu" role="menu" aria-label="Theme selection">
                ${THEME_ORDER.map(name => `
                    <button type="button" class="theme-option ${name === theme ? 'is-active' : ''}"
                            role="menuitemradio" aria-checked="${name === theme}"
                            onclick="chooseTheme('${name}', event)">
                        <span class="theme-option-icon" aria-hidden="true"><svg viewBox="0 0 24 24">${THEME_META[name].icon}</svg></span>
                        <span>${escapeHtml(labels[name])}</span>
                        <span class="theme-option-check">${name === theme ? '✓' : ''}</span>
                    </button>
                `).join('')}
            </div>
        </div>
    `;
}

function toggleThemePicker(event) {
    if (event) event.stopPropagation();
    const picker = document.getElementById('themePicker');
    if (!picker) return;
    const open = picker.classList.toggle('is-open');
    const button = picker.querySelector('.theme-picker-button');
    if (button) button.setAttribute('aria-expanded', String(open));
}

function chooseTheme(theme, event) {
    if (event) event.stopPropagation();
    setTheme(theme);
    const picker = document.getElementById('themePicker');
    if (picker) {
        picker.classList.remove('is-open');
        const button = picker.querySelector('.theme-picker-button');
        if (button) button.setAttribute('aria-expanded', 'false');
    }
    if (typeof showToast === 'function') showToast(THEME_META[theme].label, 'info');
}


/** Redraw just the theme button after a change. */
function refreshThemeToggle() {
    const existing = document.getElementById('themePicker');
    if (!existing) return;
    const parent = existing.parentElement;
    if (!parent) return;
    const wasOpen = existing.classList.contains('is-open');
    const temp = document.createElement('div');
    temp.innerHTML = renderThemeToggle();
    const replacement = temp.firstElementChild;
    if (!replacement) return;
    parent.replaceChild(replacement, existing);
    if (wasOpen) replacement.classList.add('is-open');
}

// Close the picker when clicking elsewhere.
document.addEventListener('click', () => {
    const picker = document.getElementById('themePicker');
    if (!picker) return;
    picker.classList.remove('is-open');
    const button = picker.querySelector('.theme-picker-button');
    if (button) button.setAttribute('aria-expanded', 'false');
});


/** In system mode, follow the OS if it changes mid-session. */
if (window.matchMedia) {
    const query = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = () => {
        if (getTheme() === 'system') refreshThemeToggle();
    };
    if (query.addEventListener) {
        query.addEventListener('change', onChange);
    } else if (query.addListener) {
        query.addListener(onChange);
    }
}
