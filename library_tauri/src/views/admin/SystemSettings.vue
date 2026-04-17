<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

// 1. DATA STATE
const settings = ref({ DEFAULT_LOAN_DAYS: 0, DAILY_FINE_RATE: 0 });
const forms = ref({ loanDays: null, fineRate: null });
const loading = ref(true);

// 🔍 2. FETCH CURRENT POLICIES (The Natural Way)
const fetchSettings = async () => {
  try {
    // 🚀 Global interceptor handles the Base URL and Token automatically
    const response = await axios.get('/admin/config'); 
    settings.value = response.data;
  } catch (error) {
    console.error("❌ Could not load library physics:", error);
    // Optional: if unauthorized, the interceptor or this check can handle it
    if (error.response?.status === 401) {
       alert("🔐 Architect eyes only! Please log in as Admin.");
    }
  } finally {
    loading.value = false;
  }
};

// 🏛️ 3. UPDATE POLICY (The Hybrid Way)
const updatePolicy = async (key, value) => {
  // Guard clause for empty inputs
  if (value === null || value === undefined || value === "") {
    return alert("Please enter a valid value.");
  }
  
  try {
    // 🚀 CLEAN CALL: No manual headers or full URLs needed!
    // We send 'null' as the body because we are using Query Params
    await axios.patch(`/admin/config/${key}`, null, {
      params: { new_value: value }
    });
    
    alert(`📜 Library Law Updated: ${key} is now ${value}`);
    
    // Update the UI state so the "Current" label changes immediately
    settings.value[key] = value; 

    // Reset the specific input field after success
    if (key === 'DEFAULT_LOAN_DAYS') forms.value.loanDays = null;
    if (key === 'DAILY_FINE_RATE') forms.value.fineRate = null;

  } catch (error) {
    const msg = error.response?.data?.detail || "Update failed. Check your connection or permissions.";
    alert(`🛑 Error: ${msg}`);
  }
};

// 4. LIFECYCLE
onMounted(fetchSettings);
</script>

<template>

  <div class="settings-container">
    <h2>🏛️ Library Global Policies</h2>
    <p>Adjust the "physics" of the library system here.</p>

    <div v-if="loading" class="loader">Accessing System Registry...</div>

    <div v-else class="settings-grid">
      <div class="config-card">
        <h3>Default Loan Period</h3>
        <p>Current: <strong>{{ settings.DEFAULT_LOAN_DAYS }} days</strong></p>
        <div class="input-group">
          <input type="number" v-model="forms.loanDays" placeholder="New days..." />
          <button @click="updatePolicy('DEFAULT_LOAN_DAYS', forms.loanDays)">Update</button>
        </div>
      </div>

      <div class="config-card">
        <h3>Daily Fine Rate</h3>
        <p>Current: <strong>₹{{ settings.DAILY_FINE_RATE }}</strong></p>
        <div class="input-group">
          <input type="number" v-model="forms.fineRate" placeholder="New rate..." />
          <button @click="updatePolicy('DAILY_FINE_RATE', forms.fineRate)">Update</button>
        </div>
      </div>
    </div>
  </div>
</template>


<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}
.config-card {
  border: 1px solid #ddd;
  padding: 20px;
  border-radius: 12px;
  background: #f9f9f9;
}
.input-group {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
input {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
  flex: 1;
}
button {
  background: #2c3e50;
  color: white;
  border: none;
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
}
</style>