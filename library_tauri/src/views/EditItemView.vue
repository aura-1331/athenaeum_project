<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"

const route = useRoute()
const router = useRouter()

// --- 1. ROLE DEFINITION ---
// Set to "staff" to test locking; set to "architect" to unlock sensitive controls.
const userRole = ref("staff") 
const isArchitect = computed(() => userRole.value === 'architect')

const item = ref({
  serial_no: '', accession_no: '', title: '', language: '',
  category: '', author: '', original_language: '', translation_compilation: '',
  genre: '', ddc: '', call_no: '', isbn: '', shelf: '',
  publisher: '', year: '', notes: ''
})

const originalItem = ref(null)
const loading = ref(true)
const showToast = ref(false)
const showLeaveConfirm = ref(false)

const isDirty = computed(() => {
  if (!originalItem.value) return false
  return JSON.stringify(item.value) !== JSON.stringify(originalItem.value)
})

async function loadData() {
  loading.value = true
  try {
    const res = await axios.get(`/catalogue/${route.params.id}`)
    item.value = res.data 
    originalItem.value = JSON.parse(JSON.stringify(res.data))
  } catch (err) {
    console.error("❌ Archive Access Error:", err)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!isDirty.value) return
  if (!confirm("AUTHORIZE ATOMIC UPDATE: Commit changes to the Master Ledger?")) return
  
  try {
    await axios.patch(`/catalogue/${route.params.id}`, item.value)
    if (window.__TAURI_INTERNALS__) {
      const { emit } = await import('@tauri-apps/api/event')
      await emit('record-updated', { id: route.params.id }) 
      const { invoke } = await import('@tauri-apps/api/core')
      await invoke("close_current_window")
    } else {
      showToast.value = true
      setTimeout(() => router.back(), 1200)
    }
  } catch (err) {
    alert("TRANSACTION FAILED: " + (err.response?.data?.detail || "Error"))
  }
}

function handleCancel() {
  if (isDirty.value) {
    showLeaveConfirm.value = true
  } else {
    router.back()
  }
}

function confirmLeave() {
  showLeaveConfirm.value = false
  router.back()
}

// --- SECURE CLEAR LOGIC ---
function handleClear() {
  // HARD BLOCK: Refuses to run if userRole is not architect
  if (!isArchitect.value) {
    alert("RESTRICTED ACTION: Architect level authorization is required to clear this ledger.");
    return;
  }

  if (confirm("ARCHITECT AUTHORIZATION: This will wipe all editable metadata. Proceed?")) {
    const s = item.value.serial_no;
    const a = item.value.accession_no;

    item.value = {
      ...item.value,
      title: '', language: '', category: '', author: '',
      genre: '', publisher: '', year: '', isbn: '',
      shelf: '', notes: '', translation_compilation: '',
      ddc: '', call_no: '', original_language: ''
    };

    // Restore primary keys immediately
    item.value.serial_no = s;
    item.value.accession_no = a;
  }
}

const handleGlobalKeys = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    if (isDirty.value) handleSave()
  }
  if (e.key === 'Escape') handleCancel()
}

onMounted(() => {
  loadData();
  window.addEventListener('keydown', handleGlobalKeys);
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeys);
})
</script>

<template>
  <div class="edit-container">
    <Transition name="fade">
      <div v-if="showToast" class="toast-popup">✓ Master Ledger Synchronized</div>
    </Transition>

    <div class="edit-card">
      <header class="athenaeum-header">
        <div class="motto">NON OMNIA SCRIBUNTUR SED OMNIA SERVANTUR</div>
        <div class="main-title">
          <div class="ao-logo">Athenaeum Orbis</div>
          <div class="title-text">Master Records Editor</div>
        </div>
      </header>

      <div class="edit-nav-bar">
        <button 
          type="button" 
          @click="handleClear" 
          :disabled="!isArchitect" 
          class="btn-nav-clear"
        >
          {{ isArchitect ? 'RESET FORM' : 'RESET LOCKED' }}
        </button>

        <button type="button" @click="handleCancel" class="btn-nav-back">← BACK TO CATALOGUE</button>

        <div class="edit-status">
          <span class="status-dot" :class="{ 'is-dirty': isDirty }"></span>
          {{ isDirty ? 'UNSAVED CHANGES' : 'RECORD SYNCED' }}
          <span v-if="isArchitect" class="role-badge">ARCHITECT ACCESS</span>
        </div>
      </div>

      <div v-if="loading" class="loading-text">Accessing Archives...</div>

      <form v-else @submit.prevent="handleSave" class="ledger-form">
        <div class="form-grid">
          <div class="input-box">
            <label>Serial No {{ isArchitect ? '' : '(Locked)' }}</label>
            <input v-model="item.serial_no" :readonly="!isArchitect" :class="{ 'readonly-field': !isArchitect }">
          </div>
          <div class="input-box">
            <label>Accession No {{ isArchitect ? '' : '(Locked)' }}</label>
            <input v-model="item.accession_no" :readonly="!isArchitect" :class="{ 'readonly-field': !isArchitect }">
          </div>
          <div class="input-box">
            <label>ISBN Identifier</label>
            <input v-model="item.isbn">
          </div>

          <div class="input-box full-width">
            <label>Book Title</label>
            <input v-model="item.title" required>
          </div>

          <div class="input-box"><label>Author</label><input v-model="item.author"></div>
          <div class="input-box"><label>Language</label><input v-model="item.language"></div>
          <div class="input-box"><label>Original Language</label><input v-model="item.original_language"></div>
          <div class="input-box"><label>Category</label><input v-model="item.category"></div>
          <div class="input-box"><label>Genre</label><input v-model="item.genre"></div>
          <div class="input-box"><label>DDC Index</label><input v-model="item.ddc"></div>
          <div class="input-box"><label>Publisher</label><input v-model="item.publisher"></div>
          <div class="input-box"><label>Year of Release</label><input v-model="item.year"></div>
          <div class="input-box"><label>Call Number</label><input v-model="item.call_no"></div>
          <div class="input-box"><label>Shelf Location</label><input v-model="item.shelf"></div>
          
          <div class="input-box full-width">
             <label>Translation / Compilation Details</label>
             <input v-model="item.translation_compilation">
          </div>

          <div class="input-box full-width">
            <label>Curator Notes & Administrative Annotations</label>
            <textarea v-model="item.notes" rows="4"></textarea>
          </div>
        </div>

        <div class="action-btns">
          <button type="submit" class="save-btn" :disabled="!isDirty">Save Ledger Update</button>
          <button type="button" @click="handleCancel" class="cancel-btn">Discard Changes</button>
        </div>
      </form>
    </div>

    <div v-if="showLeaveConfirm" class="confirm-overlay">
      <div class="confirm-box">
        <h3>Unsaved Changes</h3>
        <p>Leaving will discard your current ledger updates.</p>
        <div class="confirm-actions">
          <button class="btn-discard" @click="confirmLeave">Discard & Exit</button>
          <button class="btn-stay" @click="showLeaveConfirm = false">Return</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.edit-container { display: block; padding: 40px 20px; background: #064e3b; min-height: 100vh; overflow-y: auto; color: #fff; }
.edit-card { background: rgba(0, 0, 0, 0.5); padding: 40px; border-radius: 8px; width: 100%; max-width: 1200px; margin: 0 auto 40px; border-left: 8px solid #fbbf24; box-shadow: 0 30px 60px rgba(0,0,0,0.5); }

/* HEADER */
.athenaeum-header { text-align: center; margin-bottom: 40px; padding-bottom: 30px; border-bottom: 1px solid rgba(251, 191, 36, 0.2); }
.motto { color: #2dd4bf; letter-spacing: 6px; font-size: 0.75rem; font-weight: 800; margin-bottom: 15px; }
.main-title { display: flex; align-items: center; justify-content: center; gap: 15px; background: #fbbf24; padding: 12px 30px; border-radius: 4px; display: inline-flex; }
.ao-logo { color: #064e3b; font-family: 'Playfair Display', serif; font-weight: 900; font-size: 1.8rem; text-transform: uppercase; }
.title-text { color: #fbbf24; background: #064e3b; font-weight: 800; font-size: 0.9rem; padding: 5px 12px; border-radius: 3px; text-transform: uppercase; }

/* NAV BAR */
.edit-nav-bar { display: flex; justify-content: space-between; align-items: center; padding: 15px 0; margin-bottom: 40px; border-bottom: 1px double rgba(251, 191, 36, 0.3); }
.btn-nav-back { background: transparent; border: none; color: #fbbf24; font-size: 10px; font-weight: 700; cursor: pointer; opacity: 0.8; }
.btn-nav-back:hover { opacity: 1; text-decoration: underline; }

.edit-status { font-size: 10px; font-weight: 800; letter-spacing: 2px; color: #9ca3af; display: flex; align-items: center; gap: 8px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #2dd4bf; }
.status-dot.is-dirty { background: #fbbf24; box-shadow: 0 0 8px #fbbf24; }
.role-badge { background: #fbbf24; color: #000; padding: 2px 6px; border-radius: 2px; font-size: 9px; margin-left: 10px; }

/* PROTECTED RESET BUTTON */
.btn-nav-clear { background: transparent; border: 1px solid #ef4444; color: #ef4444; padding: 6px 15px; border-radius: 4px; font-size: 10px; font-weight: 800; cursor: pointer; text-transform: uppercase; transition: 0.3s; }
.btn-nav-clear:disabled { opacity: 0.25; color: #64748b; border-color: #64748b; cursor: not-allowed; filter: grayscale(1); }
.btn-nav-clear:not(:disabled):hover { background: #ef4444; color: #fff; box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }

/* FORM GRID */
.ledger-form { background: rgba(0, 0, 0, 0.2); padding: 40px; border-radius: 4px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 30px 25px; }
.full-width { grid-column: span 3; }
.input-box label { display: block; color: #fbbf24; font-size: 10px; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; }
input { width: 100%; padding: 10px 0; background: transparent !important; border: none !important; border-bottom: 1px solid rgba(251, 191, 36, 0.3) !important; color: #2dd4bf; font-family: 'Courier New', monospace; font-size: 16px; border-radius: 0 !important; }
input:focus { outline: none; border-bottom: 2px solid #fbbf24 !important; background: rgba(251, 191, 36, 0.05) !important; }
.readonly-field { color: #64748b !important; border-bottom: 1px dashed rgba(255, 255, 255, 0.1) !important; cursor: not-allowed; }
textarea { width: 100%; background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(251, 191, 36, 0.2); color: #e2e8f0; padding: 15px; font-family: 'Courier New', monospace; font-size: 15px; resize: vertical; border-radius: 4px; }

/* ACTIONS */
.action-btns { display: flex; gap: 20px; margin-top: 50px; }
.save-btn { background: #fbbf24; color: #064e3b; flex: 2; padding: 16px; border: none; font-weight: 900; text-transform: uppercase; cursor: pointer; border-radius: 4px; }
.save-btn:disabled { opacity: 0.2; cursor: default; }
.cancel-btn { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,0.2); flex: 1; padding: 16px; cursor: pointer; border-radius: 4px; }

/* MODALS */
.confirm-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.confirm-box { background: #064e3b; border: 2px solid #fbbf24; padding: 40px; border-radius: 8px; text-align: center; max-width: 400px; }
.confirm-actions { display: flex; gap: 15px; margin-top: 25px; }
.btn-discard { background: #ef4444; color: white; border: none; padding: 10px 20px; flex: 1; cursor: pointer; font-weight: bold; }
.btn-stay { background: #fbbf24; color: #064e3b; border: none; padding: 10px 20px; flex: 1; cursor: pointer; font-weight: bold; }
.toast-popup { position: fixed; bottom: 30px; right: 30px; background: #2dd4bf; color: #064e3b; padding: 15px 30px; border-radius: 4px; font-weight: 800; }
</style>