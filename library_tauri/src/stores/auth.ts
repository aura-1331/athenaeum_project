import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// @ts-ignore
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // -------------------------
  // 1. STATE (The Data)
  // -------------------------
  const accessToken = ref<string | null>(null)
  
  const access_token = computed({
    get: () => accessToken.value,
    set: (val) => { accessToken.value = val }
  })

  const refreshToken = ref<string | null>(null)
  const userId = ref<string>("USR-01")
  const userName = ref<string>("Archive Operator")
  const userRole = ref<string>("The Seeker")

  // -------------------------
  // 2. GETTERS
  // -------------------------
  const isAuthenticated = computed(() => !!accessToken.value)

  // -------------------------
  // 3. ACTIONS
  // -------------------------
  function login(tokens: any, user: any) {
    accessToken.value = tokens.access_token || tokens.access
    refreshToken.value = tokens.refresh_token || tokens.refresh
    userId.value = user.id || user.user_id || "USR-01"
    userName.value = user.name || user.username || "Archive Operator"
    userRole.value = user.role || "The Seeker"
  }

  async function logout() {
    const token = accessToken.value
    const sessionId = localStorage.getItem('active_session_id')
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

    // 1. Dispatch logout telemetry to backend
    if (token) {
      try {
        await fetch(`${baseUrl}/status_audit/session/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
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
    localStorage.setItem("logout", Date.now().toString())

    // 3. Immediately redirect to the login screen
    await router.push('/login')
  }

  return { 
    accessToken, 
    access_token, 
    refreshToken, 
    userId,
    userName, 
    userRole, 
    isAuthenticated, 
    login, 
    logout 
  }
}, {
  // @ts-ignore
  persist: true
})