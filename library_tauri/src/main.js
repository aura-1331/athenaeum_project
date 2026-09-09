import "./assets/main.css"

import { createApp } from "vue"
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate' // 1. Import the plugin
import App from "./App.vue"
import router from "./router"
import axios from 'axios'
import { useAuthStore } from "./stores/auth.ts" // 2. Import your new store

axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const refreshClient = axios.create({
  baseURL: axios.defaults.baseURL
});

// --- SET UP VUE AND PINIA FIRST ---
// We have to create the app and pinia before Axios tries to use them
const app = createApp(App)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate) // 3. Turn on the automatic backup

// --- AXIOS INTERCEPTORS ---
axios.interceptors.request.use(
  (config) => {
    // 4. Axios asks Pinia for the data, instead of looking in localStorage
    const auth = useAuthStore(pinia) 
    
    if (auth.accessToken) {
      config.headers.Authorization = `Bearer ${auth.accessToken}`;
    }

    config.headers["X-User-Name"] = auth.userName;
    config.headers["X-User-Role"] = auth.userRole;

    return config;
  },
  (error) => Promise.reject(error)
);

axios.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;

    if (
      err.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/refresh")
    ) {
      originalRequest._retry = true;

      const auth = useAuthStore(pinia);
      const refresh = auth.refreshToken;

      if (!refresh) {
        auth.logout();
        router.push("/login");
        return Promise.reject(err);
      }

      try {
        const res = await refreshClient.post("/refresh", { refresh_token: refresh });
        const newToken = res.data.access_token;

        auth.accessToken = newToken;
        originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
        return axios(originalRequest);
      } catch (refreshError) {
        auth.logout();
        router.push("/login");
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(err);
  }
);

window.addEventListener("storage", (event) => {
  if (event.key === "logout") {
    const auth = useAuthStore(pinia);
    auth.logout();
    router.push("/login");
  }
});

app.use(pinia)
app.use(router)
app.mount("#app")