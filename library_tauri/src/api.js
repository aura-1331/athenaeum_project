const BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Helper to build standard headers with telemetry & auth
function getHeaders(extraHeaders = {}) {
  const token = localStorage.getItem("access_token");
  const machineName = localStorage.getItem("terminal_machine") || "TERMINAL-01";
  const sessionId = localStorage.getItem("active_session_id") || "";

  const headers = {
    "Content-Type": "application/json",
    "X-Machine-Name": machineName,
    "X-Session-Id": sessionId,
    ...extraHeaders
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

export const api = {
  async get(endpoint, customHeaders = {}) {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "GET",
      headers: getHeaders(customHeaders)
    });

    if (!res.ok) throw await res.json();
    return res.json();
  },

  async post(endpoint, body, customHeaders = {}) {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers: getHeaders(customHeaders),
      body: JSON.stringify(body)
    });

    if (!res.ok) throw await res.json();
    return res.json();
  },

  async patch(endpoint, body, customHeaders = {}) {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "PATCH",
      headers: getHeaders(customHeaders),
      body: JSON.stringify(body)
    });

    if (!res.ok) throw await res.json();
    return res.json();
  },

  async delete(endpoint, customHeaders = {}) {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers: getHeaders(customHeaders)
    });

    if (!res.ok) throw await res.json();
    return res.json();
  }
};