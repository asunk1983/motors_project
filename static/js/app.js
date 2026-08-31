/**
 * Точка входа frontend-приложения.
 * Инициализирует State, Api, и делает их доступными глобально.
 */
window.App = (function () {
    'use strict';

    const api = window.Api;
    const state = window.State;

    // Проверяем токен при загрузке
    async function init() {
        try {
            const user = await api.me();
            state.set('user', user);
        } catch (e) {
            state.set('user', null);
        }
    }

    // Глобальный обработчик ошибок
    function handleError(err) {
        console.error(err);
        state.set('error', err.message || 'Произошла ошибка');
        setTimeout(() => state.set('error', null), 5000);
    }

    // Загрузка списка двигателей
    async function loadEngines() {
        state.set('isLoading', true);
        try {
            const params = {
                limit: state.get('pageSize'),
                offset: (state.get('currentPage') - 1) * state.get('pageSize'),
                sort: state.get('sort'),
                search_field: state.get('searchField'),
                search_query: state.get('searchQuery'),
            };
            const data = await api.listEngines(params);
            state.set('engines', data.engines || []);
            state.set('totalEngines', data.total || 0);
        } catch (e) {
            handleError(e);
        } finally {
            state.set('isLoading', false);
        }
    }

    // Загрузка бэкапов
    async function loadBackups() {
        try {
            const backups = await api.listBackups();
            state.set('backups', backups);
        } catch (e) {
            handleError(e);
        }
    }

    // Загрузка changelog
    async function loadChangelog() {
        try {
            const entries = await api.getChangelog();
            state.set('changelog', entries);
        } catch (e) {
            handleError(e);
        }
    }

    // Загрузка wishlist
    async function loadWishlist() {
        try {
            const items = await api.getWishlist();
            state.set('wishlist', items);
        } catch (e) {
            handleError(e);
        }
    }

    return {
        init,
        api,
        state,
        handleError,
        loadEngines,
        loadBackups,
        loadChangelog,
        loadWishlist,
    };
})();

// Авто-инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    window.App.init();
});
