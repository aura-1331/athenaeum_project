<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"

interface BookRecord {
  // Items table (16)
  item_id?: number | string
  serial_no?: number | string
  work_id?: number | string
  accession_no?: string
  shelf?: string
  extent_page_count?: string | number
  physical_dimensions?: string
  date_acquired?: string
  collection_fonds?: string
  physical_condition?: string
  binding_type?: string
  provenance_source?: string
  artifactual_notes?: string
  access_restrictions?: string
  digital_scan_available?: boolean | string
  ocr_status?: string
  availability_status?: string

  // Works table (26)
  title?: string
  author?: string
  language?: string
  publisher?: string
  year?: string | number
  publication_year?: string | number
  isbn?: string
  ddc?: string
  call_no?: string
  original_language?: string
  original_title?: string
  original_author?: string
  translator?: string
  compiler_editor?: string
  work_nature?: string | string[]
  edition_statement?: string
  series_title?: string
  series_volume?: string
  lccn?: string
  oclc_no?: string
  subject_headings?: string
  target_audience_era?: string
  copyright_status?: string
  notes?: string
  description?: string
  category?: string
  genre?: string | string[]
  categories?: string | string[]
  translation_compilation?: string

  // Series Relations (4)
  series_name?: string
  series_number?: string | number
  volume_number?: string | number
  related_work_id?: number | string

  // Computed (1)
  record_id?: string
  [key: string]: any
}

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const book = ref<BookRecord | null>(null)
const copiedKey = ref<string | null>(null)
const showAllFields = ref(false)

const currentId = computed(() => {
  const idParam = route.params.id
  const rawId = Array.isArray(idParam) ? idParam[0] : idParam
  return rawId || "1"
})

function hasVal(val: any): boolean {
  if (val === null || val === undefined) return false
  if (typeof val === "string" && val.trim() === "") return false
  if (Array.isArray(val) && val.length === 0) return false
  if (val === 0 || val === "0") return false
  return true
}

function shouldShow(val: any): boolean {
  return showAllFields.value || hasVal(val)
}

function formatVal(val: any): string {
  if (!hasVal(val)) return "—"
  if (Array.isArray(val)) return val.join(", ")
  if (typeof val === "boolean") return val ? "Yes" : "No"
  return String(val)
}

const publicationYearVal = computed(() => {
  const yr = book.value?.publication_year || book.value?.year
  if (!hasVal(yr)) return null
  return yr
})

const showDigitalScan = computed(() => {
  const val = book.value?.digital_scan_available
  if (!hasVal(val)) return false
  if (typeof val === "boolean") return val
  const str = String(val).trim().toLowerCase()
  return str !== "unscanned" && str !== "false" && str !== "no" && str !== "none"
})

const splitGenres = computed(() => {
  const raw = book.value?.genre || book.value?.work_nature || book.value?.categories
  if (!raw) return []
  if (Array.isArray(raw)) {
    return raw.map((g) => String(g).trim()).filter((g) => g.length > 0)
  }
  return String(raw).split("/").map((g) => g.trim()).filter((g) => g.length > 0)
})

const splitSubjects = computed(() => {
  if (!book.value?.subject_headings) return []
  return String(book.value.subject_headings).split(/[,;]/).map((s) => s.trim()).filter((s) => s.length > 0)
})

const hasClassificationData = computed(() => {
  return showAllFields.value || 
         splitGenres.value.length > 0 || 
         splitSubjects.value.length > 0 || 
         hasVal(book.value?.target_audience_era) ||
         hasVal(book.value?.work_nature)
})

const hasLineageData = computed(() => {
  if (!book.value) return false
  return showAllFields.value ||
         hasVal(book.value.original_title) ||
         hasVal(book.value.original_author) ||
         hasVal(book.value.original_language) ||
         hasVal(book.value.translator) ||
         hasVal(book.value.compiler_editor) ||
         hasVal(book.value.translation_compilation) ||
         hasVal(book.value.series_title) ||
         hasVal(book.value.series_volume) ||
         hasVal(book.value.series_name) ||
         hasVal(book.value.related_work_id) ||
         hasVal(book.value.copyright_status)
})

const hasCataloguingData = computed(() => {
  if (!book.value) return false
  return showAllFields.value ||
         hasVal(book.value.publisher) ||
         hasVal(publicationYearVal.value) ||
         hasVal(book.value.shelf) ||
         hasVal(book.value.call_no) ||
         hasVal(book.value.isbn) ||
         hasVal(book.value.ddc) ||
         hasVal(book.value.lccn) ||
         hasVal(book.value.oclc_no) ||
         hasVal(book.value.edition_statement)
})

const hasPhysicalData = computed(() => {
  if (!book.value) return false
  return showAllFields.value ||
         hasVal(book.value.extent_page_count) || 
         hasVal(book.value.physical_dimensions) || 
         hasVal(book.value.binding_type) || 
         hasVal(book.value.physical_condition) || 
         hasVal(book.value.date_acquired) || 
         hasVal(book.value.collection_fonds) || 
         hasVal(book.value.provenance_source) || 
         hasVal(book.value.access_restrictions) || 
         hasVal(book.value.ocr_status) || 
         showDigitalScan.value
})

const hasNotesData = computed(() => {
  if (!book.value) return false
  return showAllFields.value ||
         hasVal(book.value.notes) || 
         hasVal(book.value.description) || 
         hasVal(book.value.artifactual_notes)
})

function generateRecordId(serialNo: number | string) {
  const year = book.value?.publication_year || book.value?.year || new Date().getFullYear()
  return `AO-REC-${year}-${String(serialNo).padStart(6, "0")}`
}

async function fetchBookDetails() {
  loading.value = true
  error.value = false
  try {
    const response = await axios.get(`/catalogue/holding/${currentId.value}`)
    const data = response.data
    if (data) {
      if (data.serial_no && !data.record_id) {
        data.record_id = generateRecordId(data.serial_no)
      }
      book.value = data
    } else {
      error.value = true
    }
  } catch (err) {
    console.error("Failed to load record:", err)
    error.value = true
  } finally {
    loading.value = false
  }
}

async function copyValue(val: string | number | undefined, key: string) {
  if (!val) return
  try {
    await navigator.clipboard.writeText(String(val))
    copiedKey.value = key
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = null
    }, 1500)
  } catch (e) {
    console.error("Copy failed", e)
  }
}

function goToRecord(direction: "next" | "prev") {
  const num = parseInt(currentId.value, 10)
  if (isNaN(num)) return
  const nextVal = direction === "next" ? num + 1 : num - 1
  if (nextVal > 0) router.push(`/details/${nextVal}`)
}

function editRecord() {
  router.push({ name: "EditItem", params: { id: book.value?.serial_no || currentId.value } })
}

function isTauriEnvironment(): boolean {
  return typeof window !== "undefined" && Boolean((window as any).__TAURI_INTERNALS__ || (window as any).__TAURI__)
}

async function printRecord() {
  const targetId = book.value?.serial_no || currentId.value
  const safeId = String(targetId).replace(/[^a-zA-Z0-9_-]/g, "_")
  const printRoute = `/print/${safeId}`

  if (isTauriEnvironment()) {
    try {
      const { WebviewWindow } = await import("@tauri-apps/api/webviewWindow")
      const windowLabel = `print_slip_${safeId}_${Date.now()}`
      const printWin = new WebviewWindow(windowLabel, {
        url: `index.html#${printRoute}`,
        title: "Bibliographic Accession Dossier",
        width: 950,
        height: 1050,
        center: true,
        focus: true,
        alwaysOnTop: true,
        resizable: true
      })

      printWin.once("tauri://error", (err: any) => {
        console.warn("Tauri window failed, falling back to router:", err)
        router.push(printRoute)
      })
      return
    } catch (e) {
      console.warn("Tauri WebviewWindow import failed, falling back to browser mode:", e)
    }
  }

  try {
    const fullUrl = `${window.location.origin}${window.location.pathname}#${printRoute}`
    const win = window.open(fullUrl, "_blank")
    if (!win || win.closed || typeof win.closed === "undefined") {
      router.push(printRoute)
    }
  } catch {
    router.push(printRoute)
  }
}

function handleKeydown(event: KeyboardEvent) {
  const tag = (event.target as HTMLElement)?.tagName
  if (["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return

  if ((event.ctrlKey || event.metaKey) && (event.key === "p" || event.key === "P")) {
    event.preventDefault()
    printRecord()
    return
  }

  if (event.key === "Escape" || event.key === "Backspace") {
    event.preventDefault()
    router.push("/catalogue")
  } else if (event.key === "ArrowLeft") {
    goToRecord("prev")
  } else if (event.key === "ArrowRight") {
    goToRecord("next")
  } else if (event.key === "e" || event.key === "E") {
    editRecord()
  } else if (event.key === "p" || event.key === "P") {
    printRecord()
  }
}

watch(() => route.params.id, () => {
  book.value = null
  fetchBookDetails()
})

onMounted(() => {
  fetchBookDetails()
  window.addEventListener("keydown", handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown)
})
</script>

<template>
  <div class="view-wrapper">
    <!-- Floating Back to Catalogue Action -->
    <button 
      class="floating-catalogue-btn no-print" 
      @click="router.push('/catalogue')" 
      title="Return to Catalogue (Esc or Backspace)"
      aria-label="Back to Catalogue"
    >
      <span class="floating-icon">←</span>
      <span class="floating-label">Catalogue</span>
      <kbd class="floating-kbd">Esc</kbd>
    </button>

    <!-- Top Action Bar -->
    <header class="action-bar no-print">
      <!-- Fixed Back Button on Top Left -->
      <div class="action-left">
        <button class="btn back-nav-btn" @click="router.push('/catalogue')" title="Back to Catalogue (Esc)">
          <span class="btn-glyph">←</span>
          <span>Back to Catalogue</span>
          <kbd>Esc</kbd>
        </button>
      </div>

      <!-- Controls moved to Right Side -->
      <div class="action-right">
        <label class="toggle-control" title="Toggle visibility of empty schema fields">
          <input type="checkbox" v-model="showAllFields" />
          <span class="toggle-slider"></span>
          <span class="toggle-label">Show Empty Fields</span>
        </label>

        <button class="btn print-btn" @click="printRecord" title="Print this dossier (P)">
          <span class="btn-glyph">⎙</span>
          <span>Print</span>
          <kbd>P</kbd>
        </button>

        <button class="btn refresh-btn" @click="fetchBookDetails" title="Refresh Record">
          <span class="btn-glyph">↺</span>
          <span>Refresh</span>
        </button>

        <button class="btn edit-btn" @click="editRecord" title="Edit Record (E)">
          <span class="btn-glyph">✎</span>
          <span>Edit Record</span>
          <kbd>E</kbd>
        </button>
      </div>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="center-panel no-print">
      <div class="loader"></div>
      <p>Loading holding details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="center-panel error no-print">
      <h3>Record could not be found</h3>
      <button class="btn edit-btn" @click="fetchBookDetails">Retry</button>
    </div>

    <!-- Main Content Workspace -->
    <main v-else-if="book" class="dashboard-container">
      
      <!-- Primary Clean Banner (Year removed from beside title/author) -->
      <section class="banner-card">
        <div class="banner-top">
          <div class="tag-row">
            <span class="status-pill" v-if="shouldShow(book.availability_status)">
              {{ formatVal(book.availability_status) }}
            </span>
            <span class="category-pill" v-if="shouldShow(book.category)">
              {{ formatVal(book.category) }}
            </span>
            <span class="sub-pill" v-if="shouldShow(book.language)">
              {{ formatVal(book.language) }}
            </span>
          </div>
        </div>

        <h1 class="main-title">{{ book.title || 'Untitled Record' }}</h1>
        <p class="main-sub" v-if="shouldShow(book.author)">
          <strong>{{ formatVal(book.author) }}</strong>
        </p>
      </section>

      <!-- Compact Quick ID Strip -->
      <section class="quick-id-grid">
        <div class="id-card" v-if="shouldShow(book.item_id)" @click="copyValue(book.item_id, 'item')">
          <span class="id-title">Item ID</span>
          <strong class="id-value highlight">{{ formatVal(book.item_id) }}</strong>
          <span class="copy-alert no-print" v-if="copiedKey === 'item'">Copied!</span>
        </div>

        <div class="id-card" v-if="shouldShow(book.record_id)" @click="copyValue(book.record_id, 'rec')">
          <span class="id-title">Record ID</span>
          <strong class="id-value">{{ formatVal(book.record_id) }}</strong>
          <span class="copy-alert no-print" v-if="copiedKey === 'rec'">Copied!</span>
        </div>

        <div class="id-card" v-if="shouldShow(book.serial_no)" @click="copyValue(book.serial_no, 'serial')">
          <span class="id-title">Serial No</span>
          <strong class="id-value">{{ formatVal(book.serial_no) }}</strong>
          <span class="copy-alert no-print" v-if="copiedKey === 'serial'">Copied!</span>
        </div>

        <div class="id-card" v-if="shouldShow(book.accession_no)" @click="copyValue(book.accession_no, 'acc')">
          <span class="id-title">Accession No</span>
          <strong class="id-value">{{ formatVal(book.accession_no) }}</strong>
          <span class="copy-alert no-print" v-if="copiedKey === 'acc'">Copied!</span>
        </div>

        <div class="id-card" v-if="shouldShow(book.work_id)" @click="copyValue(book.work_id, 'work')">
          <span class="id-title">Work ID</span>
          <strong class="id-value">#{{ formatVal(book.work_id) }}</strong>
          <span class="copy-alert no-print" v-if="copiedKey === 'work'">Copied!</span>
        </div>
      </section>

      <!-- Option A: 3-Column Dense Layout -->
      <div class="dashboard-grid-3col">
        
        <!-- Column 1: Classification & Lineage stacked together -->
        <div class="grid-column">
          <!-- 1. Classification & Headings -->
          <div class="info-card" v-if="hasClassificationData">
            <div class="card-head">Classification & Headings</div>
            
            <div class="pair-list" style="margin-bottom: 0.85rem;" v-if="shouldShow(book.work_nature) || shouldShow(book.target_audience_era)">
              <div class="pair" v-if="shouldShow(book.work_nature)"><span class="k">Work Nature</span><span class="v">{{ formatVal(book.work_nature) }}</span></div>
              <div class="pair" v-if="shouldShow(book.target_audience_era)"><span class="k">Audience / Era</span><span class="v">{{ formatVal(book.target_audience_era) }}</span></div>
            </div>

            <div class="badge-block" v-if="shouldShow(splitGenres)">
              <span class="sub-label">Genres</span>
              <div class="chip-container" v-if="splitGenres.length > 0">
                <span v-for="g in splitGenres" :key="g" class="data-chip">{{ g }}</span>
              </div>
              <span v-else class="empty-val">—</span>
            </div>

            <div class="badge-block" v-if="shouldShow(splitSubjects)">
              <span class="sub-label">Subject Headings</span>
              <div class="chip-container" v-if="splitSubjects.length > 0">
                <span v-for="s in splitSubjects" :key="s" class="data-chip accent">{{ s }}</span>
              </div>
              <span v-else class="empty-val">—</span>
            </div>
          </div>

          <!-- 2. Textual Lineage & Series -->
          <div class="info-card" v-if="hasLineageData">
            <div class="card-head">Textual Lineage & Series</div>
            <div class="pair-list">
              <div class="pair" v-if="shouldShow(book.original_title)"><span class="k">Original Title</span><span class="v">{{ formatVal(book.original_title) }}</span></div>
              <div class="pair" v-if="shouldShow(book.original_author)"><span class="k">Original Author</span><span class="v">{{ formatVal(book.original_author) }}</span></div>
              <div class="pair" v-if="shouldShow(book.original_language)"><span class="k">Original Language</span><span class="v">{{ formatVal(book.original_language) }}</span></div>
              <div class="pair" v-if="shouldShow(book.translator)"><span class="k">Translator</span><span class="v">{{ formatVal(book.translator) }}</span></div>
              <div class="pair" v-if="shouldShow(book.compiler_editor)"><span class="k">Editor</span><span class="v">{{ formatVal(book.compiler_editor) }}</span></div>
              <div class="pair" v-if="shouldShow(book.translation_compilation)"><span class="k">Compilation Notes</span><span class="v">{{ formatVal(book.translation_compilation) }}</span></div>
              <div class="pair" v-if="shouldShow(book.series_title)"><span class="k">Series Title</span><span class="v">{{ formatVal(book.series_title) }}</span></div>
              <div class="pair" v-if="shouldShow(book.series_volume)"><span class="k">Series Volume</span><span class="v">{{ formatVal(book.series_volume) }}</span></div>
              <div class="pair" v-if="shouldShow(book.series_name)"><span class="k">Series Group</span><span class="v">{{ formatVal(book.series_name) }} <span v-if="hasVal(book.volume_number)">(Vol. {{ book.volume_number }})</span><span v-if="hasVal(book.series_number)"> (No. {{ book.series_number }})</span></span></div>
              <div class="pair" v-if="shouldShow(book.series_number) && !hasVal(book.series_name)"><span class="k">Series Number</span><span class="v">{{ formatVal(book.series_number) }}</span></div>
              <div class="pair" v-if="shouldShow(book.volume_number) && !hasVal(book.series_name)"><span class="k">Volume Number</span><span class="v">{{ formatVal(book.volume_number) }}</span></div>
              <div class="pair" v-if="shouldShow(book.related_work_id)"><span class="k">Related Work</span><span class="v mono">{{ hasVal(book.related_work_id) ? '#' + book.related_work_id : '—' }}</span></div>
              <div class="pair" v-if="shouldShow(book.copyright_status)"><span class="k">Copyright Status</span><span class="v">{{ formatVal(book.copyright_status) }}</span></div>
            </div>
          </div>
        </div>

        <!-- Column 2: Publication & Cataloguing -->
        <div class="grid-column">
          <div class="info-card" v-if="hasCataloguingData">
            <div class="card-head">Publication & Cataloguing</div>
            <div class="pair-list">
              <div class="pair" v-if="shouldShow(book.publisher)"><span class="k">Publisher</span><span class="v">{{ formatVal(book.publisher) }}</span></div>
              <div class="pair" v-if="shouldShow(publicationYearVal)"><span class="k">Publication Year</span><span class="v highlight">{{ formatVal(publicationYearVal) }}</span></div>
              <div class="pair" v-if="shouldShow(book.shelf)"><span class="k">Shelf Placement</span><span class="v highlight">{{ formatVal(book.shelf) }}</span></div>
              <div class="pair" v-if="shouldShow(book.call_no)"><span class="k">Call Number</span><span class="v highlight mono">{{ formatVal(book.call_no) }}</span></div>
              <div class="pair" v-if="shouldShow(book.isbn)"><span class="k">ISBN</span><span class="v mono">{{ formatVal(book.isbn) }}</span></div>
              <div class="pair" v-if="shouldShow(book.ddc)"><span class="k">DDC</span><span class="v mono">{{ formatVal(book.ddc) }}</span></div>
              <div class="pair" v-if="shouldShow(book.lccn)"><span class="k">LCCN</span><span class="v mono">{{ formatVal(book.lccn) }}</span></div>
              <div class="pair" v-if="shouldShow(book.oclc_no)"><span class="k">OCLC</span><span class="v mono">{{ formatVal(book.oclc_no) }}</span></div>
              <div class="pair" v-if="shouldShow(book.edition_statement)"><span class="k">Edition Statement</span><span class="v">{{ formatVal(book.edition_statement) }}</span></div>
            </div>
          </div>
        </div>

        <!-- Column 3: Physical Holding & Preservation -->
        <div class="grid-column">
          <div class="info-card" v-if="hasPhysicalData">
            <div class="card-head">Physical Holding & Preservation</div>
            <div class="pair-list">
              <div class="pair" v-if="shouldShow(book.extent_page_count)"><span class="k">Pages / Extent</span><span class="v">{{ formatVal(book.extent_page_count) }}</span></div>
              <div class="pair" v-if="shouldShow(book.physical_dimensions)"><span class="k">Dimensions</span><span class="v">{{ formatVal(book.physical_dimensions) }}</span></div>
              <div class="pair" v-if="shouldShow(book.binding_type)"><span class="k">Binding Style</span><span class="v">{{ formatVal(book.binding_type) }}</span></div>
              <div class="pair" v-if="shouldShow(book.physical_condition)"><span class="k">Condition</span><span class="v highlight">{{ formatVal(book.physical_condition) }}</span></div>
              <div class="pair" v-if="shouldShow(book.date_acquired)"><span class="k">Acquired Date</span><span class="v">{{ formatVal(book.date_acquired) }}</span></div>
              <div class="pair" v-if="shouldShow(book.collection_fonds)"><span class="k">Collection / Fonds</span><span class="v">{{ formatVal(book.collection_fonds) }}</span></div>
              <div class="pair" v-if="shouldShow(book.provenance_source)"><span class="k">Provenance</span><span class="v">{{ formatVal(book.provenance_source) }}</span></div>
              <div class="pair" v-if="shouldShow(book.access_restrictions)"><span class="k">Restrictions</span><span class="v highlight">{{ formatVal(book.access_restrictions) }}</span></div>
              <div class="pair" v-if="shouldShow(book.ocr_status)"><span class="k">OCR Status</span><span class="v">{{ formatVal(book.ocr_status) }}</span></div>
              <div class="pair" v-if="shouldShow(book.digital_scan_available)">
                <span class="k">Digital Scan</span>
                <span class="v highlight">{{ showDigitalScan ? 'Available' : 'No' }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Dedicated Notes & Artifactual Annotations -->
      <section class="dedicated-notes-card" v-if="hasNotesData">
        <div class="card-head">Notes & Annotations</div>
        <div class="notes-body" v-if="shouldShow(book.notes || book.description)">
          <p class="notes-prose">{{ formatVal(book.notes || book.description) }}</p>
        </div>
        <div class="notes-body artifact-notes" v-if="shouldShow(book.artifactual_notes)" style="margin-top: 12px;">
          <small class="sub-label">Artifactual Notes (Bookplates, Inscriptions, Marginalia)</small>
          <p class="notes-prose">{{ formatVal(book.artifactual_notes) }}</p>
        </div>
      </section>

      <!-- Footer Navigation -->
      <footer class="bottom-nav no-print">
        <button class="btn icon-btn" @click="goToRecord('prev')">← Previous</button>
        <span class="footer-hint">Keyboard: <b>[←] Prev</b> | <b>[→] Next</b> | <b>[E] Edit</b> | <b>[P] Print</b> | <b>[Esc] Back</b></span>
        <button class="btn icon-btn" @click="goToRecord('next')">Next →</button>
      </footer>
    </main>
  </div>
</template>

<style scoped>
/* Plum-Crimson & Violet Palette */
.view-wrapper {
  min-height: 100vh;
  background-color: #261b2b;
  color: #fbf5fc;
  padding: 1.25rem 2rem 4.5rem 2rem;
  box-sizing: border-box;
  font-family: inherit;
  position: relative;
}

.floating-catalogue-btn {
  position: fixed;
  bottom: 1.75rem;
  left: 2rem;
  z-index: 60;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 1.15rem;
  background: #362240;
  border: 1.5px solid #a855f7;
  color: #fbf5fc;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 10px 25px rgba(18, 8, 23, 0.65), 0 0 14px rgba(168, 85, 247, 0.3);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
}

.floating-catalogue-btn:hover {
  background: #a855f7;
  color: #ffffff;
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 14px 30px rgba(18, 8, 23, 0.75), 0 0 20px rgba(168, 85, 247, 0.5);
}

.floating-catalogue-btn:active {
  transform: translateY(0) scale(0.98);
}

.floating-icon {
  font-size: 1.05rem;
  line-height: 1;
}

.floating-label {
  letter-spacing: 0.03em;
}

.floating-kbd {
  background: #24142b;
  border: 1px solid #734e87;
  color: #e9d5ff;
  font-size: 0.7rem;
  padding: 0.12rem 0.38rem;
  border-radius: 4px;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.action-left {
  display: flex;
  align-items: center;
}

.action-right {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.back-nav-btn {
  background: #362240;
  border: 1px solid #734e87;
  font-weight: 700;
}

.back-nav-btn:hover {
  background: #a855f7;
  border-color: #c084fc;
}

.toggle-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  cursor: pointer;
  user-select: none;
  background: #362240;
  border: 1px solid #573a66;
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.toggle-control:hover {
  border-color: #a855f7;
  background: #442a52;
}

.toggle-control input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}

.toggle-slider {
  position: relative;
  width: 32px;
  height: 18px;
  background-color: #24142b;
  border: 1px solid #734e87;
  border-radius: 20px;
  transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 12px;
  width: 12px;
  left: 2px;
  bottom: 2px;
  background-color: #d8b4fe;
  border-radius: 50%;
  transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-control input:checked + .toggle-slider {
  background-color: #c026d3;
  border-color: #e879f9;
}

.toggle-control input:checked + .toggle-slider:before {
  transform: translateX(14px);
  background-color: #ffffff;
}

.toggle-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #fbf5fc;
}

.btn {
  background: #392842;
  border: 1px solid #573a66;
  color: #fbf5fc;
  padding: 0.48rem 0.95rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.15s ease;
  user-select: none;
}

.btn:hover {
  background: #533363;
  border-color: #a855f7;
  color: #ffffff;
  transform: translateY(-1px);
}

.btn:active {
  transform: translateY(1px);
}

.btn-glyph {
  font-size: 0.95rem;
  line-height: 1;
}

.btn kbd {
  background: #261b2b;
  border: 1px solid #734e87;
  border-radius: 4px;
  padding: 0.1rem 0.35rem;
  font-size: 0.68rem;
  color: #e9d5ff;
}

.print-btn {
  background: #362240;
  border-color: #6d4180;
}

.print-btn:hover {
  border-color: #f472b6;
  color: #f472b6;
}

.refresh-btn {
  background: #362240;
  border-color: #6d4180;
}

.edit-btn {
  background: #c026d3;
  border-color: #e879f9;
  color: #ffffff;
  box-shadow: 0 3px 10px rgba(192, 38, 211, 0.3);
}

.edit-btn:hover {
  background: #a21caf;
  border-color: #f0abfc;
  box-shadow: 0 4px 14px rgba(192, 38, 211, 0.45);
}

.edit-btn kbd {
  border-color: #f0abfc;
  color: #fdf4ff;
}

.banner-card {
  background: #362240;
  border: 1px solid #573467;
  border-radius: 12px;
  padding: 1.25rem 1.6rem;
  margin-bottom: 0.85rem;
  box-shadow: 0 4px 14px rgba(18, 8, 23, 0.45);
}

.banner-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.tag-row {
  display: flex;
  gap: 0.5rem;
}

.status-pill {
  background: #e11d48;
  color: #ffffff;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 6px;
}

.category-pill {
  background: #9333ea;
  color: #ffffff;
  font-size: 0.72rem;
  padding: 0.2rem 0.65rem;
  border-radius: 6px;
  font-weight: 500;
}

.sub-pill {
  background: #be185d;
  color: #ffffff;
  font-size: 0.72rem;
  padding: 0.2rem 0.65rem;
  border-radius: 6px;
  font-weight: 500;
}

.main-title {
  margin: 0.2rem 0;
  font-size: 1.65rem;
  color: #ffffff;
  font-weight: 700;
}

.main-sub {
  margin: 0.25rem 0 0 0;
  font-size: 0.95rem;
  color: #e9d5ff;
}

.quick-id-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.85rem;
}

.id-card {
  position: relative;
  background: #311c3a;
  border: 1px solid #573467;
  padding: 0.6rem 0.9rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.id-card:hover {
  background: #4a2b59;
  border-color: #f43f5e;
}

.id-title {
  display: block;
  font-size: 0.66rem;
  text-transform: uppercase;
  color: #d8b4fe;
  font-weight: 700;
  margin-bottom: 0.2rem;
}

.id-value {
  font-size: 0.92rem;
  color: #ffffff;
  font-family: monospace;
}

.id-value.highlight {
  color: #fb7185;
}

.copy-alert {
  position: absolute;
  top: 0.35rem;
  right: 0.4rem;
  background: #e11d48;
  color: #fff;
  font-size: 0.62rem;
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
}

/* 3-Column Dense Grid */
.dashboard-grid-3col {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
  margin-bottom: 0.85rem;
  align-items: start;
}

.grid-column {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.info-card {
  background: #362240;
  border: 1px solid #573467;
  border-radius: 10px;
  padding: 1.1rem 1.25rem;
}

.card-head {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: #f472b6;
  margin-bottom: 0.8rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid #573467;
}

.pair-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.pair {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  font-size: 0.84rem;
  border-bottom: 1px solid #4a2b59;
  padding-bottom: 0.38rem;
}

.pair:last-child {
  border-bottom: none;
}

.pair .k {
  color: #d8b4fe;
  flex-shrink: 0;
}

.pair .v {
  color: #fbf5fc;
  font-weight: 500;
  text-align: right;
  word-break: break-word;
}

.pair .v.mono {
  font-family: monospace;
}

.pair .v.highlight {
  color: #fb7185;
}

.empty-val {
  color: #734e87;
  font-size: 0.84rem;
}

.dedicated-notes-card {
  background: #362240;
  border: 1px solid #573467;
  border-radius: 10px;
  padding: 1.1rem 1.4rem;
  box-shadow: 0 4px 14px rgba(18, 8, 23, 0.45);
}

.dedicated-notes-card .card-head {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: #f472b6;
  margin-bottom: 0.7rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid #573467;
}

.notes-body {
  padding-left: 0.5rem;
  border-left: 3px solid #e11d48;
}

.artifact-notes {
  border-left-color: #a855f7;
}

.notes-prose {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #fbf5fc;
}

.badge-block {
  margin-bottom: 0.75rem;
}

.badge-block:last-child {
  margin-bottom: 0;
}

.sub-label {
  display: block;
  font-size: 0.7rem;
  color: #d8b4fe;
  font-weight: 700;
  margin-bottom: 0.35rem;
  text-transform: uppercase;
}

.chip-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.data-chip {
  background: #9333ea;
  color: #ffffff;
  font-size: 0.72rem;
  padding: 0.18rem 0.55rem;
  border-radius: 5px;
}

.data-chip.accent {
  background: #db2777;
  color: #ffffff;
}

.bottom-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.5rem;
  padding-top: 0.9rem;
  border-top: 1px solid #573467;
}

.footer-hint {
  font-size: 0.8rem;
  color: #d8b4fe;
}

.center-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem;
}

.loader {
  width: 34px;
  height: 34px;
  border: 3px solid #f472b6;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1100px) {
  .dashboard-grid-3col {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-grid-3col {
    grid-template-columns: 1fr;
  }
  .action-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
  .action-right {
    flex-wrap: wrap;
  }
}

@media print {
  .no-print {
    display: none !important;
  }
  .view-wrapper {
    background: #ffffff !important;
    color: #1a1a1a !important;
    padding: 0 !important;
  }
  .banner-card, .info-card, .id-card, .dedicated-notes-card {
    background: #ffffff !important;
    border: 1px solid #cccccc !important;
    box-shadow: none !important;
    color: #000000 !important;
  }
  .main-title, .id-value, .pair .v, .notes-prose {
    color: #000000 !important;
  }
  .pair .k, .id-title, .sub-label {
    color: #555555 !important;
  }
  .status-pill, .category-pill, .sub-pill, .data-chip {
    border: 1px solid #888888 !important;
    background: #eeeeee !important;
    color: #000000 !important;
  }
}
</style>