// Phase 10.9: API client for the Zoey backend.
//
// Talks to the local FastAPI server (proxied through Vite in dev).
// The backend response envelope is { ok: true, data } or an HTTP error
// with { detail } / { error }. Mutating actions (approve, reject,
// execute, cancel) are distinct endpoints; approval never starts
// execution and rejection never executes.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (!res.ok) {
    const detail = (body && (body.detail || body.error)) || `Request failed (${res.status})`;
    throw new Error(detail);
  }

  return body;
}

export const api = {
  // Chat
  async chat(message) {
    return request("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },

  // Plan / execution lifecycle (all separate, matching the backend)
  async status() {
    return request("/status");
  },
  async approvePlan() {
    return request("/plans/approve", { method: "POST" });
  },
  async rejectPlan() {
    return request("/plans/reject", { method: "POST" });
  },
  async executePlan() {
    return request("/execution/execute", { method: "POST" });
  },
  async cancelExecution() {
    return request("/execution/cancel", { method: "POST" });
  },
  async plans() {
    return request("/plans/list");
  },

  // Read-only Phase 10 panels
  async tasks(status) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    return request(`/tasks${params.toString() ? `?${params}` : ""}`);
  },
  async events(limit = 20) {
    return request(`/events?limit=${limit}`);
  },
  async memories(memoryType, limit = 20) {
    const params = new URLSearchParams();
    if (memoryType) params.set("memory_type", memoryType);
    params.set("limit", limit);
    return request(`/memories?${params}`);
  },
  async files(path = ".") {
    return request(`/files?path=${encodeURIComponent(path)}`);
  },
  async fileContent(path) {
    return request(`/files/content?path=${encodeURIComponent(path)}`);
  },
  async notifications(limit = 20) {
    return request(`/notifications?limit=${limit}`);
  },
  async apps() {
    return request("/apps");
  },
};
