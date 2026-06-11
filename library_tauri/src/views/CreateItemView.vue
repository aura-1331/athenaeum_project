<template>
  <div class="workbench">
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="eyebrow">CENTRAL REGISTRY INDEX</div>
          <h1>Accession New Copy</h1>
          <p>
            Generate a unique accession tracking number and shelf record 
            linked directly to an authorized catalogued work.
          </p>
        </div>

        <div class="stats-card">
          <span class="stats-label">REGISTRY STATUS</span>
          <span class="stats-value">ACTIVE</span>
        </div>
      </div>

      <div class="form-grid">
        <div class="input-group full">
          <label>Authorized Work ID</label>
          <input
            v-model="form.work_id"
            placeholder="e.g., ML-0012"
            class="input"
          />
        </div>

        <div
          v-if="authorityLoading"
          class="authority-banner loading full"
        >
          Consulting authority archive records...
        </div>

        <div
          v-if="authority && !authority.error"
          class="authority-banner full"
        >
          <div class="authority-title">
            {{ authority.title }}
          </div>

          <div class="authority-meta">
            <span>By {{ authority.author || 'Unknown' }}</span>
            <span>Language: {{ authority.language }}</span>
            <span>Classification: {{ authority.category }}</span>
          </div>
        </div>

        <div
          v-if="authority && authority.error"
          class="authority-banner error full"
        >
          {{ authority.error }}
        </div>

        <div class="input-group">
          <label>Volume Copy Language</label>
          <select
            v-model="form.language_id"
            class="input"
          >
            <option disabled value="">
              Select Language Profile
            </option>
            <option value="ML">
              Malayalam (ML)
            </option>
            <option value="EN">
              English (EN)
            </option>
            <option value="MU">
              Multilingual (MU)
            </option>
            <option value="GE">
              German (GE)
            </option>
          </select>
        </div>
      </div>

      <div class="actions">
        <button
          @click="createItem"
          :disabled="loading"
        >
          {{ loading ? "Assigning Accession..." : "Commit Copy to Archive" }}
        </button>
      </div>

      <div
        v-if="result && !result.error"
        class="result-card"
      >
        <div class="result-label">
          ACCESSION NUMBER ALLOCATED
        </div>
        <div class="result-accession">
          {{ result.accession_no }}
        </div>
      </div>

      <div
        v-if="result && result.error"
        class="result-error"
      >
        {{ result.error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue"
import axios from "axios"
import { dispatchAuditTrail } from "../utils/audit"

const form = ref({
  work_id: "",
  language_id: ""
})

const result = ref(null)
const loading = ref(false)

const authority = ref(null)
const authorityLoading = ref(false)

watch(
  () => form.value.work_id,
  async (newVal) => {
    authority.value = null

    if (!newVal) return

    authorityLoading.value = true

    try {
      const res = await axios.get(`/catalogue/work/${newVal}`)
      authority.value = res.data
    } catch (err) {
      authority.value = {
        error: "Authorized catalogued work not found in registry"
      }
    } finally {
      authorityLoading.value = false
    }
  }
)

async function createItem() {
  if (!form.value.work_id || !form.value.language_id) {
    return alert("Provide Work ID and Language Profile");
  }

  // 1. Force the user to justify this new entry
  const reason = prompt("Enter justification for accessioning this new copy:");
  if (!reason) {
    alert("Action cancelled: Justification is required for security audits.");
    return;
  }

  loading.value = true;
  result.value = null;

  try {
    const res = await axios.post("/catalogue/create-item", form.value);

    result.value = res.data;

    // 2. Dispatch the audit with the provided reason
    await dispatchAuditTrail(
      "CREATE",
      "CATALOGUE",
      res.data.accession_no,
      `Allocated asset tracking token for Work ID: #${form.value.work_id}`,
      reason // <--- The captured reason
    );

    alert(`Volume Copy Accessioned Successfully • ${res.data.accession_no}`);

    form.value.work_id = "";
    form.value.language_id = "";
    authority.value = null;
  } catch (err) {
    result.value = {
      error: err.response?.data?.detail || "Failed to catalog copy"
    };
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.workbench {
  min-height: 100%;
  display: flex;
  justify-content: center;
  padding: 60px;
  background: #111111;
}

.panel {
  width: 100%;
  max-width: 1100px;
  background: #141414;
  border: 1px solid rgba(184, 146, 90, 0.15);
  border-radius: 12px;
  padding: 42px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 40px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 2px;
  color: #cfb997;
  font-weight: 600;
  margin-bottom: 12px;
}

h1 {
  font-family: 'Playfair Display', serif;
  font-size: 36px;
  margin-bottom: 10px;
  color: #e0e0e0;
  font-weight: 500;
}

p {
  color: #8c8c8c;
  max-width: 520px;
  line-height: 1.6;
  font-size: 14px;
}

.stats-card {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 16px;
  border: 1px solid #282828;
  background: #161616;
  border-radius: 6px;
  min-width: 140px;
}

.stats-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #8c8c8c;
  font-weight: 600;
}

.stats-value {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 700;
  color: #10b981;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.full {
  grid-column: 1 / -1;
}

.input-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 10px;
  font-size: 12px;
  color: #cfb997;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

.input {
  height: 50px;
  background: #161616;
  border: 1px solid #282828;
  border-radius: 4px;
  padding: 0 16px;
  color: #e0e0e0;
  font-size: 14px;
  transition: all 0.2s ease;
}

select.input {
  cursor: pointer;
  color: #c5c5c5;
}

select.input option {
  background: #141414;
  color: #e0e0e0;
}

.input:focus {
  outline: none;
  border-color: #cfb997;
  background: #1a1a1a;
}

.authority-banner {
  background: #181715;
  border: 1px solid #2a251e;
  border-radius: 6px;
  padding: 20px;
  color: #c5c5c5;
}

.authority-banner.loading {
  opacity: 0.7;
  font-style: italic;
  color: #8c8c8c;
}

.authority-banner.error {
  background: #250906;
  border-color: #4a120b;
  color: #f87171;
}

.authority-title {
  font-family: 'Playfair Display', serif;
  font-size: 20px;
  color: #e0e0e0;
  margin-bottom: 12px;
}

.authority-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.authority-meta span {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 4px;
  background: #221f1a;
  border: 1px solid #2a251e;
  color: #cfb997;
}

.actions {
  margin-top: 34px;
}

button {
  height: 48px;
  padding: 0 28px;
  border-radius: 4px;
  border: none;
  background: #8b0000;
  color: white;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s ease;
}

button:hover:not(:disabled) {
  background: #a30000;
}

button:disabled {
  background: #282828;
  color: #555555;
  cursor: not-allowed;
}

.result-card {
  margin-top: 28px;
  padding: 24px;
  border-radius: 6px;
  border: 1px solid #142e24;
  background: #1a221f;
}

.result-label {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: #10b981;
  font-weight: 600;
  margin-bottom: 8px;
}

.result-accession {
  font-family: monospace;
  font-size: 30px;
  font-weight: 700;
  color: #e0e0e0;
}

.result-error {
  margin-top: 24px;
  padding: 16px;
  border-radius: 6px;
  background: #250906;
  border: 1px solid #4a120b;
  color: #f87171;
  font-size: 14px;
}
</style>