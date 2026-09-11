<template>
  <div class="login-wrapper">
    <div class="layout-container">

      <div class="brand-panel">
        <div class="scan-overlay"></div>

        <div class="brand-content">
          <div class="node-badge">
            <div class="pulse-dot"></div>
            <span>Athenaeum Archive Network</span>
          </div>

          <h2 class="brand-title">
            Institutional Memory Access
          </h2>

          <p class="brand-subtitle" v-if="currentStep === 1">
            Mapping identity credentials...
          </p>

          <p class="brand-subtitle" v-if="currentStep === 2">
            Identity verified. Credential verification in progress.
          </p>

          <p class="brand-subtitle" v-if="currentStep === 3">
            Secondary verification required.
          </p>
        </div>
      </div>

      <div class="form-panel">
        <div class="form-content">

          <div class="panel-header">
            <div class="terminal-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>

            <h1>Secure Access</h1>

            <p v-if="currentStep === 1">
              Enter your archive identity code
            </p>

            <p v-if="currentStep === 2">
              Enter your password
            </p>

            <p v-if="currentStep === 3">
              Enter verification code
            </p>
          </div>

          <!-- STEP 1: IDENTITY -->
          <form v-if="currentStep === 1" @submit.prevent="verifyIdentity">
            <div class="input-group">
              <label>Archive Identity</label>

              <div class="input-shell">
                <span class="input-prefix">ATH</span>
                <input
                  v-model="identityDigits"
                  @input="handleIdentityInput"
                  type="text"
                  required
                  maxlength="5"
                  placeholder="•••••"
                  autocomplete="off"
                  style="text-transform: uppercase;"
                />
              </div>
            </div>  
            <button class="action-btn" type="submit" :disabled="loading">
              {{ loading ? 'Verifying...' : 'Continue' }}
            </button>
          </form>

          <!-- STEP 2: PASSWORD -->
          <form v-if="currentStep === 2" @submit.prevent="verifyPassword">
            <div class="input-group">
              <label>Password</label>

              <div class="password-wrapper">
                <input
                  v-model="passkey"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="••••••••"
                />

                <button
                  type="button"
                  class="toggle-password"
                  @click="showPassword = !showPassword"
                >
                  <svg
                    v-if="!showPassword"
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>

                  <svg
                    v-else
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C5 20 1 12 1 12a21.77 21.77 0 0 1 5.06-6.94"/>
                    <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a21.77 21.77 0 0 1-2.16 3.19"/>
                    <path d="M1 1l22 22"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="remember-row">
              <label class="remember-label">
                <input type="checkbox" v-model="rememberMe" />
                <span>Remember this terminal</span>
              </label>
            </div>

            <button class="action-btn" type="submit" :disabled="loading">
              {{ loading ? 'Authenticating...' : 'Verify Password' }}
            </button>

            <button
              type="button"
              class="back-btn"
              @click="currentStep = 1; passkey = ''; errorMessage = ''"
              :disabled="loading"
            >
              ← Change Operator ID
            </button>
          </form>

          <!-- STEP 3: 2FA TOKEN -->
          <form v-if="currentStep === 3" @submit.prevent="verifyTwoFA">
            <div class="input-group">
              <label>2FA Token (Authenticator App)</label>

              <input
                v-model="tokenPin"
                type="text"
                required
                maxlength="6"
                placeholder="000000"
                inputmode="numeric"
                pattern="[0-9]*"
                autocomplete="one-time-code"
                autofocus
              />
            </div>

            <button class="action-btn" type="submit" :disabled="loading || tokenPin.length !== 6">
              {{ loading ? 'Verifying...' : 'Verify Code' }}
            </button>

            <button
              type="button"
              class="back-btn"
              @click="currentStep = 2; tokenPin = ''; errorMessage = ''"
              :disabled="loading"
            >
              ← Back to Password
            </button>
          </form>

          <p v-if="errorMessage" class="error-message">
            {{ errorMessage }}
          </p>

        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const currentStep = ref(1)

const identityDigits = ref('')
const fullOperatorId = ref('')
const passkey = ref('')
const tokenPin = ref('')
const temp2faToken = ref('')

const loading = ref(false)
const errorMessage = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)

const handleIdentityInput = () => {
  identityDigits.value = identityDigits.value
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 5)
}

// --- STEP 1: IDENTITY ---
const verifyIdentity = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    fullOperatorId.value = `ATH${identityDigits.value}`

    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    const response = await fetch(`${baseUrl}/auth/check-identity`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        identity_code: identityDigits.value
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(
        errorData.detail || 'Unable to verify identity'
      )
    }

    currentStep.value = 2

  } catch (error) {
    console.error(error)
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

// --- STEP 2: PASSWORD ---
const verifyPassword = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const formData = new URLSearchParams()
    formData.append('username', fullOperatorId.value)
    formData.append('password', passkey.value)
    formData.append('remember_me', String(rememberMe.value))

    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    const response = await fetch(`${baseUrl}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: formData
    })

    const data = await response.json()

    if (!response.ok) {
      if (data.detail === '2FA verification required') {
        currentStep.value = 3
        return
      }
      throw new Error(data.detail || 'Authentication failed')
    }

    // Intercept 2FA challenge response
    if (data.twofa_required) {
      temp2faToken.value = data.temp_token
      currentStep.value = 3
      return
    }

    const token = data.access_token || data.access || data.token
    
    if (!token) {
      throw new Error("Backend did not return a valid token. Check the console log.")
    }

    await authStore.login(
      {
        access_token: token,
        refresh_token: data.refresh_token
      },
      {
        id: data.user_id || data.operator_id,
        user_id: data.user_id,
        operator_id: data.operator_id,
        name: data.user_name || data.username || "Archive Operator",
        role: data.role || data.user_role || "The Seeker"
      }
    )

    router.push('/dashboard')

  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

// --- STEP 3: 2FA VERIFICATION ---
const verifyTwoFA = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    let response
    let data

    if (temp2faToken.value) {
      response = await fetch(`${baseUrl}/login/verify-2fa`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          temp_token: temp2faToken.value,
          totp_code: tokenPin.value.trim(),
          remember_me: rememberMe.value
        })
      })
      data = await response.json()
    } else {
      // Fallback for direct token authentication
      const formData = new URLSearchParams()
      formData.append('username', fullOperatorId.value)
      formData.append('password', passkey.value)
      formData.append('remember_me', String(rememberMe.value))
      formData.append('otp_code', tokenPin.value.trim())

      response = await fetch(`${baseUrl}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      })
      data = await response.json()
    }

    if (!response.ok) {
      throw new Error(data.detail || '2FA verification failed')
    }

    const token = data.access_token || data.access || data.token
    
    if (!token) {
      throw new Error("Backend did not return a valid token after 2FA.")
    }

    await authStore.login(
      { 
        access_token: token, 
        refresh_token: data.refresh_token 
      },
      { 
        id: data.user_id || data.operator_id,
        user_id: data.user_id,
        operator_id: data.operator_id,
        name: data.user_name || data.username || "Archive Operator", 
        role: data.role || data.user_role || "The Seeker" 
      }
    )

    router.push('/dashboard')

  } catch (error) {
    errorMessage.value = error.message
    tokenPin.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: monospace;
}

.login-wrapper {
  min-height: 100vh;
  background: #020205;
}

.layout-container {
  display: flex;
  min-height: 100vh;
}

/* LEFT PANEL */
.brand-panel {
  flex: 1;
  position: relative;
  background: #05050a;
  border-right: 1px solid #111;
  display: flex;
  align-items: center;
  padding: 60px;
  overflow: hidden;
}

.scan-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    transparent,
    rgba(99,102,241,0.12),
    transparent
  );
  animation: scanMove 5s linear infinite;
}

@keyframes scanMove {
  0% {
    transform: translateY(-100%);
  }
  100% {
    transform: translateY(100%);
  }
}

.brand-content {
  position: relative;
  z-index: 2;
}

.node-badge {
  display: inline-flex;
  gap: 10px;
  margin-bottom: 20px;
  color: #818cf8;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: #6366f1;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.5);
    opacity: 0.5;
  }
}

.brand-title {
  color: white;
  font-size: 30px;
  margin-bottom: 15px;
}

.brand-subtitle {
  color: gray;
  margin-bottom: 30px;
}

/* RIGHT PANEL */
.form-panel {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #07070f;
}

.form-content {
  width: 100%;
  max-width: 400px;
}

.panel-header h1 {
  color: white;
  margin-bottom: 10px;
}

.panel-header p {
  color: gray;
  margin-bottom: 30px;
}

.input-group {
  margin-bottom: 20px;
}

.input-group label {
  display: block;
  color: #aaa;
  margin-bottom: 8px;
}

.input-group input {
  width: 100%;
  padding: 14px;
  background: #0b0b16;
  border: 1px solid #222;
  color: white;
  border-radius: 6px;
  outline: none;
}

.input-group input:focus {
  border-color: #6366f1;
}

.action-btn {
  width: 100%;
  padding: 14px;
  background: #4f46e5;
  color: white;
  border: none;
  cursor: pointer;
  border-radius: 6px;
  font-weight: bold;
}

.action-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.back-btn {
  width: 100%;
  padding: 10px;
  background: transparent;
  color: #666;
  border: none;
  margin-top: 12px;
  cursor: pointer;
  font-size: 13px;
  transition: color 0.2s;
}

.back-btn:hover:not(:disabled) {
  color: #aaa;
}

.back-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  color: #ef4444;
  margin-top: 20px;
  font-size: 14px;
}

.terminal-icon {
  width: 64px;
  height: 64px;
  background: #111122;
  border: 1px solid #222244;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 25px;
  overflow: hidden;
}

.terminal-icon svg {
  width: 28px;
  height: 28px;
  stroke: #818cf8;
  display: block;
}

.input-shell {
  display: flex;
  align-items: center;
  width: 100%;
  background: #0b0b16;
  border: 1px solid #222;
  border-radius: 6px;
  padding: 0 14px;
}

.input-shell:focus-within {
  border-color: #6366f1;
}

.input-prefix {
  color: rgba(16, 173, 194, 0.45);
  letter-spacing: 2px;
  font-weight: normal;
  margin-right: 2px;
  font-size: 15px;
}

.input-shell input {
  flex: 1;
  background: transparent;
  border: none;
  color: white;
  padding: 14px 0;
  outline: none;
  font-size: 15px;
  letter-spacing: 2px;
}

.remember-row {
  margin-bottom: 20px;
}

.remember-label {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #777;
  font-size: 13px;
  cursor: pointer;
}

.remember-label input {
  accent-color: #6366f1;
}

.password-wrapper {
  position: relative;
}

.password-wrapper input {
  width: 100%;
  padding: 14px;
  padding-right: 50px;
  background: #0b0b16;
  border: 1px solid #222;
  color: white;
  border-radius: 6px;
  outline: none;
}

.password-wrapper input:focus {
  border-color: #6366f1;
}

.toggle-password {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-password:hover {
  color: #aaa;
}

@media (max-width: 900px) {
  .brand-panel {
    display: none;
  }
}
</style>