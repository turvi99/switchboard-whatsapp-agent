// Thin wrapper around fetch for the Switchboard dashboard API.
// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.js).
// In production, the backend serves the built frontend itself, so relative
// paths resolve correctly without any base URL configuration.

class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : null;
  if (!res.ok) {
    const message = body?.detail || `Request failed (${res.status})`;
    throw new ApiError(message, res.status, body);
  }
  return body;
}

export const api = {
  listTenants: () => request("/tenants"),
  getTenant: (tenantId) => request(`/tenants/${tenantId}`),
  getTenantStats: (tenantId) => request(`/tenants/${tenantId}/stats`),
  listSessions: (tenantId, status) =>
    request(`/tenants/${tenantId}/sessions${status ? `?status=${status}` : ""}`),
  listMessages: (tenantId, sessionId) =>
    request(`/tenants/${tenantId}/sessions/${sessionId}/messages`),
  broadcast: (tenantId, payload) =>
    request(`/tenants/${tenantId}/broadcast`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  simulateInbound: (payload) =>
    request(`/simulate/inbound`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export { ApiError };
