<template>
  <div class="login-container">
    <div class="login-card">
      <h1>🏛️ Athenaeum Login</h1>
      <p>Enter your credentials to access the library system.</p>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Username</label>
          <input v-model="username" type="text" placeholder="Enter username" required />
        </div>

        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="••••••••" required />
        </div>

        <button type="submit" :disabled="loading">
          {{ loading ? 'Authenticating...' : 'Sign In' }}
        </button>
      </form>

      <p v-if="error" class="error-msg">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref(null);
const router = useRouter();

// ----------------------------------------------------------------------------------------------------------------------------------//
// --------------------------------------------------LOGIN FUNCTION-----------------------------------------------------------------//
// --------------------------------------------------------------------------------------------------------------------------------//


const handleLogin = async () => {
  loading.value = true;
  error.value = null;

  // 1. Prepare OAuth2 Form Data (FastAPI expects this)
  const params = new URLSearchParams();
  params.append('username', username.value);
  params.append('password', password.value);

  try {
    // 2. Execute the Login Request
    const response = await axios.post('/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    // 3. Save Credentials to LocalStorage
    const token = response.data.access_token;
    localStorage.setItem('token', token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    localStorage.setItem('user_role', response.data.role);
    localStorage.setItem('user_name', username.value);
    window.dispatchEvent(new Event("auth-changed")); // Notify other components of auth change

    // 🛡️ 4. THE "SECRET SAUCE" (REACTIVE HEADER UPDATE)
    // This tells the "Natural" system to use the token IMMEDIATELY.
    // Without this, the first Dashboard call might fail with 401.
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

    console.log("✅ Login Successful. Token attached to Axios.");

    // 5. Redirect to Dashboard
    router.push({ name: 'dashboard' });
    

  } catch (err) {
    console.error("❌ Login Error:", err);
    // Handles server errors or "Incorrect username/password"
    error.value = err.response?.data?.detail || "Connection failed. Is the backend running?";
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;

  background:
    radial-gradient(circle at top right, rgba(20, 184, 166, 0.08), transparent 25%),
    radial-gradient(circle at bottom left, rgba(245, 158, 11, 0.06), transparent 20%),
    #020617;
}

.login-card {
  width: 100%;
  max-width: 430px;
  padding: 2.5rem;
  border-radius: 16px;

  background: rgba(10, 20, 40, 0.95);
  backdrop-filter: blur(10px);

  box-shadow: 0 20px 60px rgba(0,0,0,0.35);
  border: 1px solid rgba(20,184,166,0.15);

  color: white;
}

.login-card h1 {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  
}
.login-card h1 {
  color: white;
}

.login-card p {
  
  margin-bottom: 1.5rem;
  line-height: 1.5;
}
.login-card p {
  color: #cbd5e1;
}
.form-group {
  margin-bottom: 1rem;
  text-align: left;
}

label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 600;
  
}
label {
  color: #e2e8f0;
}
input {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
}
input {
  background: #0f172a;
  color: white;
  border: 1px solid #334155;
}
input:focus {
  outline: none;
  border-color: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.2);
}

button {
  width: 100%;
  padding: 14px;
  margin-top: 0.5rem;
  border: none;
  border-radius: 8px;

  background: linear-gradient(90deg, #0f766e, #14b8a6);
  color: white;

  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease;
}

button:hover {
  transform: translateY(-1px);
}

button:disabled {
  background: #64748b;
  cursor: not-allowed;
}

.error-msg {
  color: #dc2626;
  margin-top: 1rem;
  font-size: 0.9rem;
  text-align: center;
}
</style>