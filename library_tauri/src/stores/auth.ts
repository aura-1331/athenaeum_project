import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// @ts-ignore
import router from '@/router'

export interface UserSession {
  id?: string | number
  user_id?: string | number
  operator_id?: string
  operatorId?: string
  name?: string
  username?: string
  role?: string
  [key: string]: any
}

export interface TokenPayload {
  access_token?: string
  access?: string
  refresh_token?: string
  refresh?: string
  [key: string]: any
}

export const useAuthStore = defineStore('auth', () => {
  // -------------------------
  // 1. STATE
  // -------------------------
  const accessToken = ref<string | null>(localStorage.getItem('access_token') || null)
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token') || null)
  const userId = ref<string>("USR-01")
  const userName = ref<string>("Archive Operator")
  const userRole = ref<string>("The Seeker")

  // Computed access_token compatibility alias
  const access_token = computed({
    get: () => accessToken.value,
    set: (val: string | null) => { accessToken.value = val }
  })

  // Backward/forward compatibility aliases
  const token = computed(() => accessToken.value || '')
  const role = computed(() => userRole.value)
  const user = computed(() => ({
    id: userId.value,
    user_id: userId.value,
    name: userName.value,
    role: userRole.value
  }))

  // -------------------------
  // 2. GETTERS
  // -------------------------
  const isAuthenticated = computed(() => !!accessToken.value)

  // -------------------------
  // 3. ACTIONS
  // -------------------------
  function login(tokens: any, userObj?: any) {
    const rawToken = typeof tokens === 'string' 
      ? tokens 
      : (tokens?.access_token || tokens?.access || null)

    const rawRefresh = typeof tokens === 'object'
      ? (tokens?.refresh_token || tokens?.refresh || null)
      : null

    accessToken.value = rawToken
    refreshToken.value = rawRefresh

    if (rawToken) {
      localStorage.setItem('access_token', rawToken)
      localStorage.setItem('token', rawToken)
    }

    if (rawRefresh) {
      localStorage.setItem('refresh_token', rawRefresh)
    }

    if (userObj) {
      userId.value = String(userObj.id || userObj.user_id || userObj.operator_id || "USR-01")
      userName.value = userObj.name || userObj.username || "Archive Operator"
      userRole.value = userObj.role || userObj.user_role || "The Seeker"
      localStorage.setItem('user', JSON.stringify(userObj))
    }
  }

  async function logout() {
    const tokenVal = accessToken.value
    const sessionId = localStorage.getItem('active_session_id')
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

    // 1. Dispatch logout telemetry to backend
    if (tokenVal) {
      try {
        await fetch(`${baseUrl}/status_audit/session/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${tokenVal}`
          },
          body: JSON.stringify({
            session_id: sessionId || null,
            user_id: userId.value,
            username: userName.value,
            role: userRole.value,
            reason: 'Operator initiated sign-out'
          })
        })
      } catch (err) {
        console.warn('Could not record logout audit event:', err)
      }
    }

    // 2. Reset Pinia State & clean up storage
    accessToken.value = null
    refreshToken.value = null
    userId.value = "USR-01"
    userName.value = "Archive Operator"
    userRole.value = "The Seeker"

    localStorage.removeItem('active_session_id')
    localStorage.removeItem('access_token')
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.setItem("logout", Date.now().toString())

    // 3. Redirect to login screen
    if (router) {
      await router.push('/login')
    }
  }

  return {
    accessToken,
    access_token,
    refreshToken,
    userId,
    userName,
    userRole,
    isAuthenticated,
    token,
    role,
    user,
    login,
    logout
  }
}, {
  // @ts-ignore
  persist: true
})