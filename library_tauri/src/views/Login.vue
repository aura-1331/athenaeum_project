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
                  placeholder="00000"
                />

              </div>
            </div>  
            <button class="action-btn" type="submit" :disabled="loading">
              {{ loading ? 'Verifying...' : 'Continue' }}
            </button>
          </form>

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
          </form>

          <form v-if="currentStep === 3" @submit.prevent="verifyTwoFA">

            <div class="input-group">
              <label>2FA Token</label>

              <input
                v-model="tokenPin"
                type="text"
                required
                placeholder="000000"
              />
            </div>

            <button class="action-btn" type="submit" :disabled="loading">
              {{ loading ? 'Verifying...' : 'Verify Code' }}
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
const router = useRouter()

const currentStep = ref(1)

const identityDigits = ref('')
const fullOperatorId = ref('')
const passkey = ref('')
const tokenPin = ref('')

const loading = ref(false)
const errorMessage = ref('')

const handleIdentityInput = () => {
  identityDigits.value = identityDigits.value
    .replace(/\D/g, '')
    .slice(0, 5)
}

const rememberMe = ref(false)
const showPassword = ref(false)

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

const verifyPassword = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const formData = new URLSearchParams()
    formData.append('username', fullOperatorId.value)
    formData.append('password', passkey.value)
    // ADD THIS LINE: Send the checkbox value to the backend
    formData.append('remember_me', rememberMe.value)

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

    // UPDATED STORAGE LOGIC:
    // Only save the refresh token if the backend actually sent one
    if (rememberMe.value) {
      localStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
    } else {
      sessionStorage.setItem('access_token', data.access_token)
      // No refresh token is saved here because the backend didn't generate one!
    }
    
    localStorage.setItem('user_role', data.role)
    localStorage.setItem('user_name', data.user_name)

    window.dispatchEvent(new Event("auth-changed"))

    router.push('/dashboard')

  } catch (error) {
    errorMessage.value = error.message
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

.security-metrics {
  display: flex;
  gap: 20px;
}

.metric-box {
  display: flex;
  flex-direction: column;
}

.metric-val {
  color: white;
  font-weight: bold;
}

.metric-lbl {
  color: gray;
  font-size: 12px;
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
}

.action-btn {
  width: 100%;
  padding: 14px;
  background: #4f46e5;
  color: white;
  border: none;
  cursor: pointer;
  border-radius: 6px;
}

.action-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.checkbox-label {
  color: gray;
}

.error-message {
  color: red;
  margin-top: 20px;
}

.panel-footer {
  margin-top: 30px;
  color: gray;
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

.input-prefix {
  color: rgba(16, 173, 194, 0.28);
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