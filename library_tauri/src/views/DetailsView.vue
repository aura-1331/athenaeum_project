<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"

interface BookRecord {
  serial_no?: number
  record_id?: string
  genre?: string | string[]
  work_nature?: string | string[]
  categories?: string | string[]
  category?: string
  shelf?: string
  call_no?: string
  original_language?: string
  notes?: string
  ddc?: string
  // New role-based & archival fields
  original_author?: string
  translator?: string
  compiler_editor?: string
  edition_statement?: string
  series_title?: string
  series_volume?: string
  lccn?: string
  oclc_no?: string
  physical_condition?: string
  binding_type?: string
  provenance_source?: string
  artifactual_notes?: string
  access_restrictions?: string
  [key: string]: any
}

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref(false)
const book = ref<BookRecord | null>(null)
const copyButtonText = ref("Copy ID")

const currentId = computed(() => {
  const idParam = route.params.id
  const rawId = Array.isArray(idParam) ? idParam[0] : idParam
  return rawId || '1'
})

const splitGenres = computed(() => {
  const raw = book.value?.genre || book.value?.work_nature || book.value?.categories
  if (!raw) return ['GENERAL']
  if (Array.isArray(raw)) return raw.map((g: string) => g.toUpperCase())
  return raw.split('/').map((g: string) => g.trim().toUpperCase()).filter((g: string) => g.length > 0)
})

// Cleanly managed keys to avoid duplicating in system metadata section
const renderedKeys = [
  'title', 'name', 'author', 'creator', 'publisher', 
  'genre', 'work_nature', 'categories', 'category', 
  'isbn', 'ISSN', 'publication_year', 'year', 
  'language', 'shelf_location', 'call_number', 'shelf', 'call_no',
  'description', 'abstract', 
  'original_language', 'notes', 'ddc',
  'original_author', 'translator', 'compiler_editor',
  'edition_statement', 'series_title', 'series_volume',
  'lccn', 'oclc_no', 'physical_condition', 'binding_type',
  'provenance_source', 'artifactual_notes', 'access_restrictions',
  'record_id', 'work_id', 'workId', 'work_code', 
  'serial_no', 'id', '_id', 'uuid', 'accession_no'
]

const dynamicExtraFields = computed(() => {
  if (!book.value) return {}
  const extras: Record<string, any> = {}
  for (const [key, value] of Object.entries(book.value)) {
    if (!renderedKeys.includes(key) && value !== null && value !== undefined && value !== '') {
      extras[key] = value
    }
  }
  return extras
})

function generateRecordId(serialNo: number) {
  const currentYear = new Date().getFullYear()
  return `AO-REC-${currentYear}-${String(serialNo).padStart(6, '0')}`
}

async function fetchBookDetails() {
  loading.value = true
  error.value = false
  const id = currentId.value
  try {
    const response = await axios.get(`/catalogue/${id}`)
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
    console.error("Pipeline breakdown:", err)
    error.value = true
  } finally {
    loading.value = false
  }
}

function refreshRecord() {
  fetchBookDetails()
}

async function copyRecordId() {
  const idToCopy = book.value?.record_id || currentId.value
  try {
    await navigator.clipboard.writeText(String(idToCopy))
    copyButtonText.value = "Copied!"
    setTimeout(() => {
      copyButtonText.value = "Copy ID"
    }, 2000)
  } catch (err) {
    console.error("Failed to copy record ID:", err)
  }
}

watch(() => route.params.id, () => {
  fetchBookDetails()
})

function goToRecord(direction: 'next' | 'prev') {
  const parsedId = parseInt(currentId.value, 10)
  if (isNaN(parsedId)) {
    router.push("/catalogue")
    return
  }
  const newId = direction === 'next' ? parsedId + 1 : parsedId - 1
  if (newId > 0) {
    router.push(`/details/${newId}`)
  }
}

function handleKeydown(event: KeyboardEvent) {
  const targetTag = (event.target as HTMLElement)?.tagName
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(targetTag)) return

  if (event.key === 'ArrowLeft') {
    goToRecord('prev')
  } else if (event.key === 'ArrowRight') {
    goToRecord('next')
  } else if (event.key === 'e' || event.key === 'E') {
    editRecord()
  } else if (event.key === 'Backspace') {
    returnToCatalogue()
  }
}

function editRecord() {
  const sNo = book.value?.serial_no || currentId.value
  router.push({
    name: 'EditItem',
    params: { id: sNo }
  })
}

function returnToCatalogue() {
  router.push("/catalogue")
}

onMounted(() => {
  fetchBookDetails()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="saas-container">
    <!-- Top Action Toolbar -->
    <header class="saas-header">
      <div class="nav-cluster">
        <button class="btn btn-subtle" @click="returnToCatalogue" title="Shortcut: Backspace">
          <span>←</span> Back to Catalogue
        </button>
      </div>

      <div class="action-cluster">
        <button class="btn btn-action" @click="refreshRecord" title="Refresh Data">
          Refresh
        </button>
        <button class="btn btn-action" @click="editRecord" title="Shortcut: E">
          Edit Record
        </button>
        <button class="btn btn-primary" @click="copyRecordId" :title="copyButtonText">
          {{ copyButtonText }}
        </button>
      </div>
    </header>

    <!-- Main Workspace -->
    <main class="saas-main">
      <div v-if="loading" class="state-box">
        <div class="spinner"></div>
        <p>Loading archival record...</p>
      </div>

      <div v-else-if="error" class="state-box">
        <div class="error-icon">⚠️</div>
        <h3>Record Not Found</h3>
        <p>Could not retrieve record identifier [{{ currentId }}].</p>
        <button class="btn btn-primary" @click="refreshRecord">Retry</button>
      </div>

      <div v-else-if="book" class="workspace-grid-layout">
        
        <!-- Identifiers Bar -->
        <div class="saas-id-bar">
          <div class="id-item">
            <span class="field-label">Primary ID</span>
            <span class="field-val mono accent-blue">{{ book.record_id || 'PENDING' }}</span>
          </div>
          <div class="id-item">
            <span class="field-label">Work ID</span>
            <span class="field-val mono">{{ book.work_id || 'N/A' }}</span>
          </div>
          <div class="id-item">
            <span class="field-label">Serial No.</span>
            <span class="field-val mono">#{{ book.serial_no || currentId }}</span>
          </div>
          <div class="id-item">
            <span class="field-label">Database ID</span>
            <span class="field-val mono text-muted">{{ book.id || 'N/A' }}</span>
          </div>
          <div class="id-item">
            <span class="field-label">Accession No.</span>
            <span class="field-val mono accent-purple">{{ book.accession_no || 'N/A' }}</span>
          </div>
        </div>

        <!-- Main Content Split Grid -->
        <div class="content-split-grid">
          
          <!-- Left Column: Bibliographic & Role-Based Attribution -->
          <div class="column-stack">
            <section class="saas-card">
              <h3 class="card-title">Publication Overview</h3>
              
              <div class="field-row-stack">
                <span class="field-label">Title / Name</span>
                <div class="title-value">{{ book.title || 'Untitled Work' }}</div>
              </div>

              <!-- Role-Based Attribution Hierarchy -->
              <div class="field-row-stack" v-if="book.work_nature">
                <span class="field-label">Work Nature</span>
                <div class="field-val accent-blue font-medium">{{ book.work_nature }}</div>
              </div>

              <div class="field-row-stack">
                <span class="field-label">Author / Creator</span>
                <div class="field-val">{{ book.author || 'Unknown Author' }}</div>
              </div>

              <div class="field-row-stack" v-if="book.original_author">
                <span class="field-label">Original Author</span>
                <div class="field-val">{{ book.original_author }}</div>
              </div>

              <div class="field-row-stack" v-if="book.translator">
                <span class="field-label">Translator</span>
                <div class="field-val">{{ book.translator }}</div>
              </div>

              <div class="field-row-stack" v-if="book.compiler_editor">
                <span class="field-label">Compiler / Editor</span>
                <div class="field-val">{{ book.compiler_editor }}</div>
              </div>

              <div class="field-row-stack" v-if="book.publisher">
                <span class="field-label">Publisher</span>
                <div class="field-val">{{ book.publisher }}</div>
              </div>

              <div class="fields-inline-group" style="margin-top: 1rem;">
                <div class="field-row-stack" style="flex: 2;">
                  <span class="field-label">Genres & Classifications</span>
                  <div class="tags-wrapper">
                    <span v-for="genre in splitGenres" :key="genre" class="saas-tag">{{ genre }}</span>
                  </div>
                </div>

                <div class="field-row-stack" style="flex: 1;" v-if="book.category">
                  <span class="field-label">Category</span>
                  <div class="field-val">{{ book.category }}</div>
                </div>
              </div>
            </section>

            <!-- Editorial & Notes Card -->
            <section class="saas-card" v-if="book.original_language || book.notes">
              <h3 class="card-title">Editorial & Notes</h3>
              
              <div class="field-row-stack" v-if="book.original_language">
                <span class="field-label">Original Language</span>
                <div class="field-val">{{ book.original_language }}</div>
              </div>

              <div class="field-row-stack" v-if="book.notes">
                <span class="field-label">Notes</span>
                <div class="field-val notes-val">{{ book.notes }}</div>
              </div>
            </section>
          </div>

          <!-- Right Column: Specifications, Identifiers & Physical Artifact Details -->
          <div class="column-stack">
            <section class="saas-card">
              <h3 class="card-title">Specifications & Standards</h3>
              
              <div class="spec-table-row" v-if="book.isbn">
                <span class="field-label">ISBN</span>
                <span class="spec-val mono">{{ book.isbn }}</span>
              </div>

              <div class="spec-table-row" v-if="book.lccn">
                <span class="field-label">LCCN</span>
                <span class="spec-val mono">{{ book.lccn }}</span>
              </div>

              <div class="spec-table-row" v-if="book.oclc_no">
                <span class="field-label">OCLC No.</span>
                <span class="spec-val mono">{{ book.oclc_no }}</span>
              </div>

              <div class="spec-table-row" v-if="book.publication_year || book.year">
                <span class="field-label">Publication Year</span>
                <span class="spec-val mono">{{ book.publication_year || book.year }}</span>
              </div>

              <div class="spec-table-row" v-if="book.edition_statement">
                <span class="field-label">Edition</span>
                <span class="spec-val mono">{{ book.edition_statement }}</span>
              </div>

              <div class="spec-table-row" v-if="book.series_title">
                <span class="field-label">Series & Volume</span>
                <span class="spec-val mono">{{ book.series_title }} <span v-if="book.series_volume">({{ book.series_volume }})</span></span>
              </div>

              <div class="spec-table-row">
                <span class="field-label">Language</span>
                <span class="spec-val mono">{{ book.language || 'English' }}</span>
              </div>

              <div class="spec-table-row" v-if="book.ddc">
                <span class="field-label">DDC Code</span>
                <span class="spec-val mono">{{ book.ddc }}</span>
              </div>

              <div class="spec-table-row" v-if="book.shelf || book.call_no">
                <span class="field-label">Shelf / Call No.</span>
                <span class="spec-val mono">{{ book.shelf || book.call_no }}</span>
              </div>
            </section>

            <!-- Artifact & Rare-Book History Card -->
            <section class="saas-card" v-if="book.physical_condition || book.binding_type || book.provenance_source || book.artifactual_notes || book.access_restrictions">
              <h3 class="card-title">Artifact & Preservation History</h3>
              
              <div class="spec-table-row" v-if="book.physical_condition">
                <span class="field-label">Condition</span>
                <span class="field-val">{{ book.physical_condition }}</span>
              </div>

              <div class="spec-table-row" v-if="book.binding_type">
                <span class="field-label">Binding Type</span>
                <span class="field-val">{{ book.binding_type }}</span>
              </div>

              <div class="spec-table-row" v-if="book.provenance_source">
                <span class="field-label">Provenance / Source</span>
                <span class="field-val">{{ book.provenance_source }}</span>
              </div>

              <div class="spec-table-row" v-if="book.access_restrictions">
                <span class="field-label">Access Restrictions</span>
                <span class="field-val accent-purple">{{ book.access_restrictions }}</span>
              </div>

              <div class="field-row-stack" style="margin-top: 1rem;" v-if="book.artifactual_notes">
                <span class="field-label">Artifact Markers (Marginalia / Bookplates)</span>
                <div class="field-val notes-val">{{ book.artifactual_notes }}</div>
              </div>
            </section>

            <!-- Abstract Card -->
            <section class="saas-card" v-if="book.description || book.abstract">
              <h3 class="card-title">Abstract</h3>
              <p class="abstract-content">{{ book.description || book.abstract }}</p>
            </section>
          </div>

        </div>

        <!-- System Metadata Section -->
        <section class="saas-card" v-if="Object.keys(dynamicExtraFields).length > 0">
          <h3 class="card-title">System & Archival Metadata</h3>
          <div class="meta-grid">
            <div class="spec-table-row" v-for="(val, key) in dynamicExtraFields" :key="key">
              <span class="field-label">{{ key }}</span>
              <span class="field-val mono">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
            </div>
          </div>
        </section>

        <!-- Navigation Footer -->
        <footer class="saas-footer">
          <button class="btn btn-subtle" @click="goToRecord('prev')" title="Previous Record (Left Arrow)">
            ← Previous Record
          </button>
          <button class="btn btn-subtle" @click="goToRecord('next')" title="Next Record (Right Arrow)">
            Next Record →
          </button>
        </footer>

      </div>
    </main>
  </div>
</template>

<style scoped>
.saas-container {
  min-height: 100vh;
  background-color: #090d16;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  padding: 1.5rem 2rem;
}

.saas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #111827;
  padding: 0.75rem 1.25rem;
  border-radius: 6px;
  border: 1px solid #1f2937;
  margin-bottom: 1.5rem;
}

.nav-cluster, .action-cluster {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.45rem 0.85rem;
  border-radius: 5px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.btn-subtle {
  background-color: #1f2937;
  color: #cbd5e1;
  border-color: #374151;
}
.btn-subtle:hover {
  background-color: #374151;
  color: #fff;
}

.btn-action {
  background-color: #111827;
  color: #94a3b8;
  border-color: #374151;
}
.btn-action:hover {
  background-color: #1f2937;
  color: #e2e8f0;
}

.btn-primary {
  background-color: #2563eb;
  color: #ffffff;
}
.btn-primary:hover {
  background-color: #1d4ed8;
}

.saas-id-bar {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1rem;
  background-color: #111827;
  padding: 1rem 1.25rem;
  border-radius: 6px;
  border: 1px solid #1f2937;
}

.id-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.workspace-grid-layout {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.content-split-grid {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 1.25rem;
}

.column-stack {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.saas-card {
  background-color: #111827;
  border: 1px solid #1f2937;
  border-radius: 6px;
  padding: 1.25rem;
}

.card-title {
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-top: 0;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #1f2937;
}

.field-row-stack {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
}
.field-row-stack:last-child {
  margin-bottom: 0;
}

.fields-inline-group {
  display: flex;
  gap: 1rem;
}

.field-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}

.field-val {
  font-size: 0.95rem;
  color: #f8fafc;
}

.title-value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #ffffff;
  line-height: 1.4;
}

.notes-val {
  font-size: 0.9rem;
  color: #94a3b8;
  line-height: 1.5;
}

.tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.saas-tag {
  background-color: #1e3a8a;
  color: #93c5fd;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.spec-table-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #1f2937;
  font-size: 0.875rem;
}
.spec-table-row:last-child {
  border-bottom: none;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85rem;
}

.accent-blue { color: #38bdf8; }
.accent-purple { color: #c084fc; }
.text-muted { color: #64748b; }
.font-medium { font-weight: 500; }

.abstract-content {
  font-size: 0.9rem;
  line-height: 1.6;
  color: #94a3b8;
  margin: 0;
}

.saas-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 0.5rem;
}

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  background-color: #111827;
  border-radius: 6px;
  border: 1px solid #1f2937;
  color: #94a3b8;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #1f2937;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>