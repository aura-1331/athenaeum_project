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
          <span class="meta-label">CURRENTLY_EDITING</span>
          <h1 class="display-title">{{ editableBook.title }}</h1>
          <p class="display-author">BY {{ editableBook.author || 'UNKNOWN' }}</p>
        </div>

        <div class="system-status-matrix">
          <div class="status-node">
            <span>REGISTRY_RANK</span>
            <strong class="rank-badge">{{ auditData.userRole }}</strong>
          </div>
          <div class="status-node">
            <span>INDEX_MARKER</span>
            <strong class="font-mono">#{{ editableBook.serial_no }}</strong>
          </div>
        </div>

        <div class="panel-actions-stack">
          <button class="btn btn-filled" @click="triggerActionConfirm('commit')">COMMIT_CHANGES</button>
          <button class="btn btn-outline" @click="triggerActionConfirm('abort')">ABORT_TRANSACTION</button>
        </div>
      </aside>

      <main class="form-feed-column">
        <div class="form-scroll-wrapper">
          
          <fieldset class="form-fieldset">
            <legend class="fieldset-legend">01 // CORE SYSTEM IDENTITY</legend>
            
            <div class="form-row">
              <div class="field-container full-width">
                <label class="input-label">ASSET_TITLE_REGISTER</label>
                <input type="text" v-model="editableBook.title" class="panel-input font-emphasis" />
              </div>
            </div>

            <div class="form-row">
              <div class="field-container full-width">
                <label class="input-label">PRIMARY_CREATOR_ORIGIN</label>
                <input type="text" v-model="editableBook.author" class="panel-input" />
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
                <label class="input-label">RECORD_IDENTIFIER (LOCKED)</label>
                <div class="static-value font-mono">{{ editableBook.record_id }}</div>
              </div>
              <div class="field-container disabled-container">
                <label class="input-label">DATABASE_WORK_ID (LOCKED)</label>
                <div class="static-value font-mono text-amber">{{ editableBook.work_id }}</div>
              </div>
            </div>

            <div class="form-row split-2">
              <div class="field-container disabled-container">
                <label class="input-label">ACCESSION_SEQUENCE_NO (LOCKED)</label>
                <div class="static-value font-mono text-blue">{{ editableBook.accession_no }}</div>
              </div>
              <div class="field-container disabled-container">
                <label class="input-label">SERIAL_INDEX_SEQUENCE (LOCKED)</label>
                <div class="static-value font-mono text-magenta">{{ editableBook.serial_no }}</div>
              </div>
            </div>
          </fieldset>

          <fieldset 
            v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
            class="form-fieldset"
          >
            <legend class="fieldset-legend">03 // PHYSICAL SPATIAL VECTORS</legend>
            
            <div class="form-row split-2">
              <div class="field-container contextual-bg">
                <label class="input-label">SHELF_LOCATION_COORDINATES</label>
                <input type="text" v-model="editableBook.shelf" class="panel-input font-mono font-bold" />
              </div>
              <div class="field-container contextual-bg">
                <label class="input-label">CALL_SIGNATURE_MARKER</label>
                <input type="text" v-model="editableBook.call_no" class="panel-input font-mono font-bold" />
              </div>
            </div>

            <div class="form-row split-3">
              <div class="field-container">
                <label class="input-label">TEXT_LANGUAGE</label>
                <input type="text" v-model="editableBook.language" class="panel-input size-compact" />
              </div>
              <div class="field-container">
                <label class="input-label">SOURCE_ORIGIN</label>
                <input type="text" v-model="editableBook.original_language" class="panel-input size-compact" />
              </div>
              <div class="field-container">
                <label class="input-label">CLASSIFICATION</label>
                <input type="text" v-model="editableBook.genre" class="panel-input size-compact" />
              </div>
            </div>

            <div class="form-row split-3">
              <div class="field-container">
                <label class="input-label">IMPRINT_PUBLISHER</label>
                <input type="text" v-model="editableBook.publisher" class="panel-input size-compact" />
              </div>
              <div class="field-container">
                <label class="input-label">TEMPORAL_EPOCH</label>
                <input type="text" v-model="editableBook.year" class="panel-input size-compact font-mono" />
              </div>
              <div class="field-container">
                <label class="input-label">ISBN_IDENTIFIER</label>
                <input type="text" v-model="editableBook.isbn" class="panel-input size-compact font-mono" />
              </div>
            </div>
          </fieldset>

          <fieldset class="form-fieldset">
            <legend class="fieldset-legend">04 // ADMINISTRATIVE CURATORIAL LOG</legend>
            <div class="form-row">
              <div class="field-container full-width plaintext-wrapper">
                <label class="input-label">REVISE_NOTATIONS_REMARKS</label>
                <textarea v-model="editableBook.notes" class="panel-textarea" rows="6"></textarea>
              </div>
            </div>
          </fieldset>

        </div>
      </main>

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
import { ref, onMounted, onBeforeUnmount } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const editableBook = ref<any>(null)

// Confirmation HUD Reactive State Controllers
const activeModalType = ref<string | null>(null) // Values: 'commit', 'abort', or null
const countdownTimerSeconds = ref<number>(0)
let nativeIntervalReference: any = null

const auditData = ref({
  deviceID: "EDITORIAL-CARDS-STATION-01",
  ip: "192.168.1.105", 
  userName: "System Archivist",
  userRole: "The Chief" 
})

async function fetchRecordData() {
  loading.value = true
  const id = route.params.id
  try {
    const response = await axios.get(`/catalogue/${id}`)
    editableBook.value = { ...response.data }
  } catch (err) {
    console.error("Database loading exception:", err)
  } finally {
    loading.value = false
  }
}

function triggerActionConfirm(actionType: 'commit' | 'abort') {
  // Clear any dangling interval tasks running in the loop context
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  
  activeModalType.value = actionType
  countdownTimerSeconds.value = 10 // Sets 10-second auto-action window tracking constraint
  
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
  closeModalPrompt()
  
  if (targetAction === 'commit') {
    saveRecord()
  } else if (targetAction === 'abort') {
    cancelEdit()
  }
}

function closeModalPrompt() {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  activeModalType.value = null
}

async function saveRecord() {
  const id = route.params.id || editableBook.value?.serial_no
  try {
    await axios.patch(`/catalogue/${id}`, editableBook.value)
    router.push(`/details/${id}`)
  } catch (err) {
    console.error("Transaction commit rejected:", err)
    alert("Write Failure: Transaction aborted or field formatting rules syntax error.")
  }
}

function cancelEdit() {
  router.push(`/details/${route.params.id}`)
}

onBeforeUnmount(() => {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
})

onMounted(() => fetchRecordData())
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800&family=JetBrains+Mono:wght@400;700&display=swap');

.control-panel-layout {
  background-color: #111216;
  color: #e2e4e9;
  
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 9999 !important;
  
  display: flex;
  overflow: hidden;
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
  margin: 0 !important;
  padding: 0 !important;
}

.panel-container {
  display: flex;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* LEFT COLUMN STYLES */
.identity-anchor-panel {
  width: 420px;
  background-color: #0a0b0d !important;
  border-right: 1px solid #1c1f26 !important;
  padding: 48px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  flex-shrink: 0;
}

.panel-badge {
  font-size: 10px;
  font-weight: bold;
  color: #525966;
  letter-spacing: 2px;
  margin-bottom: 40px;
}

.hero-identity-block {
  margin-bottom: auto;
}

.meta-label {
  font-size: 9px;
  color: #626a7a;
  letter-spacing: 1px;
  display: block;
  margin-bottom: 8px;
}

.display-title {
  font-family: 'Cinzel', serif;
  font-size: 28px;
  font-weight: 800;
  line-height: 1.2;
  color: #ffffff;
  margin: 0 0 12px 0;
}

.display-author {
  font-size: 12px;
  color: #a3a8b4;
  margin: 0;
}

.system-status-matrix {
  background-color: #111216;
  border: 1px solid #1c1f26;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 32px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.status-node span { color: #525966; font-weight: bold; }
.rank-badge { color: #10b981; text-transform: uppercase; }

.panel-actions-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.btn {
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 14px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  text-align: center;
  transition: background-color 0.15s ease;
}

.btn-filled { background-color: #e2e4e9; color: #111216; }
.btn-filled:hover { background-color: #cdd1da; }
.btn-outline { border: 1px solid #2e333d; color: #e2e4e9; background: transparent; }
.btn-outline:hover { background-color: rgba(255,255,255,0.03); }

/* RIGHT COLUMN STYLES */
.form-feed-column {
  flex-grow: 1;
  height: 100%;
  overflow-y: auto;
  background-color: #111216;
}

.form-scroll-wrapper {
  padding: 48px 64px 64px 64px;
  max-width: 900px;
  box-sizing: border-box;
}

.form-feed-column::-webkit-scrollbar { width: 6px; }
.form-feed-column::-webkit-scrollbar-track { background: #111216; }
.form-feed-column::-webkit-scrollbar-thumb { background: #22252e; border-radius: 3px; }

.form-fieldset {
  border: none;
  margin: 0 0 40px 0;
  padding: 0;
}

.fieldset-legend {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #626a7a;
  border-bottom: 1px solid #22252e;
  width: 100%;
  padding-bottom: 12px;
  margin-bottom: 24px;
}

.form-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.form-row:last-child { margin-bottom: 0; }
.split-2 > .field-container { width: 50%; }
.split-3 > .field-container { width: 33.33%; }
.full-width { width: 100%; }

.field-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background-color: #16181f;
  border: 1px solid #22252e;
  padding: 14px 18px;
  border-radius: 8px;
  box-sizing: border-box;
  transition: border-color 0.2s ease;
}

.field-container:focus-within {
  border-color: #4a5263;
}

.disabled-container {
  background-color: #12141a !important;
  border-color: #1c1f26 !important;
}

.contextual-bg {
  background-color: #13151b;
  border-color: #1e212a;
}

.input-label {
  font-size: 9px;
  font-weight: 700;
  color: #525966;
  letter-spacing: 0.5px;
}

.panel-input {
  background: transparent;
  border: none;
  color: #ffffff;
  font-family: inherit;
  font-size: 14px;
  padding: 2px 0 0 0;
  width: 100%;
}

.panel-input:focus {
  outline: none;
}

.font-emphasis {
  font-family: 'Cinzel', serif;
  font-size: 20px;
  font-weight: 700;
}

.static-value {
  font-size: 13px;
  color: #444a57 !important;
  font-weight: 700;
  padding-top: 2px;
}

.font-bold { font-weight: bold; }
.size-compact { font-size: 13px; }

.text-amber { color: #f59e0b; }
.text-blue { color: #3b82f6 !important; }
.text-magenta { color: #ec4899 !important; }

.plaintext-wrapper { padding: 16px; }

.panel-textarea {
  background: transparent;
  border: none;
  color: #e2e4e9;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  width: 100%;
  box-sizing: border-box;
  padding-top: 4px;
}

.panel-textarea:focus {
  outline: none;
}

/* TRANSACTION HUD OVERLAY MODAL STYLES */
.modal-overlay-shroud {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background-color: rgba(10, 11, 13, 0.85);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex; align-items: center; justify-content: center;
}

.modal-alert-box {
  background-color: #16181f;
  border-top: 4px solid #22252e;
  padding: 40px;
  border-radius: 8px;
  width: 100%; max-width: 480px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  display: flex; flex-direction: column;
}

.border-emerald { border-top-color: #10b981; }
.border-crimson { border-top-color: #ef4444; }

.modal-tag {
  font-size: 10px; font-weight: 700; color: #525966; letter-spacing: 2px; margin-bottom: 16px;
}

.modal-heading {
  font-size: 18px; font-weight: 700; color: #ffffff; margin: 0 0 16px 0; letter-spacing: 0.5px;
}

.modal-body-text {
  font-size: 13px; line-height: 1.6; color: #a3a8b4; margin: 0 0 24px 0;
}

.countdown-ticker-bar {
  background-color: #111216; border: 1px solid #1c1f26; padding: 12px; border-radius: 4px;
  font-size: 11px; font-weight: bold; color: #626a7a; text-align: center; margin-bottom: 32px; letter-spacing: 0.5px;
}

.ticker-value { color: #ffffff; }

.modal-button-row { display: flex; justify-content: flex-end; gap: 16px; }

.m-btn {
  font-family: inherit; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer;
}

.bg-emerald { background-color: #10b981; color: #ffffff; }
.bg-emerald:hover { background-color: #059669; }
.bg-crimson { background-color: #ef4444; color: #ffffff; }
.bg-crimson:hover { background-color: #dc2626; }

.m-btn-dismiss { background-color: transparent; border: 1px solid #2e333d; color: #e2e4e9; }
.m-btn-dismiss:hover { background-color: rgba(255,255,255,0.03); }

.vault-loader {
  width: 100%; height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 16px; background-color: #111216;
}
.minimal-spinner {
  width: 16px; height: 16px; border: 1px solid rgba(226, 228, 233, 0.1);
  border-top-color: #e2e4e9; border-radius: 50%; animation: spin 0.7s infinite linear;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: #626a7a; }
</style>