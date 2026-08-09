/**
 * State management для frontend.
 * Простой reactive store на основе событий.
 */
window.State = (function () {
    'use strict';

    const listeners = {};
    const state = {
        engines: [],
        totalEngines: 0,
        currentEngine: null,
        filters: {},
        sort: 'location_asc',
        currentPage: 1,
        pageSize: 30,
        searchQuery: '',
        searchField: 'all',
        user: null,
        backups: [],
        changelog: [],
        wishlist: [],
        isLoading: false,
        error: null,
    };

    function get(key) {
        return key ? state[key] : { ...state };
    }

    function set(key, value) {
        const old = state[key];
        state[key] = value;
        if (old !== value) {
            (listeners[key] || []).forEach(fn => fn(value, old));
        }
    }

    function subscribe(key, fn) {
        if (!listeners[key]) listeners[key] = [];
        listeners[key].push(fn);
        return () => {
            listeners[key] = listeners[key].filter(f => f !== fn);
        };
    }

    function reset() {
        Object.keys(state).forEach(k => {
            if (k !== 'user') {
                state[k] = Array.isArray(state[k]) ? [] :
                           k === 'isLoading' ? false :
                           k === 'error' ? null :
                           typeof state[k] === 'object' && state[k] !== null ? {} :
                           state[k];
            }
        });
    }

    return { get, set, subscribe, reset };
})();
