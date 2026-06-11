<template>
  <div class="control-panel-layout">
    <div v-if="loading" class="vault-loader">
      <div class="minimal-spinner"></div>
      <span class="loading-label">RETRIEVING_WRITE_AUTHORIZATION</span>
    </div>

    <div v-else-if="editableBook" class="panel-container">
      
      <aside class="identity-anchor-panel">
        <div class="panel-badge">REVISION_STATION_01</div>
        
        <div class="hero-identity-block">
          <span class="meta-label">CURRENTLY EDITING</span>
          <h1 class="display-title">{{ editableBook.title }}</h1>
          <p class="display-author">BY {{ editableBook.author || 'UNKNOWN' }}</p>
        </div>

        <div class="system-status-matrix">
          <div class="status-node">
            <span>REGISTRY RANK</span>
            <strong class="rank-badge">{{ auditData.userRole }}</strong>
          </div>
          <div class="status-node">
            <span>INDEX MARKER</span>
            <strong class="font-mono">#{{ editableBook.serial_no }}</strong>
          </div>
        </div>

        <div class="panel-actions-stack">
          <button class="btn btn-filled" @click="triggerActionConfirm('commit')">COMMIT CHANGES</button>
          <button class="btn btn-outline" @click="triggerActionConfirm('abort')">ABORT TRANSACTION</button>
        </div>
      </aside>

      <main class="form-feed-column">
        <div class="form-scroll-wrapper">
          
          <fieldset class="form-fieldset">
            <legend class="fieldset-legend">01 // CORE PROFILE IDENTITY</legend>
            
            <div class="form-row">
              <div class="field-container full-width">
                <label class="input-label">BOOK TITLE</label>
                <input type="text" v-model="editableBook.title" class="panel-input font-emphasis" />
              </div>
            </div>

            <div class="form-row">
              <div class="field-container full-width relative-position">
                <label class="input-label">AUTHOR</label>
                <input 
                  type="text" 
                  v-model="editableBook.author" 
                  @input="searchAuthorsDebounced"
                  @focus="showAuthorSuggestions = true"
                  @blur="hideSuggestionsWithDelay('author')"
                  class="panel-input" 
                />
                <div v-if="showAuthorSuggestions && authorSuggestions.length > 0" class="typeahead-overlay-tray">
                  <div 
                    v-for="suggestion in authorSuggestions" 
                    :key="suggestion"
                    @click="selectSuggestion('author', suggestion)"
                    class="typeahead-node"
                  >
                    {{ suggestion }}
                  </div>
                </div>
              </div>
            </div>
          </fieldset>

          <fieldset 
            v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
            class="form-fieldset"
          >
            <legend class="fieldset-legend">02 // REGISTRY TOKENS & CLEARANCE</legend>
            
            <div class="form-row split-2">
              <div class="field-container disabled-container">
                <label class="input-label">RECORD IDENTIFIER</label>
                <div class="static-value font-mono">{{ editableBook.record_id }}</div>
              </div>
              <div class="field-container disabled-container">
                <label class="input-label">WORK ID</label>
                <div class="static-value font-mono text-amber">{{ editableBook.work_id }}</div>
              </div>
            </div>

            <div class="form-row split-2">
              <div class="field-container disabled-container">
                <label class="input-label">ACCESSION NO</label>
                <div class="static-value font-mono text-blue">{{ editableBook.accession_no }}</div>
              </div>
              <div class="field-container disabled-container">
                <label class="input-label">SERIAL NO</label>
                <div class="static-value font-mono text-magenta">{{ editableBook.serial_no }}</div>
              </div>
            </div>
          </fieldset>

          <fieldset 
            v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
            class="form-fieldset"
          >
            <legend class="fieldset-legend">03 // LOCATION & METADATA VECTORS</legend>
            
            <div class="form-row split-2">
              <div class="field-container contextual-bg">
                <label class="input-label">SHELF LOCATION</label>
                <input type="text" v-model="editableBook.shelf" class="panel-input font-mono font-bold" />
              </div>
              <div class="field-container contextual-bg">
                <label class="input-label">CALL NUMBER</label>
                <input type="text" v-model="editableBook.call_no" class="panel-input font-mono font-bold" />
              </div>
            </div>

            <div class="form-row split-3">
              <div class="field-container disabled-container">
                <label class="input-label">TEXT LANGUAGE</label>
                <div class="static-value font-bold text-gray-lock">{{ editableBook.language }}</div>
              </div>
              <div class="field-container">
                <label class="input-label">ORIGINAL LANGUAGE</label>
                <input type="text" v-model="editableBook.original_language" class="panel-input size-compact" />
              </div>
              <div class="field-container">
                <label class="input-label">CATEGORY</label>
                <select v-model="editableBook.category" class="panel-select-menu size-compact">
                  <option value="">-- NONE / UNASSIGNED --</option>
                  <option value="Fiction">Fiction</option>
                  <option value="Non-Fiction">Non-Fiction</option>
                  <option value="Reference">Reference</option>
                  <option value="Religious">Religious</option>
                </select>
              </div>
            </div>

            <div class="form-row split-2">
              <div class="field-container relative-position">
                <label class="input-label">PUBLISHER</label>
                <input 
                  type="text" 
                  v-model="editableBook.publisher" 
                  @input="searchPublishersDebounced"
                  @focus="showPublisherSuggestions = true"
                  @blur="hideSuggestionsWithDelay('publisher')"
                  class="panel-input size-compact" 
                />
                <div v-if="showPublisherSuggestions && publisherSuggestions.length > 0" class="typeahead-overlay-tray">
                  <div 
                    v-for="suggestion in publisherSuggestions" 
                    :key="suggestion"
                    @click="selectSuggestion('publisher', suggestion)"
                    class="typeahead-node"
                  >
                    {{ suggestion }}
                  </div>
                </div>
              </div>
              <div class="field-container">
                <label class="input-label">YEAR</label>
                <input type="text" v-model="editableBook.year" class="panel-input size-compact font-mono" />
              </div>
            </div>

            <div class="form-row split-2">
              <div class="field-container">
                <label class="input-label">ISBN</label>
                <input type="text" v-model="editableBook.isbn" class="panel-input size-compact font-mono" />
              </div>
              <div class="field-container">
                <label class="input-label">DDC</label>
                <input type="text" v-model="editableBook.ddc" class="panel-input size-compact font-mono" />
              </div>
            </div>

            <div class="form-row">
              <div class="field-container full-width layout-transparent">
                <label class="input-label">GENRE PREVIEW</label>
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

            <div class="form-row split-3">
              <div class="field-container">
                <label class="input-label">CREATIVE GENRES (GROUP A)</label>
                <select v-model="selectedGroupAGenre" @change="syncGenreSelection" class="panel-select-menu size-compact">
                  <option value="">-- CHOOSE GENRE --</option>
                  <option v-for="g in genreGroupA" :key="g" :value="g">{{ g }}</option>
                </select>
              </div>

              <div class="field-container">
                <label class="input-label">FACTUAL GENRES (GROUP B)</label>
                <select v-model="selectedGroupBGenre" @change="syncGenreSelection" class="panel-select-menu size-compact">
                  <option value="">-- CHOOSE GENRE --</option>
                  <option v-for="g in genreGroupB" :key="g" :value="g">{{ g }}</option>
                </select>
              </div>

              <div class="field-container">
                <label class="input-label">USER ADDED GENRES (GROUP C)</label>
                <select v-model="selectedGroupCGenre" @change="syncGenreSelection" class="panel-select-menu size-compact">
                  <option value="">-- CHOOSE GENRE --</option>
                  <option v-for="g in dynamicCommunityGenres" :key="g" :value="g">{{ g }}</option>
                  <option disabled class="dropdown-divider-line">────────────────────</option>
                  <option value="CUSTOM_MANUAL_OVERRIDE">[X] TYPE MANUAL INPUT</option>
                </select>
              </div>
            </div>

            <div v-if="showCustomManualGenreField" class="form-row">
              <div class="field-container full-width border-amber">
                <label class="input-label text-amber">MANUAL GENRE OVERRIDE (USE '/' FOR MULTIPLES)</label>
                <input 
                  type="text" 
                  v-model="customManualGenreText" 
                  @input="syncManualGenreInput"
                  placeholder="E.G. HISTORY/SCIENCE/PROPULSION" 
                  class="panel-input font-mono" 
                />
              </div>
            </div>
          </fieldset>

          <fieldset class="form-fieldset">
            <legend class="fieldset-legend">04 // CURATORIAL REMARKS & LOGS</legend>
            <div class="form-row">
              <div class="field-container full-width plaintext-wrapper">
                <label class="input-label">NOTES / REMARKS</label>
                <textarea v-model="editableBook.notes" class="panel-textarea" rows="6"></textarea>
              </div>
            </div>
          </fieldset>

        </div>
      </main>

    </div>

    <div v-if="toast" class="toast-banner-notification" :class="toast.type">
      <span class="toast-indicator"></span>
      <span class="toast-message-label">{{ toast.message }}</span>
    </div>

    <div v-if="activeModalType" class="modal-overlay-shroud">
      <div class="modal-alert-box" :class="activeModalType === 'commit' ? 'border-emerald' : 'border-crimson'">
        <div class="modal-tag">SYSTEM_TRANSACTION_ALERT</div>
        
        <h3 class="modal-heading">
          {{ activeModalType === 'commit' ? 'CONFIRM WRITE OPERATION?' : 'ABORT CURRENT TRANSACTION?' }}
        </h3>
        
        <p class="modal-body-text">
          {{ activeModalType === 'commit' 
              ? 'You are committing new modifications to the centralized database matrix. This record will update across all client node networks.' 
              : 'You are abandoning all pending modifications. Uncommitted form changes will be completely deleted from temporary session memory.' 
          }}
        </p>

        <div v-if="activeModalType === 'commit'" class="modal-input-field-block">
          <label class="modal-input-label">SPECIFY OPERATIONAL CHANGE JUSTIFICATION</label>
          <input 
            type="text" 
            v-model="changeReason" 
            placeholder="e.g., Fixing spelling error / Adding storage context notes..." 
            class="modal-reason-input"
          />
        </div>

        <div class="countdown-ticker-bar">
          AUTO-RESOLVING IN: <span class="ticker-value">{{ countdownTimerSeconds }}s</span>
        </div>

        <div class="modal-button-row">
          <button 
            class="m-btn m-btn-confirm" 
            :class="activeModalType === 'commit' ? 'bg-emerald' : 'bg-crimson'"
            @click="executeConfirmedAction"
          >
            EXECUTE
          </button>
          <button class="m-btn m-btn-dismiss" @click="closeModalPrompt">
            DISMISS
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"
import { dispatchAuditTrail } from '@/utils/audit';

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const editableBook = ref<any>(null)

const activeModalType = ref<string | null>(null)
const changeReason = ref<string>("")
const countdownTimerSeconds = ref<number>(0)
let nativeIntervalReference: any = null

interface ToastNotification {
  message: string
  type: 'success' | 'error'
}
const toast = ref<ToastNotification | null>(null)

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

const dynamicCommunityGenres = ref<string[]>([])

const selectedGroupAGenre = ref("")
const selectedGroupBGenre = ref("")
const selectedGroupCGenre = ref("")
const showCustomManualGenreField = ref(false)
const customManualGenreText = ref("")

const authorSuggestions = ref<string[]>([])
const publisherSuggestions = ref<string[]>([])
const showAuthorSuggestions = ref(false)
const showPublisherSuggestions = ref(false)

let debounceAuthorTimeout: any = null
let debouncePublisherTimeout: any = null

const auditData = ref({
  deviceID: "EDITORIAL-CARDS-STATION-01",
  ip: "192.168.1.105", 
  userName: "System Archivist",
  userRole: "The Chief" 
})

const liveCompiledGenreChips = computed(() => {
  if (!editableBook.value?.genre) return []
  return editableBook.value.genre.split('/').map((g: string) => g.trim().toUpperCase()).filter((g: string) => g.length > 0)
})

function triggerToastNotification(message: string, type: 'success' | 'error') {
  toast.value = { message, type }
  setTimeout(() => {
    toast.value = null
  }, 4000)
}

function parseCurrentGenresIntoDropdowns(genreString: string) {
  if (!genreString) return
  const currentTokens = genreString.split('/').map((g: string) => g.trim().toUpperCase())
  
  let matchedAny = false
  currentTokens.forEach(token => {
    if (genreGroupA.value.includes(token)) {
      selectedGroupAGenre.value = token
      matchedAny = true
    } else if (genreGroupB.value.includes(token)) {
      selectedGroupBGenre.value = token
      matchedAny = true
    } else if (dynamicCommunityGenres.value.includes(token)) {
      selectedGroupCGenre.value = token
      matchedAny = true
    }
  })

  if (!matchedAny && genreString.trim() !== "") {
    showCustomManualGenreField.value = true
    selectedGroupCGenre.value = "CUSTOM_MANUAL_OVERRIDE"
    customManualGenreText.value = genreString
  }
}

function syncGenreSelection() {
  if (selectedGroupCGenre.value === "CUSTOM_MANUAL_OVERRIDE") {
    showCustomManualGenreField.value = true
    editableBook.value.genre = customManualGenreText.value.trim().toUpperCase() || null
    return
  }
  
  showCustomManualGenreField.value = false
  const activeSelectionArray: string[] = []
  
  if (selectedGroupAGenre.value) activeSelectionArray.push(selectedGroupAGenre.value)
  if (selectedGroupBGenre.value) activeSelectionArray.push(selectedGroupBGenre.value)
  if (selectedGroupCGenre.value && selectedGroupCGenre.value !== "CUSTOM_MANUAL_OVERRIDE") {
    activeSelectionArray.push(selectedGroupCGenre.value)
  }
  
  editableBook.value.genre = activeSelectionArray.join('/') || null
  customManualGenreText.value = editableBook.value.genre || ""
}

function syncManualGenreInput() {
  editableBook.value.genre = customManualGenreText.value.trim().toUpperCase() || null
}

async function harvestSystemGenresMatrix() {
  try {
    const response = await axios.get('/catalogue?limit=1000')
    const items = response.data?.data || []
  } catch (err) {
    console.error("Failed to dynamically harvest global taxonomy metrics:", err)
  }
}

function searchAuthorsDebounced() {
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  debounceAuthorTimeout = setTimeout(async () => {
    const query = editableBook.value.author.trim()
    if (query.length < 2) {
      authorSuggestions.value = []
      return
    }
    try {
      const response = await axios.get(`/catalogue/authors/search?q=${encodeURIComponent(query)}`)
      authorSuggestions.value = response.data || []
    } catch (err) {
      console.error("Author micro-lookup breakdown:", err)
    }
  }, 200)
}

function searchPublishersDebounced() {
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
  debouncePublisherTimeout = setTimeout(async () => {
    const query = editableBook.value.publisher.trim()
    if (query.length < 2) {
      publisherSuggestions.value = []
      return
    }
    try {
      const response = await axios.get(`/catalogue/publishers/search?q=${encodeURIComponent(query)}`)
      publisherSuggestions.value = response.data || []
    } catch (err) {
      console.error("Publisher micro-lookup breakdown:", err)
    }
  }, 200)
}

function selectSuggestion(type: 'author' | 'publisher', value: string) {
  if (type === 'author') {
    editableBook.value.author = value
    authorSuggestions.value = []
    showAuthorSuggestions.value = false
  } else {
    editableBook.value.publisher = value
    publisherSuggestions.value = []
    showPublisherSuggestions.value = false
  }
}

function hideSuggestionsWithDelay(type: 'author' | 'publisher') {
  setTimeout(() => {
    if (type === 'author') showAuthorSuggestions.value = false
    else showPublisherSuggestions.value = false
  }, 250)
}

async function fetchRecordData() {
  loading.value = true
  const id = route.params.id
  try {
    await harvestSystemGenresMatrix()
    const response = await axios.get(`/catalogue/${id}`)
    editableBook.value = { ...response.data }
    
    if (editableBook.value) {
      parseCurrentGenresIntoDropdowns(editableBook.value.genre)
    }
  } catch (err) {
    console.error("Database loading exception:", err)
  } finally {
    loading.value = false
  }
}

function triggerActionConfirm(actionType: 'commit' | 'abort') {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  
  activeModalType.value = actionType
  changeReason.value = ""
  countdownTimerSeconds.value = 15
  
  nativeIntervalReference = setInterval(() => {
    countdownTimerSeconds.value--
    if (countdownTimerSeconds.value <= 0) {
      clearInterval(nativeIntervalReference)
      executeConfirmedAction()
    }
  }, 1000)
}

function executeConfirmedAction() {
  const targetAction = activeModalType.value
  
  if (targetAction === 'commit') {
    saveRecord()
  } else if (targetAction === 'abort') {
    cancelEdit()
  }
  closeModalPrompt()
}

function closeModalPrompt() {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  activeModalType.value = null
}

async function saveRecord() {
  const id = route.params.id || editableBook.value?.serial_no;
  try {
    const operationalReason = changeReason.value.trim() || "Routine operational adjustment";
    
    // 1. Perform the database update
    const response = await axios.patch(`/catalogue/${id}`, editableBook.value, {
      headers: {
        'X-Change-Reason': operationalReason
      }
    });
    
    // 2. Dispatch the Audit Trail entry
    await dispatchAuditTrail(
      'UPDATE',
      'CATALOGUE',
      id,
      `Updated record details for ${editableBook.value.title}`,
      operationalReason,
      null, // oldState
      editableBook.value // newState
    );
    
    triggerToastNotification("Authority entry modifications saved successfully.", "success");
    
    setTimeout(() => {
      router.push(`/details/${id}`);
    }, 1500);
  } catch (err) {
    console.error("Transaction commit rejected:", err);
    triggerToastNotification("Write Failure: Transaction aborted.", "error");
  }
}

function cancelEdit() {
  router.push(`/details/${route.params.id}`)
}

onBeforeUnmount(() => {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
})

onMounted(() => fetchRecordData())
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800&family=JetBrains+Mono:wght@400;700&display=swap');

.control-panel-layout {
  background-color: #111216;
  color: #e2e4e9;
  position: fixed !important;
  top: 0 !important; left: 0 !important;
  width: 100vw !important; height: 100vh !important;
  z-index: 9999 !important;
  display: flex; overflow: hidden;
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
  margin: 0 !important; padding: 0 !important;
}

.panel-container {
  display: flex;
  width: 100% !important; height: 100% !important;
  margin: 0 !important; padding: 0 !important;
}

.identity-anchor-panel {
  width: 420px; background-color: #0a0b0d !important;
  border-right: 1px solid #1c1f26 !important;
  padding: 48px; display: flex; flex-direction: column; box-sizing: border-box; flex-shrink: 0;
}

.panel-badge { font-size: 10px; font-weight: bold; color: #525966; letter-spacing: 2px; margin-bottom: 40px; }
.hero-identity-block { margin-bottom: auto; }
.meta-label { font-size: 9px; color: #626a7a; letter-spacing: 1px; display: block; margin-bottom: 8px; }
.display-title { font-family: 'Cinzel', serif; font-size: 28px; font-weight: 800; line-height: 1.2; color: #ffffff; margin: 0 0 12px 0; }
.display-author { font-size: 12px; color: #a3a8b4; margin: 0; }

.system-status-matrix {
  background-color: #111216; border: 1px solid #1c1f26; border-radius: 8px; padding: 16px; margin-bottom: 32px; display: flex; flex-direction: column; gap: 12px;
}
.status-node { display: flex; justify-content: space-between; align-items: center; font-size: 11px; }
.status-node span { color: #525966; font-weight: bold; }
.rank-badge { color: #10b981; text-transform: uppercase; }

.panel-actions-stack { display: flex; flex-direction: column; gap: 14px; }
.btn { font-family: inherit; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 14px; border: none; border-radius: 6px; cursor: pointer; text-align: center; transition: background-color 0.15s ease; }
.btn-filled { background-color: #e2e4e9; color: #111216; }
.btn-filled:hover { background-color: #cdd1da; }
.btn-outline { border: 1px solid #2e333d; color: #e2e4e9; background: transparent; }
.btn-outline:hover { background-color: rgba(255,255,255,0.03); }

.form-feed-column { flex-grow: 1; height: 100%; overflow-y: auto; background-color: #111216; }
.form-scroll-wrapper { padding: 48px 64px 64px 64px; max-width: 900px; box-sizing: border-box; }
.form-feed-column::-webkit-scrollbar { width: 6px; }
.form-feed-column::-webkit-scrollbar-track { background: #111216; }
.form-feed-column::-webkit-scrollbar-thumb { background: #22252e; border-radius: 3px; }

.form-fieldset { border: none; margin: 0 0 40px 0; padding: 0; }
.fieldset-legend { font-size: 11px; font-weight: 700; letter-spacing: 1.5px; color: #626a7a; border-bottom: 1px solid #22252e; width: 100%; padding-bottom: 12px; margin-bottom: 24px; }

.form-row { display: flex; gap: 20px; margin-bottom: 20px; }
.form-row:last-child { margin-bottom: 0; }
.split-2 > .field-container { width: 50%; }
.split-3 > .field-container { width: 33.33%; }
.full-width { width: 100%; }

.field-container { display: flex; flex-direction: column; gap: 4px; background-color: #16181f; border: 1px solid #22252e; padding: 14px 18px; border-radius: 8px; box-sizing: border-box; transition: border-color 0.2s ease; }
.field-container:focus-within { border-color: #4a5263; }
.disabled-container { background-color: #12141a !important; border-color: #1c1f26 !important; }
.contextual-bg { background-color: #13151b; border-color: #1e212a; }
.layout-transparent { background-color: transparent !important; border: 1px dashed #22252e !important; }
.border-amber { border-color: rgba(245, 158, 11, 0.4) !important; }

.input-label { font-size: 10px; font-weight: 700; color: #626a7a; letter-spacing: 0.5px; }
.panel-input { background: transparent; border: none; color: #ffffff; font-family: inherit; font-size: 14px; padding: 2px 0 0 0; width: 100%; }
.panel-input:focus { outline: none; }

.panel-select-menu { background: transparent; border: none; color: #ffffff; font-family: inherit; font-size: 14px; width: 100%; padding: 2px 0 0 0; cursor: pointer; }
.panel-select-menu:focus { outline: none; }
.panel-select-menu option { background-color: #16181f; color: #ffffff; }

.chip-assembly-dock { display: flex; flex-wrap: wrap; gap: 8px; padding-top: 4px; min-height: 24px; align-items: center; }
.active-badge-chip { font-size: 10px; font-weight: bold; background-color: rgba(236, 72, 153, 0.08); border: 1px solid rgba(236, 72, 153, 0.2); color: #ec4899; padding: 2px 8px; border-radius: 4px; }
.dock-empty-text { font-size: 12px; color: #525966; font-style: italic; }

.relative-position { position: relative; }
.typeahead-overlay-tray { position: absolute; top: 100%; left: 0; width: 100%; background-color: #12141a; border: 1px solid #2e333d; border-radius: 6px; margin-top: 4px; max-height: 180px; overflow-y: auto; z-index: 99; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
.typeahead-node { padding: 10px 16px; font-size: 13px; color: #e2e4e9; cursor: pointer; transition: background 0.15s ease; text-align: left; }
.typeahead-node:hover { background-color: rgba(184, 146, 90, 0.15); color: #fbbf24; }

.font-emphasis { font-family: 'Cinzel', serif; font-size: 20px; font-weight: 700; }
.static-value { font-size: 13px; color: #444a57 !important; font-weight: 700; padding-top: 2px; }
.font-bold { font-weight: bold; }
.size-compact { font-size: 13px; }
.text-amber { color: #f59e0b; }
.text-blue { color: #3b82f6 !important; }
.text-magenta { color: #ec4899 !important; }
.text-gray-lock { color: #525966 !important; }
.plaintext-wrapper { padding: 16px; }
.panel-textarea { background: transparent; border: none; color: #e2e4e9; font-family: inherit; font-size: 13px; line-height: 1.6; resize: none; width: 100%; box-sizing: border-box; padding-top: 4px; }
.panel-textarea:focus { outline: none; }

.toast-banner-notification {
  position: fixed; top: 24px; right: 24px;
  padding: 16px 24px; border-radius: 6px;
  background-color: #16181f; border: 1px solid #22252e;
  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
  display: flex; align-items: center; gap: 12px;
  z-index: 20000; font-size: 13px; font-weight: 500;
  animation: slideInToast 0.3s cubic-bezier(0.1, 0.8, 0.3, 1);
}
.toast-indicator { width: 8px; height: 8px; border-radius: 50%; }
.toast-banner-notification.success { border-left: 4px solid #10b981; }
.toast-banner-notification.success .toast-indicator { background-color: #10b981; }
.toast-banner-notification.error { border-left: 4px solid #ef4444; }
.toast-banner-notification.error .toast-indicator { background-color: #ef4444; }
.toast-message-label { color: #ffffff; }

@keyframes slideInToast {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.modal-overlay-shroud { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(10, 11, 13, 0.85); backdrop-filter: blur(4px); z-index: 10000; display: flex; align-items: center; justify-content: center; }
.modal-alert-box { background-color: #16181f; border-top: 4px solid #22252e; padding: 40px; border-radius: 8px; width: 100%; max-width: 480px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); display: flex; flex-direction: column; }
.border-emerald { border-top-color: #10b981; }
.border-crimson { border-top-color: #ef4444; }
.modal-tag { font-size: 10px; font-weight: 700; color: #525966; letter-spacing: 2px; margin-bottom: 16px; }
.modal-heading { font-size: 18px; font-weight: 700; color: #ffffff; margin: 0 0 16px 0; letter-spacing: 0.5px; }
.modal-body-text { font-size: 13px; line-height: 1.6; color: #a3a8b4; margin: 0 0 24px 0; }

.modal-input-field-block { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; }
.modal-input-label { font-size: 10px; font-weight: 700; color: #f59e0b; letter-spacing: 1px; }
.modal-reason-input { background-color: #111216; border: 1px solid #22252e; border-radius: 4px; padding: 12px; font-family: inherit; font-size: 13px; color: #ffffff; width: 100%; box-sizing: border-box; }
.modal-reason-input:focus { outline: none; border-color: #f59e0b; }

.countdown-ticker-bar { background-color: #111216; border: 1px solid #1c1f26; padding: 12px; border-radius: 4px; font-size: 11px; font-weight: bold; color: #626a7a; text-align: center; margin-bottom: 32px; letter-spacing: 0.5px; }
.ticker-value { color: #ffffff; }
.modal-button-row { display: flex; justify-content: flex-end; gap: 16px; }
.m-btn { font-family: inherit; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }
.bg-emerald { background-color: #10b981; color: #ffffff; }
.bg-emerald:hover { background-color: #059669; }
.bg-crimson { background-color: #ef4444; color: #ffffff; }
.bg-crimson:hover { background-color: #dc2626; }
.m-btn-dismiss { background-color: transparent; border: 1px solid #2e333d; color: #e2e4e9; }
.m-btn-dismiss:hover { background-color: rgba(255,255,255,0.03); }

.vault-loader { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; background-color: #111216; }
.minimal-spinner { width: 16px; height: 16px; border: 1px solid rgba(226, 228, 233, 0.1); border-top-color: #e2e4e9; border-radius: 50%; animation: spin 0.7s infinite linear; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: #626a7a; }
</style>