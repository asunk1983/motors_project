/**
 * API-клиент для frontend.
 * Централизует fetch-вызовы с обработкой токена, ошибок и JSON.
 */
window.Api = (function () {
    'use strict';

    const BASE = '/api';
    let token = localStorage.getItem('auth_token') || null;

    function setToken(t) {
        token = t;
        if (t) {
            localStorage.setItem('auth_token', t);
        } else {
            localStorage.removeItem('auth_token');
        }
    }

    function getToken() {
        return token;
    }

    function headers(extra) {
        const h = { 'Content-Type': 'application/json' };
        if (token) {
            h['Authorization'] = 'Bearer ' + token;
        }
        if (extra) {
            Object.assign(h, extra);
        }
        return h;
    }

    async function request(url, options) {
        const opts = Object.assign({ headers: headers() }, options);
        const resp = await fetch(BASE + url, opts);
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            const err = data.error || resp.statusText;
            const e = new Error(err);
            e.status = resp.status;
            e.data = data;
            throw e;
        }
        return data;
    }

    // --- Auth ---
    async function login(username, password) {
        const data = await request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
        setToken(data.token);
        return data;
    }

    async function logout() {
        await request('/auth/logout', { method: 'POST' });
        setToken(null);
    }

    async function me() {
        return request('/auth/me');
    }

    // --- Engines ---
    async function listEngines(params) {
        const q = new URLSearchParams(params || {}).toString();
        return request('/engines?' + q);
    }

    async function getEngine(id) {
        return request('/engine/' + id);
    }

    async function createEngine(data) {
        return request('/engine', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async function updateEngine(id, data) {
        return request('/engine/' + id, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async function deleteEngine(id) {
        return request('/engine/' + id, { method: 'DELETE' });
    }

    async function updateModes(id, modes) {
        return request('/engine/' + id + '/modes', {
            method: 'PUT',
            body: JSON.stringify({ modes }),
        });
    }

    async function updateWorks(id, works) {
        return request('/engine/' + id + '/works', {
            method: 'PUT',
            body: JSON.stringify({ works }),
        });
    }

    // --- Photos ---
    async function getPhotos(id) {
        return request('/engine/' + id + '/photos');
    }

    async function uploadPhotos(id, files) {
        const form = new FormData();
        files.forEach(f => form.append('photos', f));
        const resp = await fetch(BASE + '/engine/' + id + '/photos', {
            method: 'POST',
            headers: headers({}),
            body: form,
        });
        return resp.json();
    }

    async function deletePhoto(id, filename) {
        return request('/engine/' + id + '/photos/' + encodeURIComponent(filename), {
            method: 'DELETE',
        });
    }

    // --- Backup ---
    async function listBackups() {
        return request('/backup/list');
    }

    async function createBackup() {
        return request('/backup/create', { method: 'POST' });
    }

    async function inspectUpload(file) {
        const form = new FormData();
        form.append('file', file);
        const resp = await fetch(BASE + '/backup/inspect-upload', {
            method: 'POST',
            headers: headers({}),
            body: form,
        });
        return resp.json();
    }

    async function restoreBackup(filename) {
        return request('/backup/restore/' + encodeURIComponent(filename), {
            method: 'POST',
        });
    }

    async function confirmRestore(filename) {
        return request('/backup/confirm-restore', {
            method: 'POST',
            body: JSON.stringify({ filename }),
        });
    }

    async function downloadBackup(filename) {
        window.open(BASE + '/backup/download/' + encodeURIComponent(filename), '_blank');
    }

    async function deleteBackup(filename) {
        return request('/backup/delete/' + encodeURIComponent(filename), {
            method: 'POST',
        });
    }

    // --- Changelog / Wishlist ---
    async function getChangelog() {
        return request('/changelog');
    }

    async function createChangelogEntry(text, date) {
        return request('/changelog', {
            method: 'POST',
            body: JSON.stringify({ text, date }),
        });
    }

    async function deleteChangelogEntry(id) {
        return request('/changelog/' + id, { method: 'DELETE' });
    }

    async function getWishlist() {
        return request('/wishlist');
    }

    async function createWishlistItem(text) {
        return request('/wishlist', {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
    }

    async function updateWishlistItem(id, data) {
        return request('/wishlist/' + id, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async function deleteWishlistItem(id) {
        return request('/wishlist/' + id, { method: 'DELETE' });
    }

    return {
        setToken, getToken,
        login, logout, me,
        listEngines, getEngine, createEngine, updateEngine, deleteEngine,
        updateModes, updateWorks,
        getPhotos, uploadPhotos, deletePhoto,
        listBackups, createBackup, inspectUpload, restoreBackup,
        confirmRestore, downloadBackup, deleteBackup,
        getChangelog, createChangelogEntry, deleteChangelogEntry,
        getWishlist, createWishlistItem, updateWishlistItem, deleteWishlistItem,
    };
})();
