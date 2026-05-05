<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, provide } from "vue"

import axios from 'axios'




// 1. Core State
const rows = ref<any[]>([])
provide('allBooks', rows)
const isCompact = ref(false)
const basicViewId = ref<number | null>(null)
let abortController: AbortController | null = null

// 2. Pagination & Sorting
const page = ref(1)
const limit = ref(10)
const total = ref(0)
const globalTotal = ref(0)
const sortBy = ref("serial_no")
const order = ref("asc")
const jumpPage = ref("")

// 3. Error Handling
const jumpError = ref(false)
const jumpMsg = ref("")

// 4. Filters
const filterTitle = ref("")
const filterAuthor = ref("")
const filterGenre = ref("")
const filterLanguage = ref("")
const filterCategory = ref("")
const activeFilters = ref<Record<string, string>>({})

// 5. Computed
const totalPages = computed(() => Math.ceil(total.value / limit.value))

const visiblePages = computed((): (number | string)[] => {
  const totalP = totalPages.value
  const current = page.value
  const delta = 2
  const range: number[] = []
  const result: (number | string)[] = []

  for (let i = 1; i <= totalP; i++) {
    if (i === 1 || i === totalP || (i >= current - delta && i <= current + delta)) {
      range.push(i)
    }
  }

  let last = 0
  for (const p of range) {
    if (p - last > 1) result.push("...")
    result.push(p)
    last = p
  }

  return result
})

// 6. Context Menu
const showMenu = ref(false)
const menuPos = ref({ x: 0, y: 0 })
const activeMenuBook = ref<any>(null)

function handleRightClick(e: MouseEvent, book: any) {
  showMenu.value = true
  activeMenuBook.value = book
  menuPos.value = { x: e.clientX, y: e.clientY }
}

function closeMenu() {
  showMenu.value = false
}

// 7. Load Catalogue
async function loadCatalogue() {
  if (abortController) abortController.abort()
  abortController = new AbortController()

  try {
    const params: any = {
      page: page.value,
      limit: limit.value,
      sort_by: sortBy.value,
      order: order.value,
    }

    if (activeFilters.value.title) params.title = activeFilters.value.title
    if (activeFilters.value.author) params.author = activeFilters.value.author
    if (activeFilters.value.genre) params.genre = activeFilters.value.genre
    if (activeFilters.value.language) params.language = activeFilters.value.language

    if (activeFilters.value.category) {
      let catRaw = activeFilters.value.category.toLowerCase().replace(/[\s-]/g, "")
      params.category = catRaw === "nonfiction" ? "Non-Fiction" : activeFilters.value.category
    }

    const response = await axios.get('/catalogue/', {
      params,
      signal: abortController.signal
    })

    const payload = response.data
    rows.value = payload.data || []
    total.value = payload.total || 0

  } catch (e: any) {
    if (axios.isCancel(e)) return
    console.error("❌ Catalogue Load Error:", e)
  }
}

/// Import the WebviewWindow class from Tauri v2


async function openFullDetails(row: any) {
  if (!row?.serial_no) {
    console.error("Missing serial number:", row)
    return
  }

  const detailUrl = `/#/details/${row.serial_no}`

  try {
    // Check if app is running inside Tauri
    if ((window as any).__TAURI__) {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')

      const windowLabel = `details-${row.serial_no}`

      const existingWindow = await WebviewWindow.getByLabel(windowLabel)

      if (existingWindow) {
        await existingWindow.setFocus()
        return
      }

      const webview = new WebviewWindow(windowLabel, {
        url: detailUrl,
        title: `Book Details: ${row.title}`,
        width: 1000,
        height: 700,
        resizable: true,
      })

      webview.once("tauri://error", (e) => {
        console.error("Tauri window error:", e)
      })

    } else {
      // Browser fallback
      window.open(detailUrl, "_blank")
    }

  } catch (err) {
    console.error("Failed opening record:", err)

    // Final fallback
    window.open(detailUrl, "_blank")
  }
}

// Filters
function applyFilters() {
  page.value = 1

  const current: Record<string, string> = {}
  if (filterTitle.value) current.title = filterTitle.value
  if (filterAuthor.value) current.author = filterAuthor.value
  if (filterGenre.value) current.genre = filterGenre.value
  if (filterLanguage.value) current.language = filterLanguage.value
  if (filterCategory.value) current.category = filterCategory.value

  activeFilters.value = current
  loadCatalogue()

  filterTitle.value = ""
  filterAuthor.value = ""
  filterGenre.value = ""
  filterLanguage.value = ""
  filterCategory.value = ""
}

function resetFilters() {
  filterTitle.value = ""
  filterAuthor.value = ""
  filterGenre.value = ""
  filterLanguage.value = ""
  filterCategory.value = ""

  activeFilters.value = {}
  page.value = 1
  loadCatalogue()
}

function handleSort(column: string) {
  order.value = (sortBy.value === column && order.value === 'asc') ? 'desc' : 'asc'
  sortBy.value = column
  page.value = 1
  loadCatalogue()
}

function handleJump() {
  const p = parseInt(jumpPage.value)

  if (isNaN(p)) {
    jumpMsg.value = "Number only"
    jumpError.value = true
    return
  }

  if (p >= 1 && p <= totalPages.value) {
    page.value = p
    loadCatalogue()
    jumpPage.value = ""
    jumpError.value = false
  } else {
    jumpError.value = true
    jumpMsg.value = `Range: 1-${totalPages.value}`
    setTimeout(() => jumpError.value = false, 2500)
  }
}

function goToPage(p: number) {
  if (p >= 1 && p <= totalPages.value) {
    page.value = p
    loadCatalogue()
  }
}

onMounted(() => {
  loadCatalogue()
  window.addEventListener("click", closeMenu)
})

onUnmounted(() => {
  window.removeEventListener("click", closeMenu)
})


</script>

<template>
  <div class="catalogue-page">
    <div class="catalogue-container">
      <div class="header-section">
        <h2 class="title">Institutional Catalogue</h2>
        <div class="filter-bar">
          <input v-model="filterTitle" @keyup.enter="applyFilters" placeholder="Title..." class="filter-input" />
          <input v-model="filterAuthor" @keyup.enter="applyFilters" placeholder="Author..." class="filter-input" />
          <input v-model="filterGenre" @keyup.enter="applyFilters" placeholder="Genre..." class="filter-input" />
          <input v-model="filterLanguage" @keyup.enter="applyFilters" placeholder="Language..." class="filter-input" />
          <input v-model="filterCategory" @keyup.enter="applyFilters" placeholder="Category..." class="filter-input" />
          <div class="btn-group">
            <button @click="applyFilters" class="btn-apply">Apply</button>
            <button @click="resetFilters" class="btn-reset">Reset</button>
          </div>
        </div>

        <div v-if="Object.keys(activeFilters).length > 0" class="active-chips">
          <span v-for="(val, key) in activeFilters" :key="key" class="chip">
            <span class="chip-label">{{ key }}:</span> {{ val }}
            <button @click="() => { delete activeFilters[key]; loadCatalogue() }" class="btn-remove-chip">✕</button>
          </span>
        </div>
      </div>

      <div class="stats-bar">
        <div class="stats-left">
          <span class="stat">Total Books: <strong>{{ globalTotal }}</strong></span>
          <span v-if="total < globalTotal && total > 0" class="stat filter-result">
            Found: <strong>{{ total }}</strong>
          </span>
        </div>
        <div class="stats-actions">
          <button @click="isCompact = !isCompact; limit = isCompact ? 25 : 10; page = 1; loadCatalogue()" class="btn-density">
            {{ isCompact ? 'Relaxed View' : 'Compact View' }}
          </button>
        </div>
      </div>

      <div class="table-wrapper">
        <table class="catalogue-table" :class="{ 'compact-mode': isCompact }">
          <thead>
            <tr>
              <th @click="handleSort('serial_no')" class="sortable">SL <span class="sort-icon">{{ sortBy === 'serial_no' ? (order === 'asc' ? '↑' : '↓') : '' }}</span></th>
              <th @click="handleSort('accession_no')" class="sortable">ACCESSION <span class="sort-icon">{{ sortBy === 'accession_no' ? (order === 'asc' ? '↑' : '↓') : '' }}</span></th>
              <th @click="handleSort('title')" class="sortable" style="width: 35%">TITLE <span class="sort-icon">{{ sortBy === 'title' ? (order === 'asc' ? '↑' : '↓') : '' }}</span></th>
              <th @click="handleSort('author')" class="sortable">AUTHOR <span class="sort-icon">{{ sortBy === 'author' ? (order === 'asc' ? '↑' : '↓') : '' }}</span></th>
              <th @click="handleSort('category')" class="sortable">CATEGORY <span class="sort-icon">{{ sortBy === 'category' ? (order === 'asc' ? '↑' : '↓') : '' }}</span></th>
              <th style="width: 120px">LANGUAGE</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="rows.length === 0">
              <td colspan="6" class="no-results-row">
                <div class="no-results-content">
                  <div class="no-results-icon">📚</div>
                  <h3>No Books Found</h3>
                  <button @click="resetFilters" class="btn-clear-all">Clear Filters</button>
                </div>
              </td>
            </tr>
            <template v-for="(row, index) in rows" :key="row.serial_no">
              <tr @click.left="basicViewId = basicViewId === row.serial_no ? null : row.serial_no"
                  @contextmenu.prevent="handleRightClick($event, row)"
                  :class="{ 'active-row': basicViewId === row.serial_no }"
                  class="clickable-row" :style="{ '--delay': (index * 0.03) + 's' }">
                <td>{{ row.serial_no }}</td>
                <td class="mono">{{ row.accession_no }}</td>
                <td class="title-cell">{{ row.title }}</td>
                <td>{{ row.author }}</td>
                <td class="cat-text">{{ row.category }}</td>
                <td><span class="lang-tag">{{ row.language }}</span></td>
              </tr>
              <tr v-if="basicViewId === row.serial_no" class="basic-drawer-row">
                <td colspan="6">
                  <div class="basic-drawer-content">
                    <div class="drawer-info-grid">
                      <div class="info-pill"><strong>Genre:</strong> {{ row.genre }}</div>
                      <div class="info-pill"><strong>Year:</strong> {{ row.year }}</div>
                      <div class="info-pill highlight"><strong>Shelf:</strong> {{ row.shelf }}</div>
                    </div>
                    <button class="btn-full-info" @click.stop="openFullDetails(row)">Full Record ↗</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="pagination-footer">
        <div class="results-info">
          Showing <strong>{{ total === 0 ? 0 : (page - 1) * limit + 1 }}</strong> to <strong>{{ Math.min(page * limit, total) }}</strong> of <strong>{{ total }}</strong>
        </div>
        <div class="pager-controls">
          <div class="jump-box" :class="{ 'has-error': jumpError }">
            <input v-model="jumpPage" type="number" @keyup.enter="handleJump" placeholder="Pg" />
            <button @click="handleJump" class="btn-jump-go">Go</button>
          </div>
          <div class="pager">
            <button @click="goToPage(page - 1)" :disabled="page === 1">&lt;</button>
            <button v-for="p in visiblePages" :key="p" @click="typeof p === 'number' ? goToPage(p) : null"
                    :class="{ active: p === page }" :disabled="p === '...'">{{ p }}</button>
            <button @click="goToPage(page + 1)" :disabled="page === totalPages">&gt;</button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="showMenu && activeMenuBook" class="context-menu" :style="{ top: menuPos.y + 'px', left: menuPos.x + 'px' }">
      <button @click="basicViewId = activeMenuBook.serial_no">Quick View</button>
      <button @click="openFullDetails(activeMenuBook)">Open New Window</button>
    </div>
  </div>
</template>
<style scoped>
/* --- THEME COLORS --- */
.catalogue-page {
  --content-bg: #f4eee4;
  --table-bg: #efeae0;
  --text-primary: #111827;
  --text-muted: #6b7280;
  --border-main: #dcd7cc;
  --card-bg: #ffffff;
  --error-red: #ef4444;
  --accent: #2dd4bf;
}

[data-theme="dark"] .catalogue-page {
  --content-bg: #0f172a;
  --table-bg: #1e293b;
  --text-primary: #f8fafc;
  --text-muted: #94a3b8;
  --border-main: #334155;
  --card-bg: #0f172a;
}

.cat-text {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* --- LAYOUT --- */
.catalogue-page {
  padding: 20px;
  background: var(--content-bg);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.catalogue-container {
  background: var(--table-bg);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* --- HEADER & STATS --- */
.header-section {
  padding: 24px 24px 12px 24px;
  border-bottom: 1px solid var(--border-main);
}

.title {
  margin-bottom: 15px;
  font-size: 24px;
  color: var(--text-primary);
}

.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.stats-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.stats-left {
  display: flex;
  gap: 20px;
}

.stat {
  font-size: 13px;
  color: var(--text-muted);
}

.stat strong {
  color: var(--text-primary);
}

.filter-result strong {
  color: var(--accent);
}


/* --- INPUTS & BUTTONS --- */
.filter-input {
  background: var(--card-bg);
  border: 1px solid var(--border-main);
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--text-primary);
  flex: 1;
  min-width: 120px;
  height: 38px;
}

.btn-apply {
  background: var(--accent);
  color: #000;
  border: none;
  padding: 0 20px;
  border-radius: 6px;
  font-weight: 700;
  height: 38px;
  cursor: pointer;
}

.btn-reset {
  background: var(--border-main);
  color: var(--text-primary);
  border: none;
  padding: 0 15px;
  border-radius: 6px;
  height: 38px;
  cursor: pointer;
}

.btn-jump-go {
  background: var(--accent);
  border: none;
  border-radius: 4px;
  font-size: 10px;
  font-weight: bold;
  padding: 0 8px;
  height: 24px;
  cursor: pointer;
  margin-left: 4px;
}

/* --- TABLE --- */
.table-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px;
}

.catalogue-table {
  width: 100%;
  border-collapse: collapse;
}

.catalogue-table th {
  position: sticky;
  top: 0;
  background: var(--table-bg);
  color: var(--text-muted);
  padding: 12px;
  text-align: left;
  font-size: 11px;
  text-transform: uppercase;
  border-bottom: 2px solid var(--border-main);
  z-index: 10;
}

.catalogue-table td {
  padding: 14px 12px;
  border-bottom: 1px solid var(--border-main);
  color: var(--text-primary);
}

.title-cell {
  font-weight: 600;
  color: #0d9488;
}

.lang-tag {
  font-size: 10px;
  border: 1px solid var(--accent);
  color: #0d9488;
  padding: 2px 8px;
  border-radius: 4px;
}

/* --- FOOTER & PAGER --- */
.pagination-footer {
  padding: 15px 24px;
  border-top: 1px solid var(--border-main);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0, 0, 0, 0.02);
}

.pager-controls {
  display: flex;
  align-items: center;
  gap: 24px;
}

.jump-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.jump-box input {
  width: 50px;
  height: 32px;
  background: var(--card-bg);
  border: 1px solid var(--border-main);
  border-radius: 6px;
  text-align: center;
  color: var(--text-primary);
}

.pager {
  display: flex;
  gap: 4px;
}

.pager button {
  min-width: 32px;
  height: 32px;
  border: 1px solid var(--border-main);
  background: var(--card-bg);
  color: var(--text-primary);
  border-radius: 6px;
  cursor: pointer;
}

.pager button.active {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
  font-weight: bold;
}

/* --- ERROR TOOLTIP --- */
.has-error input {
  border-color: var(--error-red) !important;
  animation: shake 0.4s;
}

.error-tooltip {
  position: absolute;
  bottom: 110%;
  left: 50%;
  transform: translateX(-50%);
  background: var(--error-red);
  color: white;
  font-size: 10px;
  padding: 4px 10px;
  border-radius: 4px;
  white-space: nowrap;
}

.active-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 0;
}

.chip {
  background: var(--accent);
  color: #000;
  padding: 4px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chip-label {
  text-transform: uppercase;
  opacity: 0.7;
  font-size: 10px;
}

.btn-remove-chip {
  background: rgba(0, 0, 0, 0.1);
  border: none;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 10px;
}

.btn-remove-chip:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* Density Toggle Button */
.btn-density {
  background: transparent;
  border: 1px solid var(--border-main);
  color: var(--text-muted);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-density:hover {
  background: var(--card-bg);
  color: var(--accent);
  border-color: var(--accent);
}

/* Compact Mode Overrides */
.catalogue-table.compact-mode td {
  padding: 6px 12px;
  /* Reduces row height significantly */
  font-size: 13px;
  /* Slightly smaller text for better scanning */
}

.catalogue-table.compact-mode .title-cell {
  font-weight: 500;
  /* Subtle weight reduction for compact text */
}

.catalogue-table.compact-mode .lang-tag {
  padding: 0px 6px;
  /* Slimmer tags */
}

@keyframes rowFadeSlide {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.clickable-row {
  opacity: 0; 
  animation: rowFadeSlide 0.4s ease-out forwards;
  animation-delay: var(--delay);
}
/* 3. Smooth Row Height Transition (For Density Toggle) */
.catalogue-table td {
  transition: padding 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sortable {
  cursor: pointer;
  user-select: none;
  /* This prevents the "blue highlight" on fast clicks */
  transition: background 0.2s;
}

.sortable:hover {
  background: rgba(0, 0, 0, 0.05);
  /* Subtle highlight on hover */
  color: var(--accent);
}

.sort-icon {
  display: inline-block;
  width: 12px;
  margin-left: 4px;
  color: var(--accent);
  font-weight: bold;
}

.stats-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-clear-sort {
  background: transparent;
  border: none;
  color: var(--error-red);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-clear-sort:hover {
  background: rgba(239, 68, 68, 0.1);
  /* Subtle red tint on hover */
}

.no-results-row td {
  padding: 80px 0 !important;
  text-align: center;
  border: none !important;
  background: transparent !important;
}

.no-results-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-muted);
}

.no-results-icon {
  font-size: 48px;
  opacity: 0.5;
}

.no-results-content h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}

.no-results-content p {
  margin: 0;
  font-size: 14px;
}

.btn-clear-all {
  margin-top: 10px;
  background: var(--accent);
  color: #000;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-clear-all:hover {
  transform: scale(1.05);
}

.context-menu {
  position: fixed;
  background: var(--table-bg);
  border: 1px solid var(--border-main);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  z-index: 9999;
  /* Ensure it stays above EVERYTHING */
  min-width: 180px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.context-menu button {
  padding: 10px 14px;
  text-align: left;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.context-menu button:hover {
  background: var(--accent);
  color: #000;
  font-weight: 600;
}

.basic-drawer-row td {
  background: rgba(0, 0, 0, 0.02);
  padding: 0 !important;
  /* Important for clean look */
  border-bottom: 2px solid var(--border-main);
}

.basic-drawer-content {
  padding: 15px 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 4px solid var(--accent);
  animation: slideIn 0.3s ease-out;
}

.drawer-info {
  display: flex;
  gap: 30px;
  color: var(--text-muted);
}

.btn-full-info {
  background: var(--card-bg);
  border: 1px solid var(--accent);
  color: #0d9488;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-full-info:hover {
  background: var(--accent);
  color: #000;
}

.clickable-row.active-row {
  background: var(--card-bg) !important;
  border-left: 4px solid var(--accent);
}
.drawer-info-grid {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.info-pill {
  background: var(--table-bg);
  padding: 4px 12px;
  border-radius: 100px;
  font-size: 12px;
  border: 1px solid var(--border-main);
  color: var(--text-primary);
}

.info-pill strong {
  color: var(--text-muted);
  text-transform: uppercase;
  font-size: 10px;
  margin-right: 4px;
}

.info-pill.highlight {
  background: var(--accent) !important; 
  color: #000000 !important; /* THIS IS THE FIX: Pure black text */
  font-weight: 900 !important; /* Make it extra thick */
  border: none;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shake {

  0%,
  100% {
    transform: translateX(0);
  }

  25% {
    transform: translateX(-4px);
  }

  75% {
    transform: translateX(4px);
  }
}
</style>