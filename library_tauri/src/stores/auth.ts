import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // -------------------------
  // 1. STATE (The Data)
  // -------------------------
  const accessToken = ref<string | null>(null)
  
  // Computed alias to satisfy components looking for the underscore version
  const access_token = computed({
    get: () => accessToken.value,
    set: (val) => { accessToken.value = val }
  })

  const refreshToken = ref<string | null>(null)
  const userName = ref("Archive Operator")
  const userRole = ref("The Seeker")

  // -------------------------
  // 2. GETTERS (Calculated)
  // -------------------------
  const isAuthenticated = computed(() => !!accessToken.value)

  // -------------------------
  // 3. ACTIONS (Functions)
  // -------------------------
  function login(tokens: any, user: any) {
    accessToken.value = tokens.access_token || tokens.access
    refreshToken.value = tokens.refresh_token || tokens.refresh
    
    userName.value = user.name || "Archive Operator"
    userRole.value = user.role || "The Seeker"
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    userName.value = "Archive Operator"
    userRole.value = "The Seeker"
    
    localStorage.setItem("logout", Date.now().toString())
  }

  return { 
    accessToken, 
    access_token, 
    refreshToken, 
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