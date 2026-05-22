import "./assets/main.css"

import { createApp } from "vue"
import { createPinia } from 'pinia'
import App from "./App.vue"
import router from "./router"
import axios from 'axios'

axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const refreshClient = axios.create({
  baseURL: axios.defaults.baseURL
});

axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

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
      const refresh = localStorage.getItem("refresh_token") || sessionStorage.getItem("refresh_token");

      if (!refresh) {
        localStorage.clear();
        sessionStorage.clear();
        localStorage.setItem("logout", Date.now());
        window.location.href = "/login";
        return;
      }

      try {
        const res = await refreshClient.post("/refresh", { refresh_token: refresh });
        const newToken = res.data.access_token;

        if (localStorage.getItem("refresh_token")) {
          localStorage.setItem("access_token", newToken);
        } else {
          sessionStorage.setItem("access_token", newToken);
        }

        err.config.headers["Authorization"] = `Bearer ${newToken}`;
        return axios(err.config);
      } catch (refreshError) {
        localStorage.clear();
        sessionStorage.clear();
        localStorage.setItem("logout", Date.now());
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

window.addEventListener("storage", (event) => {
  if (event.key === "logout") {
    sessionStorage.clear();
    window.location.href = "/login";
  }
});

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount("#app")