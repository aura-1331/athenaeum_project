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

    <div class="form-section">
      <div class="form-grid">
        <div class="floating-group">
          <input 
            id="title-input-field"
            v-model="form.title" 
            @blur="sanitizeField('title')" 
            maxlength="255" 
            placeholder=" " 
            autocomplete="off"
            class="form-input mandatory-field" 
            :class="{ 'has-value': form.title }"
          />
          <label class="floating-label">Title *</label>
          <button v-if="form.title" @click="clearField('title')" class="clear-btn" type="button" tabindex="-1">&times;</button>
          <span class="char-counter">{{ form.title.length }}/255</span>
          <div v-show="duplicateLoading || isbnLoading" class="embedded-input-spinner"></div>
        </div>

        <div class="floating-group">
          <select v-model="form.language_id" class="form-select mandatory-field" :class="{ 'has-value': form.language_id }">
            <option disabled value="">Select Language *</option>
            <option value="Malayalam">Malayalam</option>
            <option value="English">English</option>
            <option value="Multi -Lingual">Multilingual</option>
            <option disabled class="dropdown-divider-line">──────────────</option>
            <option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option>
          </select>
          <label class="floating-label">Select Language *</label>
        </div>

        <div class="floating-group read-only-group">
          <input 
            :value="previewNumbers.serial_no" 
            disabled 
            placeholder=" " 
            class="form-input structural-lock" 
          />
          <label class="floating-label">Serial No (SL No)</label>
        </div>

        <div class="floating-group read-only-group">
          <input 
            :value="previewNumbers.accession_no" 
            disabled 
            placeholder=" " 
            class="form-input structural-lock" 
          />
          <label class="floating-label">Accession No</label>
        </div>

        <div class="floating-group">
          <select v-model="form.category" class="form-select" :class="{ 'has-value': form.category }">
            <option value="">-- Choose Category (Optional) --</option>
            <option value="Fiction">Fiction</option>
            <option value="Non-Fiction">Non-Fiction</option>
            <option value="Reference">Reference</option>
            <option value="Religious">Religious</option>
            <option value="Poetry">Poetry</option>
          </select>
          <label class="floating-label">Select Category (Optional)</label>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.call_no" 
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 'has-value': form.call_no }"
          />
          <label class="floating-label">Call No</label>
          <button v-if="form.call_no" @click="clearField('call_no')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.author" 
            @focus="showAuthorSuggestions = true"
            @blur="handleBlurAction('author')"
            maxlength="150" 
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 'has-value': form.author }"
          />
          <label class="floating-label">Author</label>
          <button v-if="form.author" @click="clearField('author')" class="clear-btn" type="button" tabindex="-1">&times;</button>
          <span class="char-counter">{{ form.author.length }}/150</span>
          
          <div v-if="showAuthorSuggestions && authorSuggestions.length > 0" class="suggestions-dropdown">
            <div 
              v-for="author in authorSuggestions" 
              :key="author" 
              @mousedown="selectAuthor(author)"
              class="suggestion-item"
            >
              {{ author }}
            </div>
          </div>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.publisher" 
            @focus="showPublisherSuggestions = true"
            @blur="handleBlurAction('publisher')"
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 'has-value': form.publisher }"
          />
          <label class="floating-label">Publisher</label>
          <button v-if="form.publisher" @click="clearField('publisher')" class="clear-btn" type="button" tabindex="-1">&times;</button>
          
          <div v-if="showPublisherSuggestions && publisherSuggestions.length > 0" class="suggestions-dropdown">
            <div 
              v-for="pub in publisherSuggestions" 
              :key="pub" 
              @mousedown="selectPublisher(pub)"
              class="suggestion-item"
            >
              {{ pub }}
            </div>
          </div>
        </div>

        <div class="floating-group full-width">
          <div class="chip-dock-wrapper">
            <label class="dock-label">ACTIVE_COMPILED_GENRE_STRING_PREVIEW</label>
            <div class="chip-assembly-dock">
              <span v-for="chip in liveCompiledGenreChips" :key="chip" class="active-badge-chip">
                {{ chip }}
              </span>
              <span v-if="liveCompiledGenreChips.length === 0" class="dock-empty-text">
                NO GENRES SELECTED
              </span>
            </div>
          </div>
        </div>

        <div class="floating-group full-width">
          <div class="split-genre-selectors">
            <div class="dropdown-wrapper">
              <select v-model="selectedGroupAGenre" @change="syncGenreSelection" class="form-select select-compact">
                <option value="">Genre Group A // Creative</option>
                <option v-for="g in genreGroupA" :key="g" :value="g">{{ g }}</option>
              </select>
            </div>
            <div class="dropdown-wrapper">
              <select v-model="selectedGroupBGenre" @change="syncGenreSelection" class="form-select select-compact">
                <option value="">Genre Group B // Factual</option>
                <option v-for="g in genreGroupB" :key="g" :value="g">{{ g }}</option>
              </select>
            </div>
            <div class="dropdown-wrapper">
              <select v-model="selectedGroupCGenre" @change="syncGenreSelection" class="form-select select-compact">
                <option value="">Genre Group C // User Added</option>
                <option v-for="g in dynamicCommunityGenres" :key="g" :value="g">{{ g }}</option>
                <option disabled class="dropdown-divider-line">────────────────────</option>
                <option value="CUSTOM_MANUAL_OVERRIDE">[X] TYPE_MANUAL_INPUT</option>
              </select>
            </div>
          </div>
        </div>

        <div class="floating-group full-width manual-override-animation" v-if="showCustomManualGenreField">
          <input 
            type="text" 
            v-model="customManualGenreText" 
            @input="syncManualGenreInput"
            placeholder="ENTER CUSTOM GENRES SEPARATED BY SLASH (E.G. ENGINEERING/PROPULSION)" 
            class="form-input manual-text-input" 
          />
          <label class="floating-label active-amber-label">Manual Genre Override</label>
        </div>

        <div class="floating-group">
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

        <div class="floating-group">
          <input 
            id="isbn-input-field"
            v-model="form.isbn" 
            placeholder=" " 
            autocomplete="off"
            class="form-input"
            :class="{ 
              'has-value': form.isbn,
              'valid-field': isIsbnValid === true, 
              'invalid-field': isIsbnValid === false 
            }"
          />
          <label class="floating-label">ISBN</label>
          <button v-if="form.isbn" @click="clearField('isbn')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            id="year-input-field"
            v-model="form.year" 
            placeholder=" " 
            autocomplete="off"
            class="form-input"
            :class="{ 
              'has-value': form.year,
              'valid-field': isYearValid === true, 
              'invalid-field': isYearValid === false 
            }"
          />
          <label class="floating-label">Year (YYYY)</label>
          <button v-if="form.year" @click="clearField('year')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            id="ddc-input-field"
            v-model="form.ddc" 
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 
              'has-value': form.ddc,
              'valid-field': isDdcValid === true,
              'invalid-field': isDdcValid === false
            }"
          />
          <label class="floating-label">DDC</label>
          <button v-if="form.ddc" @click="clearField('ddc')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.shelf" 
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 'has-value': form.shelf }"
          />
          <label class="floating-label">Shelf</label>
          <button v-if="form.shelf" @click="clearField('shelf')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>

        <div class="floating-group">
          <input 
            v-model="form.translation_compilation" 
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 'has-value': form.translation_compilation }"
          />
          <label class="floating-label">Translation/Compilation</label>
          <button v-if="form.translation_compilation" @click="clearField('translation_compilation')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>

        <div class="floating-group full-width">
          <input 
            v-model="form.notes" 
            placeholder=" " 
            autocomplete="off"
            class="form-input" 
            :class="{ 'has-value': form.notes }"
          />
          <label class="floating-label">Notes</label>
          <button v-if="form.notes" @click="clearField('notes')" class="clear-btn" type="button" tabindex="-1">&times;</button>
        </div>
      </div>

      <div class="system-feedback-panel">
        <div class="skeleton-loader-banner" v-show="duplicateLoading || isbnLoading">
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

          <div class="override-container" v-if="duplicateResult.severity === 'strong'">
            <label class="checkbox-label">
              <input type="checkbox" v-model="adminOverride" class="custom-checkbox" />
              <span>Admin Override — allow creation anyway</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <div class="form-actions-footer">
      <button
        @click="triggerCreationPrompt"
        :disabled="loading || isFrozen"
        class="submit-btn"
        :class="{ 'btn-frozen': isFrozen }"
      >
        <span v-if="isFrozen">🔒 Authority Locked</span>
        <span v-else>{{ loading ? "Saving Record..." : "Create Work" }}</span>
      </button>
      <span class="shortcut-legend">Press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to save</span>
    </div>

    <div class="modal-overlay-shroud" v-if="showPromptModal">
      <div class="modal-alert-box border-emerald">
        <div class="modal-tag">SYSTEM_TRANSACTION_ALERT</div>
        
        <h3 class="modal-heading">CONFIRM AUTHORITY RECORD REGISTRATION</h3>
        
        <p class="modal-body-text">
          You are establishing a new master authority entry layout within the security ledger registry context matrices.
        </p>

        <div class="modal-input-field-block">
          <label class="modal-input-label">SPECIFY_OPERATIONAL_CHANGE_JUSTIFICATION</label>
          <input 
            type="text" 
            v-model="creationReason" 
            placeholder="e.g., Initial acquisition entry / New community catalog release..." 
            class="modal-reason-input"
          />
        </div>

        <div class="modal-button-row">
          <button class="m-btn m-btn-confirm bg-emerald" @click="executeConfirmedCreation">
            EXECUTE
          </button>
          <button class="m-btn m-btn-dismiss" @click="showPromptModal = false">
            DISMISS
          </button>
        </div>
      </div>
    </div>

    <div v-if="result" class="operational-response-deck">
      <div v-if="result.work_id" class="status-card-panel border-emerald">
        <div class="deck-tag text-emerald">TRANSACTION_SUCCESSFUL // REGISTRY_LINK_ACTIVE</div>
        <div class="panel-main-row">
          <div class="stat-block">
            <span class="stat-label">ASSIGNED_WORK_ID</span>
            <span class="stat-value text-white">#{{ result.work_id }}</span>
          </div>
          <div class="stat-block">
            <span class="stat-label">GENERATED_ACCESSION_NO</span>
            <span class="stat-value text-gold">{{ result.accession_no }}</span>
          </div>
        </div>
        <div class="panel-footer-message">
          <div class="spinner-inline"></div>
          <span>Redirecting to local item ledger initialization sequences...</span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-fill fill-emerald"></div>
        </div>
      </div>

      <div v-else class="status-card-panel border-crimson">
        <div class="deck-tag text-crimson">TRANSACTION_ABORTED // SCHEMA_VALIDATION_FAILURE</div>
        <h4 class="error-heading">Operational Request Interrupted</h4>
        <p class="error-description">
          {{ result.detail || result.error || "The remote catalog authority engine rejected this entity context structure layout mapping." }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"

const router = useRouter()
const pasteInput = ref("")
const isParsing = ref(false)
const showAuthorSuggestions = ref(false)
const showPublisherSuggestions = ref(false)

const showPromptModal = ref(false)
const creationReason = ref("")

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
    if (!newVal) return
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
  const isbnMatch = text.match(/(?:ISBN(?:\-1[03])?:?\s*)?([0-9X]{10,13})/i)
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

  showPromptModal.value = false
  loading.value = true
  result.value = null

  try {
    const cleanedForm = {}
    Object.keys(form.value).forEach(key => {
      cleanedForm[key] = form.value[key] === "" ? null : form.value[key]
    })

    if (!cleanedForm.genre || cleanedForm.genre.trim() === "") {
      cleanedForm.genre = null
    }

    const payload = { 
      ...cleanedForm, 
      author: form.value.author.trim() || "Unknown",
      language: form.value.language_id || null,
      call_no: form.value.call_no || null 
    }
    
    const operationalReason = creationReason.value.trim() || "New registration initialization sequencing"

    const res = await axios.post("/catalogue/create-work", payload, {
      headers: {
        'X-Change-Reason': operationalReason,
        'X-Device-ID': auditData.value.deviceID,
        'X-IP-Address': auditData.value.ip
      }
    })
    
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
    result.value = err.response?.data || { error: "Request failed." }
  } finally {
    loading.value = false
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
  await harvestSystemGenresMatrix()
  focusNextField("parser-field-input")
})

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown)
})
</script>

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
  color: #a3a8b4;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.parser-field:focus {
  border-color: #cfb997;
}

.form-section {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 32px;
  background: #111111;
  border: 1px solid #1c1c1c;
  border-radius: 6px;
  padding: 24px;
  align-items: start;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.system-feedback-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  min-height: 200px;
}

.floating-group {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  height: 48px !important;
  max-height: 48px !important;
  min-height: 48px !important;
  box-sizing: border-box !important;
}

.floating-group.full-width {
  grid-column: span 2;
  height: auto !important;
  max-height: none !important;
  min-height: auto !important;
}

.form-input, 
.form-select {
  width: 100%;
  height: 48px !important;
  max-height: 48px !important;
  min-height: 48px !important;
  padding: 0 40px 0 16px;
  background: #161616;
  border: 1px solid #282828;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 14px;
  outline: none;
  box-sizing: border-box !important;
  line-height: 46px !important;
}

.mandatory-field {
  border-left: 3px solid #cfb997;
}

.structural-lock {
  background: #141414;
  border-color: #1f1f1f;
  color: #666666;
  cursor: not-allowed;
}

.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www' viewBox='0 0 24 24' fill='none' stroke='%238c8c8c' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 16px center;
  background-size: 16px;
  padding-right: 40px;
}

.floating-label {
  position: absolute;
  left: 14px;
  top: 50% !important;
  transform: translateY(-50%) !important;
  color: #555555;
  font-size: 14px;
  pointer-events: none;
  background: #111111;
  padding: 0 4px;
  transition: transform 0.15s ease, top 0.15s ease, font-size 0.15s ease;
  line-height: 1 !important;
}

.read-only-group .floating-label {
  background: #141414;
}

.form-input:focus, 
.form-select:focus {
  border-color: #cfb997;
  background: #1a1a1a;
}

.form-input:focus ~ .floating-label,
.form-input.has-value ~ .floating-label,
.form-select:focus ~ .floating-label,
.form-select.has-value ~ .floating-label,
.structural-lock ~ .floating-label {
  top: 0 !important;
  transform: translateY(-50%) !important;
  font-size: 11px;
  color: #cfb997;
}

.structural-lock ~ .floating-label {
  color: #555555;
}

.form-input.valid-field,
.form-input.valid-field:focus {
  border-color: #10b981;
}

.form-input.invalid-field,
.form-input.invalid-field:focus {
  border-color: #ef4444;
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
}

.clear-btn:hover {
  color: #ea585c;
}

.floating-group:focus-within .char-counter {
  opacity: 0.6;
}

.char-counter {
  position: absolute;
  right: 40px;
  bottom: 4px;
  font-size: 10px;
  color: #555555;
  opacity: 0;
  pointer-events: none;
  z-index: 5;
  line-height: 1 !important;
}

.embedded-input-spinner {
  position: absolute;
  right: 40px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  border: 2px solid #282828;
  border-top-color: #cfb997;
  border-radius: 50%;
  animation: spinInline 0.6s linear infinite;
  pointer-events: none;
  z-index: 4;
}

.chip-dock-wrapper {
  width: 100%;
  background-color: #16181f;
  border: 1px solid #22252e;
  border-radius: 6px;
  padding: 14px 18px;
  box-sizing: border-box;
}

.dock-label {
  font-size: 9px;
  font-weight: 700;
  color: #525966;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 8px;
}

.chip-assembly-dock {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.active-badge-chip {
  font-size: 10px;
  font-weight: bold;
  background-color: rgba(236, 72, 153, 0.08);
  border: 1px solid rgba(236, 72, 153, 0.2);
  color: #ec4899;
  padding: 2px 8px;
  border-radius: 4px;
}

.dock-empty-text {
  font-size: 12px;
  color: #525966;
  font-style: italic;
}

.split-genre-selectors {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  width: 100%;
}

.dropdown-wrapper {
  position: relative;
  width: 100%;
}

.select-compact {
  height: 44px !important;
  font-size: 13px !important;
  border-left: none !important;
  cursor: pointer;
}

.manual-override-animation {
  margin-top: 4px;
}

.manual-text-input {
  border-color: rgba(245, 158, 11, 0.3) !important;
}

.manual-text-input:focus {
  border-color: #f59e0b !important;
}

.active-amber-label {
  color: #f59e0b !important;
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
}

.submit-btn:hover:not(:disabled) {
  background: #e5cfab;
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
  border-radius: 6px;
  font-size: 14px;
  width: 100%;
  box-sizing: border-box;
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
  flex-direction: column;
  gap: 8px;
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
  width: 100%;
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
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  background: #141414;
  border: 1px solid #1c1c1c;
  border-radius: 6px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  box-sizing: border-box;
  z-index: 5;
}

.skeleton-line {
  background: linear-gradient(90deg, #1f1f1f 25%, #2c2c2c 50%, #1f1f1f 75%);
  background-size: 200% 100%;
  animation: loadingPulse 1.5s infinite ease-in-out;
  border-radius: 4px;
}

.skeleton-line.header-pulse {
  width: 120px;
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

.modal-overlay-shroud { 
  position: fixed; 
  top: 0; 
  left: 0; 
  width: 100vw; 
  height: 100vh; 
  background-color: rgba(10, 11, 13, 0.85); 
  backdrop-filter: blur(4px); 
  z-index: 10000; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  box-sizing: border-box;
}
.modal-alert-box { background-color: #16181f; border-top: 4px solid #22252e; padding: 40px; border-radius: 8px; width: 100%; max-width: 480px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); display: flex; flex-direction: column; }
.border-emerald { border-top-color: #10b981; }
.modal-tag { font-size: 10px; font-weight: 700; color: #525966; letter-spacing: 2px; margin-bottom: 16px; text-transform: uppercase; }
.modal-heading { font-size: 18px; font-weight: 700; color: #ffffff; margin: 0 0 16px 0; letter-spacing: 0.5px; }
.modal-body-text { font-size: 13px; line-height: 1.6; color: #a3a8b4; margin: 0 0 24px 0; font-family: inherit; }
.modal-input-field-block { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; width: 100%; box-sizing: border-box; }
.modal-input-label { font-size: 10px; font-weight: 700; color: #cfb997; letter-spacing: 1px; }
.modal-reason-input { background-color: #111216; border: 1px solid #22252e; border-radius: 4px; padding: 12px; font-family: inherit; font-size: 13px; color: #ffffff; width: 100%; box-sizing: border-box; }
.modal-reason-input:focus { outline: none; border-color: #cfb997; }
.modal-button-row { display: flex; justify-content: flex-end; gap: 16px; }
.m-btn { font-family: inherit; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }
.bg-emerald { background-color: #10b981; color: #ffffff; }
.bg-emerald:hover { background-color: #059669; }
.m-btn-dismiss { background-color: transparent; border: 1px solid #2e333d; color: #e2e4e9; }
.m-btn-dismiss:hover { background-color: rgba(255,255,255,0.03); }

.operational-response-deck {
  margin-top: 28px;
  width: 100%;
}

.status-card-panel {
  background-color: #16181f;
  border: 1px solid #22252e;
  border-top: 4px solid #22252e;
  border-radius: 6px;
  padding: 24px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.border-crimson {
  border-top-color: #ef4444 !important;
}

.text-emerald {
  color: #10b981 !important;
}

.text-crimson {
  color: #ef4444 !important;
}

.text-white {
  color: #ffffff;
}

.text-gold {
  color: #cfb997;
}

.deck-tag {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 16px;
  text-transform: uppercase;
}

.panel-main-row {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
}

.stat-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-block .stat-label {
  font-size: 10px;
  font-weight: 700;
  color: #525966;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  font-family: monospace;
}

.panel-footer-message {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 12px;
}

.spinner-inline {
  width: 12px;
  height: 12px;
  border: 2px solid #22252e;
  border-top-color: #10b981;
  border-radius: 50%;
  animation: spinInline 0.8s linear infinite;
}

.progress-bar-container {
  width: 100%;
  height: 3px;
  background-color: #111216;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  width: 0%;
  animation: loadTransition 0.4s forwards cubic-bezier(0.1, 0.8, 0.3, 1);
}

.fill-emerald {
  background-color: #10b981;
}

.error-heading {
  font-size: 14px;
  font-weight: 600;
  color: #e2e4e9;
  margin: 0 0 6px 0;
}

.error-description {
  font-size: 13px;
  line-height: 1.5;
  color: #a3a8b4;
  margin: 0;
  font-family: monospace;
  background-color: #0f1015;
  padding: 12px;
  border: 1px solid #1c1e24;
  border-radius: 4px;
  word-break: break-all;
}

@keyframes spinInline {
  to { transform: rotate(360deg); }
}

@keyframes loadTransition {
  to { width: 100%; }
}
</style>