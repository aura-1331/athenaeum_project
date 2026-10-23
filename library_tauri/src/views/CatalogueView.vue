<template>
  <div ref="rootEl" class="cat" :class="{ 'filters-open': filtersOpen, dark: isDark }">
    <!-- ================= HEADER ================= -->
    <header class="cat-head">
      <div class="head-title">
        <p class="eyebrow">ATHENAEUM ORBIS &middot; CARD CATALOGUE</p>
        <h1>Catalogue</h1>
        <p class="sub">
          <strong>{{ grandTotal === null ? '...' : grandTotal.toLocaleString() }}</strong> holdings on the shelves
          <span v-if="hasFilters"> &middot; <strong>{{ total.toLocaleString() }}</strong> match your search</span>
        </p>
      </div>
      <div class="head-actions">
        <button type="button" class="btn ghost filters-toggle" @click="filtersOpen = !filtersOpen">
          Filters<span v-if="activeCount" class="badge">{{ activeCount }}</span>
        </button>
        <button type="button" class="btn ghost" :disabled="exporting || !books.length" @click="exportCsv(false)">Export page</button>
        <button type="button" class="btn solid" :disabled="exporting || !total" @click="exportCsv(true)">
          {{ exporting ? 'Exporting ' + exportProgress + '...' : 'Export all matches' }}
        </button>
      </div>
    </header>

    <div class="cat-body">
      <!-- ================= FILTER RAIL ================= -->
      <aside class="rail" aria-label="Search and filters">
        <div class="field">
          <label for="cat-search">Search</label>
          <div class="search-box">
            <span class="search-icon" aria-hidden="true">&#8981;</span>
            <input
              id="cat-search"
              ref="searchEl"
              v-model="text"
              type="search"
              autocomplete="off"
              :placeholder="scopePlaceholder"
              @keydown.esc.stop="clearSearch"
            />
            <kbd v-if="!text" class="kbd" aria-hidden="true">/</kbd>
            <button v-else type="button" class="clear-x" aria-label="Clear search" @click="clearSearch">&times;</button>
          </div>
          <div class="scope" role="radiogroup" aria-label="Search in">
            <button
              v-for="s in SCOPES"
              :key="s.key"
              type="button"
              role="radio"
              :aria-checked="scope === s.key"
              :class="{ on: scope === s.key }"
              @click="scope = s.key"
            >{{ s.label }}</button>
          </div>
        </div>

        <div class="field">
          <span class="label">Category</span>
          <div class="chips">
            <button type="button" class="chip" :class="{ on: !category }" @click="category = ''">
              <span>All</span><b>{{ facetAll === null ? '' : facetAll }}</b>
            </button>
            <button
              v-for="c in CATEGORIES"
              :key="c.name"
              type="button"
              class="chip"
              :class="[{ on: category === c.name }, 'tone-' + c.tone]"
              :disabled="facets[c.name] === 0 && category !== c.name"
              @click="category = category === c.name ? '' : c.name"
            >
              <i class="dot" aria-hidden="true"></i><span>{{ c.name }}</span>
              <b>{{ facets[c.name] === undefined ? '' : facets[c.name] }}</b>
            </button>
          </div>
        </div>

        <div class="field">
          <label for="cat-language">Language</label>
          <select id="cat-language" v-model="language">
            <option value="">Any language</option>
            <option v-for="l in languages" :key="l" :value="l">{{ l }}</option>
          </select>
        </div>

        <div class="field" v-if="genres.length">
          <label for="cat-genre">Genre</label>
          <select id="cat-genre" v-model="genre">
            <option value="">Any genre</option>
            <option v-for="g in genres" :key="g" :value="g">{{ g }}</option>
          </select>
        </div>

        <div class="field two">
          <div>
            <label for="cat-sort">Sort by</label>
            <select id="cat-sort" v-model="sortBy">
              <option v-for="s in SORTS" :key="s.key" :value="s.key">{{ s.label }}</option>
            </select>
          </div>
          <button type="button" class="dir" :aria-label="order === 'asc' ? 'Ascending, switch to descending' : 'Descending, switch to ascending'" @click="order = order === 'asc' ? 'desc' : 'asc'">
            {{ order === 'asc' ? 'A\u2192Z' : 'Z\u2192A' }}
          </button>
        </div>

        <div class="field">
          <label for="cat-size">Records per page</label>
          <select id="cat-size" v-model.number="pageSize">
            <option v-for="n in [15, 30, 60, 100]" :key="n" :value="n">{{ n }}</option>
          </select>
        </div>

        <button type="button" class="btn ghost wide" :disabled="!hasFilters" @click="clearAll">Clear all filters</button>

        <p class="tips">
          <b>Tips</b><br />
          <kbd>/</kbd> search &nbsp; <kbd>&uarr;</kbd><kbd>&darr;</kbd> move &nbsp; <kbd>Enter</kbd> open
        </p>
      </aside>

      <!-- ================= RESULTS ================= -->
      <section class="results" aria-label="Results">
        <div class="meta-row">
          <p class="count" aria-live="polite">
            <template v-if="loading && !books.length">Loading records...</template>
            <template v-else-if="total === 0">No records</template>
            <template v-else>Showing <strong>{{ from }}&ndash;{{ to }}</strong> of <strong>{{ total.toLocaleString() }}</strong></template>
          </p>
          <div class="active" v-if="hasFilters">
            <span v-if="text.trim()" class="tag">{{ scopeLabel }}: &ldquo;{{ text.trim() }}&rdquo;<button type="button" aria-label="Remove search" @click="clearSearch">&times;</button></span>
            <span v-if="category" class="tag">{{ category }}<button type="button" aria-label="Remove category" @click="category = ''">&times;</button></span>
            <span v-if="language" class="tag">{{ language }}<button type="button" aria-label="Remove language" @click="language = ''">&times;</button></span>
            <span v-if="genre" class="tag">{{ genre }}<button type="button" aria-label="Remove genre" @click="genre = ''">&times;</button></span>
          </div>
        </div>

        <div v-if="error" class="banner" role="alert">
          <span>{{ error }}</span>
          <button type="button" class="btn ghost" @click="reload">Try again</button>
        </div>

        <ul v-if="loading && !books.length" class="list skeleton" aria-hidden="true">
          <li v-for="n in 8" :key="n"><i></i><i></i><i></i></li>
        </ul>

        <div v-else-if="!books.length && !error" class="empty">
          <div class="empty-mark" aria-hidden="true">&#9776;</div>
          <h2>Nothing matches that search</h2>
          <p>Try fewer words, check the spelling, or search by author instead of title.</p>
          <button v-if="hasFilters" type="button" class="btn solid" @click="clearAll">Clear all filters</button>
        </div>

        <ul v-else ref="listEl" class="list" :class="{ busy: loading }" @keydown="onListKey">
          <li v-for="book in books" :key="book.serial_no">
            <button
              type="button"
              class="row"
              :class="['tone-' + toneOf(book.category), { selected: book.serial_no === selectedSerial }]"
              :aria-current="book.serial_no === selectedSerial ? 'true' : undefined"
              @click="pick(book)"
              @dblclick="openBook(book)"
            >
              <span class="spine" aria-hidden="true"></span>
              <span class="main">
                <strong class="title">
                  <template v-for="(p, i) in parts(book.title || 'Untitled')" :key="i"><mark v-if="p.hit">{{ p.t }}</mark><template v-else>{{ p.t }}</template></template>
                </strong>
                <span class="author" :class="{ unknown: !hasAuthor(book) }">
                  <template v-for="(p, i) in parts(authorText(book))" :key="i"><mark v-if="p.hit">{{ p.t }}</mark><template v-else>{{ p.t }}</template></template>
                </span>
                <span class="line"><b class="serial">#{{ book.serial_no }}</b>{{ metaLine(book) }}</span>
              </span>
              <span class="side">
                <span class="pill" :class="'tone-' + toneOf(book.category)">{{ book.category || 'Uncategorised' }}</span>
                <span class="lang">{{ book.language }}</span>
                <span class="acc">{{ book.accession_no }}</span>
                <span v-if="book.shelf" class="shelf">Shelf {{ book.shelf }}</span>
              </span>
            </button>
          </li>
        </ul>

        <nav v-if="totalPages > 1" class="pager" aria-label="Catalogue pages">
          <button type="button" class="btn ghost" :disabled="page === 1 || loading" @click="goTo(page - 1)">&larr; Previous</button>
          <template v-for="(n, i) in pageNumbers" :key="'p' + i">
            <span v-if="n === -1" class="gap">&hellip;</span>
            <button v-else type="button" class="num" :class="{ on: n === page }" :aria-current="n === page ? 'page' : undefined" :disabled="loading" @click="goTo(n)">{{ n }}</button>
          </template>
          <button type="button" class="btn ghost" :disabled="page === totalPages || loading" @click="goTo(page + 1)">Next &rarr;</button>
        </nav>
      </section>

      <!-- ================= CARD PREVIEW ================= -->
      <aside class="card-pane" aria-label="Record preview">
        <article v-if="selectedBook" class="index-card" :class="'tone-' + toneOf(selectedBook.category)">
          <div class="card-tab">{{ selectedBook.call_no || selectedBook.accession_no || 'No call number' }}</div>
          <p class="card-kicker">{{ selectedBook.category || 'Uncategorised' }} &middot; {{ selectedBook.language }}</p>
          <h2 class="card-title">{{ selectedBook.title || 'Untitled' }}</h2>
          <p class="card-author" :class="{ unknown: !hasAuthor(selectedBook) }">{{ authorText(selectedBook) }}</p>
          <div class="card-rule"></div>
          <dl class="card-facts">
            <template v-for="f in factsOf(selectedBook)" :key="f.label">
              <dt>{{ f.label }}</dt>
              <dd :class="{ mono: f.mono }">{{ f.value }}</dd>
            </template>
          </dl>
          <div v-if="selectedBook.notes" class="card-notes"><b>Notes</b><p>{{ selectedBook.notes }}</p></div>
          <div class="card-actions">
            <button type="button" class="btn solid" @click="openBook(selectedBook)">Open full record &rarr;</button>
            <button type="button" class="btn ghost" :disabled="!selectedBook.accession_no" @click="copy(selectedBook.accession_no, 'acc')">
              {{ copied === 'acc' ? 'Copied \u2713' : 'Copy accession no.' }}
            </button>
          </div>
          <p class="card-record">{{ selectedBook.record_id }}</p>
        </article>
        <div v-else class="card-empty">
          <p>Select a record to see its catalogue card here.</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

// ---------- constants ----------
const CATEGORIES = [
  { name: 'Fiction', tone: 'rust' },
  { name: 'Non-Fiction', tone: 'teal' },
  { name: 'Reference', tone: 'ochre' },
  { name: 'Religious', tone: 'plum' },
  { name: 'Poetry', tone: 'moss' }
]
const SORTS = [
  { key: 'serial_no', label: 'Serial number' },
  { key: 'title', label: 'Title' },
  { key: 'author', label: 'Author' },
  { key: 'category', label: 'Category' },
  { key: 'genre', label: 'Genre' },
  { key: 'year', label: 'Year' },
  { key: 'publisher', label: 'Publisher' },
  { key: 'language', label: 'Language' },
  { key: 'accession_no', label: 'Accession number' },
  { key: 'work_id', label: 'Work ID' }
]
const SCOPES = [
  { key: 'all', label: 'Everything', param: 'q', hint: 'Title, author, call no., ISBN, accession...' },
  { key: 'title', label: 'Title', param: 'title', hint: 'Search titles...' },
  { key: 'author', label: 'Author', param: 'author', hint: 'Search authors...' }
]
const FALLBACK_LANGUAGES = ['Malayalam', 'English', 'Multi -Lingual', 'Malay', 'Russian', 'Arabic', 'Marathi', 'German', 'Tamil']
const PREF_KEY = 'athenaeum_catalogue_prefs'

// ---------- state ----------
const books = ref([])
const total = ref(0)
const grandTotal = ref(null)
const loading = ref(true)
const error = ref('')
const exporting = ref(false)
const exportProgress = ref('')
const filtersOpen = ref(false)
const copied = ref('')
const searchEl = ref(null)
const rootEl = ref(null)
const isDark = ref(false)
const listEl = ref(null)

const text = ref('')
const debouncedText = ref('')
const scope = ref('all')
const category = ref('')
const language = ref('')
const genre = ref('')
const sortBy = ref('serial_no')
const order = ref('asc')
const pageSize = ref(15)
const page = ref(1)
const selectedSerial = ref(null)

const facets = ref({})
const facetAll = ref(null)
const languages = ref(FALLBACK_LANGUAGES)
const genres = ref([])
const isWide = ref(true)

// ---------- derived ----------
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const from = computed(() => (total.value ? (page.value - 1) * pageSize.value + 1 : 0))
const to = computed(() => Math.min(page.value * pageSize.value, total.value))
const term = computed(() => debouncedText.value.trim())
const hasFilters = computed(() => Boolean(term.value || category.value || language.value || genre.value))
const activeCount = computed(() => [term.value, category.value, language.value, genre.value].filter(Boolean).length)
const scopeObj = computed(() => SCOPES.find(s => s.key === scope.value) || SCOPES[0])
const scopePlaceholder = computed(() => scopeObj.value.hint)
const scopeLabel = computed(() => scopeObj.value.label)
const selectedBook = computed(() => books.value.find(b => b.serial_no === selectedSerial.value) || null)

const pageNumbers = computed(() => {
  const n = totalPages.value, c = page.value
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1)
  const set = new Set([1, 2, n - 1, n, c - 1, c, c + 1].filter(p => p >= 1 && p <= n))
  const sorted = [...set].sort((a, b) => a - b)
  const out = []
  sorted.forEach((p, i) => { if (i && p - sorted[i - 1] > 1) out.push(-1); out.push(p) })
  return out
})

// ---------- helpers ----------
const PLACEHOLDER_AUTHOR = /^(author|unknown|n\/a|-+)$/i
function hasAuthor(b) {
  const a = String((b && b.author) || '').trim()
  return Boolean(a) && !PLACEHOLDER_AUTHOR.test(a)
}
function authorText(b) { return hasAuthor(b) ? String(b.author).trim() : 'Author not recorded' }
function metaLine(b) {
  const year = Number(b.year) > 0 ? String(b.year) : ''
  return [b.genre, year, b.publisher].filter(v => v && String(v).trim()).join(' \u00b7 ')
}

function toneOf(name) {
  const hit = CATEGORIES.find(c => c.name === name)
  return hit ? hit.tone : 'none'
}

function parts(value) {
  const str = String(value ?? '')
  const q = term.value
  if (!q) return [{ t: str, hit: false }]
  const lower = str.toLowerCase(), needle = q.toLowerCase()
  const out = []
  let i = 0
  while (i < str.length) {
    const at = lower.indexOf(needle, i)
    if (at === -1) { out.push({ t: str.slice(i), hit: false }); break }
    if (at > i) out.push({ t: str.slice(i, at), hit: false })
    out.push({ t: str.slice(at, at + needle.length), hit: true })
    i = at + needle.length
  }
  return out.length ? out : [{ t: str, hit: false }]
}

function factsOf(b) {
  const rows = [
    ['Author', b.author], ['Genre', b.genre], ['Year', b.year], ['Publisher', b.publisher],
    ['Original language', b.original_language], ['Translation / compilation', b.translation_compilation],
    ['ISBN', b.isbn, true], ['DDC', b.ddc, true], ['Call no.', b.call_no, true],
    ['Accession no.', b.accession_no, true], ['Serial no.', b.serial_no, true], ['Work ID', b.work_id, true],
    ['Shelf', b.shelf, true]
  ]
  return rows
    .filter(r => r[1] !== null && r[1] !== undefined && String(r[1]).trim() !== '' && r[0] !== 'Author' && !(r[0] === 'Year' && !(Number(r[1]) > 0)))
    .map(r => ({ label: r[0], value: r[1], mono: Boolean(r[2]) }))
}

function baseParams(withCategory) {
  const p = {}
  if (term.value) p[scopeObj.value.param] = term.value
  if (withCategory && category.value) p.category = category.value
  if (language.value) p.language = language.value
  if (genre.value) p.genre = genre.value
  return p
}

function friendly(err) {
  const status = err && err.response && err.response.status
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to view the catalogue.'
  if (status === 400) return (err.response.data && err.response.data.detail) || 'The server did not accept that search.'
  return 'The catalogue could not be loaded. Check your connection and try again.'
}

// ---------- loading ----------
let requestId = 0

async function fetchPage() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get('/catalogue', {
      params: { ...baseParams(true), page: page.value, limit: pageSize.value, sort_by: sortBy.value, order: order.value }
    })
    if (id !== requestId) return
    const data = res.data || {}
    books.value = Array.isArray(data.data) ? data.data : []
    total.value = Number(data.total || 0)
    if (!books.value.some(b => b.serial_no === selectedSerial.value)) {
      selectedSerial.value = isWide.value && books.value.length ? books.value[0].serial_no : null
    }
  } catch (err) {
    if (id !== requestId) return
    books.value = []
    total.value = 0
    error.value = friendly(err)
    if (err && err.response && err.response.status === 401) router.push('/login')
  } finally {
    if (id === requestId) loading.value = false
  }
}

let facetId = 0
async function fetchFacets() {
  const id = ++facetId
  const base = { ...baseParams(false), page: 1, limit: 1 }
  const calls = [axios.get('/catalogue', { params: base }), ...CATEGORIES.map(c => axios.get('/catalogue', { params: { ...base, category: c.name } }))]
  const results = await Promise.allSettled(calls)
  if (id !== facetId) return
  const count = r => (r.status === 'fulfilled' ? Number((r.value.data || {}).total || 0) : undefined)
  facetAll.value = count(results[0]) ?? null
  const next = {}
  CATEGORIES.forEach((c, i) => { next[c.name] = count(results[i + 1]) })
  facets.value = next
}

async function fetchEverythingCount() {
  try {
    const res = await axios.get('/catalogue', { params: { page: 1, limit: 1 } })
    grandTotal.value = Number((res.data || {}).total || 0)
  } catch (e) { /* the header simply keeps showing ... */ }
}

async function fetchOptions() {
  try {
    const res = await axios.get('/catalogue/review/field-options')
    const d = res.data || {}
    if (Array.isArray(d.languages) && d.languages.length) languages.value = d.languages
    if (Array.isArray(d.genres)) genres.value = d.genres
  } catch (e) { /* other roles keep the built-in language list */ }
}

function reload() { fetchPage(); fetchFacets() }

// ---------- actions ----------
function goTo(n) {
  if (n < 1 || n > totalPages.value || n === page.value) return
  page.value = n
  fetchPage()
  nextTick(() => { if (listEl.value) listEl.value.scrollIntoView({ block: 'start', behavior: 'smooth' }) })
}
function pick(book) {
  if (isWide.value) selectedSerial.value = book.serial_no
  else openBook(book)
}
function openBook(book) { router.push('/details/' + book.serial_no) }
function clearSearch() { text.value = ''; debouncedText.value = '' }
function clearAll() { clearSearch(); category.value = ''; language.value = ''; genre.value = '' }

async function copy(value, key) {
  try {
    await navigator.clipboard.writeText(String(value))
    copied.value = key
    setTimeout(() => { if (copied.value === key) copied.value = '' }, 1600)
  } catch (e) { copied.value = '' }
}

function onListKey(e) {
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Enter') return
  const idx = books.value.findIndex(b => b.serial_no === selectedSerial.value)
  if (e.key === 'Enter') {
    if (idx >= 0 && e.target && e.target.classList && e.target.classList.contains('row')) { e.preventDefault(); openBook(books.value[idx]) }
    return
  }
  e.preventDefault()
  const nextIdx = Math.min(books.value.length - 1, Math.max(0, idx + (e.key === 'ArrowDown' ? 1 : -1)))
  selectedSerial.value = books.value[nextIdx].serial_no
  nextTick(() => {
    const rows = listEl.value ? listEl.value.querySelectorAll('.row') : []
    if (rows[nextIdx]) rows[nextIdx].focus()
  })
}

function onGlobalKey(e) {
  const tag = (e.target && e.target.tagName) || ''
  if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
    e.preventDefault()
    filtersOpen.value = true
    nextTick(() => searchEl.value && searchEl.value.focus())
  }
}

// ---------- export ----------
function csvEscape(v) { return '"' + String(v ?? '').replace(/"/g, '""') + '"' }

async function exportCsv(all) {
  const columns = ['serial_no', 'work_id', 'accession_no', 'title', 'author', 'category', 'genre', 'language', 'year', 'publisher', 'isbn', 'ddc', 'call_no', 'shelf', 'record_id']
  let rows = books.value
  if (all) {
    exporting.value = true
    rows = []
    try {
      const cap = 5000
      for (let p = 1; rows.length < Math.min(total.value, cap); p++) {
        exportProgress.value = rows.length + ' / ' + Math.min(total.value, cap)
        const res = await axios.get('/catalogue', { params: { ...baseParams(true), page: p, limit: 100, sort_by: sortBy.value, order: order.value } })
        const chunk = (res.data && res.data.data) || []
        if (!chunk.length) break
        rows = rows.concat(chunk)
      }
    } catch (err) {
      error.value = 'The export stopped early: ' + friendly(err)
    } finally { exporting.value = false; exportProgress.value = '' }
  }
  if (!rows.length) return
  const csv = [columns.join(','), ...rows.map(r => columns.map(k => csvEscape(r[k])).join(','))].join('\r\n')
  const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = all ? 'catalogue-matches.csv' : 'catalogue-page-' + page.value + '.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// ---------- remember state (URL + preferences) ----------
function syncUrl() {
  const q = {}
  if (term.value) q.q = term.value
  if (scope.value !== 'all') q.in = scope.value
  if (category.value) q.cat = category.value
  if (language.value) q.lang = language.value
  if (genre.value) q.genre = genre.value
  if (sortBy.value !== 'serial_no') q.sort = sortBy.value
  if (order.value !== 'asc') q.order = order.value
  if (page.value > 1) q.page = String(page.value)
  if (pageSize.value !== 15) q.size = String(pageSize.value)
  router.replace({ query: q }).catch(() => {})
}
function savePrefs() {
  try { localStorage.setItem(PREF_KEY, JSON.stringify({ pageSize: pageSize.value, sortBy: sortBy.value, order: order.value })) } catch (e) { /* storage unavailable */ }
}
function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(PREF_KEY) || '{}')
    if ([15, 30, 60, 100].includes(saved.pageSize)) pageSize.value = saved.pageSize
    if (SORTS.some(s => s.key === saved.sortBy)) sortBy.value = saved.sortBy
    if (saved.order === 'asc' || saved.order === 'desc') order.value = saved.order
  } catch (e) { /* ignore broken preferences */ }
  const q = route.query
  const one = v => (Array.isArray(v) ? v[0] : v) || ''
  if (one(q.q)) { text.value = one(q.q); debouncedText.value = one(q.q) }
  if (SCOPES.some(s => s.key === one(q.in))) scope.value = one(q.in)
  if (CATEGORIES.some(c => c.name === one(q.cat))) category.value = one(q.cat)
  language.value = one(q.lang)
  genre.value = one(q.genre)
  if (SORTS.some(s => s.key === one(q.sort))) sortBy.value = one(q.sort)
  if (one(q.order) === 'asc' || one(q.order) === 'desc') order.value = one(q.order)
  if ([15, 30, 60, 100].includes(Number(one(q.size)))) pageSize.value = Number(one(q.size))
  const p = parseInt(one(q.page), 10)
  if (p > 0) page.value = p
}

// ---------- reactions ----------
let debounceTimer = null
watch(text, v => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { debouncedText.value = v }, 350)
})

let ready = false
watch([debouncedText, scope, category, language, genre, sortBy, order, pageSize], (now, before) => {
  if (!ready) return
  const facetsChanged = now[0] !== before[0] || now[1] !== before[1] || now[3] !== before[3] || now[4] !== before[4]
  page.value = 1
  fetchPage()
  if (facetsChanged) fetchFacets()
  savePrefs()
  syncUrl()
})
watch(page, () => { if (ready) syncUrl() })

function channelsOf(css) {
  const m = String(css).match(/rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)(?:[ ,/]+([\d.]+))?/)
  return m ? { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] } : null
}
function detectDark() {
  const html = document.documentElement
  const body = document.body
  const hints = [html.getAttribute('data-theme'), body && body.getAttribute('data-theme'), html.className, body && body.className].join(' ').toLowerCase()
  if (/(^|[^a-z])(dark|night)([^a-z]|$)/.test(hints)) { isDark.value = true; return }
  // otherwise look at the colour the app paints behind this page
  let el = rootEl.value ? rootEl.value.parentElement : null
  while (el) {
    const c = channelsOf(getComputedStyle(el).backgroundColor)
    if (c && c.a > 0.5) { isDark.value = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) < 115; return }
    el = el.parentElement
  }
  isDark.value = false
}
let themeObserver = null
function watchTheme() {
  detectDark()
  themeObserver = new MutationObserver(records => {
    if (records.some(r => r.target.contains(rootEl.value) && r.target !== rootEl.value)) requestAnimationFrame(detectDark)
  })
  themeObserver.observe(document.documentElement, { attributes: true, subtree: true, attributeFilter: ['class', 'data-theme', 'style'] })
}

function onResize() { isWide.value = window.matchMedia('(min-width: 1200px)').matches }

onMounted(async () => {
  onResize()
  watchTheme()
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onGlobalKey)
  loadState()
  await fetchPage()
  ready = true
  fetchFacets()
  fetchEverythingCount()
  fetchOptions()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onGlobalKey)
  clearTimeout(debounceTimer)
  if (themeObserver) themeObserver.disconnect()
})
</script>

<style scoped>
/* ===== design tokens: warm paper, forest ink, brass accents ===== */
.cat {
  --paper: #f5f0e4; --card: #fffdf7; --ink: #23312b; --muted: #6f776f; --line: #ddd4c1;
  --forest: #2f5d46; --forest-ink: #ffffff; --brass: #b08d3c; --soft: #ece5d3; --focus: #b08d3c;
  --rust: #b4533a; --teal: #2a7d74; --ochre: #9a7a1f; --plum: #7a4b8c; --moss: #4d7a3a; --none: #8b8b80;
  min-height: 100%; box-sizing: border-box; padding: 26px clamp(14px, 2.4vw, 36px) 40px;
  background: var(--paper); color: var(--ink); font-family: 'Segoe UI', system-ui, -apple-system, Arial, sans-serif;
}
.cat.dark, :global(html[data-theme='dark']) .cat {
  --paper: #121a16; --card: #1a2520; --ink: #e9efe9; --muted: #98a59c; --line: #2c3a32;
  --forest: #7cc79b; --forest-ink: #0d1a12; --brass: #d3b25f; --soft: #22302a; --focus: #d3b25f;
  --rust: #e08a70; --teal: #5cc4b8; --ochre: #d9b84f; --plum: #c39ad6; --moss: #93c77c; --none: #98a59c;
}
.cat *, .cat *::before, .cat *::after { box-sizing: border-box; }
.cat button, .cat input, .cat select { font: inherit; color: inherit; }
.cat h1, .cat h2, .cat h3, .cat p, .cat strong, .cat dd, .cat dt { color: inherit; }
.cat { --serif: Georgia, 'Noto Serif Malayalam', 'Nirmala UI', 'Kartika', 'Times New Roman', serif; }
.cat :focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.tone-rust { --tone: var(--rust); } .tone-teal { --tone: var(--teal); } .tone-ochre { --tone: var(--ochre); }
.tone-plum { --tone: var(--plum); } .tone-moss { --tone: var(--moss); } .tone-none { --tone: var(--none); }

/* ===== header ===== */
.cat-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; padding-bottom: 20px; border-bottom: 2px solid var(--ink); }
.eyebrow { margin: 0 0 6px; font-size: 11px; letter-spacing: .18em; font-weight: 700; color: var(--brass); }
.cat-head h1 { margin: 0; font: 400 clamp(34px, 4.4vw, 54px)/1 var(--serif); letter-spacing: -.02em; color: var(--ink); }
.sub { margin: 10px 0 0; color: var(--muted); font-size: 14px; }
.sub strong { color: var(--ink); }
.head-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.filters-toggle { display: none; }
.badge { margin-left: 8px; background: var(--forest); color: var(--forest-ink); border-radius: 99px; padding: 1px 8px; font-size: 11px; font-weight: 700; }

.btn { border: 1px solid var(--line); background: var(--card); padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: transform .15s, filter .15s, background .15s; }
.btn.solid { background: var(--forest); color: var(--forest-ink); border-color: var(--forest); }
.btn.ghost:hover:not(:disabled) { background: var(--soft); }
.btn:hover:not(:disabled) { transform: translateY(-1px); }
.btn:active:not(:disabled) { transform: translateY(1px) scale(.98); }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn.wide { width: 100%; }

/* ===== 3-zone body ===== */
.cat-body { display: grid; grid-template-columns: 250px minmax(0, 1fr) 350px; gap: 26px; align-items: start; padding-top: 24px; }

/* ===== filter rail ===== */
.rail { position: sticky; top: 14px; max-height: calc(100vh - 130px); overflow-y: auto; display: grid; align-content: start; gap: 20px; padding: 20px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; }
.field { display: grid; gap: 8px; }
.field.two { grid-template-columns: 1fr auto; align-items: end; }
.field label, .field .label { font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.field select { width: 100%; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); }
.search-box { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 12px; font-size: 18px; color: var(--muted); }
.search-box input { width: 100%; padding: 12px 38px 12px 36px; border: 2px solid var(--line); border-radius: 10px; background: var(--paper); font-size: 14px; }
.search-box input:focus { border-color: var(--forest); outline: none; }
.kbd, .tips kbd { font: 11px ui-monospace, Consolas, monospace; border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 5px; padding: 1px 6px; background: var(--paper); color: var(--muted); }
.kbd { position: absolute; right: 10px; }
.clear-x { position: absolute; right: 6px; border: 0; background: transparent; font-size: 22px; line-height: 1; padding: 4px 8px; cursor: pointer; color: var(--muted); }
.scope { display: flex; gap: 4px; padding: 3px; background: var(--soft); border-radius: 9px; }
.scope button { flex: 1; border: 0; background: transparent; padding: 7px 4px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; color: var(--muted); }
.scope button.on { background: var(--card); color: var(--ink); box-shadow: 0 1px 3px rgba(0, 0, 0, .15); }
.chips { display: grid; gap: 6px; }
.chip { display: flex; align-items: center; gap: 9px; width: 100%; text-align: left; padding: 9px 12px; border: 1px solid var(--line); border-radius: 9px; background: var(--paper); cursor: pointer; font-size: 13px; transition: border-color .15s, background .15s; }
.chip span { flex: 1; }
.chip b { font: 700 12px ui-monospace, Consolas, monospace; color: var(--muted); }
.chip .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--tone, var(--forest)); }
.chip:hover:not(:disabled) { border-color: var(--tone, var(--forest)); }
.chip.on { background: var(--tone, var(--forest)); border-color: var(--tone, var(--forest)); color: #fff; }
.chip.on b { color: #fff; }
.chip.on .dot { background: #fff; }
.chip:disabled { opacity: .4; cursor: not-allowed; }
.dir { height: 40px; padding: 0 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); font-weight: 700; cursor: pointer; }
.tips { margin: 0; font-size: 12px; line-height: 2; color: var(--muted); border-top: 1px dashed var(--line); padding-top: 14px; }

/* ===== results ===== */
.results { min-width: 0; }
.meta-row { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.count { margin: 0; font-size: 14px; color: var(--muted); }
.count strong { color: var(--ink); }
.active { display: flex; gap: 8px; flex-wrap: wrap; }
.tag { display: inline-flex; align-items: center; gap: 6px; padding: 4px 6px 4px 11px; border-radius: 99px; background: var(--soft); font-size: 12px; font-weight: 600; }
.tag button { border: 0; background: transparent; cursor: pointer; font-size: 16px; line-height: 1; padding: 0 4px; color: var(--muted); }
.banner { display: flex; justify-content: space-between; align-items: center; gap: 14px; padding: 12px 16px; margin-bottom: 14px; border: 1px solid var(--rust); border-left-width: 6px; border-radius: 10px; background: var(--card); }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; transition: opacity .15s; }
.list.busy { opacity: .55; }
.row { position: relative; display: grid; grid-template-columns: 6px minmax(0, 1fr) minmax(112px, 150px); gap: 16px; align-items: center; width: 100%; text-align: left; padding: 14px 18px 14px 0; border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; overflow: hidden; transition: transform .15s, box-shadow .15s, border-color .15s; }
.row:hover { transform: translateX(3px); box-shadow: 0 4px 14px rgba(0, 0, 0, .1); }
.row.selected { border-color: var(--tone, var(--forest)); box-shadow: 0 0 0 2px var(--tone, var(--forest)) inset; }
.spine { align-self: stretch; background: var(--tone, var(--none)); }
.line .serial { margin-right: 10px; font: 700 12px ui-monospace, Consolas, monospace; color: var(--ink); opacity: .7; }
.main { display: grid; gap: 4px; min-width: 0; }
.title { font: 500 16px/1.4 var(--serif); overflow-wrap: anywhere; color: var(--ink); }
.author { font-size: 13px; color: var(--muted); overflow-wrap: anywhere; }
.author.unknown, .card-author.unknown { opacity: .65; font-style: italic; }
.line { font-size: 12px; line-height: 1.5; color: var(--muted); overflow-wrap: anywhere; }
mark { background: color-mix(in srgb, var(--brass) 40%, transparent); color: inherit; border-radius: 3px; padding: 0 1px; }
.side { display: grid; justify-items: end; gap: 5px; font-size: 12px; }
.pill { padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; color: #fff; background: var(--tone, var(--none)); }
.lang { color: var(--muted); }
.acc { font: 700 12px ui-monospace, Consolas, monospace; }
.shelf { font-size: 11px; color: var(--muted); }

.skeleton li { display: grid; gap: 8px; padding: 18px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); }
.skeleton i { display: block; height: 12px; border-radius: 6px; background: linear-gradient(90deg, var(--soft), var(--line), var(--soft)); background-size: 200% 100%; animation: shimmer 1.2s infinite linear; }
.skeleton i:nth-child(1) { width: 55%; height: 16px; } .skeleton i:nth-child(2) { width: 35%; } .skeleton i:nth-child(3) { width: 20%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

.empty { display: grid; justify-items: center; gap: 10px; text-align: center; padding: 60px 20px; border: 2px dashed var(--line); border-radius: 14px; }
.empty-mark { font-size: 38px; color: var(--brass); }
.empty h2 { margin: 0; font: 400 24px Georgia, serif; }
.empty p { margin: 0 0 8px; color: var(--muted); max-width: 380px; }

.pager { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px; margin-top: 22px; }
.num { min-width: 38px; height: 38px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); cursor: pointer; font-weight: 600; }
.num.on { background: var(--forest); color: var(--forest-ink); border-color: var(--forest); }
.num:disabled { cursor: not-allowed; }
.gap { padding: 0 4px; color: var(--muted); }

/* ===== catalogue card preview ===== */
.card-pane { position: sticky; top: 14px; max-height: calc(100vh - 130px); overflow-y: auto; padding-bottom: 24px; }
.index-card { position: relative; padding: 46px 26px 22px; background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--tone, var(--forest)); border-radius: 4px 4px 14px 14px; box-shadow: 0 10px 0 -4px var(--soft), 0 18px 30px -10px rgba(0, 0, 0, .25); background-image: repeating-linear-gradient(to bottom, transparent 0 31px, color-mix(in srgb, var(--line) 55%, transparent) 31px 32px); background-position: 0 150px; background-repeat: repeat-y; }
.card-tab { position: absolute; top: -1px; left: 22px; padding: 6px 14px; background: var(--tone, var(--forest)); color: #fff; font: 700 12px ui-monospace, Consolas, monospace; letter-spacing: .06em; border-radius: 0 0 9px 9px; max-width: calc(100% - 44px); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-kicker { margin: 0 0 8px; font-size: 11px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--tone, var(--forest)); }
.card-title { margin: 0; font: 400 24px/1.3 var(--serif); overflow-wrap: anywhere; color: var(--ink); }
.card-author { margin: 8px 0 0; font-size: 15px; color: var(--muted); font-style: italic; }
.card-rule { height: 2px; margin: 18px 0 10px; background: #c0392b; opacity: .75; }
.card-facts { display: grid; grid-template-columns: 118px minmax(0, 1fr); margin: 0; font-size: 13px; }
.card-facts dt { padding: 5px 0; color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.card-facts dd { margin: 0; padding: 4px 0; overflow-wrap: anywhere; }
.card-facts dd.mono { font: 600 13px ui-monospace, Consolas, monospace; }
.card-notes { margin-top: 14px; padding: 10px 12px; background: var(--soft); border-radius: 8px; font-size: 13px; }
.card-notes b { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.card-notes p { margin: 4px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.card-actions { display: grid; gap: 8px; margin-top: 18px; }
.card-record { margin: 14px 0 0; text-align: right; font: 11px ui-monospace, Consolas, monospace; color: var(--muted); }
.card-empty { padding: 40px 24px; text-align: center; border: 2px dashed var(--line); border-radius: 14px; color: var(--muted); }

/* ===== responsive ===== */
@media (max-width: 1199px) {
  .cat-body { grid-template-columns: 250px minmax(0, 1fr); }
  .card-pane { display: none; }
}
@media (max-width: 820px) {
  .cat-body { grid-template-columns: 1fr; }
  .rail { position: static; display: none; }
  .filters-open .rail { display: grid; }
  .filters-toggle { display: inline-block; }
  .row { grid-template-columns: 6px minmax(0, 1fr); padding: 14px 14px 14px 0; }
  .side { grid-column: 2; justify-items: start; grid-auto-flow: column; justify-content: start; gap: 12px; align-items: center; }
}
@media (prefers-reduced-motion: reduce) {
  .row, .btn, .list, .chip { transition: none; }
  .skeleton i { animation: none; }
}
</style>
