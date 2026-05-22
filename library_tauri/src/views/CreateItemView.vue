<script setup>
import { ref, watch } from "vue"
import axios from "axios"

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
        error: "Authority not found"
      }
    } finally {
      authorityLoading.value = false
    }
  }
)

async function createItem() {
  if (!form.value.work_id || !form.value.language_id) {
    return alert("Provide Work ID and Language")
  }

  loading.value = true
  result.value = null

  try {
    const res = await axios.post(
      "/catalogue/create-item",
      form.value
    )

    result.value = res.data

    alert(`Item Created • ${res.data.accession_no}`)

    form.value.work_id = ""
    form.value.language_id = ""

    authority.value = null

  } catch (err) {
    result.value = {
      error:
        err.response?.data?.detail ||
        "Creation failed"
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="workbench">

    <div class="panel">

      <div class="panel-header">
        <div>
          <div class="eyebrow">
            INVENTORY REGISTRY
          </div>

          <h1>Create Inventory Item</h1>

          <p>
            Generate accessioned archival inventory
            from an authority record.
          </p>
        </div>

        <div class="stats-card">
          <span class="stats-label">SYSTEM</span>
          <span class="stats-value">READY</span>
        </div>
      </div>

      <div class="form-grid">

        <div class="input-group full">
          <label>Authority Work ID</label>

          <input
            v-model="form.work_id"
            placeholder="ML-0012"
            class="input"
          />
        </div>

        <div
          v-if="authorityLoading"
          class="authority-banner loading full"
        >
          Loading authority record...
        </div>

        <div
          v-if="authority && !authority.error"
          class="authority-banner full"
        >
          <div class="authority-title">
            {{ authority.title }}
          </div>

          <div class="authority-meta">
            <span>{{ authority.author }}</span>
            <span>{{ authority.language }}</span>
            <span>{{ authority.category }}</span>
          </div>
        </div>

        <div
          v-if="authority && authority.error"
          class="authority-banner error full"
        >
          {{ authority.error }}
        </div>

        <div class="input-group">
          <label>Item Language</label>

          <select
            v-model="form.language_id"
            class="input"
          >
            <option disabled value="">
              Select Language
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
          {{ loading ? "Generating..." : "Generate Item" }}
        </button>
      </div>

      <div
        v-if="result && !result.error"
        class="result-card"
      >
        <div class="result-label">
          ACCESSION GENERATED
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

<style scoped>
.workbench {
  min-height: 100%;
  display: flex;
  justify-content: center;
  padding: 60px;
}

.panel {
  width: 100%;
  max-width: 1100px;

  background: rgba(255,255,255,0.02);

  border: 1px solid rgba(184,146,90,0.12);

  border-radius: 18px;

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
  color: #8b7355;
  margin-bottom: 12px;
}

h1 {
  font-size: 42px;
  margin-bottom: 10px;
  color: #f5f5f5;
}

p {
  color: #777;
  max-width: 520px;
  line-height: 1.6;
}

.stats-card {
  display: flex;
  flex-direction: column;

  align-items: flex-end;

  padding: 18px;

  border: 1px solid rgba(184,146,90,0.1);

  border-radius: 12px;

  min-width: 140px;
}

.stats-label {
  font-size: 10px;
  letter-spacing: 2px;
  color: #777;
}

.stats-value {
  margin-top: 8px;
  font-size: 22px;
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
  font-size: 13px;
  color: #999;
  letter-spacing: 1px;
}

.input {
  height: 54px;

  background: rgba(255,255,255,0.03);

  border: 1px solid rgba(255,255,255,0.08);

  border-radius: 10px;

  padding: 0 16px;

  color: white;

  font-size: 15px;

  transition: 0.2s;
}

.input:focus {
  outline: none;

  border-color: rgba(99,102,241,0.6);

  background: rgba(255,255,255,0.05);
}

.authority-banner {
  background: rgba(99,102,241,0.08);

  border: 1px solid rgba(99,102,241,0.2);

  border-radius: 12px;

  padding: 20px;
}

.authority-banner.loading {
  opacity: 0.7;
}

.authority-banner.error {
  background: rgba(239,68,68,0.08);

  border-color: rgba(239,68,68,0.2);

  color: #f87171;
}

.authority-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 12px;
}

.authority-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.authority-meta span {
  font-size: 13px;

  padding: 6px 10px;

  border-radius: 999px;

  background: rgba(255,255,255,0.05);

  color: #aaa;
}

.actions {
  margin-top: 34px;
}

button {
  height: 52px;

  padding: 0 26px;

  border-radius: 10px;

  border: 1px solid rgba(99,102,241,0.35);

  background: linear-gradient(
    180deg,
    rgba(99,102,241,0.22),
    rgba(99,102,241,0.12)
  );

  color: white;

  font-size: 14px;

  font-weight: 600;

  cursor: pointer;

  transition: 0.2s;
}

button:hover {
  transform: translateY(-1px);

  border-color: rgba(99,102,241,0.7);
}

.result-card {
  margin-top: 28px;

  padding: 24px;

  border-radius: 14px;

  border: 1px solid rgba(16,185,129,0.2);

  background: rgba(16,185,129,0.06);
}

.result-label {
  font-size: 11px;

  letter-spacing: 2px;

  color: #6ee7b7;

  margin-bottom: 12px;
}

.result-accession {
  font-size: 34px;

  font-weight: 800;

  letter-spacing: 1px;

  color: white;
}

.result-error {
  margin-top: 24px;

  padding: 16px;

  border-radius: 10px;

  background: rgba(239,68,68,0.08);

  border: 1px solid rgba(239,68,68,0.2);

  color: #f87171;
}
</style>