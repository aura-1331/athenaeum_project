<template>
  <div class="classification-layout">
    <!-- LEFT PANEL: STRUCTURAL METRICS -->
    <aside class="metric-sidebar">
      <router-link to="/dashboard" class="escape-matrix-link">
        <span class="escape-icon">←</span>
        RETURN_TO_SYSTEM_CORE
      </router-link>

      <div class="panel-badge">CLASSIFICATION // TAXONOMY</div>

      <div class="hero-identity-block">
        <span class="meta-label">INDEX_TYPE</span>
        <h1 class="display-title">SUBJECTS</h1>
        <p class="display-summary">
          System taxonomic index mapping category frequencies and call
          signature footprints.
        </p>
      </div>

      <div class="system-status-matrix">
        <div class="status-node">
          <span>ACTIVE_SUBJECTS</span>
          <strong class="font-mono text-magenta">
            {{ aggregatedSubjectsList.length }}
          </strong>
        </div>

        <div class="status-node">
          <span>CATALOGUED_ITEMS</span>
          <strong class="font-mono">{{ totalAssetCount }}</strong>
        </div>
      </div>
    </aside>

    <!-- RIGHT PANEL -->
    <main class="registry-feed-column">
      <div class="feed-scroll-wrapper">
        <!-- SUBJECT SEARCH -->
        <header v-if="!selectedSubject" class="feed-header">
          <div class="search-box-wrapper">
            <span class="search-icon">⌕</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="FILTER_BY_SUBJECT_OR_GENRE_NAME..."
              class="search-input"
            />
          </div>
        </header>

        <!-- SELECTED SUBJECT HEADER -->
        <header v-else class="feed-header-isolated">
          <div class="filter-breadcrumb-badge">
            FILTER_ACTIVE // TAXONOMY:
            <span class="highlight">{{ selectedSubject }}</span>
          </div>

          <button
            type="button"
            class="clear-filter-btn"
            @click="clearSubjectSelection"
          >
            [X] RESET_REGISTRY_VIEW
          </button>
        </header>

        <div class="table-container">
          <!-- PRIMARY SUBJECT TABLE -->
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
                <td colspan="3" class="text-center py-8 text-muted font-mono">
                  PARSING_TAXONOMY_NODES...
                </td>
              </tr>

              <tr v-else-if="errorMessage">
                <td colspan="3" class="text-center py-8 error-message">
                  {{ errorMessage }}
                </td>
              </tr>

              <tr v-else-if="filteredSubjects.length === 0">
                <td colspan="3" class="text-center py-8 text-muted font-mono">
                  NO_TAXONOMY_MATCHES_FOUND
                </td>
              </tr>

              <tr
                v-else
                v-for="subj in filteredSubjects"
                :key="subj.tag"
                class="data-row"
              >
                <td class="text-left">
                  <button
                    type="button"
                    class="interactive-identity-trigger"
                    @click="selectSubject(subj.tag)"
                  >
                    {{ subj.tag || 'UNASSIGNED' }}
                  </button>
                </td>

                <td class="text-center font-mono text-magenta size-small">
                  {{ subj.category }}
                </td>

                <td class="text-right font-mono text-blue bold">
                  {{ subj.count }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- BOOKS UNDER SELECTED SUBJECT -->
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
              <tr v-if="loading">
                <td colspan="4" class="text-center py-8 text-muted font-mono">
                  LOADING_SUBJECT_ASSETS...
                </td>
              </tr>

              <tr v-else-if="errorMessage">
                <td colspan="4" class="text-center py-8 error-message">
                  {{ errorMessage }}
                </td>
              </tr>

              <tr v-else-if="targetedSubjectBooks.length === 0">
                <td colspan="4" class="text-center py-8 text-muted font-mono">
                  NO_ASSETS_FOUND_FOR_THIS_SUBJECT
                </td>
              </tr>

              <tr
                v-else
                v-for="book in targetedSubjectBooks"
                :key="extractId(book)"
                class="data-row"
              >
                <td class="font-mono size-small text-muted text-left">
                  #{{ book.accession_no ?? extractId(book) }}
                </td>

                <td class="text-left">
                  <router-link
                    :to="`/details/${extractId(book)}`"
                    class="interactive-book-trigger"
                  >
                    {{ book.title || 'UNTITLED_ASSET_RECORD' }}
                  </router-link>
                </td>

                <td class="text-left size-small font-bold text-primary">
                  {{ book.author || 'UNKNOWN AUTHOR' }}
                </td>

                <td class="text-right font-mono size-small text-blue">
                  {{ book.call_number || book.call_no || 'UNASSIGNED' }}
                </td>
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

interface CatalogueItem {
  serial_no?: string | number
  id?: string | number
  item_id?: string | number
  accession?: string | number
  accession_no?: string | number
  title?: string
  author?: string
  genre?: string
  category?: string
  call_number?: string
  call_no?: string
  [key: string]: unknown
}

interface SubjectAggregate {
  tag: string
  count: number
  category: string
}

interface CatalogueResponse {
  data?: CatalogueItem[]
  total?: number
}

const loading = ref(true)
const searchQuery = ref('')
const selectedSubject = ref<string | null>(null)
const errorMessage = ref('')

const masterCatalogueData = ref<CatalogueItem[]>([])
const aggregatedSubjectsList = ref<SubjectAggregate[]>([])
const totalAssetCount = ref(0)

/**
 * Return the identifier used by the catalogue and details route.
 * Confirm which identifier your backend's details endpoint expects.
 */
function extractId(book: CatalogueItem): string | number {
  return (
    book.serial_no ??
    book.id ??
    book.item_id ??
    book.accession_no ??
    book.accession ??
    'undefined'
  )
}

/**
 * Split multi-subject genre strings and normalize their casing.
 * Example: "Science / History" -> ["SCIENCE", "HISTORY"]
 */
function normalizeGenre(value: unknown): string[] {
  if (typeof value !== 'string' || !value.trim()) {
    return ['UNCLASSIFIED']
  }

  const genres = value
    .split('/')
    .map(part => part.trim().replace(/\s+/g, ' ').toUpperCase())
    .filter(Boolean)

  return genres.length ? [...new Set(genres)] : ['UNCLASSIFIED']
}

/**
 * Build subject counts from the catalogue records.
 * Each record counts once per distinct subject it contains.
 */
function buildSubjectsRegistry(items: CatalogueItem[]): void {
  const mapping = new Map<
    string,
    {
      count: number
      categories: Map<string, number>
    }
  >()

  for (const item of items) {
    const genres = normalizeGenre(item.genre)

    const category =
      typeof item.category === 'string' && item.category.trim()
        ? item.category.trim()
        : 'General'

    for (const tag of genres) {
      let entry = mapping.get(tag)

      if (!entry) {
        entry = {
          count: 0,
          categories: new Map<string, number>()
        }

        mapping.set(tag, entry)
      }

      entry.count += 1

      entry.categories.set(
        category,
        (entry.categories.get(category) ?? 0) + 1
      )
    }
  }

  aggregatedSubjectsList.value = Array.from(mapping.entries())
    .map(([tag, entry]) => {
      let category = 'General'
      let highestCount = 0

      for (const [name, count] of entry.categories) {
        if (count > highestCount) {
          category = name
          highestCount = count
        }
      }

      return {
        tag,
        count: entry.count,
        category
      }
    })
    .sort((a, b) => a.tag.localeCompare(b.tag))
}

/**
 * Fetch the catalogue and then build the subject registry.
 *
 * Assumes the API accepts page + limit and returns:
 * { data: CatalogueItem[], total: number }
 *
 * If your backend uses skip + limit or returns a plain array,
 * adjust the request and response parsing accordingly.
 */
async function compileSubjectsRegistry(): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  try {
    const allItems: CatalogueItem[] = []
    const limit = 100
    let page = 1
    let expectedTotal: number | null = null

    const seenPageSignatures = new Set<string>()

    while (true) {
      const response = await axios.get<CatalogueResponse>(
        '/catalogue/',
        {
          params: {
            page,
            limit
          }
        }
      )

      const payload = response.data

      const batch = Array.isArray(payload?.data)
        ? payload.data
        : []

      if (
        typeof payload?.total === 'number' &&
        Number.isFinite(payload.total)
      ) {
        expectedTotal = payload.total
      }

      if (batch.length === 0) {
        break
      }

      // Prevent an infinite loop if the server repeats a page.
      const signature = batch
        .map(item => String(extractId(item)))
        .join('|')

      if (seenPageSignatures.has(signature)) {
        throw new Error(
          'Catalogue pagination returned a repeated page. ' +
          'Check the backend pagination parameters.'
        )
      }

      seenPageSignatures.add(signature)
      allItems.push(...batch)

      if (
        expectedTotal !== null &&
        allItems.length >= expectedTotal
      ) {
        break
      }

      if (batch.length < limit) {
        break
      }

      page += 1
    }

    masterCatalogueData.value = allItems

    totalAssetCount.value =
      expectedTotal ?? allItems.length

    buildSubjectsRegistry(allItems)
  } catch (error: unknown) {
    console.error('Failed to load subjects registry:', error)

    if (axios.isAxiosError(error)) {
      const detail = error.response?.data?.detail

      errorMessage.value =
        typeof detail === 'string'
          ? detail
          : error.message || 'Unable to load the catalogue.'
    } else if (error instanceof Error) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = 'Unable to load the catalogue.'
    }

    masterCatalogueData.value = []
    aggregatedSubjectsList.value = []
    totalAssetCount.value = 0
  } finally {
    loading.value = false
  }
}

/**
 * Filter the subject table using the search field.
 */
const filteredSubjects = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase()

  if (!query) {
    return aggregatedSubjectsList.value
  }

  return aggregatedSubjectsList.value.filter(subject =>
    subject.tag.toLocaleLowerCase().includes(query) ||
    subject.category.toLocaleLowerCase().includes(query)
  )
})

/**
 * Return all catalogue records belonging to the selected subject.
 */
const targetedSubjectBooks = computed(() => {
  const selected = selectedSubject.value

  if (!selected) {
    return []
  }

  return masterCatalogueData.value.filter(item =>
    normalizeGenre(item.genre).includes(selected)
  )
})

function selectSubject(tag: string): void {
  selectedSubject.value = tag
}

function clearSubjectSelection(): void {
  selectedSubject.value = null
}

onMounted(() => {
  void compileSubjectsRegistry()
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

.classification-layout {
  background-color: var(--app-bg);
  color: var(--text-primary);
  position: fixed !important;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999 !important;
  display: flex;
  overflow: hidden;
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
}

.metric-sidebar {
  width: 420px;
  background-color: var(--surface-2) !important;
  border-right: 1px solid var(--border-main) !important;
  padding: 48px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  flex-shrink: 0;
}

.escape-matrix-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--accent);
  text-decoration: none;
  margin-bottom: 32px;
  letter-spacing: 1px;
  font-weight: bold;
  border: 1px solid var(--catalog-card-border);
  padding: 8px 12px;
  border-radius: 4px;
  background: var(--catalog-accent-soft);
  transition: all 0.2s ease;
}

.escape-matrix-link:hover {
  color: var(--button-text);
  background: var(--accent);
  border-color: var(--accent);
}

.escape-icon {
  font-size: 14px;
}

.panel-badge {
  font-size: 10px;
  font-weight: bold;
  color: var(--text-muted);
  letter-spacing: 2px;
  margin-bottom: 40px;
}

.hero-identity-block {
  margin-bottom: auto;
}

.meta-label {
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 1px;
  display: block;
  margin-bottom: 8px;
}

.display-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 16px;
  letter-spacing: 1px;
}

.display-summary {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-muted);
  margin: 0;
}

.system-status-matrix {
  background-color: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.status-node span {
  color: var(--text-muted);
  font-weight: bold;
}

.registry-feed-column {
  flex-grow: 1;
  min-width: 0;
  height: 100%;
  overflow-y: auto;
  background-color: var(--app-bg);
}

.feed-scroll-wrapper {
  padding: 48px 64px;
  max-width: 1000px;
  box-sizing: border-box;
}

.feed-header {
  margin-bottom: 32px;
}

.feed-header-isolated {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  background-color: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 6px;
  padding: 14px 20px;
  margin-bottom: 32px;
  box-shadow: var(--shadow);
}

.filter-breadcrumb-badge {
  font-size: 11px;
  font-weight: bold;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.filter-breadcrumb-badge .highlight {
  color: var(--accent);
  font-weight: 800;
}

.clear-filter-btn {
  background: transparent;
  border: none;
  color: var(--text-danger);
  font-family: inherit;
  font-size: 11px;
  font-weight: bold;
  cursor: pointer;
  letter-spacing: 1px;
}

.clear-filter-btn:hover {
  text-decoration: underline;
}

.search-box-wrapper {
  background-color: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: var(--shadow);
}

.search-icon {
  color: var(--text-muted);
  font-size: 16px;
}

.search-input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 13px;
  width: 100%;
  min-width: 0;
}

.search-input:focus {
  outline: none;
}

.table-container {
  background-color: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 8px;
  overflow-x: auto;
  box-shadow: var(--shadow);
}

.vault-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.vault-table th {
  background-color: var(--surface-2);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-main);
  text-transform: uppercase;
  white-space: nowrap;
}

.vault-table td {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-main);
  color: var(--text-secondary);
  vertical-align: middle;
}

.data-row:hover {
  background-color: var(--hover-bg);
}

.interactive-identity-trigger {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  padding: 0;
  text-align: left;
  text-transform: uppercase;
}

.interactive-identity-trigger:hover {
  color: var(--accent);
  text-decoration: underline;
}

.interactive-book-trigger {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: bold;
  transition: color 0.2s ease;
}

.interactive-book-trigger:hover {
  color: var(--accent);
  text-decoration: underline;
}

.error-message {
  color: var(--text-danger);
  font-family: 'JetBrains Mono', monospace;
}

.text-left {
  text-align: left;
}

.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

.text-blue {
  color: var(--accent);
}

.text-magenta {
  color: var(--accent);
}

.text-muted {
  color: var(--text-muted);
}

.text-primary {
  color: var(--text-primary);
}

.bold {
  font-weight: bold;
}

.size-small {
  font-size: 11px;
}

.py-8 {
  padding-top: 32px;
  padding-bottom: 32px;
}

@media (max-width: 900px) {
  .classification-layout {
    position: relative !important;
    height: auto;
    min-height: 100vh;
    min-height: 100dvh;
    flex-direction: column;
    overflow: auto;
  }

  .metric-sidebar {
    width: 100%;
    padding: 24px;
    gap: 20px;
  }

  .hero-identity-block {
    margin-bottom: 0;
  }

  .panel-badge {
    margin-bottom: 12px;
  }

  .registry-feed-column {
    height: auto;
    overflow: visible;
  }

  .feed-scroll-wrapper {
    padding: 24px;
    max-width: none;
  }
}

@media (max-width: 600px) {
  .feed-scroll-wrapper {
    padding: 16px;
  }

  .feed-header-isolated {
    align-items: flex-start;
    flex-direction: column;
  }

  .vault-table th,
  .vault-table td {
    padding: 12px;
  }
}
</style>