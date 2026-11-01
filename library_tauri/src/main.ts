
import { createApp } from "vue"
import { createPinia } from "pinia"
import piniaPluginPersistedstate from "pinia-plugin-persistedstate"
import axios, {
  type InternalAxiosRequestConfig,
  type AxiosError,
} from "axios"

import App from "./App.vue"
import router from "./router/index.ts"

import { useAuthStore } from "./stores/auth.ts"

import "./assets/main.css"

const app = createApp(App)

const pinia = createPinia()

pinia.use(piniaPluginPersistedstate)

app.use(pinia)

const auth = useAuthStore()

const API_BASE =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"

// -------------------------
// CSRF
// -------------------------

function getCsrfToken(): string | null {
  const stored = localStorage.getItem("csrf_token")

  if (stored) {
    return stored
  }

  const match = document.cookie.match(
    /(?:^|;\s*)csrf_token=([^;]*)/
  )

  return match
    ? decodeURIComponent(match[1])
    : null
}

// -------------------------
// API CONFIGURATION
// -------------------------

axios.defaults.baseURL = API_BASE
axios.defaults.withCredentials = true

// -------------------------
// CHECK API REQUEST DESTINATION
// -------------------------

function isRequestToOurApi(
  config: InternalAxiosRequestConfig
): boolean {
  const url = String(config.url || "")

  if (/^https?:\/\//i.test(url)) {
    return url.startsWith(API_BASE)
  }

  const base = String(config.baseURL || API_BASE)

  return base.startsWith(API_BASE)
}

// -------------------------
// REQUEST INTERCEPTOR
// -------------------------

axios.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = auth.accessToken

    if (token && isRequestToOurApi(config)) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  }
)

// -------------------------
// REFRESH CLIENT
// -------------------------

const refreshClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

let refreshPromise: Promise<void> | null = null

// -------------------------
// RESTORE SESSION
// -------------------------

async function restoreSession(): Promise<void> {
  const storedUser = localStorage.getItem("user")

  try {
    const csrfToken = getCsrfToken()

    const response = await refreshClient.post(
      "/auth/refresh",
      null,
      {
        headers: csrfToken
          ? {
              "X-CSRF-Token": csrfToken,
            }
          : {},
      }
    )

    const newAccessToken: string | undefined =
      response.data?.access_token

    if (!newAccessToken) {
      throw new Error(
        "Refresh response did not contain an access token"
      )
    }

    // Access token remains memory-only.
    auth.accessToken = newAccessToken

    // Restore non-sensitive user information.
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
    // Clear authentication state.
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

// -------------------------
// RESPONSE INTERCEPTOR
// -------------------------

axios.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & {
          _authRetry?: boolean
        })
      | undefined

    const status = error.response?.status

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._authRetry ||
      String(originalRequest.url || "").includes(
        "/auth/refresh"
      )
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

      originalRequest.headers =
        originalRequest.headers || {}

      originalRequest.headers.Authorization =
        `Bearer ${auth.accessToken}`

      return axios(originalRequest)

    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  }
)

// -------------------------
// START APPLICATION
// -------------------------

restoreSession().finally(() => {
  app.use(router)
  app.mount("#app")
})
