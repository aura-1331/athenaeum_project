<template>
  <div v-if="isOpen" class="vault-modal-backdrop" @click.self="close">
    <div class="vault-modal-card">
      <div class="modal-top">
        <div>
          <span class="system-tag">ENGINE // BATCH_CATALOGUE_REGISTER</span>
          <h2 class="title">Print Catalogue Ledger</h2>
        </div>
        <button class="close-btn" @click="close">&times;</button>
      </div>

      <div class="filter-matrix">
        <div class="form-row full">
          <label>TITLE SUBSTRING / KEYWORD</label>
          <input 
            v-model="keyword" 
            type="text" 
            placeholder="Type any word appearing in title..." 
          />
        </div>

        <div class="form-row">
          <label>AUTHOR</label>
          <select v-model="selectedAuthor">
            <option value="">ALL AUTHORS</option>
            <option v-for="author in authorsList" :key="author" :value="author">
              {{ author }}
            </option>
          </select>
        </div>

        <div class="form-row">
          <label>CATEGORY</label>
          <select v-model="selectedCategory">
            <option value="">ALL CATEGORIES</option>
            <option v-for="cat in categoriesList" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
        </div>

        <div class="form-row">
          <label>GENRE</label>
          <select v-model="selectedGenre">
            <option value="">ALL GENRES</option>
            <option v-for="genre in genresList" :key="genre" :value="genre">
              {{ genre }}
            </option>
          </select>
        </div>

        <div class="form-row">
          <label>LANGUAGE</label>
          <select v-model="selectedLanguage">
            <option value="">ALL LANGUAGES</option>
            <option v-for="lang in languagesList" :key="lang" :value="lang">
              {{ lang }}
            </option>
          </select>
        </div>
      </div>

      <div class="telemetry-bar">
        <span>MATCHING ASSETS: <strong>{{ matchedBooks.length }}</strong> VOLUMES</span>
        <button class="reset-link" @click="resetFilters">RESET_FILTERS</button>
      </div>

      <div class="modal-actions">
        <button class="action-btn cancel" @click="close">ABORT</button>
        <button 
          class="action-btn print" 
          :disabled="matchedBooks.length === 0 || loading"
          @click="initiatePrint"
        >
          {{ loading ? 'SYNCING_CATALOGUE...' : 'EXECUTE_PRINT' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Mounting target for print generation -->
  <div v-if="isPrinting" class="print-mount-point">
    <PrintCatalogueRegister
      :books="matchedBooks"
      :filterSummary="activeFilterText"
      @printed="onPrintedDone"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import PrintCatalogueRegister from '@/components/print/PrintCatalogueRegister.vue'

const isOpen = ref(false)
const isPrinting = ref(false)
const loading = ref(false)
const rawBooks = ref<any[]>([])

const keyword = ref('')
const selectedAuthor = ref('')
const selectedCategory = ref('')
const selectedGenre = ref('')
const selectedLanguage = ref('')

async function fetchAllHoldings() {
  loading.value = true
  try {
    const res = await axios.get('/catalogue/', { params: { limit: 1000 } })
    rawBooks.value = res.data?.data || []
  } catch (err) {
    console.error('Failed to sync catalogue for batch print:', err)
  } finally {
    loading.value = false
  }
}

//onMounted(() => {
// fetchAllHoldings()
//})

const authorsList = computed(() => 
  Array.from(new Set(rawBooks.value.map(b => b.author).filter(Boolean))).sort()
)

const categoriesList = computed(() => 
  Array.from(new Set(rawBooks.value.map(b => b.category).filter(Boolean))).sort()
)

const genresList = computed(() => {
  const set = new Set<string>()
  rawBooks.value.forEach(b => {
    if (b.genre) {
      b.genre.split(/[/,]+/).forEach((g: string) => set.add(g.trim().toUpperCase()))
    }
  })
  return Array.from(set).sort()
})

const languagesList = computed(() => 
  Array.from(new Set(rawBooks.value.map(b => b.language).filter(Boolean))).sort()
)

const matchedBooks = computed(() => {
  return rawBooks.value.filter(book => {
    if (keyword.value && !book.title?.toLowerCase().includes(keyword.value.toLowerCase())) {
      return false
    }
    if (selectedAuthor.value && book.author !== selectedAuthor.value) {
      return false
    }
    if (selectedCategory.value && book.category !== selectedCategory.value) {
      return false
    }
    if (selectedGenre.value && !book.genre?.toUpperCase().includes(selectedGenre.value)) {
      return false
    }
    if (selectedLanguage.value && book.language !== selectedLanguage.value) {
      return false
    }
    return true
  })
})

const activeFilterText = computed(() => {
  const parts: string[] = []
  if (keyword.value) parts.push(`Keyword: "${keyword.value}"`)
  if (selectedAuthor.value) parts.push(`Author: ${selectedAuthor.value}`)
  if (selectedCategory.value) parts.push(`Category: ${selectedCategory.value}`)
  if (selectedGenre.value) parts.push(`Genre: ${selectedGenre.value}`)
  if (selectedLanguage.value) parts.push(`Language: ${selectedLanguage.value}`)
  return parts.length > 0 ? parts.join(' | ') : 'FULL_COLLECTION'
})

function resetFilters() {
  keyword.value = ''
  selectedAuthor.value = ''
  selectedCategory.value = ''
  selectedGenre.value = ''
  selectedLanguage.value = ''
}

function openModal(prefills?: { author?: string; category?: string; genre?: string; language?: string }) {
  if (prefills) {
    if (prefills.author) selectedAuthor.value = prefills.author
    if (prefills.category) selectedCategory.value = prefills.category
    if (prefills.genre) selectedGenre.value = prefills.genre
    if (prefills.language) selectedLanguage.value = prefills.language
  }
  isOpen.value = true
  fetchAllHoldings()
}

function close() {
  isOpen.value = false
}

function initiatePrint() {
  isPrinting.value = true
}

function onPrintedDone() {
  isPrinting.value = false
  isOpen.value = false
}

defineExpose({ openModal })
</script>

<style scoped>
.vault-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 11, 15, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  font-family: 'JetBrains Mono', monospace;
}

.vault-modal-card {
  width: 90%;
  max-width: 640px;
  background: #16181f;
  border: 1px solid #22252e;
  border-radius: 10px;
  padding: 32px;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
  color: #e2e4e9;
}

.modal-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.system-tag {
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
  letter-spacing: 1.5px;
}

.title {
  font-family: 'Cinzel', serif;
  font-size: 22px;
  font-weight: 800;
  color: #ffffff;
  margin: 6px 0 0 0;
}

.close-btn {
  background: none;
  border: none;
  color: #626a7a;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #ffffff;
}

.filter-matrix {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.full {
  grid-column: span 2;
}

.form-row label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.form-row input,
.form-row select {
  width: 100%;
  background: #111216;
  border: 1px solid #22252e;
  color: #e2e4e9;
  padding: 10px 12px;
  border-radius: 4px;
  font-family: inherit;
  font-size: 12px;
  box-sizing: border-box;
}

.form-row input:focus,
.form-row select:focus {
  outline: none;
  border-color: #e2e4e9;
}

.telemetry-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding-top: 14px;
  border-top: 1px solid #22252e;
  font-size: 11px;
  color: #a3a8b4;
}

.reset-link {
  background: none;
  border: none;
  color: #f59e0b;
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}

.reset-link:hover {
  text-decoration: underline;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.action-btn {
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  padding: 10px 22px;
  border-radius: 4px;
  cursor: pointer;
}

.action-btn.cancel {
  background: none;
  border: 1px solid #2e333d;
  color: #e2e4e9;
}

.action-btn.print {
  background: #e2e4e9;
  border: none;
  color: #111216;
}

.action-btn.print:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

@media print {
  .vault-modal-backdrop {
    display: none !important;
  }
}
</style>