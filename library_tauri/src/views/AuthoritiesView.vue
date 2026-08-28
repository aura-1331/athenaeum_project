<template>
  <div class="authority-page">

    <!-- HEADER -->
    <header class="page-header">
      <div>
        <div class="eyebrow">CLASSIFICATION // REGISTRY</div>
        <h1>Authorities</h1>
        <p class="subtitle">
          Controlled authority records and verification status across the catalogue.
        </p>
      </div>

      <div class="header-meta">
        <div class="meta-label">REGISTRY</div>
        <div class="meta-value">{{ filteredAuthorities.length }}</div>
      </div>
    </header>

    <!-- METRICS -->
    <section class="metrics">
      <div class="metric-card">
        <div class="metric-label">TOTAL AUTHORITIES</div>
        <div class="metric-value">{{ authorities.length }}</div>
      </div>

      <div class="metric-card provisional">
        <div class="metric-label">PROVISIONAL</div>
        <div class="metric-value">{{ provisionalCount }}</div>
      </div>

      <div class="metric-card verified">
        <div class="metric-label">VERIFIED</div>
        <div class="metric-value">{{ verifiedCount }}</div>
      </div>

      <div class="metric-card rejected">
        <div class="metric-label">REJECTED</div>
        <div class="metric-value">{{ rejectedCount }}</div>
      </div>
    </section>

    <!-- TOOLBAR -->
    <section class="toolbar">
      <div class="search-box">
        <span class="search-icon">⌕</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search authority code or preferred name..."
        />
        <button
          v-if="searchQuery"
          class="clear-search"
          type="button"
          @click="searchQuery = ''"
        >
          ×
        </button>
      </div>

      <div class="filters">
  <button
    v-for="filter in filters"
    :key="filter.value"
    type="button"
    class="filter-button"
    :class="[statusClass(filter.value) || 'all', { active: statusFilter === filter.value }]"
    @click="statusFilter = filter.value"
  >
    {{ filter.label }}
  </button>
</div>
    </section>

    <!-- ERROR -->
    <div v-if="errorMessage" class="error-banner">
      <div>
        <strong>REQUEST FAILED</strong>
        <span>{{ errorMessage }}</span>
      </div>
      <button type="button" @click="fetchAuthorities">
        RETRY
      </button>
    </div>

    <!-- LOADING -->
    <div v-if="loading" class="state-panel">
      <div class="state-code">LOADING</div>
      <div class="state-text">Loading authority registry...</div>
    </div>

    <!-- EMPTY -->
    <div v-else-if="!filteredAuthorities.length" class="state-panel">
      <div class="state-code">NO RECORDS</div>
      <div class="state-text">
        No authorities match the current search or filter.
      </div>
      <button
        v-if="searchQuery || statusFilter"
        type="button"
        class="reset-button"
        @click="resetFilters"
      >
        RESET FILTERS
      </button>
    </div>

    <!-- TABLE -->
    <section v-else class="registry-panel">
      <div class="table-head">
        <div>AUTHORITY CODE</div>
        <div>PREFERRED NAME</div>
        <div>TYPE</div>
        <div>STATUS</div>
        <div></div>
      </div>

      <div
        v-for="authority in filteredAuthorities"
        :key="authority.authority_id"
        class="authority-row"
        @click="openAuthority(authority)"
      >
        <div class="authority-code">
          {{ authority.authority_code }}
        </div>
        <div class="authority-name">
          {{ authority.preferred_name }}
        </div>
        <div class="authority-type">
          {{ authority.authority_type }}
        </div>
        <div>
          <span
            class="status-badge"
            :class="statusClass(authority.status)"
          >
            {{ authority.status }}
          </span>
        </div>
        <div class="row-action">
          VIEW →
        </div>
      </div>
    </section>

    <!-- DETAIL DRAWER -->
    <div
      v-if="selectedAuthority"
      class="drawer-backdrop"
      @click.self="closeAuthority"
    >
      <aside class="detail-drawer">
        <div class="drawer-header">
          <div>
            <div class="eyebrow">AUTHORITY RECORD</div>
            <h2>{{ selectedAuthority.preferred_name }}</h2>
            <div class="drawer-code">{{ selectedAuthority.authority_code }}</div>
          </div>
          <button type="button" class="close-button" @click="closeAuthority">
            ×
          </button>
        </div>

        <section class="detail-section">
          <div class="detail-grid">
            <div class="detail-item">
              <span>AUTHORITY ID</span>
              <strong>{{ selectedAuthority.authority_id }}</strong>
            </div>
            <div class="detail-item">
              <span>TYPE</span>
              <strong>{{ selectedAuthority.authority_type }}</strong>
            </div>
            <div class="detail-item">
              <span>STATUS</span>
              <strong>
                <span
                  class="status-badge"
                  :class="statusClass(selectedAuthority.status)"
                >
                  {{ selectedAuthority.status }}
                </span>
              </strong>
            </div>
            <div class="detail-item">
              <span>CREATED</span>
              <strong>{{ formatDate(selectedAuthority.created_at) }}</strong>
            </div>
          </div>
        </section>

        <section v-if="selectedAuthority.notes" class="detail-section">
          <div class="section-title">NOTES</div>
          <div class="notes">{{ selectedAuthority.notes }}</div>
        </section>

        <section class="detail-section">
          <div class="section-title">VARIANT NAMES</div>
          <div v-if="selectedAuthority.variants?.length" class="variant-list">
            <div
              v-for="variant in selectedAuthority.variants"
              :key="variant.variant_id"
              class="variant-row"
            >
              <span>{{ variant.variant_name }}</span>
              <small>{{ variant.variant_type }}</small>
            </div>
          </div>
          <div v-else class="muted">
            No variant names recorded.
          </div>
        </section>

        <section class="detail-section">
          <div class="section-title">CONNECTED WORKS</div>
          <div v-if="selectedAuthority.works?.length" class="works-list">
            <div
              v-for="work in selectedAuthority.works"
              :key="`${work.work_id}-${work.sequence_no}`"
              class="work-row"
            >
              <div class="work-id">{{ work.work_id }}</div>
              <div class="work-info">
                <strong>{{ work.title || 'Untitled work' }}</strong>
                <span>{{ work.relationship_type }}</span>
              </div>
            </div>
          </div>
          <div v-else class="muted">
            No works connected to this authority.
          </div>
        </section>

        <section v-if="selectedAuthority.verified_at" class="detail-section">
          <div class="section-title">VERIFICATION</div>
          <div class="verification-info">
            <div>
              <span>VERIFIED AT</span>
              <strong>{{ formatDate(selectedAuthority.verified_at) }}</strong>
            </div>
            <div>
              <span>VERIFIED BY</span>
              <strong>{{ selectedAuthority.verified_by }}</strong>
            </div>
          </div>
        </section>

        <section class="drawer-actions">
          <div
            v-if="actionMessage"
            class="action-message"
            :class="{ failure: actionFailed }"
          >
            {{ actionMessage }}
          </div>

          <template v-if="selectedAuthority.status === 'PROVISIONAL'">
            <button
              type="button"
              class="action-button verify"
              :disabled="actionLoading"
              @click="verifyAuthority"
            >
              <span v-if="actionLoading && actionType === 'VERIFY'">VERIFYING...</span>
              <span v-else>VERIFY AUTHORITY</span>
            </button>
            <button
              type="button"
              class="action-button reject"
              :disabled="actionLoading"
              @click="rejectAuthority"
            >
              <span v-if="actionLoading && actionType === 'REJECT'">REJECTING...</span>
              <span v-else>REJECT AUTHORITY</span>
            </button>
          </template>

          <div
            v-else-if="selectedAuthority.status === 'VERIFIED'"
            class="status-message"
          >
            This authority has been verified.
          </div>
          <div
            v-else-if="selectedAuthority.status === 'REJECTED'"
            class="status-message"
          >
            This authority has been rejected.
          </div>
        </section>
      </aside>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const API_BASE = 'http://127.0.0.1:8000'

const authorities = ref([])
const loading = ref(false)
const errorMessage = ref('')
const searchQuery = ref('')
const statusFilter = ref('')
const selectedAuthority = ref(null)

const actionLoading = ref(false)
const actionType = ref('')
const actionMessage = ref('')
const actionFailed = ref(false)

const filters = [
  { label: 'ALL', value: '' },
  { label: 'PROVISIONAL', value: 'PROVISIONAL' },
  { label: 'VERIFIED', value: 'VERIFIED' },
  { label: 'REJECTED', value: 'REJECTED' }
]

const provisionalCount = computed(() =>
  authorities.value.filter(item => item.status === 'PROVISIONAL').length
)

const verifiedCount = computed(() =>
  authorities.value.filter(item => item.status === 'VERIFIED').length
)

const rejectedCount = computed(() =>
  authorities.value.filter(item => item.status === 'REJECTED').length
)

const filteredAuthorities = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return authorities.value.filter(authority => {
    const matchesStatus =
      !statusFilter.value ||
      authority.status === statusFilter.value

    if (!matchesStatus) return false
    if (!query) return true

    return (
      String(authority.authority_code || '').toLowerCase().includes(query) ||
      String(authority.preferred_name || '').toLowerCase().includes(query) ||
      String(authority.authority_type || '').toLowerCase().includes(query)
    )
  })
})

function getAccessToken() {
  try {
    const auth = JSON.parse(localStorage.getItem('auth'))
    return auth?.accessToken || auth?.token || null
  } catch (error) {
    console.error('Auth state read error:', error)
    return null
  }
}

async function apiRequest(path, options = {}) {
  const token = getAccessToken()

  if (!token) {
    throw new Error('Please log in again.')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  })

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    const message = body?.detail || body?.message || `Request failed with status ${response.status}`
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  return body
}

async function fetchAuthorities() {
  loading.value = true
  errorMessage.value = ''

  try {
    const data = await apiRequest('/authority/')
    authorities.value = Array.isArray(data?.data) ? data.data : []
  } catch (error) {
    errorMessage.value = error.message || 'Unable to load authorities.'
  } finally {
    loading.value = false
  }
}

async function openAuthority(authority) {
  selectedAuthority.value = { ...authority, variants: [], works: [] }
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const detail = await apiRequest(`/authority/${authority.authority_id}`)
    selectedAuthority.value = detail
  } catch (error) {
    actionFailed.value = true
    actionMessage.value = error.message || 'Unable to load authority details.'
  }
}

function closeAuthority() {
  if (actionLoading.value) return
  selectedAuthority.value = null
  actionMessage.value = ''
  actionFailed.value = false
}

async function verifyAuthority() {
  if (!selectedAuthority.value || selectedAuthority.value.status !== 'PROVISIONAL') return
  if (!window.confirm(`Verify authority "${selectedAuthority.value.preferred_name}"?`)) return

  actionLoading.value = true
  actionType.value = 'VERIFY'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(`/authority/${selectedAuthority.value.authority_id}/verify`, {
      method: 'PATCH'
    })
    if (data?.authority) selectedAuthority.value = { ...selectedAuthority.value, ...data.authority }
    actionMessage.value = data?.message || 'Authority verified.'
    await fetchAuthorities()
  } catch (error) {
    actionFailed.value = true
    actionMessage.value = error.message || 'Verification failed.'
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

async function rejectAuthority() {
  if (!selectedAuthority.value || selectedAuthority.value.status !== 'PROVISIONAL') return
  if (!window.confirm(`Reject authority "${selectedAuthority.value.preferred_name}"?`)) return

  actionLoading.value = true
  actionType.value = 'REJECT'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(`/authority/${selectedAuthority.value.authority_id}/reject`, {
      method: 'PATCH'
    })
    if (data?.authority) selectedAuthority.value = { ...selectedAuthority.value, ...data.authority }
    actionMessage.value = data?.message || 'Authority rejected.'
    await fetchAuthorities()
  } catch (error) {
    actionFailed.value = true
    actionMessage.value = error.message || 'Rejection failed.'
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

function resetFilters() {
  searchQuery.value = ''
  statusFilter.value = ''
}

function statusClass(status) {
  return String(status || '').toLowerCase().replace(/\s+/g, '-')
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

onMounted(() => {
  fetchAuthorities()
})
</script>

<style scoped>
/* ============================================================
   PAGE CONTAINER
============================================================ */
.authority-page {
  min-height: 100%;
  padding: 34px 40px 60px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--content-bg);
  box-sizing: border-box;
}

.authority-page * {
  box-sizing: border-box;
}


/* ============================================================
   HEADER
============================================================ */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.page-header h1 {
  margin: 0;
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.subtitle {
  margin: 10px 0 0;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.5;
}

.header-meta {
  text-align: right;
}

.meta-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--text-muted);
}

.meta-value {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}


/* ============================================================
   METRICS (COLOR-CODED)
============================================================ */
.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin-bottom: 28px;
  border: 1px solid var(--border-main);
  background: var(--border-main);
}

.metric-card {
  padding: 22px;
  min-height: 100px;
  background: var(--surface);
}

.metric-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-muted);
}

.metric-value {
  margin-top: 10px;
  font-size: 30px;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-card.provisional .metric-value {
  color: #f59e0b;
}

.metric-card.verified .metric-value {
  color: #22c55e;
}

.metric-card.rejected .metric-value {
  color: #ef4444;
}


/* ============================================================
   TOOLBAR & FILTER BUTTONS
============================================================ */
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.search-box {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  border: 1px solid var(--border-main);
  background: var(--surface);
}

.search-icon {
  padding-left: 16px;
  color: var(--text-muted);
  font-size: 20px;
}

.search-box input {
  width: 100%;
  padding: 13px 42px 13px 12px;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
}

.search-box input::placeholder {
  color: var(--text-muted);
  opacity: 0.7;
}

.clear-search {
  position: absolute;
  right: 12px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 20px;
}

.filters {
  display: flex;
  gap: 8px;
}

.filter-button {
  padding: 10px 16px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  color: var(--text-muted);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-button:hover {
  background: var(--hover-bg);
  color: var(--text-primary);
}

.filter-button.all.active {
  background: var(--active-bg);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 700;
}

.filter-button.provisional {
  color: #f59e0b;
}

.filter-button.provisional:hover,
.filter-button.provisional.active {
  background: rgba(245, 158, 11, 0.16);
  border-color: #f59e0b;
  color: #f59e0b;
  font-weight: 700;
}

.filter-button.verified {
  color: #22c55e;
}

.filter-button.verified:hover,
.filter-button.verified.active {
  background: rgba(34, 197, 94, 0.16);
  border-color: #22c55e;
  color: #22c55e;
  font-weight: 700;
}

.filter-button.rejected {
  color: #ef4444;
}

.filter-button.rejected:hover,
.filter-button.rejected.active {
  background: rgba(239, 68, 68, 0.16);
  border-color: #ef4444;
  color: #ef4444;
  font-weight: 700;
}


/* ============================================================
   ERROR & STATES
============================================================ */
.error-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  border: 1px solid rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.error-banner strong {
  font-size: 12px;
  letter-spacing: 0.12em;
}

.error-banner span {
  font-size: 14px;
  margin-top: 4px;
}

.error-banner button,
.reset-button {
  border: 1px solid var(--border-main);
  background: var(--surface);
  color: var(--text-primary);
  padding: 10px 16px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.reset-button:hover {
  background: var(--hover-bg);
  color: var(--accent);
}

.state-panel {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 1px solid var(--border-main);
  background: var(--surface);
}

.state-code {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--text-muted);
}

.state-text {
  margin-top: 10px;
  font-size: 14px;
  color: var(--text-muted);
}


/* ============================================================
   TABLE
============================================================ */
.registry-panel {
  border: 1px solid var(--border-main);
  background: var(--surface);
}

.table-head,
.authority-row {
  display: grid;
  grid-template-columns: 190px minmax(260px, 1fr) 140px 140px 80px;
  align-items: center;
}

.table-head {
  min-height: 46px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-main);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  background: var(--hover-bg);
}

.authority-row {
  min-height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-main);
  cursor: pointer;
  transition: background 0.15s ease;
}

.authority-row:last-child {
  border-bottom: none;
}

.authority-row:hover {
  background: var(--hover-bg);
}

.authority-code {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
}

.authority-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.authority-type {
  font-size: 13px;
  color: var(--text-muted);
}

.row-action {
  text-align: right;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.15s ease;
}

.authority-row:hover .row-action {
  color: var(--accent);
}


/* ============================================================
   STATUS BADGES
============================================================ */
.status-badge {
  display: inline-block;
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  border-radius: 2px;
}

.status-badge.provisional {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.16);
  border: 1px solid rgba(245, 158, 11, 0.45);
}

.status-badge.verified {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.16);
  border: 1px solid rgba(34, 197, 94, 0.45);
}

.status-badge.rejected {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.16);
  border: 1px solid rgba(239, 68, 68, 0.45);
}


/* ============================================================
   DETAIL DRAWER (USES APP THEME TOKENS)
============================================================ */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
}

.detail-drawer {
  width: min(640px, 94vw);
  height: 100%;
  overflow-y: auto;
  padding: 34px;
  background: var(--content-bg);
  color: var(--text-primary);
  border-left: 1px solid var(--border-main);
  box-shadow: -20px 0 50px rgba(0, 0, 0, 0.4);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-main);
}

.drawer-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
}

.drawer-code {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.close-button {
  width: 38px;
  height: 38px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  color: var(--text-primary);
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  background: var(--hover-bg);
  color: var(--accent);
}

.detail-section {
  padding: 24px 0;
  border-bottom: 1px solid var(--border-main);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.detail-item span,
.verification-info span,
.section-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-muted);
}

.detail-item strong,
.verification-info strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.notes {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  opacity: 0.9;
}

.muted {
  font-size: 13px;
  color: var(--text-muted);
}

.variant-row,
.work-row {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--border-main);
  margin-bottom: 6px;
}

.variant-row {
  justify-content: space-between;
}

.variant-row span,
.work-info strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.variant-row small,
.work-id,
.work-info span {
  font-size: 12px;
  color: var(--text-muted);
}

.work-row {
  gap: 16px;
}

.verification-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}

.drawer-actions {
  padding: 26px 0 40px;
}

.action-message {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  font-size: 13px;
  color: var(--text-primary);
}

.action-message.failure {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.action-button {
  width: 100%;
  min-height: 46px;
  margin-bottom: 10px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-button:hover:not(:disabled) {
  opacity: 0.85;
}

.action-button.verify {
  border-color: rgba(34, 197, 94, 0.5);
  color: #22c55e;
  background: rgba(34, 197, 94, 0.12);
}

.action-button.reject {
  border-color: rgba(239, 68, 68, 0.5);
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
}

.status-message {
  padding: 16px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  font-size: 13px;
  color: var(--text-muted);
}


/* ============================================================
   RESPONSIVE
============================================================ */
@media (max-width: 900px) {
  .authority-page {
    padding: 25px 20px 50px;
  }
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .table-head,
  .authority-row {
    grid-template-columns: 150px minmax(200px, 1fr) 110px 120px 65px;
  }
}
</style>