// =============================================
//  utils.js — shared JS for posts/modals/theme
//  (auth-related code lives in auth.js)
//  (dark mode "instant apply" is inline in base.html)
// =============================================


// ── 1. THEME TOGGLE ───────────────────────────
function initThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    const label  = document.getElementById('themeLabel');
    const html   = document.documentElement;

    if (!toggle) return;

    const saved = localStorage.getItem('theme') || 'light';
    toggle.checked    = saved === 'dark';
    label.textContent = saved === 'dark' ? '☀️' : '🌙';

    toggle.addEventListener('change', function () {
        const theme = this.checked ? 'dark' : 'light';
        html.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
        label.textContent = theme === 'dark' ? '☀️' : '🌙';
    });
}


// ── 2. NEW POST MODAL ─────────────────────────
let newPostModal = null;

function initNewPostModal() {
    const el = document.getElementById('newPostModal');
    if (!el) {
        console.warn('newPostModal element not found');
        return;
    }
    if (typeof bootstrap === 'undefined') {
        console.error('bootstrap is not loaded — newPostModal cannot initialize');
        return;
    }
    newPostModal = new bootstrap.Modal(el);
}

function openNewPostModal() {
    if (!newPostModal) {
        console.error('newPostModal was never initialized');
        return;
    }
    if (!isLoggedIn()) {           // ← from auth.js
        window.location.href = '/login';
        return;
    }

    document.getElementById('newTitle').value   = '';
    document.getElementById('newContent').value = '';
    document.getElementById('newPostError').classList.add('d-none');
    newPostModal.show();
}

async function saveNewPost() {
    const title    = document.getElementById('newTitle').value.trim();
    const content  = document.getElementById('newContent').value.trim();
    const errorDiv = document.getElementById('newPostError');

    if (!title || !content) {
        errorDiv.textContent = 'All fields are required.';
        errorDiv.classList.remove('d-none');
        return;
    }

    const res = await fetch('/api/posts', {
        method: 'POST',
        headers: authHeaders(),   // ← from auth.js
        body: JSON.stringify({ title, content })
    });

    if (res.ok) {
        const data = await res.json();
        newPostModal.hide();
        window.location.href = `/posts/${data.id}`;
    } else {
        const data = await res.json();
        errorDiv.textContent = data.detail || 'Failed to create post.';
        errorDiv.classList.remove('d-none');
    }
}


// ── 3. EDIT POST MODAL ────────────────────────
let editModal     = null;
let currentPostId = null;

function initEditModal() {
    const el = document.getElementById('editModal');
    if (!el) return;
    editModal = new bootstrap.Modal(el);
}

function openEditModal(id, title, content) {
    currentPostId = id;
    document.getElementById('editTitle').value   = title;
    document.getElementById('editContent').value = content;
    document.getElementById('editError').classList.add('d-none');
    editModal.show();
}

async function saveEdit() {
    const title    = document.getElementById('editTitle').value.trim();
    const content  = document.getElementById('editContent').value.trim();
    const errorDiv = document.getElementById('editError');

    if (!title || !content) {
        errorDiv.textContent = 'Title and content are required.';
        errorDiv.classList.remove('d-none');
        return;
    }

    const res = await fetch(`/api/posts/${currentPostId}`, {
        method: 'PATCH',
        headers: authHeaders(),   // ← from auth.js
        body: JSON.stringify({ title, content })
    });

    if (res.ok) {
        editModal.hide();
        location.reload();
    } else {
        const data = await res.json();
        errorDiv.textContent = data.detail || 'Failed to save.';
        errorDiv.classList.remove('d-none');
    }
}


// ── 4. DELETE POST ────────────────────────────
async function deletePost(id) {
    if (!confirm('Delete this post?')) return;

    const res = await fetch(`/api/posts/${id}`, {
        method: 'DELETE',
        headers: authHeaders()    // ← from auth.js
    });

    if (res.ok) {
        if (window.location.pathname.startsWith('/posts/')) {
            window.location.href = '/';
        } else {
            location.reload();
        }
    } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Failed to delete post.');
    }
}


// ── 5. INIT ON PAGE LOAD ──────────────────────
document.addEventListener('DOMContentLoaded', function () {
    initThemeToggle();
    initNewPostModal();
    initEditModal();
});