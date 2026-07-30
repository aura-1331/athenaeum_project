import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // -------------------------
  // 1. STATE (The Data)
  // -------------------------
  const accessToken = ref(null)
  const refreshToken = ref(null)
  const userName = ref("Archive Operator")
  const userRole = ref("The Seeker")

  // -------------------------
  // 2. GETTERS (Calculated)
  // -------------------------
  // Returns true if the user has an active token
  const isAuthenticated = computed(() => !!accessToken.value)

  // -------------------------
  // 3. ACTIONS (Functions)
  // -------------------------
  function login(tokens, user) {
    // Save tokens (adjust the keys depending on your exact backend response)
    accessToken.value = tokens.access_token || tokens.access
    refreshToken.value = tokens.refresh_token || tokens.refresh
    
    // Save user data
    userName.value = user.name || "Archive Operator"
    userRole.value = user.role || "The Seeker"
  }

  function logout() {
    // Wipe out the state in Pinia
    accessToken.value = null
    refreshToken.value = null
    userName.value = "Archive Operator"
    userRole.value = "The Seeker"
    
    // This triggers the cross-tab logout you set up in main.js
    localStorage.setItem("logout", Date.now().toString())
  }

  return { 
    accessToken, 
    refreshToken, 
    userName, 
    userRole, 
    isAuthenticated, 
    login, 
    logout 
  }
}, {
  // -------------------------
  // 4. PERSISTENCE MAGIC
  // -------------------------
  // This one line tells Pinia to automatically save this store to localStorage
  persist: true
})