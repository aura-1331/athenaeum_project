<template>
  <div class="work-page" :class="themeMode === 'light' ? 'theme-light' : 'theme-dark'">
    <header class="work-header">
      <div>
        <div class="eyebrow">CATALOGUE // AUTHORITY RECORD</div>
        <h1>Create Work</h1>
        <p class="page-intro">Create a new bibliographic record for the Athenaeum catalogue.</p>
      </div>
      <div class="authority-badge" :class="user_role === 'The Chief' ? 'chief' : 'keeper'">
        <span class="badge-dot"></span>
        <div>
          <strong>{{ user_role === 'The Chief' ? 'THE CHIEF' : 'THE KEEPER' }}</strong>
          <small>{{ user_role === 'The Chief' ? 'DIRECT CATALOGUE AUTHORITY' : 'VERIFICATION REQUIRED' }}</small>
        </div>
      </div>
    </header>

    <section class="authority-note" :class="user_role === 'The Chief' ? 'chief-note' : 'keeper-note'">
      <div class="note-title">{{ user_role === 'The Chief' ? 'Direct catalogue registration' : 'Submit for verification' }}</div>
      <p v-if="user_role === 'The Chief'">This Work will be entered directly into the authoritative catalogue.</p>
      <p v-else>This Work will remain pending until The Chief reviews and approves it.</p>
    </section>

    <section class="intake-card">
      <div class="section-heading">
        <div>
          <span class="section-number">01</span>
          <div><h2>Rapid Metadata Intake</h2><p>Paste a citation or raw catalogue information to pre-fill the record.</p></div>
        </div>
      </div>
      <div class="parser-row" :class="{ working: isParsing }">
        <span class="parser-icon">PASTE</span>
        <input id="parser-field-input" v-model="pasteInput" @paste="handleMetadataPaste" placeholder="Paste citation, ISBN, publication details, or catalogue text…" :disabled="isParsing" />
        <span v-if="isParsing" class="parser-status">READING…</span>
      </div>
    </section>

    <section class="form-card">
      <div class="section-heading">
        <div>
          <span class="section-number">02</span>
          <div><h2>Work Identity</h2><p>The information that identifies this bibliographic record.</p></div>
        </div>
      </div>
      <div class="field-grid">
        <label class="field field-wide"><span>Title <b>*</b></span><div class="input-wrap"><input id="title-input-field" v-model="form.title" @blur="sanitizeField('title')" maxlength="255" autocomplete="off" placeholder="Work title" /><button v-if="form.title" @click="clearField('title')" type="button">×</button><em>{{ form.title.length }}/255</em><i v-show="duplicateLoading || isbnLoading" class="spinner"></i></div></label>
        <label class="field"><span>Language <b>*</b></span><select v-model="form.language_id"><option disabled value="">Select language</option><option value="Malayalam">Malayalam</option><option value="English">English</option><option value="Multi -Lingual">Multilingual</option><option disabled>────────────</option><option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option></select></label>
        <label class="field"><span>Author</span><div class="input-wrap"><input v-model="form.author" @focus="showAuthorSuggestions = true" @blur="handleBlurAction('author')" maxlength="150" autocomplete="off" placeholder="Author name" /><button v-if="form.author" @click="clearField('author')" type="button">×</button><em>{{ form.author.length }}/150</em><div v-if="showAuthorSuggestions && authorSuggestions.length" class="suggestions-dropdown"><div v-for="author in authorSuggestions" :key="author" @mousedown="selectAuthor(author)">{{ author }}</div></div></div></label>
        <label class="field"><span>Publisher</span><div class="input-wrap"><input v-model="form.publisher" @focus="showPublisherSuggestions = true" @blur="handleBlurAction('publisher')" autocomplete="off" placeholder="Publisher" /><button v-if="form.publisher" @click="clearField('publisher')" type="button">×</button><div v-if="showPublisherSuggestions && publisherSuggestions.length" class="suggestions-dropdown"><div v-for="pub in publisherSuggestions" :key="pub" @mousedown="selectPublisher(pub)">{{ pub }}</div></div></div></label>
        <label class="field"><span>Category</span><select v-model="form.category"><option value="">No category</option><option value="Fiction">Fiction</option><option value="Non-Fiction">Non-Fiction</option><option value="Reference">Reference</option><option value="Religious">Religious</option><option value="Poetry">Poetry</option></select></label>
        <label class="field"><span>Year</span><div class="input-wrap"><input id="year-input-field" v-model="form.year" placeholder="YYYY" inputmode="numeric" /></div></label>
        <label class="field"><span>ISBN</span><div class="input-wrap"><input id="isbn-input-field" v-model="form.isbn" placeholder="ISBN" autocomplete="off" :class="{ valid: isIsbnValid === true, invalid: isIsbnValid === false }" /><button v-if="form.isbn" @click="clearField('isbn')" type="button">×</button></div></label>
        <div class="field generated"><span>Serial No</span><strong>{{ previewNumbers.serial_no }}</strong></div>
        <div class="field generated"><span>Accession No</span><strong>{{ previewNumbers.accession_no }}</strong></div>
      </div>
    </section>

    <section class="form-card">
      <div class="section-heading"><div><span class="section-number">03</span><div><h2>Classification & Discovery</h2><p>Place the Work where readers and staff can find it.</p></div></div></div>
      <div class="field-grid">
        <label class="field"><span>DDC</span><div class="input-wrap"><input id="ddc-input-field" v-model="form.ddc" placeholder="e.g. 823.9" :class="{ valid: isDdcValid === true, invalid: isDdcValid === false }" /></div></label>
        <label class="field"><span>Call No</span><div class="input-wrap"><input v-model="form.call_no" placeholder="Call number" /><button v-if="form.call_no" @click="clearField('call_no')" type="button">×</button></div></label>
        <label class="field"><span>Shelf</span><div class="input-wrap"><input v-model="form.shelf" placeholder="Shelf location" /><button v-if="form.shelf" @click="clearField('shelf')" type="button">×</button></div></label>
        <div class="field full-field"><span>Genre</span><div class="genre-controls"><select v-model="selectedGroupAGenre" @change="syncGenreSelection"><option value="">Creative genres</option><option v-for="g in genreGroupA" :key="g" :value="g">{{ g }}</option></select><select v-model="selectedGroupBGenre" @change="syncGenreSelection"><option value="">Factual genres</option><option v-for="g in genreGroupB" :key="g" :value="g">{{ g }}</option></select><select v-model="selectedGroupCGenre" @change="syncGenreSelection"><option value="">Other genres</option><option v-for="g in dynamicCommunityGenres" :key="g" :value="g">{{ g }}</option><option disabled>────────────</option><option value="CUSTOM_MANUAL_OVERRIDE">Enter manually</option></select></div></div>
        <div v-if="showCustomManualGenreField" class="field full-field"><span>Custom Genre</span><input v-model="customManualGenreText" @input="syncManualGenreInput" placeholder="Separate multiple genres with /" /></div>
        <div class="genre-preview full-field"><span>Selected genres</span><div><span v-for="chip in liveCompiledGenreChips" :key="chip">{{ chip }}</span><small v-if="!liveCompiledGenreChips.length">No genres selected</small></div></div>
      </div>
    </section>

    <section class="form-card">
      <div class="section-heading"><div><span class="section-number">04</span><div><h2>Translation & Bibliographic Details</h2><p>Record language relationships and additional catalogue information.</p></div></div></div>
      <div class="field-grid">
        <label class="field"><span>Original Language</span><select v-model="form.original_language"><option value="" disabled>Select original language</option><option value="Malayalam">Malayalam</option><option value="English">English</option><option value="Multi -Lingual">Multilingual</option><option disabled>────────────</option><option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option></select></label>
        <label class="field"><span>Translation / Compilation</span><div class="input-wrap"><input v-model="form.translation_compilation" placeholder="e.g. Russian translation" /><button v-if="form.translation_compilation" @click="clearField('translation_compilation')" type="button">×</button></div></label>
        <label class="field full-field"><span>Notes</span><div class="input-wrap"><textarea v-model="form.notes" rows="3" placeholder="Additional bibliographic notes"></textarea></div></label>
      </div>
    </section>

    <section class="check-card">
      <div class="check-heading"><div><span class="section-number">05</span><div><h2>Catalogue Check</h2><p>We check existing records before allowing a new Work to be created.</p></div></div><span v-if="duplicateLoading" class="checking">CHECKING…</span></div>
      <div v-if="duplicateResult.severity === 'none' && !duplicateLoading" class="check-clear"><span>✓</span><div><strong>No matching Work detected</strong><small>The record can proceed to the authority action below.</small></div></div>
      <div v-if="duplicateResult.severity !== 'none' && !duplicateLoading" class="duplicate-alert" :class="duplicateResult.severity">
        <div class="duplicate-title">{{ duplicateResult.severity === 'strong' ? 'Exact Work already exists' : duplicateResult.severity === 'medium' ? 'Similar Work found' : 'Related Work found' }}</div>
        <div v-for="m in duplicateResult.matches" :key="m.work_id" class="match-row"><div @click="confirmPrefill(m)"><strong>{{ m.title }}</strong><small>{{ m.author }} · {{ m.language }}</small></div><button v-if="duplicateResult.severity === 'strong'" @click="useExistingAuthority(m)" type="button">USE EXISTING WORK → ADD ITEM</button></div>
        <label v-if="duplicateResult.severity === 'strong'" class="override"><input type="checkbox" v-model="adminOverride" /> Allow Chief override for this duplicate</label>
      </div>
    </section>

    <footer class="authority-footer">
      <div><span class="footer-label">{{ user_role === 'The Chief' ? 'CHIEF AUTHORITY' : 'KEEPER SUBMISSION' }}</span><strong>{{ user_role === 'The Chief' ? 'Create directly in catalogue' : 'Submit for Chief verification' }}</strong><p>{{ user_role === 'The Chief' ? 'The Work becomes an approved catalogue record immediately.' : 'The Work enters the verification queue and is not live until approved.' }}</p></div>
      <button class="submit-btn" @click="triggerCreationPrompt" :disabled="loading || isFrozen">
        <span v-if="isFrozen">Authority locked by duplicate</span>
        <span v-else-if="loading">{{ user_role === 'The Chief' ? 'Creating Work…' : 'Submitting…' }}</span>
        <span v-else>{{ user_role === 'The Chief' ? 'CREATE WORK' : 'SUBMIT FOR VERIFICATION' }}</span>
      </button>
    </footer>

    <div class="modal-backdrop" v-if="showPromptModal">
      <section class="confirm-modal">
        <div class="modal-eyebrow">{{ user_role === 'The Chief' ? 'DIRECT REGISTRATION' : 'VERIFICATION SUBMISSION' }}</div>
        <h2>{{ user_role === 'The Chief' ? 'Create this Work?' : 'Submit this Work for verification?' }}</h2>
        <p>{{ user_role === 'The Chief' ? 'This Work will be registered directly as an approved catalogue record.' : 'This Work will be submitted to The Chief. It will remain pending until a decision is made.' }}</p>
        <label><span>Reason for this catalogue action</span><input v-model="creationReason" placeholder="e.g. New acquisition / New translation edition" /></label>
        <div class="modal-actions"><button class="cancel-btn" @click="showPromptModal = false">CANCEL</button><button class="confirm-btn" @click="executeConfirmedCreation">{{ user_role === 'The Chief' ? 'CREATE WORK' : 'SUBMIT FOR VERIFICATION' }}</button></div>
      </section>
    </div>

    <div v-if="result" class="result-card" :class="result.work_id ? 'success' : 'error'">
      <strong>{{ result.work_id ? (user_role === 'The Chief' ? 'Work created successfully' : 'Work submitted for verification') : 'Work creation failed' }}</strong>
      <span v-if="result.work_id">Work ID #{{ result.work_id }} · Accession {{ result.accession_no }}</span>
      <span v-else>{{ result.detail || result.error || 'The catalogue rejected the request.' }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import { dispatchAuditTrail } from '@/utils/audit';
import { storeToRefs } from "pinia"
import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const authStore = useAuthStore()
const { userRole: user_role } = storeToRefs(authStore)

const pasteInput = ref("")
const isParsing = ref(false)
const showAuthorSuggestions = ref(false)
const showPublisherSuggestions = ref(false)

const showPromptModal = ref(false)
const creationReason = ref("")

const themeMode = ref(document.documentElement.getAttribute("data-theme") || localStorage.getItem("ui-theme") || "dark")
let themeObserver = null

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
  original_language: "",
  shelf: "S-0-S",
  notes: ""
})

const previewNumbers = ref({
  serial_no: "[Auto-Generated by System]",
  accession_no: "[Select Language First]",
  call_no: ""
})

const result = ref(null)
const loading = ref(false)
const duplicateLoading = ref(false)
const isbnLoading = ref(false)

const duplicateResult = ref({
  severity: "none",
  matches: []
})

const adminOverride = ref(false)
let typingTimer = null

const extraLanguages = ["Arabic", "French", "German", "Russian", "Tamil", "Telugu", "Marathi", "Malay"]

const genreGroupA = ref([
  "ADVENTURE", "BIOGRAPHY", "CLASSIC", "DETECTIVE", "FANTASY", 
  "FOLKLORE", "FOLKTALES", "HORROR", "MYSTERY", "NOVEL", 
  "POETRY", "SATIRE", "SHORT STORIES", "TEMPLE SONGS"
])

const genreGroupB = ref([
  "AETHISM", "ANIMAL HUSBANDRY", "AUTOBIOGRAPHY", "COLLECTION OF PROVERBS", 
  "COLLECTION OF WORKS", "EDUCATIONAL", "ENCYCLOPEDIA", "ENGINEERING", 
  "FORENSIC INVESTIGATIONS", "FUTURISM", "HISTORY", "HOBBY", "INVESTIGATION", 
  "MEDICINE (AYURVEDA)", "MEMOIR", "PHILATELY", "PHILOSOPHY", "POLITICS", 
  "PSYCHOLOGY", "SCIENCE", "SERVICE STORY", "STUDY", "VETERINARY"
])

const dynamicCommunityGenres = ref([])

const selectedGroupAGenre = ref("")
const selectedGroupBGenre = ref("")
const selectedGroupCGenre = ref("")

const showCustomManualGenreField = ref(false)
const customManualGenreText = ref("")

const auditData = ref({
  deviceID: "EDITORIAL-CARDS-STATION-01",
  ip: "192.168.1.105"
})

const isFrozen = computed(() => {
  return duplicateResult.value.severity === "strong" && !adminOverride.value
})

const isIsbnValid = computed(() => {
  if (!form.value.isbn) return null
  const cleanLen = form.value.isbn.replace(/-/g, "").length
  return cleanLen === 10 || cleanLen === 13
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

const autocompleteAuthors = ref([])
const authorSuggestions = computed(() => {
  return autocompleteAuthors.value
})

const autocompletePublishers = ref([])
const publisherSuggestions = computed(() => {
  return autocompletePublishers.value
})

const liveCompiledGenreChips = computed(() => {
  if (!form.value.genre) return []
  return form.value.genre.split('/').map(g => g.trim().toUpperCase()).filter(g => g.length > 0)
})

function syncGenreSelection() {
  if (selectedGroupCGenre.value === "CUSTOM_MANUAL_OVERRIDE") {
    showCustomManualGenreField.value = true
    form.value.genre = customManualGenreText.value.trim().toUpperCase()
    return
  }
  
  showCustomManualGenreField.value = false
  const activeSelectionArray = []
  
  if (selectedGroupAGenre.value) activeSelectionArray.push(selectedGroupAGenre.value)
  if (selectedGroupBGenre.value) activeSelectionArray.push(selectedGroupBGenre.value)
  if (selectedGroupCGenre.value && selectedGroupCGenre.value !== "CUSTOM_MANUAL_OVERRIDE") {
    activeSelectionArray.push(selectedGroupCGenre.value)
  }
  
  form.value.genre = activeSelectionArray.join('/') || ""
}

function syncManualGenreInput() {
  form.value.genre = customManualGenreText.value.trim().toUpperCase()
}

async function harvestSystemGenresMatrix() {
  try {
    const response = await axios.get('/catalogue?limit=1000')
    const items = response.data?.data || []
    const gatheredSet = new Set()

    items.forEach((item) => {
      if (!item.genre) return
      item.genre.split('/').forEach((g) => {
        const standardToken = g.trim().toUpperCase()
        if (standardToken && standardToken !== "NO GENRE YET" && standardToken !== "GENERAL") {
          if (!genreGroupA.value.includes(standardToken) && !genreGroupB.value.includes(standardToken)) {
            gatheredSet.add(standardToken)
          }
        }
      })
    })
    dynamicCommunityGenres.value = Array.from(gatheredSet).sort()
  } catch (err) {
    console.error("Failed to dynamically harvest global taxonomy metrics:", err)
  }
}

async function fetchNextNumbers() {
  if (!form.value.language_id) return
  try {
    const params = { language: form.value.language_id }
    if (form.value.category) {
      params.category = form.value.category
    }
    const res = await axios.get("/catalogue/next-numbers", { params })
    previewNumbers.value.serial_no = res.data.serial_no
    previewNumbers.value.accession_no = res.data.accession_no
    
    if (res.data.call_no && (!form.value.call_no || form.value.call_no.endsWith('-') || previewNumbers.value.call_no === form.value.call_no)) {
      form.value.call_no = res.data.call_no
      previewNumbers.value.call_no = res.data.call_no
    }
  } catch (err) {
    console.error(err)
  }
}

async function handleIsbnLookup(cleanIsbn) {
  isbnLoading.value = true
  try {
    const res = await axios.get("/catalogue/isbn-lookup", { params: { isbn: cleanIsbn } })
    if (res.data) {
      if (res.data.title) form.value.title = res.data.title
      if (res.data.author) form.value.author = res.data.author
      if (res.data.publisher) form.value.publisher = res.data.publisher
      if (res.data.year) form.value.year = String(res.data.year)
      if (res.data.genre) {
        form.value.genre = res.data.genre
        const currentTokens = res.data.genre.split('/').map(g => g.trim().toUpperCase())
        currentTokens.forEach(token => {
          if (genreGroupA.value.includes(token)) selectedGroupAGenre.value = token
          else if (genreGroupB.value.includes(token)) selectedGroupBGenre.value = token
          else if (dynamicCommunityGenres.value.includes(token)) selectedGroupCGenre.value = token
          else {
            showCustomManualGenreField.value = true
            customManualGenreText.value = res.data.genre
            selectedGroupCGenre.value = "CUSTOM_MANUAL_OVERRIDE"
          }
        })
      }
      if (res.data.ddc) form.value.ddc = res.data.ddc
    }
  } catch (err) {
    console.error(err)
  } finally {
    isbnLoading.value = false
  }
}

function selectAuthor(name) {
  form.value.author = name
  autocompleteAuthors.value = []
  showAuthorSuggestions.value = false
}

function selectPublisher(name) {
  form.value.publisher = name
  autocompletePublishers.value = []
  showPublisherSuggestions.value = false
}

function hideSuggestionsWithDelay(type) {
  setTimeout(() => {
    if (type === 'author') showAuthorSuggestions.value = false
    else showPublisherSuggestions.value = false
  }, 250)
}

function handleBlurAction(fieldName) {
  sanitizeField(fieldName)
  hideSuggestionsWithDelay(fieldName)
}

watch(
  () => form.value.author,
  async (newVal) => {
    if (!newVal || newVal.trim().length < 2) {
      autocompleteAuthors.value = []
      return
    }
    try {
      const res = await axios.get("/catalogue/authors/search", {
        params: { q: newVal }
      })
      autocompleteAuthors.value = res.data
    } catch (err) {
      console.error(err)
    }
  }
)

watch(
  () => form.value.publisher,
  async (newVal) => {
    if (!newVal || newVal.trim().length < 2) {
      autocompletePublishers.value = []
      return
    }
    try {
      const res = await axios.get("/catalogue/publishers/search", {
        params: { q: newVal }
      })
      autocompletePublishers.value = res.data
    } catch (err) {
      console.error(err)
    }
  }
)

watch(
  () => [form.value.language_id, form.value.category],
  () => {
    fetchNextNumbers()
  }
)

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
  (newVal, oldVal) => {
    if (!newVal || isParsing.value) return
    let digits = newVal.replace(/[^0-9X]/gi, "")
    if (digits.length > 13) {
      digits = digits.slice(0, 13)
    }
    
    let formatted = digits
    if (digits.length === 13) {
      formatted = `${digits.slice(0, 3)}-${digits.slice(3, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 12)}-${digits.slice(12, 13)}`
    } else if (digits.length === 10) {
      formatted = `${digits.slice(0, 1)}-${digits.slice(1, 4)}-${digits.slice(4, 9)}-${digits.slice(9, 10)}`
    }
    
    if (formatted !== newVal) {
      form.value.isbn = formatted
    }
    
    const cleanLen = digits.length
    if ((cleanLen === 13 || cleanLen === 10) && newVal.length > (oldVal ? oldVal.length : 0)) {
      handleIsbnLookup(digits)
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

async function handleMetadataPaste(event) {
  const pastedText =
    event?.clipboardData?.getData("text") || pasteInput.value || ""

  if (!pastedText.trim()) return

  isParsing.value = true

  const text = pastedText.trim()

  // Detect ISBN-10 or ISBN-13, with or without spaces/hyphens.
  const isbnMatch = text.match(
    /(?:ISBN(?:[-\s]?1[03])?:?\s*)?([0-9X](?:[\s-]?[0-9X]){9,12})/i
  )

  const yearMatch = text.match(/\b(18|19|20)\d{2}\b/)
  const ddcMatch = text.match(/\b([0-9]{3}(?:\.[0-9]+)?)\b/)

  let cleanPastedIsbn = ""

  if (isbnMatch) {
    cleanPastedIsbn = isbnMatch[1]
      .replace(/[\s-]/g, "")
      .toUpperCase()

    form.value.isbn = cleanPastedIsbn
  }

  if (yearMatch) form.value.year = yearMatch[0]
  if (ddcMatch) form.value.ddc = ddcMatch[1]

  const lowerText = text.toLowerCase()

  if (lowerText.includes("malayalam")) {
    form.value.language_id = "Malayalam"
  } else if (lowerText.includes("english")) {
    form.value.language_id = "English"
  } else if (
    lowerText.includes("multilingual") ||
    lowerText.includes("multi-lingual")
  ) {
    form.value.language_id = "Multi -Lingual"
  }

  if (lowerText.includes("fiction") || lowerText.includes("novel")) {
    form.value.category = "Fiction"
  } else if (
    lowerText.includes("non-fiction") ||
    lowerText.includes("biography")
  ) {
    form.value.category = "Non-Fiction"
  } else if (
    lowerText.includes("reference") ||
    lowerText.includes("dictionary")
  ) {
    form.value.category = "Reference"
  } else if (
    lowerText.includes("religious") ||
    lowerText.includes("bible")
  ) {
    form.value.category = "Religious"
  } else if (lowerText.includes("poetry") || lowerText.includes("poem")) {
    form.value.category = "Poetry"
  }

  const lines = text
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean)

  if (lines.length > 0 && !isbnMatch && !yearMatch) {
    if (lines[0] && lines[0].length < 100) {
      form.value.title = toTitleCase(lines[0])
    }

    if (lines[1] && lines[1].length < 60) {
      form.value.author = toTitleCase(lines[1])
    }
  }

  // IMPORTANT:
  // A pasted ISBN must explicitly call the backend lookup.
  // We do not rely on the ISBN watcher here.
  if (cleanPastedIsbn.length === 10 || cleanPastedIsbn.length === 13) {
    await handleIsbnLookup(cleanPastedIsbn)
  }

  pasteInput.value = ""
  isParsing.value = false
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
  if (fieldName === 'genre') {
    selectedGroupAGenre.value = ""
    selectedGroupBGenre.value = ""
    selectedGroupCGenre.value = ""
    customManualGenreText.value = ""
    showCustomManualGenreField.value = false
  }
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
  if (work.genre) {
    form.value.genre = work.genre
    const currentTokens = work.genre.split('/').map(g => g.trim().toUpperCase())
    currentTokens.forEach(token => {
      if (genreGroupA.value.includes(token)) selectedGroupAGenre.value = token
      else if (genreGroupB.value.includes(token)) selectedGroupBGenre.value = token
      else if (dynamicCommunityGenres.value.includes(token)) selectedGroupCGenre.value = token
      else {
        showCustomManualGenreField.value = true
        customManualGenreText.value = work.genre
        selectedGroupCGenre.value = "CUSTOM_MANUAL_OVERRIDE"
      }
    })
  }
}

function useExistingAuthority(work) {
  router.push(`/create-item?work_id=${work.work_id}&language_id=${work.language}`)
}

function triggerCreationPrompt() {
  if (!form.value.title || !form.value.language_id) {
    alert("Title and Language are mandatory fields.")
    return
  }
  
  const yearInt = parseInt(form.value.year, 10);
  if (form.value.year && (isNaN(yearInt) || yearInt < 1000 || yearInt > 2026)) {
    alert("Invalid year: Please enter a valid 4-digit year between 1000 and 2026.");
    focusNextField("year-input-field");
    return;
  }

  if (isFrozen.value || loading.value) return
  creationReason.value = ""
  showPromptModal.value = true
}

async function executeConfirmedCreation() {
  const yearInt = parseInt(form.value.year, 10);
  if (form.value.year && (isNaN(yearInt) || yearInt < 1000 || yearInt > 2026)) {
    alert("Transaction aborted: The year provided is invalid.");
    showPromptModal.value = false;
    return;
  }

  showPromptModal.value = false;
  loading.value = true;
  result.value = null;

  try {
    const cleanedForm = {};
    Object.keys(form.value).forEach(key => {
      cleanedForm[key] = form.value[key] === "" ? null : form.value[key];
    });

    if (!cleanedForm.genre || cleanedForm.genre.trim() === "") {
      cleanedForm.genre = null;
    }

    const payload = { 
      ...cleanedForm, 
      author: form.value.author.trim() || "Unknown",
      language: form.value.language_id || null,
      call_no: form.value.call_no || null 
    };
    
    const operationalReason = creationReason.value.trim() || "New registration initialization sequencing";

    const res = await axios.post("/catalogue/create-work", payload, {
      headers: {
        'X-Change-Reason': operationalReason,
        'X-Device-ID': auditData.value.deviceID,
        'X-IP-Address': auditData.value.ip
      }
    });
    
    const data = res.data;
    result.value = data;

    // --- ADD THIS CALL TO FINISH AUDITING ---
    await dispatchAuditTrail(
      "CREATE",
      "CATALOGUE",
      data.work_id,
      `Registered new authority work: ${payload.title}`,
      operationalReason
    );

    setTimeout(() => {
      router.push({
        path: '/create-item',
        query: { 
          work_id: data.work_id, 
          language_id: form.value.language_id 
        }
      });
    }, 400);
  } catch (err) {
    console.error(err);
    result.value = err.response?.data || { error: "Request failed." };
  } finally {
    loading.value = false;
  }
}

function handleKeyDown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault()
    if (!showPromptModal.value) {
      triggerCreationPrompt()
    } else {
      executeConfirmedCreation()
    }
  }
}

onMounted(async () => {
  window.addEventListener("keydown", handleKeyDown)

  themeObserver = new MutationObserver(() => {
    themeMode.value = document.documentElement.getAttribute("data-theme") || "dark"
  })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"]
  })

  await harvestSystemGenresMatrix()
  focusNextField("parser-field-input")
})

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown)
  if (themeObserver) themeObserver.disconnect()
})
</script>


<style scoped>
:root { color-scheme: dark; }
.work-page { max-width: 1120px; margin: 0 auto; padding: 34px 30px 60px; color: #e7e4de; }
.work-header { display:flex; justify-content:space-between; align-items:flex-start; gap:28px; margin-bottom:22px; }
.eyebrow,.footer-label,.modal-eyebrow { font-size:10px; letter-spacing:1.8px; font-weight:700; color:#77736d; text-transform:uppercase; }
h1 { margin:7px 0 6px; font-size:30px; font-weight:500; letter-spacing:-.4px; color:#eee9df; }
.page-intro { margin:0; color:#8e8a84; font-size:13px; }
.authority-badge { display:flex; align-items:center; gap:10px; padding:11px 14px; border:1px solid #292825; border-radius:8px; min-width:205px; background:#141413; }
.authority-badge strong { display:block; font-size:11px; letter-spacing:1.1px; }
.authority-badge small { display:block; margin-top:4px; color:#77736d; font-size:9px; letter-spacing:.8px; }
.badge-dot { width:7px; height:7px; border-radius:50%; background:#a99776; }
.authority-badge.keeper .badge-dot { background:#9b8f7a; }
.authority-note { padding:15px 18px; border:1px solid #292825; border-radius:8px; margin-bottom:20px; background:#141413; }
.authority-note .note-title { font-size:12px; font-weight:700; letter-spacing:.5px; }
.authority-note p { margin:5px 0 0; color:#85817b; font-size:12px; line-height:1.5; }
.chief-note { border-left:3px solid #b5a27d; }
.keeper-note { border-left:3px solid #77736d; }
.intake-card,.form-card,.check-card { background:#121211; border:1px solid #242320; border-radius:9px; margin-bottom:16px; overflow:visible; }
.section-heading,.check-heading { padding:20px 22px 16px; border-bottom:1px solid #22211e; }
.section-heading > div,.check-heading > div { display:flex; gap:13px; align-items:flex-start; }
.section-number { flex:0 0 auto; font-size:10px; letter-spacing:1px; color:#8d8066; padding-top:2px; }
h2 { margin:0; font-size:15px; font-weight:600; color:#ddd8ce; }
.section-heading p,.check-heading p { margin:4px 0 0; font-size:11px; color:#706d68; }
.parser-row { display:flex; align-items:center; gap:12px; padding:14px 18px; }
.parser-row input { flex:1; height:40px; background:#181817; border:1px solid #2b2a27; border-radius:6px; color:#ddd8ce; padding:0 13px; outline:none; font-size:13px; }
.parser-row input:focus { border-color:#8d8066; }
.parser-icon { font-size:9px; letter-spacing:1px; color:#8d8066; font-weight:700; }
.parser-status,.checking { font-size:9px; letter-spacing:1px; color:#8d8066; }
.form-card { padding-bottom:22px; }
.field-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; padding:20px 22px 0; }
.field { position:relative; display:flex; flex-direction:column; gap:7px; min-width:0; }
.field > span { font-size:10px; font-weight:700; letter-spacing:.8px; color:#85817b; text-transform:uppercase; }
.field b { color:#b5a27d; }
.field input,.field select,.field textarea { width:100%; box-sizing:border-box; background:#181817; border:1px solid #2b2a27; border-radius:6px; color:#ded9d0; outline:none; font:inherit; font-size:13px; }
.field input,.field select { height:43px; padding:0 12px; }
.field textarea { padding:11px 12px; resize:vertical; min-height:78px; }
.field input:focus,.field select:focus,.field textarea:focus { border-color:#8d8066; }
.field-wide,.full-field { grid-column:1 / -1; }
.input-wrap { position:relative; }
.input-wrap input { padding-right:62px; }
.input-wrap button { position:absolute; right:10px; top:50%; transform:translateY(-50%); border:0; background:none; color:#65615c; font-size:18px; cursor:pointer; }
.input-wrap em { position:absolute; right:30px; bottom:5px; font-style:normal; font-size:8px; color:#56534e; }
.spinner { position:absolute; right:12px; top:14px; width:13px; height:13px; border:2px solid #302f2b; border-top-color:#a99776; border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
.generated strong { height:43px; display:flex; align-items:center; padding:0 12px; box-sizing:border-box; background:#151514; border:1px solid #24231f; border-radius:6px; color:#65615c; font-size:12px; font-weight:500; }
.genre-controls { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.genre-preview { margin-top:0; }
.genre-preview > div { min-height:43px; display:flex; align-items:center; flex-wrap:wrap; gap:7px; padding:8px 10px; box-sizing:border-box; background:#151514; border:1px solid #24231f; border-radius:6px; }
.genre-preview span { padding:5px 8px; border-radius:4px; background:#242119; color:#b5a27d; font-size:10px; letter-spacing:.3px; }
.genre-preview small { color:#5e5b56; font-size:11px; }
.suggestions-dropdown { position:absolute; top:68px; left:0; right:0; z-index:50; background:#191918; border:1px solid #37352f; border-radius:6px; box-shadow:0 12px 28px rgba(0,0,0,.45); overflow:hidden; }
.suggestions-dropdown div { padding:10px 12px; color:#bbb6ae; font-size:12px; cursor:pointer; }
.suggestions-dropdown div:hover { background:#25231f; color:#e5dfd4; }
.valid { border-color:#587b66 !important; }
.invalid { border-color:#824e4e !important; }
.check-card { padding-bottom:0; }
.check-heading { display:flex; justify-content:space-between; }
.check-clear { display:flex; align-items:center; gap:12px; padding:18px 22px; }
.check-clear > span { width:28px; height:28px; display:grid; place-items:center; border:1px solid #405648; border-radius:50%; color:#91aa98; }
.check-clear strong,.check-clear small { display:block; }
.check-clear strong { font-size:12px; }
.check-clear small { margin-top:3px; font-size:11px; color:#6e6a64; }
.duplicate-alert { padding:18px 22px; }
.duplicate-alert.strong { background:#1a1413; border-top:1px solid #3a2825; }
.duplicate-alert.medium { background:#191713; }
.duplicate-alert.weak { background:#13171a; }
.duplicate-title { font-size:12px; font-weight:700; margin-bottom:10px; }
.match-row { display:flex; justify-content:space-between; align-items:center; gap:15px; padding:11px 0; border-top:1px solid #292722; }
.match-row strong,.match-row small { display:block; }
.match-row strong { font-size:12px; }
.match-row small { margin-top:3px; font-size:10px; color:#77736d; }
.match-row button { flex:0 0 auto; background:transparent; border:1px solid #4a4337; border-radius:5px; color:#b5a27d; padding:8px 10px; font-size:9px; font-weight:700; cursor:pointer; }
.override { display:flex; gap:8px; margin-top:10px; color:#77736d; font-size:10px; }
.authority-footer { display:flex; justify-content:space-between; align-items:center; gap:25px; padding:20px 22px; margin-top:20px; border:1px solid #2d2a25; border-radius:9px; background:#161513; }
.authority-footer strong { display:block; margin-top:4px; font-size:14px; font-weight:600; }
.authority-footer p { margin:5px 0 0; color:#77736d; font-size:11px; }
.submit-btn { min-width:230px; height:46px; padding:0 22px; border:1px solid #b5a27d; border-radius:6px; background:#b5a27d; color:#161513; font-size:11px; font-weight:800; letter-spacing:.8px; cursor:pointer; }
.submit-btn:hover:not(:disabled) { background:#c6b58f; }
.submit-btn:disabled { opacity:.45; cursor:not-allowed; }
.modal-backdrop { position:fixed; inset:0; z-index:10000; display:grid; place-items:center; padding:20px; background:rgba(7,7,6,.78); backdrop-filter:blur(5px); }
.confirm-modal { width:min(470px,100%); padding:28px; box-sizing:border-box; border:1px solid #35322c; border-radius:10px; background:#171715; box-shadow:0 25px 70px rgba(0,0,0,.6); }
.confirm-modal h2 { margin-top:8px; font-size:20px; color:#ece7de; }
.confirm-modal > p { margin:10px 0 22px; color:#8a867f; font-size:12px; line-height:1.6; }
.confirm-modal label span { display:block; margin-bottom:7px; font-size:10px; color:#85817b; text-transform:uppercase; letter-spacing:.7px; }
.confirm-modal input { width:100%; height:43px; box-sizing:border-box; background:#10100f; border:1px solid #2e2c28; border-radius:6px; color:#ddd8ce; padding:0 12px; outline:none; }
.modal-actions { display:flex; justify-content:flex-end; gap:9px; margin-top:22px; }
.cancel-btn,.confirm-btn { height:39px; padding:0 16px; border-radius:5px; font-size:10px; font-weight:700; cursor:pointer; }
.cancel-btn { background:transparent; border:1px solid #34322e; color:#99958e; }
.confirm-btn { background:#b5a27d; border:1px solid #b5a27d; color:#151411; }
.result-card { margin-top:16px; padding:16px 20px; border-radius:8px; display:flex; flex-direction:column; gap:5px; font-size:12px; }
.result-card.success { background:#141b17; border:1px solid #304738; color:#a8bea9; }
.result-card.error { background:#1b1515; border:1px solid #49302f; color:#c99591; }
.result-card span { color:#77736d; font-size:11px; }
@media (max-width:760px) { .work-page{padding:24px 16px 45px}.work-header,.authority-footer{flex-direction:column;align-items:stretch}.authority-badge{min-width:0}.field-grid{grid-template-columns:1fr}.field-wide,.full-field{grid-column:auto}.genre-controls{grid-template-columns:1fr}.submit-btn{width:100%}.match-row{align-items:flex-start;flex-direction:column}.match-row button{width:100%} }



/* ============================================================
   VERIFIED THEME PALETTE
   App.vue writes data-theme="light" / "dark" on <html>.
   themeMode mirrors that state, and these explicit component
   classes guarantee that Create Work changes with the shell.
============================================================ */

.work-page.theme-dark {
  --cw-page: #030712;
  --cw-card: #0f172a;
  --cw-card-2: #111827;
  --cw-input: #181817;
  --cw-border: #1e293b;
  --cw-border-soft: #242320;
  --cw-text: #f9fafb;
  --cw-muted: #9ca3af;
  --cw-accent: #2dd4bf;
  --cw-accent-warm: #b5a27d;
}

.work-page.theme-light {
  --cw-page: #f8fafc;
  --cw-card: #ffffff;
  --cw-card-2: #ffffff;
  --cw-input: #ffffff;
  --cw-border: #e2e8f0;
  --cw-border-soft: #d8e0e8;
  --cw-text: #0f172a;
  --cw-muted: #475569;
  --cw-accent: #0d9488;
  --cw-accent-warm: #806f4f;
}

.work-page.theme-light,
.work-page.theme-dark {
  color: var(--cw-text);
  background: transparent;
}

.work-page.theme-light h1,
.work-page.theme-light h2,
.work-page.theme-light .authority-badge strong,
.work-page.theme-light .authority-footer strong,
.work-page.theme-light .check-clear strong,
.work-page.theme-light .match-row strong {
  color: var(--cw-text);
}

.work-page.theme-light .eyebrow,
.work-page.theme-light .footer-label,
.work-page.theme-light .modal-eyebrow,
.work-page.theme-light .parser-icon,
.work-page.theme-light .parser-status,
.work-page.theme-light .checking,
.work-page.theme-light .section-number {
  color: var(--cw-accent);
}

.work-page.theme-light .page-intro,
.work-page.theme-light .authority-note p,
.work-page.theme-light .section-heading p,
.work-page.theme-light .check-heading p,
.work-page.theme-light .authority-footer p,
.work-page.theme-light .match-row small,
.work-page.theme-light .override,
.work-page.theme-light .check-clear small,
.work-page.theme-light .field > span,
.work-page.theme-light .authority-badge small {
  color: var(--cw-muted);
}

.work-page.theme-light .authority-badge,
.work-page.theme-light .authority-note,
.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card,
.work-page.theme-light .authority-footer,
.work-page.theme-light .confirm-modal {
  background: var(--cw-card);
  border-color: var(--cw-border);
  color: var(--cw-text);
}

.work-page.theme-light .section-heading,
.work-page.theme-light .check-heading,
.work-page.theme-light .match-row {
  border-color: var(--cw-border);
}

.work-page.theme-light .parser-row input,
.work-page.theme-light .field input,
.work-page.theme-light .field select,
.work-page.theme-light .field textarea,
.work-page.theme-light .confirm-modal input,
.work-page.theme-light .generated strong,
.work-page.theme-light .genre-preview > div {
  background: var(--cw-input);
  border-color: var(--cw-border);
  color: var(--cw-text);
}

.work-page.theme-light .parser-row input::placeholder,
.work-page.theme-light .field input::placeholder,
.work-page.theme-light .field textarea::placeholder,
.work-page.theme-light .confirm-modal input::placeholder {
  color: #64748b;
  opacity: 1;
}

.work-page.theme-light .parser-row input:focus,
.work-page.theme-light .field input:focus,
.work-page.theme-light .field select:focus,
.work-page.theme-light .field textarea:focus,
.work-page.theme-light .confirm-modal input:focus {
  border-color: var(--cw-accent);
  box-shadow: 0 0 0 2px rgba(13,148,136,.10);
}

.work-page.theme-light .input-wrap button {
  color: #64748b;
}

.work-page.theme-light .input-wrap em {
  color: #64748b;
}

.work-page.theme-light .generated strong {
  color: #64748b;
}

.work-page.theme-light .genre-preview span {
  background: rgba(13,148,136,.10);
  color: #0f766e;
}

.work-page.theme-light .genre-preview small {
  color: #64748b;
}

.work-page.theme-light .suggestions-dropdown {
  background: #ffffff;
  border-color: var(--cw-border);
  box-shadow: 0 12px 28px rgba(15,23,42,.14);
}

.work-page.theme-light .suggestions-dropdown div {
  color: #334155;
}

.work-page.theme-light .suggestions-dropdown div:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.work-page.theme-light .submit-btn,
.work-page.theme-light .confirm-btn {
  background: #0d9488;
  border-color: #0d9488;
  color: #ffffff;
}

.work-page.theme-light .submit-btn:hover:not(:disabled),
.work-page.theme-light .confirm-btn:hover:not(:disabled) {
  background: #0f766e;
}

.work-page.theme-light .cancel-btn {
  background: transparent;
  border-color: #cbd5e1;
  color: #475569;
}

.work-page.theme-light .match-row button {
  border-color: #b8c5d2;
  color: #0f766e;
}

.work-page.theme-light .modal-backdrop {
  background: rgba(15,23,42,.38);
}

.work-page.theme-light .result-card.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.work-page.theme-light .result-card.error {
  background: #fff7f7;
  border-color: #fecaca;
  color: #991b1b;
}

.work-page.theme-light .result-card span {
  color: #64748b;
}

.work-page.theme-light .isbn-top-alert {
  background: #fff4f2;
  border-color: #f0b8b1;
  border-left-color: #b45149;
  color: #7f2924;
  box-shadow: 0 6px 18px rgba(127,41,36,.08);
}

.work-page.theme-light .isbn-top-alert p {
  color: #8b4a45;
}

.work-page.theme-light .isbn-lookup-status.error {
  background: #fff4f2;
  border-color: #efc1bc;
  color: #9f3f38;
}

.work-page.theme-light .isbn-lookup-status.success {
  color: #28734b;
}

/* Keep dark mode deliberately close to the original approved look. */
.work-page.theme-dark {
  color: var(--cw-text);
}

.work-page.theme-dark .authority-badge,
.work-page.theme-dark .authority-note,
.work-page.theme-dark .intake-card,
.work-page.theme-dark .form-card,
.work-page.theme-dark .check-card,
.work-page.theme-dark .authority-footer,
.work-page.theme-dark .confirm-modal {
  background: var(--cw-card);
  border-color: var(--cw-border);
}

.work-page.theme-dark .field input,
.work-page.theme-dark .field select,
.work-page.theme-dark .field textarea,
.work-page.theme-dark .parser-row input,
.work-page.theme-dark .confirm-modal input {
  background: var(--cw-input);
  border-color: var(--cw-border-soft);
  color: var(--cw-text);
}

.work-page.theme-dark .section-heading,
.work-page.theme-dark .check-heading,
.work-page.theme-dark .match-row {
  border-color: var(--cw-border-soft);
}


/* ============================================================
   CREATE WORK — REFINED LIGHT THEME
   Cool archival workspace + white catalogue cards.
   The authority badge is intentionally a separate warm
   institutional surface.
============================================================ */

.work-page.theme-light {
  --cw-page: #e9edf3;
  --cw-card: #ffffff;
  --cw-input: #f7f9fb;
  --cw-border: #cfd7e2;
  --cw-border-soft: #dde3eb;
  --cw-text: #172033;
  --cw-muted: #536174;
  --cw-accent: #0d9488;
  --cw-accent-warm: #806f4f;

  max-width: none;
  width: 100%;
  min-height: 100%;
  background: var(--cw-page);
  padding: 34px 30px 60px;
}

/* Keep the workspace background full-width while preserving the
   comfortable reading width of the actual catalogue content. */
.work-page.theme-light > .work-header,
.work-page.theme-light > .authority-note,
.work-page.theme-light > .intake-card,
.work-page.theme-light > .form-card,
.work-page.theme-light > .check-card,
.work-page.theme-light > .authority-footer,
.work-page.theme-light > .result-card {
  width: min(1120px, 100%);
  margin-left: auto;
  margin-right: auto;
}

/* Header */
.work-page.theme-light .eyebrow,
.work-page.theme-light .footer-label,
.work-page.theme-light .modal-eyebrow {
  color: #0f766e;
}

.work-page.theme-light h1,
.work-page.theme-light h2,
.work-page.theme-light .authority-footer strong,
.work-page.theme-light .check-clear strong,
.work-page.theme-light .match-row strong {
  color: var(--cw-text);
}

.work-page.theme-light .page-intro,
.work-page.theme-light .section-heading p,
.work-page.theme-light .check-heading p,
.work-page.theme-light .authority-footer p,
.work-page.theme-light .field > span,
.work-page.theme-light .authority-badge small,
.work-page.theme-light .check-clear small,
.work-page.theme-light .match-row small,
.work-page.theme-light .override {
  color: var(--cw-muted);
}

/* Chief authority badge — deliberately different from ordinary cards. */
.work-page.theme-light .authority-badge.chief {
  background: #f3ecdd;
  border-color: #d7c7a5;
  color: #302a20;
  box-shadow: 0 3px 10px rgba(76, 59, 29, 0.08);
}

.work-page.theme-light .authority-badge.chief strong {
  color: #302a20;
}

.work-page.theme-light .authority-badge.chief small {
  color: #74664e;
}

.work-page.theme-light .authority-badge.chief .badge-dot {
  background: #a88f5d;
}

/* Keeper gets a cool verification identity rather than the Chief's gold. */
.work-page.theme-light .authority-badge.keeper {
  background: #e7f0f2;
  border-color: #b8d0d5;
  color: #18353b;
}

.work-page.theme-light .authority-badge.keeper strong {
  color: #18353b;
}

.work-page.theme-light .authority-badge.keeper small {
  color: #557078;
}

.work-page.theme-light .authority-badge.keeper .badge-dot {
  background: #4f8b91;
}

/* Authority explanation remains distinct from ordinary catalogue cards. */
.work-page.theme-light .authority-note {
  background: #f4f7fa;
  border-color: #ccd6e1;
  color: var(--cw-text);
}

.work-page.theme-light .chief-note {
  border-left-color: #a88f5d;
}

.work-page.theme-light .keeper-note {
  border-left-color: #4f8b91;
}

.work-page.theme-light .authority-note .note-title {
  color: var(--cw-text);
}

.work-page.theme-light .authority-note p {
  color: var(--cw-muted);
}

/* Normal catalogue surfaces */
.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card,
.work-page.theme-light .authority-footer {
  background: var(--cw-card);
  border-color: var(--cw-border);
  box-shadow: 0 2px 8px rgba(23, 32, 51, 0.035);
}

.work-page.theme-light .section-heading,
.work-page.theme-light .check-heading,
.work-page.theme-light .match-row {
  border-color: var(--cw-border-soft);
}

.work-page.theme-light .section-number {
  color: #0d8179;
}

/* Inputs are intentionally one step darker than the white cards. */
.work-page.theme-light .parser-row input,
.work-page.theme-light .field input,
.work-page.theme-light .field select,
.work-page.theme-light .field textarea,
.work-page.theme-light .confirm-modal input,
.work-page.theme-light .generated strong,
.work-page.theme-light .genre-preview > div {
  background: var(--cw-input);
  border-color: var(--cw-border);
  color: var(--cw-text);
}

.work-page.theme-light .parser-row input::placeholder,
.work-page.theme-light .field input::placeholder,
.work-page.theme-light .field textarea::placeholder,
.work-page.theme-light .confirm-modal input::placeholder {
  color: #718096;
  opacity: 1;
}

.work-page.theme-light .parser-row input:focus,
.work-page.theme-light .field input:focus,
.work-page.theme-light .field select:focus,
.work-page.theme-light .field textarea:focus,
.work-page.theme-light .confirm-modal input:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.10);
}

.work-page.theme-light .input-wrap button {
  color: #64748b;
}

.work-page.theme-light .input-wrap em,
.work-page.theme-light .generated strong {
  color: #64748b;
}

.work-page.theme-light .parser-icon,
.work-page.theme-light .parser-status,
.work-page.theme-light .checking {
  color: #0f766e;
}

/* Genre surfaces */
.work-page.theme-light .genre-preview span {
  background: #e4f2ef;
  color: #0f766e;
}

.work-page.theme-light .genre-preview small {
  color: #64748b;
}

/* Suggestions */
.work-page.theme-light .suggestions-dropdown {
  background: #ffffff;
  border-color: var(--cw-border);
  box-shadow: 0 12px 28px rgba(23, 32, 51, 0.14);
}

.work-page.theme-light .suggestions-dropdown div {
  color: #334155;
}

.work-page.theme-light .suggestions-dropdown div:hover {
  background: #edf2f6;
  color: #172033;
}

/* Catalogue check */
.work-page.theme-light .check-clear > span {
  border-color: #9ab5a3;
  color: #3d7350;
}

.work-page.theme-light .duplicate-alert.strong {
  background: #fff7f5;
  border-top-color: #edc8c2;
}

.work-page.theme-light .duplicate-alert.medium {
  background: #fffaf0;
}

.work-page.theme-light .duplicate-alert.weak {
  background: #f2f7f9;
}

.work-page.theme-light .match-row button {
  border-color: #9bb8bd;
  color: #0f766e;
}

/* Authority action */
.work-page.theme-light .submit-btn,
.work-page.theme-light .confirm-btn {
  background: #0d9488;
  border-color: #0d9488;
  color: #ffffff;
}

.work-page.theme-light .submit-btn:hover:not(:disabled),
.work-page.theme-light .confirm-btn:hover:not(:disabled) {
  background: #0f766e;
}

.work-page.theme-light .cancel-btn {
  background: transparent;
  border-color: #c2ccd7;
  color: #475569;
}

/* Modal */
.work-page.theme-light .modal-backdrop {
  background: rgba(23, 32, 51, 0.42);
}

.work-page.theme-light .confirm-modal {
  background: #ffffff;
  border-color: var(--cw-border);
  color: var(--cw-text);
  box-shadow: 0 25px 70px rgba(23, 32, 51, 0.24);
}

.work-page.theme-light .confirm-modal h2 {
  color: var(--cw-text);
}

.work-page.theme-light .confirm-modal > p {
  color: var(--cw-muted);
}

.work-page.theme-light .confirm-modal label span {
  color: var(--cw-muted);
}

/* ISBN warning */
.work-page.theme-light .isbn-top-alert {
  background: #fff4f2;
  border-color: #efc3bc;
  border-left-color: #b45149;
  color: #7f2924;
  box-shadow: 0 6px 18px rgba(127, 41, 36, 0.08);
}

.work-page.theme-light .isbn-top-alert p {
  color: #8b4a45;
}

/* Result */
.work-page.theme-light .result-card.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.work-page.theme-light .result-card.error {
  background: #fff7f7;
  border-color: #fecaca;
  color: #991b1b;
}

.work-page.theme-light .result-card span {
  color: #64748b;
}

@media (max-width: 760px) {
  .work-page.theme-light {
    padding: 24px 16px 45px;
  }
}


/* ============================================================
   FINAL LIGHT-MODE CONTRAST PASS
   Goal: make every structural layer unmistakable.
============================================================ */

.work-page.theme-light {
  background: #e9edf3;
}

/* Catalogue cards: visibly separated from the workspace. */
.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card,
.work-page.theme-light .authority-footer {
  background: #ffffff;
  border: 1px solid #c4ceda;
  box-shadow:
    0 2px 4px rgba(23, 32, 51, 0.035),
    0 8px 20px rgba(23, 32, 51, 0.045);
}

/* Section headers get their own quiet surface, so the card
   does not read as one uninterrupted white sheet. */
.work-page.theme-light .section-heading,
.work-page.theme-light .check-heading {
  background: #f4f6f9;
  border-bottom: 1px solid #d4dce5;
}

/* Give the first rapid-intake body a matching visual division. */
.work-page.theme-light .intake-card .parser-row {
  background: #ffffff;
}

/* Inputs: clearly identifiable, but still restrained. */
.work-page.theme-light .parser-row input,
.work-page.theme-light .field input,
.work-page.theme-light .field select,
.work-page.theme-light .field textarea,
.work-page.theme-light .confirm-modal input,
.work-page.theme-light .generated strong,
.work-page.theme-light .genre-preview > div {
  background: #f5f7fa;
  border: 1px solid #c5cfda;
  color: #172033;
}

/* Slightly stronger focus so the active field is obvious. */
.work-page.theme-light .parser-row input:focus,
.work-page.theme-light .field input:focus,
.work-page.theme-light .field select:focus,
.work-page.theme-light .field textarea:focus,
.work-page.theme-light .confirm-modal input:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.11);
  background: #ffffff;
}

/* Chief authority: unmistakably separate from catalogue cards. */
.work-page.theme-light .authority-badge.chief {
  background: #efe5cf;
  border: 1px solid #cfbb91;
  box-shadow:
    0 2px 5px rgba(76, 59, 29, 0.06),
    0 7px 16px rgba(76, 59, 29, 0.07);
}

.work-page.theme-light .authority-badge.chief strong {
  color: #332b1d;
}

.work-page.theme-light .authority-badge.chief small {
  color: #756447;
}

.work-page.theme-light .authority-badge.chief .badge-dot {
  background: #a98e58;
  box-shadow: 0 0 0 3px rgba(169, 142, 88, 0.12);
}

/* Authority note: separate from both the page and the catalogue cards. */
.work-page.theme-light .authority-note {
  background: #f7f8fa;
  border: 1px solid #cbd5df;
  box-shadow: 0 2px 7px rgba(23, 32, 51, 0.025);
}

/* Keep the Chief footer/action area visually authoritative. */
.work-page.theme-light .authority-footer {
  border-left: 3px solid #a98e58;
}

/* Check area should read as a deliberate status panel. */
.work-page.theme-light .check-clear {
  background: #f8fafb;
  border: 1px solid #d2dbe4;
  border-radius: 7px;
}

/* Make the section number and headings slightly more structured. */
.work-page.theme-light .section-number {
  color: #0d8179;
  font-weight: 700;
}

.work-page.theme-light .field > span {
  color: #465569;
  font-weight: 700;
}

/* Small separation between consecutive cards. */
.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card {
  margin-bottom: 18px;
}


/* LIGHT MODE — SLIGHTLY STRONGER CONTRAST */
.work-page.theme-light {
  background: #e3e8f0;
}

.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card,
.work-page.theme-light .authority-footer {
  border-color: #b8c4d1;
  box-shadow:
    0 2px 5px rgba(23, 32, 51, 0.05),
    0 9px 22px rgba(23, 32, 51, 0.065);
}

.work-page.theme-light .section-heading,
.work-page.theme-light .check-heading {
  background: #edf1f5;
  border-bottom-color: #c6d0db;
}

.work-page.theme-light .parser-row input,
.work-page.theme-light .field input,
.work-page.theme-light .field select,
.work-page.theme-light .field textarea,
.work-page.theme-light .generated strong,
.work-page.theme-light .genre-preview > div {
  background: #f1f4f7;
  border-color: #b9c5d1;
}

.work-page.theme-light .parser-row input:hover,
.work-page.theme-light .field input:hover,
.work-page.theme-light .field select:hover,
.work-page.theme-light .field textarea:hover {
  border-color: #aab8c6;
}

.work-page.theme-light .authority-note {
  background: #f1f4f7;
  border-color: #bdc9d5;
}

.work-page.theme-light .check-clear {
  background: #f1f5f7;
  border-color: #c1ccd6;
}

.work-page.theme-light .authority-badge.chief {
  background: #eadfc7;
  border-color: #c4ad7d;
}


/* ============================================================
   LIGHT MODE — TURQUOISE CATALOGUE CARDS
   The light theme now mirrors the dark theme's visual structure:
   coloured catalogue cards, distinct fields, and clear hierarchy.
============================================================ */

.work-page.theme-light {
  background: #e7eef0;
}

/* Main catalogue cards: turquoise/blue-green, not white. */
.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card {
  background: #d5eaea;
  border: 1px solid #a9cdcd;
  box-shadow:
    0 2px 5px rgba(20, 67, 70, 0.06),
    0 9px 22px rgba(20, 67, 70, 0.07);
}

/* Section headers are a lighter turquoise layer within each card. */
.work-page.theme-light .section-heading,
.work-page.theme-light .check-heading {
  background: #c9e3e3;
  border-bottom: 1px solid #a9caca;
}

/* Body remains lighter than the card, while retaining the tint. */
.work-page.theme-light .intake-card .parser-row,
.work-page.theme-light .form-card .form-body,
.work-page.theme-light .check-card .check-body {
  background: transparent;
}

/* Inputs remain visibly inset from the turquoise cards. */
.work-page.theme-light .parser-row input,
.work-page.theme-light .field input,
.work-page.theme-light .field select,
.work-page.theme-light .field textarea,
.work-page.theme-light .generated strong,
.work-page.theme-light .genre-preview > div {
  background: #edf6f6;
  border: 1px solid #a9c5c7;
  color: #172f35;
}

.work-page.theme-light .parser-row input:focus,
.work-page.theme-light .field input:focus,
.work-page.theme-light .field select:focus,
.work-page.theme-light .field textarea:focus {
  background: #f8fcfc;
  border-color: #168f8a;
  box-shadow: 0 0 0 3px rgba(22, 143, 138, 0.13);
}

/* Stronger headings on the coloured cards. */
.work-page.theme-light .section-heading h2,
.work-page.theme-light .check-heading h2 {
  color: #17333a;
}

.work-page.theme-light .section-heading p,
.work-page.theme-light .check-heading p {
  color: #4d6870;
}

.work-page.theme-light .section-number {
  color: #087c78;
}

/* Labels need enough contrast against turquoise. */
.work-page.theme-light .field > span {
  color: #38545b;
  font-weight: 700;
}

/* Authority explanation sits outside the catalogue-card system. */
.work-page.theme-light .authority-note {
  background: #f4f7f8;
  border-color: #bdccd1;
}

/* Chief authority remains intentionally gold and therefore stands out
   from the turquoise catalogue surfaces. */
.work-page.theme-light .authority-badge.chief {
  background: #eadfc7;
  border-color: #c4ad7d;
}

.work-page.theme-light .authority-footer {
  background: #f5f8f8;
  border-color: #bdccd1;
  border-left: 3px solid #a98e58;
}

/* Status panel keeps its own neutral treatment. */
.work-page.theme-light .check-clear {
  background: #edf5f5;
  border-color: #b9cdcf;
}

/* Suggestions stay clean and neutral above the tinted cards. */
.work-page.theme-light .suggestions-dropdown {
  background: #ffffff;
  border-color: #b9cbd0;
}

/* Slightly stronger separation between catalogue sections. */
.work-page.theme-light .intake-card,
.work-page.theme-light .form-card,
.work-page.theme-light .check-card {
  margin-bottom: 20px;
}

</style>
