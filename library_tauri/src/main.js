import { createApp } from "vue"
import { createPinia } from "pinia"
import piniaPluginPersistedstate from "pinia-plugin-persistedstate"
import axios from "axios"

import App from "./App.vue"
import router from "./router"

import { useAuthStore } from "./stores/auth"

import "./assets/main.css"

const app = createApp(App)

const pinia = createPinia()

pinia.use(piniaPluginPersistedstate)

app.use(pinia)

const auth = useAuthStore()

const API_BASE =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"

/*
 * Configure the main Axios client.
 *
 * All normal API requests such as:
 *   /dashboard/summary
 *   /catalogue/
 *   /status_audit/system-logs
 *
 * will now be sent to the backend API.
 */
axios.defaults.baseURL = API_BASE
axios.defaults.withCredentials = true

/*
 * Attach the short-lived access token to normal
 * authenticated API requests.
 *
 * The access token exists only in Pinia memory.
 * It is NOT stored in localStorage.
 */
axios.interceptors.request.use((config) => {
  const token = auth.accessToken

  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

/*
 * Separate Axios client for refresh operations.
 *
 * The refresh token is held by the browser in the
 * HttpOnly refresh_token cookie, so the frontend does
 * not read or store that token.
 */
const refreshClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true
})

let refreshPromise = null

/*
 * Restore an existing authenticated session when the
 * application starts.
 *
 * The short-lived access token is intentionally kept
 * only in Pinia memory.
 *
 * The refresh token remains inside the HttpOnly cookie.
 */
async function restoreSession() {
  const storedUser = localStorage.getItem("user")

  try {
    const response =
      await refreshClient.post("/auth/refresh")

    const newAccessToken =
      response.data?.access_token

    if (!newAccessToken) {
      throw new Error(
        "Refresh response did not contain an access token"
      )
    }

    /*
     * IMPORTANT:
     * Access token is memory-only.
     *
     * Do NOT write it to localStorage.
     */
    auth.accessToken = newAccessToken

    /*
     * Restore non-sensitive user identity information.
     */
    if (storedUser) {
      try {
        const userObj = JSON.parse(storedUser)

        auth.userId = String(
          userObj.id ||
          userObj.user_id ||
          userObj.operator_id ||
          "USR-01"
        )

        auth.userName =
          userObj.name ||
          userObj.username ||
          "Archive Operator"

        auth.userRole =
          userObj.role ||
          userObj.user_role ||
          "The Seeker"

      } catch (error) {
        console.warn(
          "Could not restore persisted user:",
          error
        )
      }
    }

    console.info(
      "Authentication session restored"
    )

  } catch (error) {
    /*
     * No valid refresh session exists.
     *
     * Clear in-memory authentication state and remove
     * any legacy access-token values left by older versions.
     */
    auth.accessToken = null
    auth.refreshToken = null

    localStorage.removeItem("access_token")
    localStorage.removeItem("token")
    localStorage.removeItem("user")

    console.info(
      "No active authentication session found"
    )
  }
}

/*
 * Retry one authenticated request after an expired access token is
 * refreshed. Concurrent 401 responses share the same refresh operation.
 */
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._authRetry ||
      String(originalRequest.url || "").includes("/auth/refresh")
    ) {
      return Promise.reject(error)
    }

    originalRequest._authRetry = true

    try {
      if (!refreshPromise) {
        refreshPromise = restoreSession().finally(() => {
          refreshPromise = null
        })
      }

      await refreshPromise

      if (!auth.accessToken) {
        return Promise.reject(error)
      }

      originalRequest.headers = originalRequest.headers || {}
      originalRequest.headers.Authorization = `Bearer ${auth.accessToken}`

      return axios(originalRequest)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  }
)

/*
 * Restore authentication before mounting the application.
 *
 * We deliberately do not use top-level await because
 * the current Vite build target does not support it.
 */
restoreSession().finally(() => {
  app.use(router)
  app.mount("#app")
})