<script setup>
import { ref, watch, computed } from "vue"
import { useRouter } from "vue-router"
import axios from "axios" // 🚀 1. Import the Hybrid Engine

const router = useRouter()

const form = ref({
  title: "",
  author: "",
  publisher: "",
  language_id: "",
  category: "",
  isbn: "",
  year: "",
  ddc: "",
  call_no: "",
  translation_compilation: "",
  genre: "",
  original_language: ""
})

const result = ref(null)
const loading = ref(false)

// =============================
// AUTHORITY LOCK STATE
// =============================
const duplicateResult = ref({
  severity: "none",
  matches: []
})

const adminOverride = ref(false)
let typingTimer = null

const isFrozen = computed(() => {
  return duplicateResult.value.severity === "strong" && !adminOverride.value
})

// =============================
// LIVE DUPLICATE CHECK (Natural)
// =============================
watch(
  () => [form.value.title, form.value.author, form.value.language_id],
  () => {
    clearTimeout(typingTimer)
    if (!form.value.title) {
      duplicateResult.value = { severity: "none", matches: [] }
      return
    }
    typingTimer = setTimeout(checkDuplicate, 350)
  }
)

async function checkDuplicate() {
  try {
    // 🚀 Natural Axios POST: No manual headers or stringifying
    const res = await axios.post("/catalogue/check-duplicate", {
      title: form.value.title,
      author: form.value.author,
      language: form.value.language_id
    })
    duplicateResult.value = res.data
  } catch (err) {
    console.error("❌ Duplicate check failed:", err)
  }
}

// =============================
// PREFILL & NAVIGATION
// =============================
function confirmPrefill(work) {
  const ok = confirm("Load this work into the form?")
  if (!ok) return
  form.value.title = work.title || ""
  form.value.author = work.author || ""
  form.value.language_id = work.language || ""
  form.value.category = work.category || ""
  form.value.publisher = work.publisher || ""
  form.value.year = work.year || ""
}

function useExistingAuthority(work) {
  router.push(`/create-item?work_id=${work.work_id}&language_id=${work.language}`)
}

// =============================
// CREATE WORK → HYBRID FLOW
// =============================
async function submitWork() {
  if (isFrozen.value) return

  loading.value = true
  result.value = null

  try {
    // 🚀 Natural Axios POST: Base URL and Token handled by main.js
    const res = await axios.post("/catalogue/create-work", form.value)
    const data = res.data
    result.value = data

    // ⭐ NEW FLOW: Move to accession generation immediately
    setTimeout(() => {
      router.push({
        path: '/create-item',
        query: { 
          work_id: data.work_id, 
          language_id: form.value.language_id 
        }
      })
    }, 400)

  } catch (err) {
    console.error("❌ Work creation failed:", err)
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
    <h2>Create Work (Authority Record)</h2>

    <!-- AUTHORITY PANEL -->
    <div
      v-if="duplicateResult.severity !== 'none'"
      class="duplicate-box"
      :class="duplicateResult.severity"
    >
      <strong v-if="duplicateResult.severity === 'strong'">
        🔒 Authority Freeze Active — Exact work exists
      </strong>

      <strong v-if="duplicateResult.severity === 'medium'">
        ⚠ Similar work exists
      </strong>

      <strong v-if="duplicateResult.severity === 'weak'">
        ℹ Possible related works
      </strong>

      <div
        v-for="m in duplicateResult.matches"
        :key="m.work_id"
        class="dup-item"
      >
        <div class="dup-text" @click="confirmPrefill(m)">
          {{ m.title }} — {{ m.author }} — {{ m.language }}
        </div>

        <button
          v-if="duplicateResult.severity === 'strong'"
          class="use-existing"
          @click="useExistingAuthority(m)"
        >
          Use Existing Authority
        </button>
      </div>

      <div v-if="duplicateResult.severity === 'strong'" class="override-box">
        <label>
          <input type="checkbox" v-model="adminOverride" />
          Admin Override — allow creation anyway
        </label>
      </div>
    </div>

    <!-- FORM -->
    <div class="form-grid">
      <input v-model="form.title" placeholder="Title" />
      <input v-model="form.author" placeholder="Author" />
      <input v-model="form.publisher" placeholder="Publisher" />

      <select v-model="form.language_id">
        <option disabled value="">Select Language</option>
        <option value="Malayalam">Malayalam</option>
        <option value="English">English</option>
        <option value="Multi -Lingual">Multilingual</option>
      </select>

      <select v-model="form.category">
        <option disabled value="">Select Category</option>
        <option>Fiction</option>
        <option>Non-Fiction</option>
        <option>Reference</option>
        <option>Religious</option>
        <option>Poetry</option>
      </select>

      <input v-model="form.isbn" placeholder="ISBN (auto fetch enabled)" />
      <input v-model="form.year" placeholder="Year" />
      <input v-model="form.ddc" placeholder="DDC" />
      <input v-model="form.call_no" placeholder="Call No" />
      <input v-model="form.translation_compilation" placeholder="Translation/Compilation" />
      <input v-model="form.genre" placeholder="Genre" />
      <input v-model="form.original_language" placeholder="Original Language" />
    </div>

    <button
      @click="submitWork"
      :disabled="loading || isFrozen"
      class="create-btn"
    >
      <span v-if="isFrozen">🔒 Authority Locked</span>
      <span v-else>{{ loading ? "Saving..." : "Create Work" }}</span>
    </button>

    <pre v-if="result">{{ result }}</pre>
  </div>
</template>

<style scoped>
.page { max-width: 900px; }

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

input, select {
  padding: 6px;
  border: 1px solid #ccc;
  font-size: 14px;
}

.create-btn {
  padding: 8px 14px;
  cursor: pointer;
}

.duplicate-box {
  padding: 12px;
  margin-bottom: 14px;
  border-radius: 8px;
  font-size: 13px;
}

.duplicate-box.strong { background:#fee2e2; }
.duplicate-box.medium { background:#fef3c7; }
.duplicate-box.weak { background:#e0f2fe; }

.dup-item {
  margin-top:6px;
  padding:6px;
  border-radius:6px;
  background:#ffffff;
  display:flex;
  justify-content:space-between;
  align-items:center;
}

.use-existing {
  background:#111827;
  color:white;
  border:none;
  border-radius:6px;
  padding:4px 10px;
  font-size:12px;
}

.override-box {
  margin-top:10px;
  font-size:12px;
}
</style>