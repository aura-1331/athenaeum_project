<script setup>
import { ref, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import axios from 'axios'

const router = useRouter()
const query = ref("")
const results = ref([])
const selectedItem = ref(null)
const loading = ref(false)
const searchInput = ref(null)
const auditQuery = ref("")

// Pagination state
const page = ref(1)
const limit = 5
const total = ref(0)
let debounceTimer = null

const categories = {
  identity: ['title', 'author', 'language', 'category', 'genre', 'isbn'],
  library: ['accession_no', 'call_no', 'publisher', 'year', 'ddc', 'notes', 'original_language'],
  system: ['work_id', 'serial_no'] 
}

const filteredAudit = computed(() => {
  if (!selectedItem.value?.audit) return []
  if (!auditQuery.value) return selectedItem.value.audit
  const q = auditQuery.value.toLowerCase()
  return selectedItem.value.audit.filter(a => 
    a.old_status.toLowerCase().includes(q) || 
    a.new_status.toLowerCase().includes(q) || 
    a.changed_at.toLowerCase().includes(q)
  )
})

const totalPages = computed(() => Math.ceil(total.value / limit))

function handleInput(){
  clearTimeout(debounceTimer)
  const q = query.value.trim()
  if(!q){ results.value=[]; total.value=0; selectedItem.value=null; return }
  debounceTimer = setTimeout(() => { 
    page.value = 1; 
    performSearch(q) 
  }, 300)
}

// 🔍 1. GLOBAL SEARCH (Uses the Natural Interceptor)
async function performSearch(q){
  if (!q) return
  loading.value = true
  try {
    // 🚀 Switch to Axios. 
    // We don't need the full URL 'http://127.0.0.1:8000' because main.js handles it!
    const response = await axios.get('/search', {
      params: {
        q: q,
        page: page.value,
        limit: limit
      }
    })
    
    const data = response.data
    const list = data.data || []
    results.value = list
    total.value = data.total || list.length
  } catch (err) {
    console.error("❌ Search failed:", err)
    if (err.response?.status === 401) router.push('/login')
  } finally {
    loading.value = false
  }
}

function changePage(newPage) {
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    performSearch(query.value)
  }
}

// 📖 2. ITEM INSPECTOR (Uses the Natural Interceptor)
async function openDetail(serial) {
  try {
    // 🚀 Switch to Axios. 
    const response = await axios.get(`/search/item/${serial}`)
    selectedItem.value = response.data
    auditQuery.value = "" 
  } catch (err) {
    console.error("❌ Failed to load item details:", err)
  }
}

function closeInspector(){ selectedItem.value = null }
function exportToPDF() { window.print() }

// FIX: Added 'serial' parameter so the table buttons work
function goToEdit(serial) {
  const id = serial || selectedItem.value?.metadata?.serial_no
  if (id) {
    router.push(`/edit-item/${id}`)
  }
}

onMounted(() => {
  searchInput.value?.focus()
  if (query.value) {
    performSearch(query.value)
  }
})

function highlight(text){
  if(!text) return ""
  const str = text.toString()
  if(!query.value) return str
  const regex = new RegExp(`(${query.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi")
  return str.replace(regex, `<mark>$1</mark>`)
}

const getGroup = (groupKeys) => {
  if (!selectedItem.value) return {}
  const filtered = {}
  groupKeys.forEach(key => {
    if (selectedItem.value.metadata[key] !== undefined && !key.includes('search_key')) {
      filtered[key] = selectedItem.value.metadata[key]
    }
  })
  return filtered
}
</script>

<template>
<div class="search-page">
  <div class="search-header no-print">
    <h2>Global Search <span class="count" v-if="total > 0">({{ total }} results)</span></h2>
    <input ref="searchInput" class="search-input" v-model="query" @input="handleInput" placeholder="Search books...">
  </div>

  <div class="results-container no-print">
    <div v-if="loading" class="loading-state">Searching...</div>
    
    <div v-if="results.length && !loading" class="result-list">
  <div
    v-for="(row, index) in results"
    :key="row.serial_no"
    class="result-card"
  >
    <div class="result-left">
      <small class="result-index">
        #{{ ((page - 1) * limit) + index + 1 }}
      </small>

      <h3 
        class="result-title"
        @click="openDetail(row.serial_no)"
        v-html="highlight(row.title)"
      ></h3>

      <p class="result-author" v-html="highlight(row.author)"></p>

      <div class="result-meta">
        <span>{{ row.language || "Unknown Language" }}</span>
        <span>{{ row.accession_no || row.serial_no }}</span>
      </div>
    </div>

    <div class="result-right">
      <button
        class="inspect-btn"
        @click="openDetail(row.serial_no)"
      >
        Inspect Record
      </button>

      <button
        class="edit-btn-small"
        @click="goToEdit(row.serial_no)"
      >
        Edit
      </button>
    </div>
  </div>
</div>

    <div v-if="total > limit" class="pagination no-print">
      <button :disabled="page === 1" @click="changePage(page - 1)">PREV</button>
      <span class="page-info">Page {{ page }} of {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">NEXT</button>
    </div>

    <div v-if="!loading && query && !results.length" class="empty-msg">
      No books found matching "{{ query }}"
    </div>
  </div>

  <Transition name="fade">
    <div v-if="selectedItem" class="modal-overlay" @click.self="closeInspector">
      <div class="inspector modal-content">
        <div class="inspector-title-box">
          <h3>{{ selectedItem.metadata.title }}</h3>
          <div class="header-actions no-print">
            <button class="edit-btn" @click="goToEdit()">Edit Book</button> 
            <button class="pdf-btn" @click="exportToPDF">Export PDF</button>
            <button class="close-btn" @click="closeInspector">Close</button>
          </div>
        </div>

        <div class="scroll-content">
          <div v-for="(keys, groupName) in categories" :key="groupName" :class="['category-section', groupName + '-bg']">
            <div class="category-label">{{ groupName.toUpperCase() }} DETAILS</div>
            <div class="meta-grid">
              <div v-for="(val, key) in getGroup(keys)" :key="key" class="meta-item" :class="{ 'full-width': key === 'notes' }">
                <small class="sub-label">{{ key.toUpperCase().replace('_', ' ') }}</small>
                <div v-html="highlight(String(val))" class="val-text"></div>
              </div>
            </div>
          </div>

          <div class="audit-section">
            <div class="audit-sticky-header no-print">
              <div class="category-label">RECORD HISTORY</div>
              <input v-model="auditQuery" class="audit-search" placeholder="Filter history...">
            </div>
            
            <div class="audit-timestamps">
               <p><strong>Created:</strong> {{ selectedItem.metadata.created_at }}</p>
               <p><strong>Updated:</strong> {{ selectedItem.metadata.updated_at }}</p>
            </div>

            <ul v-if="filteredAudit.length">
              <li v-for="a in filteredAudit" :key="a.id" class="audit-li">
                <span class="status-badge">{{ a.old_status }}</span> → <span class="status-badge new">{{ a.new_status }}</span>
                <span class="audit-time">{{ a.changed_at }}</span>
              </li>
            </ul>
            <div v-else class="empty-msg">No history found.</div>
          </div>
        </div>
      </div> 
    </div>
  </Transition>
</div>
</template>

<style scoped>
/* Updated to target specific columns */
th:nth-child(1), td:nth-child(1), 
th:nth-child(2), td:nth-child(2) {
  width: 80px;
  text-align: center;
  color: #888;
}

.edit-btn-small {
  background: #fcc419;
  color: #000;
  border: none;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 12px;
  transition: background 0.2s;
}

.edit-btn-small:hover {
  background: #ffec99;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.search-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 30px;
}
.search-input {
  width: 100%;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #25324a;
  background: #101827;
  color: white;
  margin-bottom: 10px;
  font-size: 15px;
  transition: all 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: #18d2c3;
  box-shadow: 0 0 0 3px rgba(24,210,195,0.15);
}

.loading-state { text-align: center; padding: 20px; color: #888; }

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  background: #111827;
  border-radius: 12px;
  overflow: hidden;
}
tbody tr:hover {
  background: rgba(24,210,195,0.08);
}
th { text-align: left; padding: 12px; background: #222; color: #888; font-size: 0.8rem; text-transform: uppercase; border-bottom: 2px solid #333;}
td { padding: 12px; border-bottom: 1px solid #333; font-size: 0.9rem; }
.title {
  cursor: pointer;
  color: #18d2c3;
  font-weight: 600;
}
.title:hover { text-decoration: underline; }

.pagination { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 25px; padding: 10px; }
.pagination button { background: #333; color: white; border: 1px solid #444; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.pagination button:hover:not(:disabled) { background: #444; }
.pagination button:disabled { opacity: 0.3; cursor: not-allowed; }
.page-info { font-size: 0.85rem; color: #888; }

.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); display: flex; justify-content: center; align-items: center; z-index: 1000; }

.inspector.modal-content {
  background: #0b1120;}

.inspector-title-box {
  background: linear-gradient(
    90deg,
    #0f172a,
    #152238
  );
  border-bottom: 1px solid #23314d;}

.header-actions { display: flex; gap: 8px; }
.edit-btn { background: #f59f00; color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 0.8rem; }
.pdf-btn { background: #2b8a3e; color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.close-btn { background: rgba(0,0,0,0.3); color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }

.scroll-content { overflow-y: auto; flex-grow: 1; }
.category-section { padding: 25px; border-bottom: 1px solid #222; }

.category-label { color: #4dabf7; font-size: 0.8rem; font-weight: 800; margin-bottom: 15px; letter-spacing: 1px; }
.sub-label { color: #fcc419; font-size: 0.7rem; font-weight: 700; margin-bottom: 5px; display: block; }
.val-text { color: #ffffff !important; font-size: 1rem; }

.meta-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
.full-width { grid-column: 1 / -1; }

.audit-sticky-header { position: sticky; top: 0; background: #0a0c0e; padding: 15px 0; display: flex; justify-content: space-between; align-items: center; z-index: 5; border-bottom: 1px solid #222; }
.audit-search { background: #1a1a1a; border: 1px solid #444; color: white; padding: 6px 12px; border-radius: 4px; font-size: 0.85rem; width: 220px; }

.audit-section { padding: 0 25px 25px 25px; background: #0a0c0e; }
.audit-timestamps { font-size: 0.85rem; color: #999; margin: 15px 0; }
.audit-li { padding: 12px 0; border-bottom: 1px solid #222; font-size: 0.85rem; display: flex; align-items: center; gap: 10px; }
.status-badge { background: #333; padding: 2px 8px; border-radius: 4px; color: #aaa; }
.status-badge.new {
  background: #18d2c3;
  color: #04111f;
  font-weight: bold;
}
.audit-time { color: #666; font-size: 0.75rem; margin-left: auto; }

mark { background: #fcc419; color: black; border-radius: 2px; }

.result-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 20px;
}

.result-card {
  background: #111827;
  border: 1px solid #22314d;
  border-radius: 14px;
  padding: 22px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
}

.result-card:hover {
  transform: translateY(-2px);
  border-color: #18d2c3;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
}

.result-index {
  color: #18d2c3;
  font-weight: bold;
}

.result-title {
  color: white;
  font-size: 20px;
  margin: 8px 0;
  cursor: pointer;
}

.result-title:hover {
  color: #18d2c3;
}

.result-author {
  color: #94a3b8;
  margin-bottom: 10px;
}

.result-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.result-meta span {
  background: #1e293b;
  color: #18d2c3;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.result-right {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.inspect-btn {
  background: #18d2c3;
  color: #04111f;
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
}

@media print {
  .no-print { display: none !important; }
  .modal-overlay { background: white; position: absolute; }
  .inspector.modal-content { border: none; width: 100%; max-height: none; }
  .val-text, .sub-label, .category-label { color: black !important; }
}
</style>