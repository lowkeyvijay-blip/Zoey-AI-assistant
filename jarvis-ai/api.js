/* ===========================
   J.A.R.V.I.S. v4 — Zoey Backend API Client
   Phase 10.9 integration.
   =========================== */

(function (global) {
    'use strict';

    // Same-origin with the FastAPI server that also serves this page.
    // Response envelope: { ok: true, data } or an HTTP error body
    // carrying { detail } / { error }. Mutating lifecycle actions
    // (approve, reject, execute, cancel) are distinct endpoints and
    // approval never starts execution.
    const BASE = '/api';

    async function request(path, options) {
        const res = await fetch(BASE + path, {
            headers: { 'Content-Type': 'application/json' },
            ...(options || {}),
        });

        let body = null;
        try {
            body = await res.json();
        } catch (e) {
            body = null;
        }

        if (!res.ok) {
            const detail = (body && (body.detail || body.error)) || 'Request failed (' + res.status + ')';
            throw new Error(detail);
        }

        return body;
    }

    const JarvisAPI = {
        // Health / connectivity
        async health() {
            return request('/health');
        },

        // Chat
        async chat(message) {
            return request('/chat', {
                method: 'POST',
                body: JSON.stringify({ message: message }),
            });
        },

        // Plan / execution lifecycle (all separate, matching the backend)
        async status() {
            return request('/status');
        },
        async approvePlan() {
            return request('/plans/approve', { method: 'POST' });
        },
        async rejectPlan() {
            return request('/plans/reject', { method: 'POST' });
        },
        async executePlan() {
            return request('/execution/execute', { method: 'POST' });
        },
        async cancelExecution() {
            return request('/execution/cancel', { method: 'POST' });
        },
        async plans() {
            return request('/plans/list');
        },

        // Read-only Phase 10 resources
        async tasks(status) {
            const params = new URLSearchParams();
            if (status) params.set('status', status);
            const qs = params.toString();
            return request('/tasks' + (qs ? '?' + qs : ''));
        },
        async events(limit) {
            limit = limit === undefined ? 20 : limit;
            return request('/events?limit=' + encodeURIComponent(limit));
        },
        async memories(memoryType, limit) {
            limit = limit === undefined ? 20 : limit;
            const params = new URLSearchParams();
            if (memoryType) params.set('memory_type', memoryType);
            params.set('limit', limit);
            return request('/memories?' + params.toString());
        },
        async files(path) {
            path = path === undefined ? '.' : path;
            return request('/files?path=' + encodeURIComponent(path));
        },
        async fileContent(path) {
            return request('/files/content?path=' + encodeURIComponent(path));
        },
        async notifications(limit) {
            limit = limit === undefined ? 20 : limit;
            return request('/notifications?limit=' + encodeURIComponent(limit));
        },
        async apps() {
            return request('/apps');
        },
    };

    global.JarvisAPI = JarvisAPI;
})(window);
