<template>
  <div class="classification-layout">
    <!-- LEFT PANEL: STRUCTURAL METRICS -->
    <aside class="metric-sidebar">
      <router-link to="/dashboard" class="escape-matrix-link">
        <span class="escape-icon">←</span>
        RETURN_TO_SYSTEM_CORE
      </router-link>

      <div class="panel-badge">CLASSIFICATION // REGISTRY</div>

      <div class="hero-identity-block">
        <span class="meta-label">INDEX_TYPE</span>
        <h1 class="display-title">AUTHORS</h1>
        <p class="display-summary">
          Master log of unique creators and contribution metrics across the
          active matrix database.
        </p>
      </div>

      <div class="system-status-matrix">
        <div class="status-node">
          <span>UNIQUE_CREATORS</span>
          <strong class="font-mono text-emerald">
            {{ aggregatedAuthorsList.length }}
          </strong>
        </div>

        <div class="status-node">
          <span>TOTAL_DATABASE_ITEMS</span>
          <strong class="font-mono">{{ totalAssetCount }}</strong>
        </div>
      </div>
    </aside>

    <!-- RIGHT PANEL: AUTHORS REGISTRY -->
    <main class="registry-feed-column">
      <div class="feed-scroll-wrapper">
        <!-- AUTHOR SEARCH -->
        <header v-if="!selectedAuthor" class="feed-header">
          <div class="search-box-wrapper">
            <span class="search-icon">⌕</span>

            <input
              v-model="searchQuery"
              type="text"
              placeholder="FILTER_BY_CREATOR_NAME..."
              class="search-input"
            />
          </div>
        </header>

        <!-- SELECTED AUTHOR HEADER -->
        <header v-else class="feed-header-isolated">
          <div class="filter-breadcrumb-badge">
            FILTER_ACTIVE // CREATOR:
            <span class="highlight">{{ selectedAuthor }}</span>
          </div>

          <button
            type="button"
            class="clear-filter-btn"
            @click="clearAuthorSelection"
          >
            [X] RESET_REGISTRY_VIEW
          </button>
        </header>

        <div class="table-container">
          <!-- PRIMARY AUTHORS TABLE -->
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
                <td colspan="3" class="text-center py-8 text-muted font-mono">
                  RETRIEVING_CREATOR_MATRICES...
                </td>
              </tr>

              <tr v-else-if="errorMessage">
                <td colspan="3" class="text-center py-8 error-message">
                  {{ errorMessage }}
                </td>
              </tr>

              <tr v-else-if="filteredAuthors.length === 0">
                <td colspan="3" class="text-center py-8 text-muted font-mono">
                  NO_MATCHING_RECORDS_FOUND
                </td>
              </tr>

              <tr
                v-else
                v-for="author in filteredAuthors"
                :key="author.name"
                class="data-row"
              >
                <td class="text-left">
                  <button
                    type="button"
                    class="interactive-identity-trigger"
                    @click="selectAuthor(author.name)"
                  >
                    {{ author.name || 'UNKNOWN_CREATOR' }}
                  </button>
                </td>

                <td class="text-center font-mono text-blue size-small">
                  {{ author.primaryLanguage }}
                </td>

                <td class="text-right font-mono text-amber bold">
                  {{ author.count }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- SELECTED AUTHOR'S BOOKS -->
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
              <tr v-if="loading">
                <td colspan="4" class="text-center py-8 text-muted font-mono">
                  LOADING_CREATOR_ASSETS...
                </td>
              </tr>

              <tr v-else-if="errorMessage">
                <td colspan="4" class="text-center py-8 error-message">
                  {{ errorMessage }}
                </td>
              </tr>

              <tr v-else-if="targetedAuthorBooks.length === 0">
                <td colspan="4" class="text-center py-8 text-muted font-mono">
                  NO_ASSETS_FOUND_FOR_THIS_CREATOR
                </td>
              </tr>

              <tr
                v-else
                v-for="book in targetedAuthorBooks"
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

                <td class="text-center font-mono text-magenta size-small">
                  {{ book.genre || 'GENERAL' }}
                </td>

                <td class="text-right font-mono size-small text-blue">
                  {{ book.call_no || 'UNASSIGNED' }}
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
  author?: string | null
  language?: string | null
  genre?: string | null
  call_no?: string | null
  [key: string]: unknown
}

interface AuthorAggregate {
  name: string
  count: number
  primaryLanguage: string
}

interface CatalogueResponse {
  data?: CatalogueItem[]
  total?: number
  page?: number
  limit?: number
}

const loading = ref(true)
const searchQuery = ref('')
const selectedAuthor = ref<string | null>(null)
const errorMessage = ref('')

const masterCatalogueData = ref<CatalogueItem[]>([])
const aggregatedAuthorsList = ref<AuthorAggregate[]>([])
const totalAssetCount = ref(0)

/**
 * The catalogue detail endpoint uses serial_no.
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
 * Normalize author names to avoid grouping the same author separately
 * because of leading/trailing spaces or repeated whitespace.
 */
function normalizeAuthor(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) {
    return 'UNKNOWN_CREATOR'
  }

  return value.trim().replace(/\s+/g, ' ')
}

/**
 * Normalize language values for the language-frequency count.
 */
function normalizeLanguage(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) {
    return 'Unknown'
  }

  return value.trim().replace(/\s+/g, ' ')
}

/**
 * Build the authors registry from all fetched catalogue records.
 *
 * The primary language is the most frequent language among each
 * author's catalogue records.
 */
function buildAuthorsRegistry(items: CatalogueItem[]): void {
  const mapping = new Map<
    string,
    {
      count: number
      languages: Map<string, number>
    }
  >()

  for (const item of items) {
    const authorName = normalizeAuthor(item.author)
    const language = normalizeLanguage(item.language)

    let entry = mapping.get(authorName)

    if (!entry) {
      entry = {
        count: 0,
        languages: new Map<string, number>()
      }

      mapping.set(authorName, entry)
    }

    entry.count += 1

    entry.languages.set(
      language,
      (entry.languages.get(language) ?? 0) + 1
    )
  }

  aggregatedAuthorsList.value = Array.from(mapping.entries())
    .map(([name, entry]) => {
      let primaryLanguage = 'Unknown'
      let highestCount = 0

      for (const [language, count] of entry.languages) {
        if (count > highestCount) {
          primaryLanguage = language
          highestCount = count
        }
      }

      return {
        name,
        count: entry.count,
        primaryLanguage
      }
    })
    .sort((a, b) => {
      const countDifference = b.count - a.count

      return countDifference !== 0
        ? countDifference
        : a.name.localeCompare(b.name)
    })
}

/**
 * Load every page of the catalogue.
 *
 * This matches the FastAPI response:
 * {
 *   data: [...],
 *   total: number,
 *   page: number,
 *   limit: number
 * }
 *
 * The backend supports a maximum limit of 100.
 */
async function compileAuthorsRegistry(): Promise<void> {
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

      if (!Array.isArray(payload?.data)) {
        throw new Error(
          'Unexpected catalogue response: expected a data array.'
        )
      }

      const batch = payload.data

      if (
        typeof payload.total === 'number' &&
        Number.isFinite(payload.total)
      ) {
        expectedTotal = payload.total
      }

      if (batch.length === 0) {
        break
      }

      // Detect repeated pages to avoid an infinite pagination loop.
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

      // Stop when all records reported by the backend are fetched.
      if (
        expectedTotal !== null &&
        allItems.length >= expectedTotal
      ) {
        break
      }

      // A shorter page means there are no further records.
      if (batch.length < limit) {
        break
      }

      page += 1
    }

    masterCatalogueData.value = allItems

    // Use the backend's total when available.
    totalAssetCount.value = expectedTotal ?? allItems.length

    buildAuthorsRegistry(allItems)
  } catch (error: unknown) {
    console.error('Failed to load authors registry:', error)

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
    aggregatedAuthorsList.value = []
    totalAssetCount.value = 0
  } finally {
    loading.value = false
  }
}

/**
 * Search authors by name.
 */
const filteredAuthors = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase()

  if (!query) {
    return aggregatedAuthorsList.value
  }

  return aggregatedAuthorsList.value.filter(author =>
    author.name.toLocaleLowerCase().includes(query)
  )
})

/**
 * Get all catalogue records belonging to the selected author.
 */
const targetedAuthorBooks = computed(() => {
  const selected = selectedAuthor.value

  if (!selected) {
    return []
  }

  return masterCatalogueData.value.filter(
    item => normalizeAuthor(item.author) === selected
  )
})

function selectAuthor(name: string): void {
  selectedAuthor.value = name
}

function clearAuthorSelection(): void {
  selectedAuthor.value = null
}

onMounted(() => {
  void compileAuthorsRegistry()
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

.text-left {
  text-align: left;
}

.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

.text-emerald {
  color: var(--accent);
}

.text-blue {
  color: var(--accent);
}

.text-magenta {
  color: var(--accent);
}

.text-amber {
  color: var(--accent);
}

.text-muted {
  color: var(--text-muted);
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

.error-message {
  color: var(--text-danger);
  font-family: 'JetBrains Mono', monospace;
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