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
  height: 80vh;
}
.login-card {
  padding: 2rem;
  border: 1px solid #ddd;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
  background: white;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.form-group {
  margin-bottom: 1rem;
  text-align: left;
}
input {
  width: 100%;
  padding: 10px;
  margin-top: 5px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
button {
  width: 100%;
  padding: 12px;
  background-color: #2c3e50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}
button:disabled { background-color: #7f8c8d; }
.error-msg { color: #e74c3c; margin-top: 1rem; font-size: 0.9rem; }
</style>