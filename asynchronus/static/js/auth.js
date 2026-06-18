// =============================================
//  auth.js — login state, token, logout
// =============================================


// ── TOKEN HELPERS ──────────────────────────────
function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function clearToken() {
    localStorage.removeItem('token');
}

function isLoggedIn() {
    return !!getToken();
}

// returns headers with Authorization if logged in
function authHeaders() {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}


// ── LOGOUT ──────────────────────────────────────
function logout() {
    clearToken();
    window.location.href = '/';
}


// ── NAVBAR LOGIN STATE ─────────────────────────
// Replaces the "Login" button with the username + Logout
// if a valid token exists. Runs on every page via DOMContentLoaded.
async function initAuthArea() {
    const authArea = document.getElementById('authArea');
    if (!authArea) return;

    const token = getToken();
    if (!token) return; // not logged in — Login button stays as-is (default HTML)

    try {
        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            clearToken(); // token invalid/expired
            return;
        }

        const user = await res.json();
        const roles = user.roles || [];
        const isPrivileged = roles.includes('admin') || roles.includes('superadmin');

        // reveal the Admin nav link only for admins/superadmins
        const adminNavItem = document.getElementById('adminNavItem');
        if (adminNavItem && isPrivileged) {
            adminNavItem.style.display = '';
        }

        authArea.innerHTML = `
            <div class="dropdown">
                <button class="btn btn-sm btn-outline-light dropdown-toggle" type="button" data-bs-toggle="dropdown">
                    ${user.username}
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="/account">My Account</a></li>
                    <li><a class="dropdown-item" href="/users/${user.id}/posts">My Posts</a></li>
                    ${isPrivileged ? '<li><a class="dropdown-item" href="/admin">Admin Panel</a></li>' : ''}
                    <li><hr class="dropdown-divider"></li>
                    <li><button class="dropdown-item text-danger" onclick="logout()">Logout</button></li>
                </ul>
            </div>
        `;
    } catch (err) {
        console.error('Failed to fetch current user', err);
    }
}


// ── INIT ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    initAuthArea();
});