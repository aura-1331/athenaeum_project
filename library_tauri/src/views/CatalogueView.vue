<template>
  <div class="athenaeum-vault">
    <main class="catalogue-main">
      <header class="catalogue-header">
        <div class="header-top-row">
          <div class="cat-path">Main Registry <span class="sep">/</span> Index Lucerna</div>
          <div class="stats-tracker">
            <span class="total-badge">Total System: <strong>{{ totalBooks }} Books</strong></span>
            <span class="pipe">|</span>
            <span class="page-badge">This Page Contains: <strong>{{ books.length }} Books</strong></span>
          </div>
        </div>
        <h1 class="catalogue-title">The Central Index Catalogue</h1>
      </header>

      <div v-if="loading && books.length === 0" class="vault-loader">Consulting the Orbis Registry...</div>

      <div v-else-if="books.length === 0" class="empty-catalogue">
        No records match the requested lookup criteria.
      </div>

      <div v-else class="grid-scroll-container" ref="scrollContainer" @scroll="handleScroll">
        <div class="catalogue-grid">
          <div 
            v-for="(item, index) in books" 
            :key="`${item.serial_no}-${index}`" 
            class="book-card"
            :style="getCardStyle(item.serial_no)"
            @click="viewBook(item.serial_no)"
          >
            <div class="card-spine">
              <span class="card-sl">#{{ item.serial_no }}</span>
            </div>
            <div class="card-body">
              <div class="card-meta">
                <span>{{ item.category }}</span>
                <span>•</span>
                <span>Acc No: <strong>{{ item.accession_no }}</strong></span>
              </div>
              <h3 class="card-title">{{ item.title }}</h3>
              <p class="card-author">Scribe: <strong>{{ item.author || 'Unknown' }}</strong></p>
              <footer class="card-footer">
                <span class="badge-shelf">Shelf {{ item.shelf || 'N/A' }}</span>
                <span class="badge-id">{{ item.record_id }}</span>
              </footer>
            </div>
          </div>
        </div>

        <div v-if="loadingMore" class="loading-more-indicator">
          Retrieving subsequent records...
        </div>
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

const router = useRouter()
const books = ref<any[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const totalBooks = ref(0)
const currentPage = ref(1)
const itemsPerPage = ref(12)
const scrollContainer = ref<HTMLElement | null>(null)

const colorPalette = [
  { bg: "#ffffff", text: "#111111", meta: "#8b0000", border: "rgba(0,0,0,0.06)", foot: "rgba(0,0,0,0.05)" },
  { bg: "#250906", text: "#f2e8cf", meta: "#d4af37", border: "rgba(214,175,55,0.2)", foot: "rgba(255,255,255,0.05)" },
  { bg: "#141d26", text: "#ffffff", meta: "#1da1f2", border: "rgba(255,255,255,0.1)", foot: "rgba(255,255,255,0.05)" },
  { bg: "#f4f1ea", text: "#2c3e50", meta: "#e74c3c", border: "rgba(0,0,0,0.08)", foot: "rgba(0,0,0,0.04)" },
  { bg: "#1e272c", text: "#eceff1", meta: "#00b0ff", border: "rgba(255,255,255,0.08)", foot: "rgba(255,255,255,0.04)" },
  { bg: "#e8f5e9", text: "#1b5e20", meta: "#2e7d32", border: "rgba(0,0,0,0.06)", foot: "rgba(0,0,0,0.03)" },
  { bg: "#3e2723", text: "#efebe9", meta: "#ffb74d", border: "rgba(255,255,255,0.1)", foot: "rgba(255,255,255,0.05)" }
]

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

function getCardStyle(serialNo: number) {
  const scheme = colorPalette[serialNo % colorPalette.length]
  return {
    '--card-bg': scheme.bg,
    '--card-text': scheme.text,
    '--card-meta': scheme.meta,
    '--card-border': scheme.border,
    '--card-foot': scheme.foot
  }
}

async function fetchCatalogue(appendMode = false) {
  if (!appendMode) {
    loading.value = true
  } else {
    loadingMore.value = true
  }

  try {
    const params = {
      page: currentPage.value,
      limit: itemsPerPage.value,
      sort_by: "serial_no",
      order: "asc"
    }

    const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token")

    if (!token) {
      loading.value = false
      loadingMore.value = false
      router.push("/login")
      return
    }

    const config = {
      params,
      headers: {
        Authorization: `Bearer ${token}`
      }
    }

    const response = await axios.get("/catalogue/", config)
    
    if (appendMode) {
      books.value = [...books.value, ...response.data.data]
    } else {
      books.value = response.data.data
      if (scrollContainer.value) {
        scrollContainer.value.scrollTop = 0
      }
    }
    totalBooks.value = response.data.total
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
    loadingMore.value = false
  }
}

function goToPage(targetPage: number) {
  if (targetPage >= 1 && targetPage <= totalPages.value) {
    currentPage.value = targetPage
    fetchCatalogue(false)
  }
}

function handleScroll() {
  if (!scrollContainer.value || loading.value || loadingMore.value) return

  const { scrollTop, scrollHeight, clientHeight } = scrollContainer.value

  const cardHeight = 160
  const rowGap = 25
  const scrollIndex = Math.floor(scrollTop / (cardHeight + rowGap))
  const itemsPerRow = Math.max(1, Math.floor(scrollContainer.value.clientWidth / 280))
  const itemsPassed = scrollIndex * itemsPerRow
  
  const currentScrollPage = Math.min(
    totalPages.value,
    Math.max(1, Math.ceil(itemsPassed / itemsPerPage.value) + 1)
  )
  
  if (currentScrollPage !== currentPage.value) {
    currentPage.value = currentScrollPage
  }

  if (scrollTop + clientHeight >= scrollHeight - 50) {
    const currentFetchedPages = Math.ceil(books.value.length / itemsPerPage.value)
    if (currentFetchedPages < totalPages.value) {
      currentPage.value = currentFetchedPages + 1
      fetchCatalogue(true)
    }
  }
}

function viewBook(serialNo: number) {
  const routeData = router.resolve(`/details/${serialNo}`)
  window.open(routeData.href, '_blank')
}

onMounted(() => {
  fetchCatalogue(false)
})
</script>

<style scoped>
.athenaeum-vault {
  --mahogany: #250906;
  --gold: #d4af37;
  --parchment: #f2e8cf;
  --ink: #111;
  --blood: #8b0000;
  background: var(--parchment); 
  height: 100%; 
  width: 100%; 
  display: flex; 
}

.catalogue-main {
  flex-grow: 1;
  background: var(--parchment);
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100vh - 40px);
}

.catalogue-header { 
  padding: 30px 40px 15px; 
  border-bottom: 1px solid rgba(0,0,0,0.08); 
}

.header-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.cat-path { 
  font-size: 13px; 
  font-weight: 800; 
  color: var(--mahogany); 
  text-transform: uppercase; 
  letter-spacing: 1.5px; 
}

.cat-path .sep { 
  color: var(--blood); 
  padding: 0 5px; 
}

.stats-tracker {
  display: flex;
  align-items: center;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #3d2b1f;
  font-weight: 700;
}

.stats-tracker strong {
  color: var(--blood);
  font-weight: 900;
}

.pipe {
  margin: 0 12px;
  opacity: 0.3;
}

.catalogue-title {
  font-family: 'Playfair Display', serif; 
  font-size: 30px; 
  color: var(--ink); 
  margin: 0; 
  font-weight: 900; 
}

.grid-scroll-container {
  flex-grow: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 30px 40px;
}

.catalogue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 25px;
  align-items: start;
}

.book-card {
  background: var(--card-bg, #fff);
  border-radius: 4px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  display: flex;
  cursor: pointer;
  overflow: hidden;
  border: 1px solid var(--card-border, rgba(0, 0, 0, 0.06));
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  height: 160px;
}

.book-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(37, 9, 6, 0.25);
}

.card-spine {
  width: 35px;
  background: var(--mahogany);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-sl {
  color: var(--gold);
  font-weight: 900;
  font-size: 11px;
  transform: rotate(-90deg);
  white-space: nowrap;
}

.card-body {
  flex-grow: 1;
  padding: 15px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
}

.card-meta {
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 800;
  color: var(--card-meta, #555);
  letter-spacing: 0.5px;
}

.card-meta strong {
  color: var(--blood);
  font-weight: 900;
}

.card-meta span {
  opacity: 0.7;
  margin: 0 4px;
}

.card-title {
  font-family: 'Playfair Display', serif;
  font-size: 16px;
  color: var(--card-text, var(--ink));
  margin: 5px 0;
  font-weight: 900;
  line-height: 1.2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-author {
  font-size: 12px;
  color: var(--card-text, #555);
  opacity: 0.8;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  border-top: 1px solid var(--card-border, rgba(0, 0, 0, 0.05));
  padding-top: 8px;
  background: var(--card-foot, transparent);
}

.badge-shelf {
  font-size: 10px;
  font-weight: 800;
  background: rgba(37, 9, 6, 0.08);
  color: var(--mahogany);
  padding: 2px 6px;
  border-radius: 3px;
}

.badge-id {
  font-size: 9px;
  font-weight: 700;
  color: var(--card-text, #777);
  opacity: 0.6;
}

.vault-loader, .empty-catalogue {
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: var(--mahogany);
  font-style: italic;
}

.loading-more-indicator {
  text-align: center;
  padding: 20px 0;
  font-size: 12px;
  font-weight: 800;
  color: var(--mahogany);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.catalogue-footer {
  padding: 15px 40px; 
  background: rgba(0, 0, 0, 0.04); 
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex; 
  justify-content: center; 
  align-items: center;
  margin-top: auto;
}

.pagination-matrix {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-matrix-nav, .btn-matrix-number {
  background: transparent;
  border: 1px solid var(--mahogany);
  color: var(--mahogany);
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 35px;
}

.btn-matrix-number.active, .btn-matrix-nav:hover:not(:disabled), .btn-matrix-number:hover {
  background: var(--mahogany);
  color: #fff;
}

.btn-matrix-nav:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.matrix-ellipsis {
  color: var(--mahogany);
  font-weight: 900;
  padding: 0 4px;
}
</style>