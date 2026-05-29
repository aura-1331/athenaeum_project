<template>
  <div class="classification-layout">
    <aside class="metric-sidebar">
      <router-link to="/dashboard" class="escape-matrix-link">
        <span class="escape-icon">←</span> RETURN_TO_SYSTEM_CORE
      </router-link>

      <div class="panel-badge">CLASSIFICATION // REGISTRY</div>
      <div class="hero-identity-block">
        <span class="meta-label">INDEX_TYPE</span>
        <h1 class="display-title">AUTHORS</h1>
        <p class="display-summary">Master log of unique creators and contribution metrics across the active matrix database.</p>
      </div>

      <div class="system-status-matrix">
        <div class="status-node">
          <span>UNIQUE_CREATORS</span>
          <strong class="font-mono text-emerald">{{ aggregatedAuthorsList.length }}</strong>
        </div>
        <div class="status-node">
          <span>TOTAL_DATABASE_ITEMS</span>
          <strong class="font-mono">{{ totalAssetCount }}</strong>
        </div>
      </div>
    </aside>

    <main class="registry-feed-column">
      <div class="feed-scroll-wrapper">
        
        <header v-if="!selectedAuthor" class="feed-header">
          <div class="search-box-wrapper">
            <span class="search-icon">⌕</span>
            <input 
              type="text" 
              v-model="searchQuery" 
              placeholder="FILTER_BY_CREATOR_NAME..." 
              class="search-input"
            />
          </div>
        </header>

        <header v-else class="feed-header-isolated">
          <div class="filter-breadcrumb-badge">
            FILTER_ACTIVE // CREATOR: <span class="highlight">{{ selectedAuthor.toUpperCase() }}</span>
          </div>
          <button @click="clearAuthorSelection" class="clear-filter-btn">
            [X] RESET_REGISTRY_VIEW
          </button>
        </header>

        <div class="table-container">
          <table v-if="!selectedAuthor" class="vault-table">
            <thead>
              <tr>
                <th class="text-left">CREATOR_IDENTITY</th>
                <th class="text-center">PRIMARY_LANGUAGE</th>
                <th class="text-right">REGISTERED_WORKS</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="3" class="text-center py-8 text-muted font-mono">RETRIEVING_CREATOR_MATRICES...</td>
              </tr>
              <tr v-else-if="filteredAuthors.length === 0">
                <td colspan="3" class="text-center py-8 text-muted font-mono">NO_MATCHING_RECORDS_FOUND</td>
              </tr>
              <tr v-else v-for="author in filteredAuthors" :key="author.name" class="data-row">
                <td class="text-left">
                  <button @click="selectAuthor(author.name)" class="interactive-identity-trigger">
                    {{ author.name || 'UNKNOWN_CREATOR' }}
                  </button>
                </td>
                <td class="text-center font-mono text-blue size-small">{{ author.primaryLanguage }}</td>
                <td class="text-right font-mono text-amber bold">{{ author.count }}</td>
              </tr>
            </tbody>
          </table>

          <table v-else class="vault-table">
            <thead>
              <tr>
                <th class="text-left">ACCESSION_ID</th>
                <th class="text-left">BOOK_TITLE_REGISTRY</th>
                <th class="text-center">CLASSIFICATION</th>
                <th class="text-right">CATALOGUE_TRACK</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="book in targetedAuthorBooks" :key="extractId(book)" class="data-row">
                <td class="font-mono size-small text-muted text-left">#{{ book.accession_no || extractId(book) }}</td>
                <td class="text-left">
                  <router-link :to="'/details/' + extractId(book)" class="interactive-book-trigger">
                    {{ book.title || 'UNTITLED_ASSET_RECORD' }}
                  </router-link>
                </td>
                <td class="text-center font-mono text-magenta size-small">{{ book.genre || 'GENERAL' }}</td>
                <td class="text-right font-mono size-small text-blue">{{ book.call_number || book.call_no || 'UNASSIGNED' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

interface AuthorAggregate {
  name: string
  count: number
  primaryLanguage: string
}

const loading = ref(true)
const searchQuery = ref('')
const selectedAuthor = ref<string | null>(null)

const masterCatalogueData = ref<any[]>([])
const aggregatedAuthorsList = ref<AuthorAggregate[]>([])
const totalAssetCount = ref(0)

function extractId(book: any): string | number {
  if (!book) return 'undefined'
  const targetId = book.serial_no ?? book.id ?? book.item_id ?? book.accession
  return targetId !== undefined ? targetId : 'undefined'
}

async function compileAuthorsRegistry() {
  loading.value = true
  try {
    const response = await axios.get('/catalogue?limit=1000')
    const items = response.data?.data || []
    masterCatalogueData.value = items
    totalAssetCount.value = items.length

    const mapping: Record<string, { count: number; languages: Record<string, number> }> = {}

    items.forEach((item: any) => {
      const authorName = item.author ? item.author.trim() : 'UNKNOWN_CREATOR'
      const lang = item.language || 'Unknown'
      
      if (!mapping[authorName]) {
        mapping[authorName] = { count: 0, languages: {} }
      }
      mapping[authorName].count++
      mapping[authorName].languages[lang] = (mapping[authorName].languages[lang] || 0) + 1
    })

    aggregatedAuthorsList.value = Object.keys(mapping).map(name => {
      const langMap = mapping[name].languages
      const primaryLang = Object.keys(langMap).reduce((a: string, b: string) => langMap[a] > langMap[b] ? a : b)
      return {
        name,
        count: mapping[name].count,
        primaryLanguage: primaryLang
      }
    }).sort((a, b) => b.count - a.count)

  } catch (err) {
    console.error("Failed to compile author metrics matrix:", err)
  } finally {
    loading.value = false
  }
}

const filteredAuthors = computed(() => {
  if (!searchQuery.value) return aggregatedAuthorsList.value
  const query = searchQuery.value.toLowerCase().trim()
  return aggregatedAuthorsList.value.filter(a => a.name.toLowerCase().includes(query))
})

const targetedAuthorBooks = computed(() => {
  if (!selectedAuthor.value) return []
  return masterCatalogueData.value.filter(
    item => (item.author ? item.author.trim() : 'UNKNOWN_CREATOR') === selectedAuthor.value
  )
})

function selectAuthor(name: string) {
  selectedAuthor.value = name
}

function clearAuthorSelection() {
  selectedAuthor.value = null
}

onMounted(() => {
  setTimeout(() => {
    compileAuthorsRegistry()
  }, 150)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

.classification-layout {
  background-color: #111216;
  color: #e2e4e9;
  position: fixed !important;
  top: 0; left: 0; width: 100vw; height: 100vh;
  z-index: 9999 !important;
  display: flex; overflow: hidden;
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
}

.metric-sidebar {
  width: 420px; background-color: #0a0b0d !important;
  border-right: 1px solid #1c1f26 !important;
  padding: 48px; display: flex; flex-direction: column; box-sizing: border-box; flex-shrink: 0;
}

.escape-matrix-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #f59e0b;
  text-decoration: none;
  margin-bottom: 32px;
  letter-spacing: 1px;
  font-weight: bold;
  border: 1px solid rgba(245, 158, 11, 0.2);
  padding: 8px 12px;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.03);
  transition: all 0.2s ease;
}
.escape-matrix-link:hover {
  color: #ffffff;
  background: #f59e0b;
  border-color: #f59e0b;
}
.escape-icon { font-size: 14px; }

.panel-badge { font-size: 10px; font-weight: bold; color: #525966; letter-spacing: 2px; margin-bottom: 40px; }
.hero-identity-block { margin-bottom: auto; }
.meta-label { font-size: 9px; color: #626a7a; letter-spacing: 1px; display: block; margin-bottom: 8px; }
.display-title { font-size: 32px; font-weight: 800; color: #ffffff; margin: 0 0 16px 0; letter-spacing: 1px; }
.display-summary { font-size: 12px; line-height: 1.6; color: #626a7a; margin: 0; }

.system-status-matrix {
  background-color: #111216; border: 1px solid #1c1f26; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.status-node { display: flex; justify-content: space-between; align-items: center; font-size: 11px; }
.status-node span { color: #525966; font-weight: bold; }

.registry-feed-column { flex-grow: 1; height: 100%; overflow-y: auto; background-color: #111216; }
.feed-scroll-wrapper { padding: 48px 64px; max-width: 1000px; box-sizing: border-box; }

.feed-header { margin-bottom: 32px; }
.feed-header-isolated {
  display: flex; justify-content: space-between; align-items: center;
  background-color: #16181f; border: 1px solid #22252e; border-radius: 6px;
  padding: 14px 20px; margin-bottom: 32px;
}
.filter-breadcrumb-badge { font-size: 11px; font-weight: bold; color: #525966; letter-spacing: 1px; }
.filter-breadcrumb-badge .highlight { color: #f59e0b; font-weight: 800; }

.clear-filter-btn {
  background: transparent; border: none; color: #f87171; font-family: inherit;
  font-size: 11px; font-weight: bold; cursor: pointer; letter-spacing: 1px;
}
.clear-filter-btn:hover { color: #ef4444; text-decoration: underline; }

.search-box-wrapper {
  background-color: #16181f; border: 1px solid #22252e; border-radius: 6px; padding: 12px 16px; display: flex; align-items: center; gap: 12px;
}
.search-icon { color: #525966; font-size: 16px; }
.search-input { background: transparent; border: none; color: #ffffff; font-family: inherit; font-size: 13px; width: 100%; }
.search-input:focus { outline: none; }

.table-container { background-color: #16181f; border: 1px solid #22252e; border-radius: 8px; overflow: hidden; }
.vault-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
.vault-table th { background-color: #12141a; color: #525966; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 16px 24px; border-bottom: 1px solid #22252e; text-transform: uppercase; }
.vault-table td { padding: 16px 24px; border-bottom: 1px solid #1c1f26; color: #a3a8b4; vertical-align: middle; }
.data-row:hover { background-color: rgba(255,255,255,0.01); }

.interactive-identity-trigger {
  background: transparent; border: none; color: #ffffff; font-family: inherit;
  font-size: 13px; font-weight: bold; cursor: pointer; padding: 0; text-align: left;
}
.interactive-identity-trigger:hover { color: #10b981; text-decoration: underline; }

.interactive-book-trigger {
  color: #ffffff; text-decoration: none; font-weight: bold; transition: color 0.2s ease;
}
.interactive-book-trigger:hover { color: #3b82f6; text-decoration: underline; }

.text-left { text-align: left; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-emerald { color: #10b981; }
.text-blue { color: #3b82f6; }
.text-magenta { color: #ec4899; }
.text-amber { color: #f59e0b; }
.text-muted { color: #525966; }
.bold { font-weight: bold; }
.size-small { font-size: 11px; }
.py-8 { padding-top: 32px; padding-bottom: 32px; }
</style>