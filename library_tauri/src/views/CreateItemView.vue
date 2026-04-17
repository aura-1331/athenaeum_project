<script setup>
import { ref, watch } from "vue"
import axios from "axios" // 🚀 1. Import the Hybrid Engine

const form = ref({
  work_id: "",
  language_id: ""
})

const result = ref(null)
const loading = ref(false)

const authority = ref(null)
const authorityLoading = ref(false)

// =====================================================
// ⭐ LOAD AUTHORITY DETAILS (Natural)
// =====================================================
watch(
  () => form.value.work_id,
  async (newVal) => {
    authority.value = null
    if (!newVal) return

    authorityLoading.value = true

    try {
      // 🚀 Clean Axios call: Base URL and Token handled by main.js
      const res = await axios.get(`/catalogue/work/${newVal}`)
      authority.value = res.data
    } catch (err) {
      console.error("Authority fetch failed:", err)
      authority.value = { error: "Authority not found or Access Denied" }
    } finally {
      authorityLoading.value = false
    }
  }
)

// =====================================================
// 🏗️ CREATE ITEM (Natural)
// =====================================================
async function createItem() {
  if (!form.value.work_id || !form.value.language_id) {
    return alert("Please provide Work ID and Language.")
  }

  loading.value = true
  result.value = null

  try {
    // 🚀 Natural Axios POST: No manual headers or stringifying needed!
    const res = await axios.post("/catalogue/create-item", form.value)
    
    result.value = res.data
    alert(`✅ Item Created! Accession: ${res.data.accession_no}`)
    
    // Optional: Reset form after success
    form.value.work_id = ""
    form.value.language_id = ""
    authority.value = null

  } catch (err) {
    console.error("Creation failed:", err)
    result.value = { 
      error: err.response?.data?.detail || "Request failed. Check permissions." 
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <h2>Create Item (Generate Accession)</h2>

    <!-- WORK ID INPUT -->
    <input
      v-model="form.work_id"
      placeholder="Work ID"
      class="input"
    />

    <!-- ⭐ AUTHORITY BANNER -->
    <div v-if="authorityLoading" class="authority loading">
      Loading authority...
    </div>

    <div
      v-if="authority && !authority.error"
      class="authority"
    >
      <strong>Authority Loaded:</strong>

      <div class="auth-line">
        <span class="label">Title:</span>
        {{ authority.title }}
      </div>

      <div class="auth-line">
        <span class="label">Author:</span>
        {{ authority.author }}
      </div>

      <div class="auth-line">
        <span class="label">Language:</span>
        {{ authority.language }}
      </div>

      <div class="auth-line">
        <span class="label">Category:</span>
        {{ authority.category }}
      </div>
    </div>

    <div
      v-if="authority && authority.error"
      class="authority error"
    >
      {{ authority.error }}
    </div>

    <!-- LANGUAGE SELECT -->
    <select v-model="form.language_id" class="input">
      <option disabled value="">Select Language</option>
      <option value="ML">Malayalam (ML)</option>
      <option value="EN">English (EN)</option>
      <option value="MU">Multilingual (MU)</option>
      <option value="GE">German (GE)</option>
    </select>

    <button @click="createItem" :disabled="loading">
      {{ loading ? "Creating..." : "Create Item" }}
    </button>

    <pre v-if="result">{{ result }}</pre>
  </div>
</template>


<style scoped>
.page {
  max-width: 600px;
}

.input {
  display: block;
  width: 100%;
  margin-bottom: 12px;
  padding: 8px;
  border: 1px solid #d1d5db;
}

button {
  padding: 8px 14px;
  background: #111827;
  color: white;
  border: none;
  cursor: pointer;
}

/* =====================================================
⭐ AUTHORITY BANNER STYLE
===================================================== */
.authority {
  background: #f3f4f6;
  border-left: 5px solid #111827;
  padding: 12px;
  margin-bottom: 14px;
  border-radius: 6px;
}

.authority.loading {
  background: #e5e7eb;
}

.authority.error {
  background: #fee2e2;
  border-left-color: #dc2626;
}

.auth-line {
  font-size: 14px;
  margin-top: 4px;
}

.label {
  font-weight: 700;
  margin-right: 6px;
}
</style>