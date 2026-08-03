<template>
  <div class="athenaeum-vault">
    <main class="catalogue-main">
      <header class="catalogue-header">
        <div class="header-top-row">
          <div class="cat-path">Main Registry <span class="sep">/</span> Central Catalogue Index</div>
          <div class="stats-tracker">
            <span class="total-badge">Total System: <strong>{{ totalBooks }} Records</strong></span>
            <span class="pipe">|</span>
            <span class="page-badge">Showing: <strong>{{ books.length }}</strong></span>
          </div>
        </div>
        <h1 class="catalogue-title">The Central Index Catalogue</h1>
      </header>

      <div v-if="loading" class="vault-loader">Consulting the Registry...</div>

      <div v-else-if="books.length === 0" class="empty-catalogue">
        No records match the requested catalogue criteria.
      </div>

      <div v-else class="ledger-table-wrapper" ref="scrollContainer">
        <table class="ledger-table">
          <thead>
            <tr>
              <th class="col-sl">SL No</th>
              <th class="col-work-id">Work ID</th>
              <th class="col-acc">Accession No</th>
              <th class="col-title">Title</th>
              <th class="col-author">Author</th>
              <th class="col-cat">Category</th>
              <th class="col-shelf">Shelf</th>
              <th class="col-id">Record ID</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="(item, index) in books" 
              :key="`${item.serial_no}-${index}`"
              class="ledger-row"
              @click="viewBook(item.serial_no)"
            >
              <td class="cell-sl">#{{ (currentPage - 1) * itemsPerPage + index + 1 }}</td>
              <td class="cell-work-id">#{{ item.work_id || item.id || '—' }}</td>
              <td class="cell-acc"><span class="acc-pill">{{ item.accession_no }}</span></td>
              <td class="cell-title" :title="item.title">{{ item.title }}</td>
              <td class="cell-author">{{ item.author || '—' }}</td>
              <td class="cell-cat"><span class="cat-tag">{{ item.category }}</span></td>
              <td class="cell-shelf">{{ item.shelf || '—' }}</td>
              <td class="cell-id">{{ item.record_id }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="catalogue-footer">
        <div class="pagination-matrix">
          <button class="btn-matrix-nav" :disabled="currentPage === 1" @click="goToPage(1)">First</button>
          <button class="btn-matrix-nav" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">&lt;</button>

          <template v-for="(page, idx) in visiblePages" :key="idx">
            <span v-if="page === -1" class="matrix-ellipsis">...</span>
            <button 
              v-else 
              class="btn-matrix-number" 
              :class="{ active: page === currentPage }" 
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
          </template>

          <button class="btn-matrix-nav" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">&gt;</button>
          <button class="btn-matrix-nav" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">Last</button>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import { useAuthStore } from '@/stores/auth.ts' // <-- 1. IMPORT PINIA

const router = useRouter()
const authStore = useAuthStore() // <-- 2. INITIALIZE PINIA

const books = ref<any[]>([])
const loading = ref(true)
const totalBooks = ref(0)
const currentPage = ref(1)
const itemsPerPage = ref(15)
const scrollContainer = ref<HTMLElement | null>(null)

const totalPages = computed(() => {
  return Math.ceil(totalBooks.value / itemsPerPage.value) || 1
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages: number[] = []

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    if (current > 3) {
      pages.push(-1)
    }
    const start = Math.max(2, current - 1)
    const end = Math.min(total - 1, current + 1)
    for (let i = start; i <= end; i++) {
      if (!pages.includes(i)) pages.push(i)
    }
    if (current < total - 2) {
      pages.push(-1)
    }
    if (!pages.includes(total)) pages.push(total)
  }
  return pages
})

async function fetchCatalogue() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      limit: itemsPerPage.value,
      sort_by: "serial_no",
      order: "asc"
    }

    // 3. THE FIX: Grab the token directly from the Pinia store!
    // We check both common naming conventions just to be safe.
    const token = authStore.accessToken || authStore.access_token

    if (!token) {
      loading.value = false
      router.push("/login")
      return
    }

    const config = {
      params,
      headers: {
        Authorization: `Bearer ${token}`
      }
    }

    // NOTE: Make sure your axios defaults have the base URL set, 
    // or change this to your full URL (e.g., 'http://127.0.0.1:8000/catalogue/')
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    const response = await axios.get(`${baseUrl}/catalogue/`, config)
    
    books.value = response.data.data
    totalBooks.value = response.data.total
    
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = 0
    }
  } catch (err: any) {
    if (err.response?.status === 401) {
      books.value = []
      totalBooks.value = 0
      router.push("/login")
      return
    }
    console.error("Failed to map the records:", err)
  } finally {
    loading.value = false
  }
}

function goToPage(targetPage: number) {
  if (targetPage >= 1 && targetPage <= totalPages.value) {
    currentPage.value = targetPage
    fetchCatalogue()
  }
}

function viewBook(serialNo: number) {
  router.push(`/details/${serialNo}`)
}

onMounted(() => {
  fetchCatalogue()
})
</script>

<style scoped>
.athenaeum-vault {
  background: #111111;
  height: 100%;
  width: 100%;
  display: flex;
}

.catalogue-main {
  flex-grow: 1;
  background: #111111;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100vh - 40px);
}

.catalogue-header { 
  padding: 24px 32px 16px; 
  border-bottom: 1px solid #1c1c1c; 
}

.header-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.cat-path { 
  font-size: 11px; 
  font-weight: 600; 
  color: #cfb997; 
  text-transform: uppercase; 
  letter-spacing: 1.5px; 
}

.cat-path .sep { 
  color: #444444; 
  padding: 0 4px; 
}

.stats-tracker {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #8c8c8c;
}

.stats-tracker strong {
  color: #e0e0e0;
  font-weight: 600;
}

.pipe {
  margin: 0 10px;
  color: #262626;
}

.catalogue-title {
  font-size: 22px; 
  color: #e0e0e0; 
  margin: 0; 
  font-weight: 500; 
  letter-spacing: 0.5px;
}

.ledger-table-wrapper {
  flex-grow: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.ledger-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.ledger-table th {
  background: #161616;
  color: #cfb997;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 14px 16px;
  border-bottom: 1px solid #282828;
}

.ledger-row {
  border-bottom: 1px solid #1c1c1c;
  cursor: pointer;
  transition: background 0.2s ease;
}

.ledger-row:hover {
  background: #181715;
}

.ledger-row td {
  padding: 14px 16px;
  font-size: 13px;
  color: #c5c5c5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-sl, .cell-sl { width: 80px; font-family: monospace; color: #8c8c8c !important; }
.col-work-id, .cell-work-id { width: 90px; font-family: monospace; color: #cfb997 !important; }
.col-acc, .cell-acc { width: 140px; }
.col-title { max-width: 300px; }
.cell-title { font-weight: 500; color: #e0e0e0 !important; }
.col-author, .cell-author { max-width: 200px; }
.col-cat, .cell-cat { width: 130px; }
.col-shelf, .cell-shelf { width: 100px; }
.col-id, .cell-id { width: 180px; font-family: monospace; color: #555555 !important; font-size: 12px !important; }

.acc-pill {
  background: #1a221f;
  color: #10b981;
  font-family: monospace;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid #142e24;
}

.cat-tag {
  background: #1b1916;
  color: #cfb997;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #2a251e;
}

.vault-loader, .empty-catalogue {
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  color: #8c8c8c;
}

.catalogue-footer {
  padding: 16px 32px; 
  background: #141414; 
  border-top: 1px solid #1c1c1c;
  display: flex; 
  justify-content: center; 
  align-items: center;
  margin-top: auto;
}

.pagination-matrix {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-matrix-nav, .btn-matrix-number {
  background: #161616;
  border: 1px solid #282828;
  color: #a3a3a3;
  font-size: 12px;
  font-weight: 500;
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.15s ease;
  min-width: 32px;
}

.btn-matrix-number.active {
  background: #cfb997;
  color: #121212;
  border-color: #cfb997;
  font-weight: 600;
}

.btn-matrix-nav:hover:not(:disabled), .btn-matrix-number:hover:not(.active) {
  border-color: #cfb997;
  color: #cfb997;
}

.btn-matrix-nav:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.matrix-ellipsis {
  color: #444444;
  padding: 0 4px;
}

/* =====================================================
   📱 MOBILE RESPONSIVENESS FIXES
===================================================== */
@media (max-width: 768px) {
  .catalogue-header {
    padding: 16px 16px 12px 16px;
  }

  .header-top-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 12px;
  }

  .pipe {
    display: none; /* Hide the separator on mobile to save space */
  }

  .stats-tracker {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .ledger-table-wrapper {
    padding: 16px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch; /* Smooth horizontal scrolling */
  }

  /* Force the table to be wider than the phone screen so it doesn't crush text */
  .ledger-table {
    min-width: 800px; 
  }

  .catalogue-footer {
    padding: 16px;
  }

  .pagination-matrix {
    flex-wrap: wrap; /* Allows pagination buttons to wrap to a new line if needed */
    justify-content: center;
  }
}
</style>