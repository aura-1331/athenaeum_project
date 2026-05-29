<template>
  <div class="classification-layout">
    <!-- LEFT PANEL: STRUCTURAL METRICS -->
    <aside class="metric-sidebar">
      <router-link to="/dashboard" class="escape-matrix-link">
        <span class="escape-icon">←</span> RETURN_TO_SYSTEM_CORE
      </router-link>

      <div class="panel-badge">CLASSIFICATION // TAXONOMY</div>
      <div class="hero-identity-block">
        <span class="meta-label">INDEX_TYPE</span>
        <h1 class="display-title">SUBJECTS</h1>
        <p class="display-summary">System taxonomic index mapping category frequencies and call signature footprints.</p>
      </div>

      <div class="system-status-matrix">
        <div class="status-node">
          <span>ACTIVE_SUBJECTS</span>
          <strong class="font-mono text-magenta">{{ aggregatedSubjectsList.length }}</strong>
        </div>
        <div class="status-node">
          <span>CATALOGUED_ITEMS</span>
          <strong class="font-mono">{{ totalAssetCount }}</strong>
        </div>
      </div>
    </aside>

    <!-- RIGHT PANEL: SUBJECT GRID LIST / DRILL DOWN FEED -->
    <main class="registry-feed-column">
      <div class="feed-scroll-wrapper">
        
        <!-- HEADER MODE A: TAXONOMY BROWSING -->
        <header v-if="!selectedSubject" class="feed-header">
          <div class="search-box-wrapper">
            <span class="search-icon">⌕</span>
            <input 
              type="text" 
              v-model="searchQuery" 
              placeholder="FILTER_BY_SUBJECT_OR_GENRE_NAME..." 
              class="search-input"
            />
          </div>
        </header>

        <!-- HEADER MODE B: ACTIVE FILTRATION RESET -->
        <header v-else class="feed-header-isolated">
          <div class="filter-breadcrumb-badge">
            FILTER_ACTIVE // TAXONOMY: <span class="highlight">{{ selectedSubject.toUpperCase() }}</span>
          </div>
          <button @click="clearSubjectSelection" class="clear-filter-btn">
            [X] RESET_REGISTRY_VIEW
          </button>
        </header>

        <div class="table-container">
          <!-- VIEW GRID A: PRIMARY SUBJECT AGGREGATIONS -->
          <table v-if="!selectedSubject" class="vault-table">
            <thead>
              <tr>
                <th class="text-left">SUBJECT_TAXONOMY_TAG</th>
                <th class="text-center">STRUCTURAL_CATEGORY</th>
                <th class="text-right">DENSITY_COUNT</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="3" class="text-center py-8 text-muted font-mono">PARSING_TAXONOMY_NODES...</td>
              </tr>
              <tr v-else-if="filteredSubjects.length === 0">
                <td colspan="3" class="text-center py-8 text-muted font-mono">NO_TAXONOMY_MATCHES_FOUND</td>
              </tr>
              <tr v-else v-for="subj in filteredSubjects" :key="subj.tag" class="data-row">
                <td class="text-left">
                  <button @click="selectSubject(subj.tag)" class="interactive-identity-trigger">
                    {{ subj.tag || 'UNASSIGNED' }}
                  </button>
                </td>
                <td class="text-center font-mono text-magenta size-small">{{ subj.category }}</td>
                <td class="text-right font-mono text-blue bold">{{ subj.count }}</td>
              </tr>
            </tbody>
          </table>

          <!-- VIEW GRID B: ISOLATED SUBJECT ASSETS LINKED TO DETAILS VIEW -->
          <table v-else class="vault-table">
            <thead>
              <tr>
                <th class="text-left">ACCESSION_ID</th>
                <th class="text-left">BOOK_TITLE_REGISTRY</th>
                <th class="text-left">CREATOR_ORIGIN</th>
                <th class="text-right">CATALOGUE_TRACK</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="book in targetedSubjectBooks" :key="extractId(book)" class="data-row">
                <td class="font-mono size-small text-muted text-left">#{{ book.accession_no || extractId(book) }}</td>
                <td class="text-left">
                  <router-link :to="'/details/' + extractId(book)" class="interactive-book-trigger">
                    {{ book.title || 'UNTITLED_ASSET_RECORD' }}
                  </router-link>
                </td>
                <td class="text-left size-small font-bold text-white">{{ book.author || 'UNKNOWN AUTHOR' }}</td>
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

interface SubjectAggregate {
  tag: string
  count: number
  category: string
}

const loading = ref(true)
const searchQuery = ref('')
const selectedSubject = ref<string | null>(null)

const masterCatalogueData = ref<any[]>([])
const aggregatedSubjectsList = ref<SubjectAggregate[]>([])
const totalAssetCount = ref(0)

function extractId(book: any): string | number {
  if (!book) return 'undefined'
  const targetId = book.serial_no ?? book.id ?? book.item_id ?? book.accession
  return targetId !== undefined ? targetId : 'undefined'
}

async function compileSubjectsRegistry() {
  loading.value = true
  try {
    const response = await axios.get('/catalogue?limit=1000')
    const items = response.data?.data || []
    masterCatalogueData.value = items
    totalAssetCount.value = items.length

    const mapping: Record<string, { count: number; category: string }> = {}

    items.forEach((item: any) => {
      const rawGenre = item.genre ? item.genre.trim() : 'UNCLASSIFIED'
      const category = item.category || 'General'
      
      // Split genres by slash, trim whitespace from each split token, and run aggregations on each individual part
      const subGenres = rawGenre.split('/').map((g: string) => g.trim()).filter((g: string) => g.length > 0)

      subGenres.forEach((genreTag: string) => {
        // Enforce UPPERCASE formatting for grouping stability across listings
        const standardizedTag = genreTag.toUpperCase()
        
        if (!mapping[standardizedTag]) {
          mapping[standardizedTag] = { count: 0, category: category }
        }
        mapping[standardizedTag].count++
      })
    })

    aggregatedSubjectsList.value = Object.keys(mapping).map(tag => ({
      tag,
      count: mapping[tag].count,
      category: mapping[tag].category
    })).sort((a, b) => a.tag.localeCompare(b.tag))

  } catch (err) {
    console.error("Failed to parse taxonomy structural footprints:", err)
  } finally {
    loading.value = false
  }
}

const filteredSubjects = computed(() => {
  if (!searchQuery.value) return aggregatedSubjectsList.value
  const query = searchQuery.value.toLowerCase().trim()
  return aggregatedSubjectsList.value.filter(s => s.tag.toLowerCase().includes(query))
})

const targetedSubjectBooks = computed(() => {
  if (!selectedSubject.value) return []
  const target = selectedSubject.value.toUpperCase()
  
  return masterCatalogueData.value.filter((item: any) => {
    if (!item.genre) return target === 'UNCLASSIFIED'
    
    // Split item's subgenres array to match cross-referenced keys accurately
    const currentSubGenres = item.genre.split('/').map((g: string) => g.trim().toUpperCase())
    return currentSubGenres.includes(target)
  })
})

function selectSubject(tag: string) {
  selectedSubject.value = tag
}

function clearSubjectSelection() {
  selectedSubject.value = null
}

onMounted(() => {
  setTimeout(() => {
    compileSubjectsRegistry()
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
  text-transform: uppercase;
}
.interactive-identity-trigger:hover { color: #ec4899; text-decoration: underline; }

.interactive-book-trigger {
  color: #ffffff; text-decoration: none; font-weight: bold; transition: color 0.2s ease;
}
.interactive-book-trigger:hover { color: #3b82f6; text-decoration: underline; }

.text-left { text-align: left; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-blue { color: #3b82f6; }
.text-magenta { color: #ec4899; }
.text-muted { color: #525966; }
.bold { font-weight: bold; }
.size-small { font-size: 11px; }
.py-8 { padding-top: 32px; padding-bottom: 32px; }
</style>