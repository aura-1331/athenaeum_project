<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"

const router = useRouter()
const currentTab = ref("descriptive")
const pasteInput = ref("")
const isParsing = ref(false)
const showAuthorSuggestions = ref(false)

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
const duplicateLoading = ref(false)

const duplicateResult = ref({
  severity: "none",
  matches: []
})

const adminOverride = ref(false)
let typingTimer = null

const savedAuthors = [
  "Abraham T. Kovoor",
  "Agatha Christie",
  "Arthur Conan Doyle",
  "Bram Stoker",
  "Dan Brown",
  "Edward Snowden",
  "J. K. Rowling",
  "J.R.R. Tolkien",
  "Manu S. Pillai",
  "Paulo Coelho",
  "Sasi Tharoor",
  "Yuval Noah Harari"
]

const extraLanguages = ["Arabic", "French", "German", "Russian"]

const isFrozen = computed(() => {
  return duplicateResult.value.severity === "strong" && !adminOverride.value
})

const calculatedAccession = computed(() => {
  if (!form.value.language_id) return ""
  return form.value.language_id.slice(0, 2).toUpperCase() + "-AUTO"
})

const calculatedCallNo = computed(() => {
  if (!form.value.language_id || !form.value.category) return ""
  const langLetter = form.value.language_id.charAt(0).toUpperCase()
  let catCode = ""
  if (form.value.category === "Fiction") catCode = "FIC"
  else if (form.value.category === "Non-Fiction") catCode = "NF"
  else if (form.value.category === "Reference") catCode = "REF"
  else if (form.value.category === "Religious") catCode = "REL"
  else catCode = "GEN"
  return `${langLetter}-${catCode}-AUTO.0`
})

const isIsbnValid = computed(() => {
  if (!form.value.isbn) return null
  return form.value.isbn.length === 10 || form.value.isbn.length === 13
})

const isYearValid = computed(() => {
  if (!form.value.year) return null
  const y = parseInt(form.value.year, 10)
  return y >= 1000 && y <= 2026
})

const isDdcValid = computed(() => {
  if (!form.value.ddc) return null
  return /^[0-9]{3}(\.[0-9]+)?$/.test(form.value.ddc)
})

const authorSuggestions = computed(() => {
  if (!form.value.author) return []
  return savedAuthors.filter(a => 
    a.toLowerCase().includes(form.value.author.toLowerCase())
  )
})

watch(
  () => [form.value.title, form.value.author, form.value.language_id],
  () => {
    clearTimeout(typingTimer)
    if (!form.value.title) {
      duplicateResult.value = { severity: "none", matches: [] }
      duplicateLoading.value = false
      return
    }
    duplicateLoading.value = true
    typingTimer = setTimeout(checkDuplicate, 350)
  }
)

watch(
  () => form.value.year,
  (newVal) => {
    if (!newVal) return
    const cleaned = newVal.replace(/\D/g, "")
    form.value.year = cleaned.slice(0, 4)
    if (form.value.year.length === 4) {
      focusNextField("ddc-input-field")
    }
  }
)

watch(
  () => form.value.isbn,
  (newVal) => {
    if (!newVal) return
    let cleaned = newVal.replace(/[^0-9X]/gi, "")
    if (cleaned.length > 13) {
      cleaned = cleaned.slice(0, 13)
    }
    form.value.isbn = cleaned
    if (form.value.isbn.length === 13 || form.value.isbn.length === 10) {
      focusNextField("year-input-field")
    }
  }
)

watch(
  () => form.value.ddc,
  (newVal) => {
    if (!newVal) return
    let cleaned = newVal.replace(/[^0-9.]/g, "")
    const parts = cleaned.split(".")
    let base = parts[0].replace(/\D/g, "")
    if (base.length > 3) {
      cleaned = base.slice(0, 3) + "." + base.slice(3) + (parts[1] ? parts[1] : "")
    } else if (base.length === 3 && parts.length > 1) {
      cleaned = base + "." + parts[1].replace(/\D/g, "")
    } else {
      cleaned = base
    }
    form.value.ddc = cleaned
  }
)

function toTitleCase(str) {
  if (!str) return ""
  return str
    .replace(/\s+/g, " ")
    .toLowerCase()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function sanitizeField(fieldName) {
  if (["title", "author", "publisher", "genre"].includes(fieldName)) {
    form.value[fieldName] = toTitleCase(form.value[fieldName]).trim()
  }
}

function focusNextField(elementId) {
  setTimeout(() => {
    const el = document.getElementById(elementId)
    if (el) el.focus()
  }, 10)
}

function handleMetadataPaste() {
  if (!pasteInput.value) return
  isParsing.value = true
  
  const text = pasteInput.value
  const isbnMatch = text.match(/(?:ISBN(?:-1[03])?:?\s*)?([0-9X]{10,13})/i)
  const yearMatch = text.match(/\b(18|19|20)\d{2}\b/)
  const ddcMatch = text.match(/\b([0-9]{3}(?:\.[0-9]+)?)\b/)
  
  if (isbnMatch) form.value.isbn = isbnMatch[1]
  if (yearMatch) form.value.year = yearMatch[0]
  if (ddcMatch) form.value.ddc = ddcMatch[1]
  
  const lowerText = text.toLowerCase()
  if (lowerText.includes("malayalam")) form.value.language_id = "Malayalam"
  else if (lowerText.includes("english")) form.value.language_id = "English"
  else if (lowerText.includes("multilingual") || lowerText.includes("multi-lingual")) form.value.language_id = "Multi -Lingual"
  
  if (lowerText.includes("fiction") || lowerText.includes("novel")) form.value.category = "Fiction"
  else if (lowerText.includes("non-fiction") || lowerText.includes("biography")) form.value.category = "Non-Fiction"
  else if (lowerText.includes("reference") || lowerText.includes("dictionary")) form.value.category = "Reference"
  else if (lowerText.includes("religious") || lowerText.includes("bible")) form.value.category = "Religious"
  else if (lowerText.includes("poetry") || lowerText.includes("poem")) form.value.category = "Poetry"

  const lines = text.split("\n").map(l => l.trim()).filter(Boolean)
  if (lines.length > 0 && !isbnMatch && !yearMatch) {
    if (lines[0] && lines[0].length < 100) form.value.title = toTitleCase(lines[0])
    if (lines[1] && lines[1].length < 60) form.value.author = toTitleCase(lines[1])
  }
  
  setTimeout(() => {
    pasteInput.value = ""
    isParsing.value = false
    focusNextField("title-input-field")
  }, 400)
}

function selectAuthor(name) {
  form.value.author = name
  showAuthorSuggestions.value = false
}

async function checkDuplicate() {
  try {
    const res = await axios.post("/catalogue/check-duplicate", {
      title: form.value.title,
      author: form.value.author,
      language: form.value.language_id
    })
    duplicateResult.value = res.data
  } catch (err) {
    console.error(err)
  } finally {
    duplicateLoading.value = false
  }
}

function clearField(fieldName) {
  form.value[fieldName] = ""
}

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

async function submitWork() {
  if (isFrozen.value || loading.value) return
  loading.value = true
  result.value = null

  try {
    const cleanedForm = {}
    Object.keys(form.value).forEach(key => {
      cleanedForm[key] = form.value[key] === "" ? null : form.value[key]
    })

    // Map language_id to language so the backend reads it correctly
    const payload = { 
      ...cleanedForm, 
      language: form.value.language_id || null,
      accession_no: calculatedAccession.value, 
      call_no: calculatedCallNo.value || null 
    }
    console.log("CATEGORY =", form.value.category)
    console.log("PAYLOAD =", payload)
    const res = await axios.post("/catalogue/create-work", payload)
    const data = res.data
    result.value = data

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
    console.error(err)
    result.value = { 
      error: err.response?.data?.detail || "Request failed." 
    }
  } finally {
    loading.value = false
  }
}

function handleKeyDown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault()
    submitWork()
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown)
  focusNextField("parser-field-input")
})

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown)
})
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Create Work <span class="subtitle">(Authority Record)</span></h2>

    <div class="parser-wrapper" :class="{ working: isParsing }">
      <div class="parser-label">
        <span>📋 Rapid Raw Metadata Intake Dropzone</span>
        <span class="parser-hint">Paste citation lines, raw catalog details, or text summaries to auto-fill records</span>
      </div>
      <input 
        id="parser-field-input"
        v-model="pasteInput"
        @input="handleMetadataPaste"
        placeholder="Paste plain reference block text directly here..." 
        class="parser-field"
        :disabled="isParsing"
      />
    </div>

    <div class="tab-header">
      <button 
        type="button"
        class="tab-link" 
        :class="{ active: currentTab === 'descriptive' }"
        @click="currentTab = 'descriptive'"
      >
        Descriptive Metadata
      </button>
      <button 
        type="button"
        class="tab-link" 
        :class="{ active: currentTab === 'classification' }"
        @click="currentTab = 'classification'"
      >
        Identity & Classification
      </button>
    </div>

    <div v-if="duplicateLoading" class="skeleton-loader-banner">
      <div class="skeleton-line header-pulse"></div>
      <div class="skeleton-line card-pulse"></div>
    </div>

    <div
      v-if="duplicateResult.severity !== 'none' && !duplicateLoading"
      class="banner-alert"
      :class="duplicateResult.severity"
    >
      <div class="banner-header">
        <span v-if="duplicateResult.severity === 'strong'">🔒 Authority Freeze Active — Exact work exists</span>
        <span v-if="duplicateResult.severity === 'medium'">⚠️ Similar work exists</span>
        <span v-if="duplicateResult.severity === 'weak'">ℹ️ Possible related works</span>
      </div>

      <div class="matches-list">
        <div
          v-for="m in duplicateResult.matches"
          :key="m.work_id"
          class="match-card"
        >
          <div class="match-details" @click="confirmPrefill(m)">
            <span class="match-title">{{ m.title }}</span>
            <span class="match-meta">{{ m.author }} • {{ m.language }}</span>
          </div>

          <button
            v-if="duplicateResult.severity === 'strong'"
            class="action-btn-secondary"
            @click="useExistingAuthority(m)"
          >
            Use Existing Authority
          </button>
        </div>
      </div>

      <div v-if="duplicateResult.severity === 'strong'" class="override-container">
        <label class="checkbox-label">
          <input type="checkbox" v-model="adminOverride" class="custom-checkbox" />
          <span>Admin Override — allow creation anyway</span>
        </label>
      </div>
    </div>

    <div v-show="currentTab === 'descriptive'" class="form-section">
      <div class="form-grid">
        <div class="floating-group">
          <input 
            id="title-input-field"
            v-model="form.title" 
            @blur="sanitizeField('title')" 
            maxlength="255" 
            placeholder=" " 
            class="form-input" 
            :class="{ 'has-value': form.title }"
          />
          <label class="floating-label">Title</label>
          <button v-if="form.title" @click="clearField('title')" class="clear-btn" type="button">&times;</button>
          <span class="char-counter">{{ form.title.length }}/255</span>
        </div>
        
        <div class="floating-group">
          <input 
            v-model="form.author" 
            @blur="sanitizeField('author')" 
            @focus="showAuthorSuggestions = true"
            maxlength="150" 
            placeholder=" " 
            class="form-input" 
            :class="{ 'has-value': form.author }"
          />
          <label class="floating-label">Author</label>
          <button v-if="form.author" @click="clearField('author')" class="clear-btn" type="button">&times;</button>
          <span class="char-counter">{{ form.author.length }}/150</span>
          
          <div v-if="showAuthorSuggestions && authorSuggestions.length > 0" class="suggestions-dropdown">
            <div 
              v-for="author in authorSuggestions" 
              :key="author" 
              @click="selectAuthor(author)"
              class="suggestion-item"
            >
              {{ author }}
            </div>
          </div>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.publisher" 
            @blur="sanitizeField('publisher')" 
            placeholder=" " 
            class="form-input" 
            :class="{ 'has-value': form.publisher }"
          />
          <label class="floating-label">Publisher</label>
          <button v-if="form.publisher" @click="clearField('publisher')" class="clear-btn" type="button">&times;</button>
        </div>

        <div class="floating-group">
          <select v-model="form.language_id" class="form-select" :class="{ 'has-value': form.language_id }">
            <option disabled value="">Select Language</option>
            <option value="Malayalam">Malayalam</option>
            <option value="English">English</option>
            <option value="Multi -Lingual">Multilingual</option>
            <option disabled class="dropdown-divider-line">──────────────</option>
            <option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option>
          </select>
          <label class="floating-label">Select Language</label>
        </div>

        <div class="floating-group">
          <select v-model="form.category" class="form-select" :class="{ 'has-value': form.category }">
            <option disabled value="">Select Category</option>
            <option value="Fiction">Fiction</option>
            <option value="Non-Fiction">Non-Fiction</option>
            <option value="Reference">Reference</option>
            <option value="Religious">Religious</option>
            <option value="Poetry">Poetry</option>
          </select>
          <label class="floating-label">Select Category</label>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.genre" 
            @blur="sanitizeField('genre')" 
            placeholder=" " 
            class="form-input" 
            :class="{ 'has-value': form.genre }"
          />
          <label class="floating-label">Genre</label>
          <button v-if="form.genre" @click="clearField('genre')" class="clear-btn" type="button">&times;</button>
        </div>

        <div class="floating-group full-width">
          <select v-model="form.original_language" class="form-select" :class="{ 'has-value': form.original_language }">
            <option value="" disabled selected hidden></option>
            <option value="Malayalam">Malayalam</option>
            <option value="English">English</option>
            <option value="Multi -Lingual">Multilingual</option>
            <option disabled class="dropdown-divider-line">──────────────</option>
            <option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option>
          </select>
          <label class="floating-label">Original Language</label>
        </div>
      </div>
    </div>

    <div v-show="currentTab === 'classification'" class="form-section">
      <div class="form-grid">
        <div class="floating-group">
          <input 
            id="isbn-input-field"
            v-model="form.isbn" 
            placeholder=" " 
            class="form-input"
            :class="{ 
              'has-value': form.isbn,
              'valid-field': isIsbnValid === true, 
              'invalid-field': isIsbnValid === false 
            }"
          />
          <label class="floating-label">ISBN (Digits/X auto-jumps)</label>
          <button v-if="form.isbn" @click="clearField('isbn')" class="clear-btn" type="button">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            id="year-input-field"
            v-model="form.year" 
            placeholder=" " 
            class="form-input"
            :class="{ 
              'has-value': form.year,
              'valid-field': isYearValid === true, 
              'invalid-field': isYearValid === false 
            }"
          />
          <label class="floating-label">Year (YYYY auto-jumps)</label>
          <button v-if="form.year" @click="clearField('year')" class="clear-btn" type="button">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            id="ddc-input-field"
            v-model="form.ddc" 
            placeholder=" " 
            class="form-input" 
            :class="{ 
              'has-value': form.ddc,
              'valid-field': isDdcValid === true,
              'invalid-field': isDdcValid === false
            }"
          />
          <label class="floating-label">DDC</label>
          <button v-if="form.ddc" @click="clearField('ddc')" class="clear-btn" type="button">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.call_no" 
            placeholder=" " 
            class="form-input" 
            :class="{ 'has-value': form.call_no }"
          />
          <label class="floating-label">Call No</label>
          <button v-if="form.call_no" @click="clearField('call_no')" class="clear-btn" type="button">&times;</button>
        </div>

        <div class="floating-group full-width">
          <input 
            v-model="form.translation_compilation" 
            placeholder=" " 
            class="form-input" 
            :class="{ 'has-value': form.translation_compilation }"
          />
          <label class="floating-label">Translation/Compilation</label>
          <button v-if="form.translation_compilation" @click="clearField('translation_compilation')" class="clear-btn" type="button">&times;</button>
        </div>
      </div>

      <div class="system-previews-grid" v-if="calculatedAccession || calculatedCallNo">
        <div class="preview-card" v-if="calculatedAccession">
          <span class="preview-title">SYSTEM ASSIGNED ACCESSION PREFIX</span>
          <span class="preview-value">{{ calculatedAccession }}</span>
        </div>
        <div class="preview-card" v-if="calculatedCallNo">
          <span class="preview-title">SYSTEM PROPOSED CALL BASE</span>
          <span class="preview-value">{{ calculatedCallNo }}</span>
        </div>
      </div>
    </div>

    <div class="form-actions-footer">
      <button
        @click="submitWork"
        :disabled="loading || isFrozen"
        class="submit-btn"
        :class="{ 'btn-frozen': isFrozen }"
      >
        <span v-if="isFrozen">🔒 Authority Locked</span>
        <span v-else>{{ loading ? "Saving Record..." : "Create Work" }}</span>
      </button>
      <span class="shortcut-legend">Press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to save</span>
    </div>

    <div v-if="result" class="result-container">
      <pre class="json-output">{{ result }}</pre>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
  color: #e0e0e0;
}

.page-title {
  font-size: 24px;
  font-weight: 500;
  color: #cfb997;
  margin-bottom: 24px;
  letter-spacing: 0.5px;
}

.subtitle {
  font-size: 16px;
  color: #8c8c8c;
  font-weight: 400;
  margin-left: 6px;
}

.parser-wrapper {
  background: #121212;
  border: 1px dashed #333333;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 28px;
  transition: all 0.3s ease;
}

.parser-wrapper.working {
  border-color: #cfb997;
  background: #171614;
}

.parser-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 500;
  color: #cfb997;
}

.parser-hint {
  font-size: 11px;
  color: #555555;
  font-weight: 400;
}

.parser-field {
  width: 100%;
  height: 38px;
  padding: 0 12px;
  background: #181818;
  border: 1px solid #262626;
  border-radius: 4px;
  color: #a3a3a3;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.parser-field:focus {
  border-color: #cfb997;
}

.tab-header {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #1c1c1c;
  margin-bottom: 24px;
}

.tab-link {
  padding: 12px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #8c8c8c;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-link:hover {
  color: #cfb997;
}

.tab-link.active {
  color: #cfb997;
  border-bottom-color: #cfb997;
}

.form-section {
  background: #111111;
  border: 1px solid #1c1c1c;
  border-radius: 0 0 6px 6px;
  padding: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.floating-group {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.floating-group.full-width {
  grid-column: span 2;
}

.form-input, 
.form-select {
  width: 100%;
  height: 48px;
  padding: 0 40px 0 16px;
  background: #161616;
  border: 1px solid #282828;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 14px;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
}

.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238c8c8c' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 16px center;
  background-size: 16px;
  padding-right: 40px;
}

.floating-label {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #555555;
  font-size: 14px;
  pointer-events: none;
  transition: all 0.2s ease;
  background: #111111;
  padding: 0 4px;
}

.form-input:focus, 
.form-select:focus {
  border-color: #cfb997;
  background: #1a1a1a;
  box-shadow: 0 0 0 3px rgba(207, 185, 151, 0.1);
}

.form-input:focus ~ .floating-label,
.form-input.has-value ~ .floating-label,
.form-select:focus ~ .floating-label,
.form-select.has-value ~ .floating-label {
  top: 0;
  font-size: 11px;
  color: #cfb997;
}

.form-input.valid-field,
.form-input.valid-field:focus {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-input.invalid-field,
.form-input.invalid-field:focus {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.dropdown-divider-line {
  color: #2d2d2d;
  text-align: center;
}

.suggestions-dropdown {
  position: absolute;
  top: 52px;
  left: 0;
  width: 100%;
  background: #161616;
  border: 1px solid #282828;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.suggestion-item {
  padding: 10px 16px;
  font-size: 13px;
  color: #c5c5c5;
  cursor: pointer;
  transition: background 0.15s;
}

.suggestion-item:hover {
  background: #202020;
  color: #cfb997;
}

.clear-btn {
  position: absolute;
  right: 14px;
  background: none;
  border: none;
  color: #555555;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s ease;
}

.clear-btn:hover {
  color: #ea585c;
}

.floating-group:focus-within .char-counter {
  opacity: 1;
}

.char-counter {
  position: absolute;
  bottom: -16px;
  right: 4px;
  font-size: 10px;
  color: #555555;
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.system-previews-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px dashed #222222;
}

.preview-card {
  background: #141414;
  border: 1px dashed #2a2a2a;
  padding: 12px 16px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preview-title {
  font-size: 10px;
  color: #666666;
  letter-spacing: 0.5px;
}

.preview-value {
  font-size: 15px;
  font-family: monospace;
  color: #cfb997;
  font-weight: 600;
}

.form-actions-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.submit-btn {
  height: 46px;
  padding: 0 40px;
  background: #cfb997;
  color: #121212;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  background: #e5cfab;
  box-shadow: 0 4px 12px rgba(207, 185, 151, 0.15);
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.submit-btn.btn-frozen {
  background: #241818;
  color: #ea585c;
  border: 1px solid #442021;
}

.shortcut-legend {
  font-size: 12px;
  color: #555555;
}

kbd {
  background: #1c1c1c;
  border: 1px solid #333333;
  color: #8c8c8c;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: inherit;
  font-size: 11px;
}

.banner-alert {
  padding: 16px;
  margin-bottom: 24px;
  border-radius: 6px;
  font-size: 14px;
}

.banner-alert.strong {
  background: #1c1212;
  border: 1px solid #442323;
  color: #ea585c;
}

.banner-alert.medium {
  background: #1c1812;
  border: 1px solid #443723;
  color: #eab308;
}

.banner-alert.weak {
  background: #12171c;
  border: 1px solid #233544;
  color: #38bdf8;
}

.banner-header {
  font-weight: 600;
  margin-bottom: 12px;
}

.matches-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.match-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #141414;
  border: 1px solid #242424;
  border-radius: 4px;
}

.match-details {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.match-title {
  color: #e0e0e0;
  font-weight: 500;
}

.match-meta {
  font-size: 12px;
  color: #8c8c8c;
}

.action-btn-secondary {
  height: 32px;
  padding: 0 12px;
  background: #222222;
  color: #cfb997;
  border: 1px solid #333333;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.action-btn-secondary:hover {
  background: #2c2c2c;
}

.override-container {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #442323;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #8c8c8c;
  font-size: 13px;
}

.custom-checkbox {
  accent-color: #ea585c;
}

.skeleton-loader-banner {
  background: #141414;
  border: 1px solid #1c1c1c;
  border-radius: 6px;
  padding: 18px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  background: linear-gradient(90deg, #1f1f1f 25%, #2c2c2c 50%, #1f1f1f 75%);
  background-size: 200% 100%;
  animation: loadingPulse 1.5s infinite ease-in-out;
  border-radius: 4px;
}

.skeleton-line.header-pulse {
  width: 200px;
  height: 14px;
}

.skeleton-line.card-pulse {
  width: 100%;
  height: 45px;
}

@keyframes loadingPulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.result-container {
  margin-top: 24px;
  background: #141414;
  border: 1px solid #2d2d2d;
  border-radius: 4px;
  padding: 16px;
}

.json-output {
  margin: 0;
  font-family: monospace;
  font-size: 13px;
  color: #a3a3a3;
  overflow-x: auto;
}
</style>