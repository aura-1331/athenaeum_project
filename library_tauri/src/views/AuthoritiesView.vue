<template>
  <div class="authority-page">

    <!-- =========================================================
         HEADER
    ========================================================== -->
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


    <!-- =========================================================
         METRICS
    ========================================================== -->
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


    <!-- =========================================================
         TOOLBAR
    ========================================================== -->
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
          :class="{ active: statusFilter === filter.value }"
          @click="statusFilter = filter.value"
        >
          {{ filter.label }}
        </button>

      </div>

    </section>


    <!-- =========================================================
         ERROR
    ========================================================== -->
    <div v-if="errorMessage" class="error-banner">
      <div>
        <strong>REQUEST FAILED</strong>
        <span>{{ errorMessage }}</span>
      </div>

      <button type="button" @click="fetchAuthorities">
        RETRY
      </button>
    </div>


    <!-- =========================================================
         LOADING
    ========================================================== -->
    <div v-if="loading" class="state-panel">
      <div class="state-code">LOADING</div>
      <div class="state-text">Loading authority registry...</div>
    </div>


    <!-- =========================================================
         EMPTY
    ========================================================== -->
    <div
      v-else-if="!filteredAuthorities.length"
      class="state-panel"
    >
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


    <!-- =========================================================
         TABLE
    ========================================================== -->
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


    <!-- =========================================================
         DETAIL DRAWER
    ========================================================== -->
    <div
      v-if="selectedAuthority"
      class="drawer-backdrop"
      @click.self="closeAuthority"
    >

      <aside class="detail-drawer">

        <div class="drawer-header">

          <div>
            <div class="eyebrow">AUTHORITY RECORD</div>

            <h2>
              {{ selectedAuthority.preferred_name }}
            </h2>

            <div class="drawer-code">
              {{ selectedAuthority.authority_code }}
            </div>
          </div>

          <button
            type="button"
            class="close-button"
            @click="closeAuthority"
          >
            ×
          </button>

        </div>


        <!-- BASIC DETAILS -->
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
              <strong>
                {{ formatDate(selectedAuthority.created_at) }}
              </strong>
            </div>

          </div>

        </section>


        <!-- NOTES -->
        <section
          v-if="selectedAuthority.notes"
          class="detail-section"
        >

          <div class="section-title">NOTES</div>

          <div class="notes">
            {{ selectedAuthority.notes }}
          </div>

        </section>


        <!-- VARIANTS -->
        <section class="detail-section">

          <div class="section-title">
            VARIANT NAMES
          </div>

          <div
            v-if="selectedAuthority.variants?.length"
            class="variant-list"
          >

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


        <!-- CONNECTED WORKS -->
        <section class="detail-section">

          <div class="section-title">
            CONNECTED WORKS
          </div>

          <div
            v-if="selectedAuthority.works?.length"
            class="works-list"
          >

            <div
              v-for="work in selectedAuthority.works"
              :key="`${work.work_id}-${work.sequence_no}`"
              class="work-row"
            >

              <div class="work-id">
                {{ work.work_id }}
              </div>

              <div class="work-info">
                <strong>
                  {{ work.title || 'Untitled work' }}
                </strong>

                <span>
                  {{ work.relationship_type }}
                </span>
              </div>

            </div>

          </div>

          <div v-else class="muted">
            No works connected to this authority.
          </div>

        </section>


        <!-- VERIFICATION INFO -->
        <section
          v-if="selectedAuthority.verified_at"
          class="detail-section"
        >

          <div class="section-title">
            VERIFICATION
          </div>

          <div class="verification-info">

            <div>
              <span>VERIFIED AT</span>
              <strong>
                {{ formatDate(selectedAuthority.verified_at) }}
              </strong>
            </div>

            <div>
              <span>VERIFIED BY</span>
              <strong>
                {{ selectedAuthority.verified_by }}
              </strong>
            </div>

          </div>

        </section>


        <!-- ACTIONS -->
        <section class="drawer-actions">

          <div
            v-if="actionMessage"
            class="action-message"
            :class="{ failure: actionFailed }"
          >
            {{ actionMessage }}
          </div>


          <!-- PROVISIONAL -->
          <template v-if="selectedAuthority.status === 'PROVISIONAL'">

            <button
              type="button"
              class="action-button verify"
              :disabled="actionLoading"
              @click="verifyAuthority"
            >
              <span v-if="actionLoading && actionType === 'VERIFY'">
                VERIFYING...
              </span>

              <span v-else>
                VERIFY AUTHORITY
              </span>
            </button>


            <button
              type="button"
              class="action-button reject"
              :disabled="actionLoading"
              @click="rejectAuthority"
            >
              <span v-if="actionLoading && actionType === 'REJECT'">
                REJECTING...
              </span>

              <span v-else>
                REJECT AUTHORITY
              </span>
            </button>

          </template>


          <!-- VERIFIED -->
          <div
            v-else-if="selectedAuthority.status === 'VERIFIED'"
            class="status-message verified-message"
          >
            This authority has been verified.
          </div>


          <!-- REJECTED -->
          <div
            v-else-if="selectedAuthority.status === 'REJECTED'"
            class="status-message rejected-message"
          >
            This authority has been rejected.
          </div>


          <!-- OTHER -->
          <div
            v-else
            class="status-message"
          >
            No actions are available for this authority.
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

    if (!matchesStatus) {
      return false
    }

    if (!query) {
      return true
    }

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
    return auth?.accessToken || null
  } catch (error) {
    console.error('Unable to read authentication state:', error)
    return null
  }
}

async function apiRequest(path, options = {}) {
  const token = getAccessToken()

  if (!token) {
    throw new Error('Authentication token is missing.')
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
    const message =
      body?.detail ||
      body?.message ||
      `Request failed with status ${response.status}`

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
    console.error('Authority registry error:', error)
    errorMessage.value = error.message || 'Unable to load authorities.'
  } finally {
    loading.value = false
  }
}

async function openAuthority(authority) {
  selectedAuthority.value = {
    ...authority,
    variants: [],
    works: []
  }

  actionMessage.value = ''
  actionFailed.value = false

  try {
    const detail = await apiRequest(`/authority/${authority.authority_id}`)
    selectedAuthority.value = detail
  } catch (error) {
    console.error('Authority detail error:', error)
    actionFailed.value = true
    actionMessage.value = error.message || 'Unable to load authority details.'
  }
}

function closeAuthority() {
  if (actionLoading.value) {
    return
  }
  selectedAuthority.value = null
  actionMessage.value = ''
  actionFailed.value = false
}

async function verifyAuthority() {
  if (!selectedAuthority.value || selectedAuthority.value.status !== 'PROVISIONAL') {
    return
  }

  const confirmed = window.confirm(
    `Verify authority "${selectedAuthority.value.preferred_name}"?`
  )
  if (!confirmed) return

  actionLoading.value = true
  actionType.value = 'VERIFY'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(
      `/authority/${selectedAuthority.value.authority_id}/verify`,
      { method: 'PATCH' }
    )

    if (data?.authority) {
      selectedAuthority.value = {
        ...selectedAuthority.value,
        ...data.authority
      }
    }

    actionMessage.value = data?.message || 'Authority verified successfully.'
    await fetchAuthorities()
  } catch (error) {
    console.error('Authority verification error:', error)
    actionFailed.value = true
    actionMessage.value = error.message || 'Unable to verify authority.'
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

async function rejectAuthority() {
  if (!selectedAuthority.value || selectedAuthority.value.status !== 'PROVISIONAL') {
    return
  }

  const confirmed = window.confirm(
    `Reject authority "${selectedAuthority.value.preferred_name}"?`
  )
  if (!confirmed) return

  actionLoading.value = true
  actionType.value = 'REJECT'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(
      `/authority/${selectedAuthority.value.authority_id}/reject`,
      { method: 'PATCH' }
    )

    if (data?.authority) {
      selectedAuthority.value = {
        ...selectedAuthority.value,
        ...data.authority
      }
    }

    actionMessage.value = data?.message || 'Authority rejected successfully.'
    await fetchAuthorities()
  } catch (error) {
    console.error('Authority rejection error:', error)
    actionFailed.value = true
    actionMessage.value = error.message || 'Unable to reject authority.'
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
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

onMounted(() => {
  fetchAuthorities()
})
</script>


<style scoped>
/* ============================================================
   DESIGN TOKENS (LIGHT DEFAULT / ADAPTIVE)
============================================================ */
.authority-page {
  --page-fg: #181b20;
  --page-fg-subtle: #4b5563;
  --page-fg-muted: #6b7280;
  --page-border: rgba(24, 27, 32, 0.16);
  --page-border-subtle: rgba(24, 27, 32, 0.08);
  --page-surface: rgba(24, 27, 32, 0.025);
  --page-surface-hover: rgba(24, 27, 32, 0.06);

  --drawer-bg: #fbfbfb;
  --drawer-fg: #181b20;
  --drawer-border: rgba(24, 27, 32, 0.15);
  --drawer-backdrop: rgba(15, 18, 22, 0.45);

  --status-provisional-fg: #854d0e;
  --status-provisional-bg: #fef9c3;
  --status-provisional-border: #fde047;

  --status-verified-fg: #166534;
  --status-verified-bg: #dcfce7;
  --status-verified-border: #86efac;

  --status-rejected-fg: #991b1b;
  --status-rejected-bg: #fee2e2;
  --status-rejected-border: #fca5a5;

  min-height: 100%;
  padding: 34px 40px 60px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  color: var(--page-fg);
}

/* Dark Mode Tokens */
:global(html.dark) .authority-page,
:global(body.dark) .authority-page,
:global(.dark) .authority-page,
:global([data-theme="dark"]) .authority-page {
  --page-fg: #f4f4f5;
  --page-fg-subtle: #a1a1aa;
  --page-fg-muted: #71717a;
  --page-border: rgba(255, 255, 255, 0.12);
  --page-border-subtle: rgba(255, 255, 255, 0.06);
  --page-surface: rgba(255, 255, 255, 0.03);
  --page-surface-hover: rgba(255, 255, 255, 0.07);

  --drawer-bg: #141416;
  --drawer-fg: #f4f4f5;
  --drawer-border: rgba(255, 255, 255, 0.12);
  --drawer-backdrop: rgba(0, 0, 0, 0.7);

  --status-provisional-fg: #fde047;
  --status-provisional-bg: rgba(234, 179, 8, 0.15);
  --status-provisional-border: rgba(234, 179, 8, 0.4);

  --status-verified-fg: #86efac;
  --status-verified-bg: rgba(34, 197, 94, 0.15);
  --status-verified-border: rgba(34, 197, 94, 0.4);

  --status-rejected-fg: #fca5a5;
  --status-rejected-bg: rgba(239, 68, 68, 0.15);
  --status-rejected-border: rgba(239, 68, 68, 0.4);
}


/* ============================================================
   HEADER
============================================================ */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.16em;
  color: var(--page-fg-muted);
  margin-bottom: 10px;
}

.page-header h1 {
  margin: 0;
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 10px 0 0;
  font-size: 14px;
  color: var(--page-fg-subtle);
  line-height: 1.5;
}

.header-meta {
  text-align: right;
}

.meta-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--page-fg-muted);
  letter-spacing: 0.14em;
}

.meta-value {
  margin-top: 6px;
  font-size: 26px;
  font-weight: 600;
}


/* ============================================================
   METRICS
============================================================ */
.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin-bottom: 28px;
  border: 1px solid var(--page-border);
  background: var(--page-border-subtle);
}

.metric-card {
  padding: 22px;
  min-height: 100px;
  background: var(--page-surface);
}

.metric-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--page-fg-muted);
}

.metric-value {
  margin-top: 10px;
  font-size: 30px;
  font-weight: 600;
}


/* ============================================================
   TOOLBAR
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
  border: 1px solid var(--page-border);
  background: var(--page-surface);
}

.search-icon {
  padding-left: 16px;
  color: var(--page-fg-muted);
  font-size: 20px;
}

.search-box input {
  width: 100%;
  padding: 13px 42px 13px 12px;
  border: none;
  outline: none;
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: 14px;
}

.clear-search {
  position: absolute;
  right: 12px;
  border: none;
  background: transparent;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.filters {
  display: flex;
  gap: 6px;
}

.filter-button {
  padding: 12px 16px;
  border: 1px solid var(--page-border);
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  opacity: 0.75;
}

.filter-button:hover {
  opacity: 1;
  background: var(--page-surface-hover);
}

.filter-button.active {
  opacity: 1;
  background: var(--page-surface-hover);
  border-color: var(--page-fg-subtle);
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
  border: 1px solid rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
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
  border: 1px solid var(--page-border);
  background: transparent;
  color: inherit;
  padding: 10px 16px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.state-panel {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 1px solid var(--page-border);
}

.state-code {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.16em;
  color: var(--page-fg-muted);
}

.state-text {
  margin-top: 10px;
  font-size: 14px;
  color: var(--page-fg-subtle);
}


/* ============================================================
   TABLE
============================================================ */
.registry-panel {
  border: 1px solid var(--page-border);
}

.table-head,
.authority-row {
  display: grid;
  grid-template-columns: 190px minmax(260px, 1fr) 140px 140px 80px;
  align-items: center;
}

.table-head {
  min-height: 44px;
  padding: 0 20px;
  border-bottom: 1px solid var(--page-border);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--page-fg-muted);
}

.authority-row {
  min-height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid var(--page-border-subtle);
  cursor: pointer;
  transition: background 0.15s ease;
}

.authority-row:last-child {
  border-bottom: none;
}

.authority-row:hover {
  background: var(--page-surface-hover);
}

.authority-code {
  font-size: 13px;
  font-weight: 500;
  color: var(--page-fg-subtle);
}

.authority-name {
  font-size: 15px;
  font-weight: 500;
}

.authority-type {
  font-size: 13px;
  color: var(--page-fg-muted);
}

.row-action {
  text-align: right;
  font-size: 12px;
  font-weight: 600;
  color: var(--page-fg-muted);
}

.authority-row:hover .row-action {
  color: var(--page-fg);
}


/* ============================================================
   STATUS BADGES
============================================================ */
.status-badge {
  display: inline-block;
  padding: 5px 9px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  border: 1px solid transparent;
  border-radius: 2px;
}

.status-badge.provisional {
  color: var(--status-provisional-fg);
  background: var(--status-provisional-bg);
  border-color: var(--status-provisional-border);
}

.status-badge.verified {
  color: var(--status-verified-fg);
  background: var(--status-verified-bg);
  border-color: var(--status-verified-border);
}

.status-badge.rejected {
  color: var(--status-rejected-fg);
  background: var(--status-rejected-bg);
  border-color: var(--status-rejected-border);
}


/* ============================================================
   DETAIL DRAWER
============================================================ */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  background: var(--drawer-backdrop);
}

.detail-drawer {
  width: min(640px, 94vw);
  height: 100%;
  overflow-y: auto;
  padding: 34px;
  background: var(--drawer-bg);
  color: var(--drawer-fg);
  border-left: 1px solid var(--drawer-border);
  box-shadow: -20px 0 50px rgba(0, 0, 0, 0.25);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--drawer-border);
}

.drawer-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  line-height: 1.35;
}

.drawer-code {
  margin-top: 8px;
  font-size: 13px;
  color: var(--page-fg-muted);
}

.close-button {
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border: 1px solid var(--drawer-border);
  background: transparent;
  color: inherit;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.close-button:hover {
  background: var(--page-surface-hover);
}

.detail-section {
  padding: 24px 0;
  border-bottom: 1px solid var(--drawer-border);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-item span,
.verification-info span,
.section-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--page-fg-muted);
}

.detail-item strong,
.verification-info strong {
  font-size: 14px;
  font-weight: 500;
}

.section-title {
  margin-bottom: 14px;
}

.notes {
  font-size: 14px;
  line-height: 1.7;
  color: var(--page-fg-subtle);
}

.muted {
  font-size: 13px;
  color: var(--page-fg-muted);
}

.variant-list,
.works-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.variant-row,
.work-row {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  background: var(--page-surface);
}

.variant-row {
  justify-content: space-between;
}

.variant-row span {
  font-size: 14px;
}

.variant-row small {
  font-size: 12px;
  color: var(--page-fg-muted);
}

.work-row {
  gap: 16px;
}

.work-id {
  width: 54px;
  font-size: 12px;
  font-weight: 500;
  color: var(--page-fg-muted);
}

.work-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.work-info strong {
  font-size: 14px;
  font-weight: 500;
}

.work-info span {
  font-size: 12px;
  color: var(--page-fg-muted);
}

.verification-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}

.verification-info div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.drawer-actions {
  padding: 26px 0 40px;
}

.action-message {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--drawer-border);
  font-size: 13px;
  line-height: 1.5;
}

.action-message.failure {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.08);
}

.action-button {
  width: 100%;
  min-height: 46px;
  margin-bottom: 10px;
  border: 1px solid var(--drawer-border);
  background: var(--page-surface);
  color: inherit;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 0.15s ease;
}

.action-button:hover:not(:disabled) {
  background: var(--page-surface-hover);
}

.action-button:disabled {
  cursor: wait;
  opacity: 0.45;
}

.action-button.verify {
  border-color: var(--status-verified-border);
  color: var(--status-verified-fg);
  background: var(--status-verified-bg);
}

.action-button.reject {
  border-color: var(--status-rejected-border);
  color: var(--status-rejected-fg);
  background: var(--status-rejected-bg);
}

.status-message {
  padding: 16px;
  border: 1px solid var(--drawer-border);
  font-size: 13px;
  color: var(--page-fg-subtle);
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

  .filters {
    overflow-x: auto;
  }

  .table-head,
  .authority-row {
    grid-template-columns: 150px minmax(200px, 1fr) 110px 120px 65px;
  }
}

@media (max-width: 650px) {
  .page-header {
    flex-direction: column;
    gap: 15px;
  }

  .header-meta {
    text-align: left;
  }

  .metrics {
    grid-template-columns: 1fr 1fr;
  }

  .table-head {
    display: none;
  }

  .authority-row {
    grid-template-columns: 1fr auto;
    gap: 8px;
    padding: 16px;
  }

  .authority-code,
  .authority-name,
  .authority-type {
    grid-column: 1;
  }

  .authority-row > div:nth-child(4) {
    grid-column: 2;
    grid-row: 1 / span 2;
  }

  .row-action {
    display: none;
  }

  .detail-drawer {
    width: 100%;
    padding: 24px;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>