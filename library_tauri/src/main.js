import "./assets/main.css"
import { createApp } from "vue"
import { createPinia } from 'pinia'
import App from "./App.vue"
import router from "./router"
import axios from 'axios'

// 🛡️ 1. CONFIGURE GLOBAL AXIOS
axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';


// 🛡️ REQUEST INTERCEPTOR (attach token)
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);


// 🔄 Separate axios for refresh (no loop)
const refreshClient = axios.create({
  baseURL: axios.defaults.baseURL
});


// 🔁 RESPONSE INTERCEPTOR (auto refresh + retry)
axios.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (
      err.response?.status === 401 &&
      err.config &&
      !err.config._retry &&
      !err.config.url.includes("/refresh")
    ) {
      err.config._retry = true;

      const refresh = localStorage.getItem("refresh_token");

      // ❌ No refresh token → logout
      if (!refresh) {
        localStorage.clear();
        localStorage.setItem("logout", Date.now());
        window.location.href = "/login";
        return;
      }

      try {
        // 🔄 get new access token
        const res = await refreshClient.post("/refresh", {
          refresh_token: refresh
        });

        const newToken = res.data.access_token;

        // 💾 store new token
        localStorage.setItem("token", newToken);

        // 🔥 update global axios header
        axios.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;

        // 🔁 retry original request
        err.config.headers["Authorization"] = `Bearer ${newToken}`;
        return axios(err.config);

      } catch (refreshError) {
        // ❌ refresh failed → logout everywhere
        localStorage.clear();
        localStorage.setItem("logout", Date.now());
        window.location.href = "/login";
      }
    }

    return Promise.reject(err);
  }
);


// 🔔 SYNC LOGOUT ACROSS TABS
window.addEventListener("storage", (event) => {
  if (event.key === "logout") {
    window.location.href = "/login";
  }
});


// 🚀 INITIALIZE APP
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount("#app")