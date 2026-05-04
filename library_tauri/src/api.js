const BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const api = {
  async get(endpoint) {
    const res = await fetch(`${BASE_URL}${endpoint}`);
    return res.json();
  },

  async post(endpoint, body) {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) throw await res.json();

    return res.json();
  }
};