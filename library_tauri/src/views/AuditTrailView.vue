<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'
import LedgerIntegrityBadge from '@/components/LedgerIntegrityBadge.vue'

import { API_BASE } from '@/config'

const authStore = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')
const logs = ref([])
const totalLogs = ref(0)
const totalEvents = ref(0)

const searchQuery = ref('')
const selectedAction = ref('')
const selectedOutcome = ref('')
const selectedCategory = ref('')
const selectedPeriod = ref('all')
const currentPage = ref(1)
const pageLimit = ref(25)

const expandedRows = ref(new Set())
const rawViews = ref(new Set())
const selectedEvent = ref(null)

const groupEvents = ref({})
const groupLoading = ref(new Set())
const groupErrors = ref({})

const activeTab = ref('all')
const mobileInspectorOpen = ref(false)

const autoRefreshEnabled = ref(false)
let autoRefreshTimer = null
const searchInputRef = ref(null)

let debounceTimer = null
let requestController = null

const baseUrl = API_BASE

const maxPages = computed(() =>
  Math.max(1, Math.ceil(totalLogs.value / pageLimit.value))
)

const visibleFailureCount = computed(() =>
  logs.value.filter(log => isFailure(log)).length
)

const visibleSecurityCount = computed(() =>
  logs.value.filter(log => isSecurityAction(log.action_type)).length
)

const rangeStart = computed(() =>
  totalLogs.value === 0 ? 0 : (currentPage.value - 1) * pageLimit.value + 1
)

const rangeEnd = computed(() =>
  Math.min(currentPage.value * pageLimit.value, totalLogs.value)
)

const selectedOutcomeLabel = computed(() => {
  if (!selectedEvent.value) return '—'
  return getOutcome(selectedEvent.value) || 'Not recorded'
})

const selectedMetadata = computed(() => {
  const event = selectedEvent.value
  return event?.extra_metadata || {}
})

function getToken() {
  return authStore.accessToken || ''
}

function authHeaders() {
  const token = getToken()
  return {
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  }
}

async function apiGet(path, signal) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'GET',
    headers: authHeaders(),
    signal
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Request failed (${response.status})`)
  }

  return response.json()
}

function buildLogUrl() {
  const params = new URLSearchParams({
    limit: String(pageLimit.value),
    offset: String((currentPage.value - 1) * pageLimit.value)
  })

  if (searchQuery.value.trim()) {
    params.set('actor_filter', searchQuery.value.trim())
  }

  if (selectedAction.value) {
    params.set('action_filter', selectedAction.value)
  }

  if (selectedOutcome.value) {
    params.set('outcome_filter', selectedOutcome.value)
  }

  if (selectedCategory.value) {
    params.set('category_filter', selectedCategory.value)
  }

  if (selectedPeriod.value !== 'all') {
    const now = Date.now()
    const durations = {
      hour: 60 * 60 * 1000,
      day: 24 * 60 * 60 * 1000,
      week: 7 * 24 * 60 * 60 * 1000
    }

    const duration = durations[selectedPeriod.value]

    if (duration) {
      params.set('from_timestamp', new Date(now - duration).toISOString())
      params.set('to_timestamp', new Date(now).toISOString())
    }
  }

  return `/status_audit/system-logs?${params.toString()}`
}

async function fetchLogs() {
  if (requestController) requestController.abort()

  requestController = new AbortController()
  loading.value = true
  errorMessage.value = ''

  try {
    const data = await apiGet(buildLogUrl(), requestController.signal)

    logs.value = Array.isArray(data.items) ? data.items : []
    totalLogs.value = Number(data.total ?? 0)
    totalEvents.value = Number(data.total_events ?? data.total ?? 0)

    if (selectedEvent.value) {
      const stillVisible = logs.value.some(
        log => log.id === selectedEvent.value.id
      )

      if (!stillVisible) {
        selectedEvent.value = null
      }
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('Failed to load audit records:', error)
      errorMessage.value = error.message || 'Unable to load audit records.'
      logs.value = []
      totalLogs.value = 0
      totalEvents.value = 0
    }
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  currentPage.value = 1
  expandedRows.value = new Set()
  groupEvents.value = {}
  groupErrors.value = {}
  fetchLogs()
}

function handleSearchDebounced() {
  clearTimeout(debounceTimer)

  debounceTimer = setTimeout(() => {
    applyFilters()
  }, 350)
}

function clearSearch() {
  searchQuery.value = ''
  applyFilters()
}

function setTab(tab) {
  activeTab.value = tab

  selectedAction.value = ''
  selectedCategory.value = ''
  selectedOutcome.value = ''

  if (tab === 'authentication') {
    selectedAction.value = 'TOKEN_REFRESH'
  } else if (tab === 'ledger') {
    selectedAction.value = 'UPDATE_LEDGER'
  }

  applyFilters()
}

function changePage(page) {
  if (page < 1 || page > maxPages.value || loading.value) return

  currentPage.value = page
  expandedRows.value = new Set()
  groupEvents.value = {}
  groupErrors.value = {}
  selectedEvent.value = null

  fetchLogs()
}

function isGroup(log) {
  return log?.display_type === 'group'
}

function getOutcome(log) {
  if (!log) return ''

  const metadata = log.extra_metadata || {}
  const diffs = log.detailed_diffs || log.diff_payload || {}

  return String(
    log.outcome ??
    diffs.outcome ??
    metadata.status ??
    metadata.outcome ??
    ''
  ).toUpperCase()
}

function isFailure(log) {
  if (!log || isGroup(log)) return false

  const outcome = getOutcome(log)
  const action = String(log.action_type || '').toUpperCase()

  return (
    ['FAILED', 'FAILURE', 'ERROR', 'DENIED', 'REJECTED'].includes(outcome) ||
    action.includes('FAILED') ||
    action.includes('REJECT') ||
    action.includes('DENIED')
  )
}

function isSecurityAction(action) {
  const value = String(action || '').toUpperCase()

  return [
    'UPDATE_LEDGER',
    'AUTHORITY_REJECT',
    'USER_REVOKE',
    'PASSWORD_CHANGE',
    'LOGIN_FAILED',
    'RESOLVE_INCIDENT',
    'ITEM_REJECT',
    'DELETE',
    'REVOKE'
  ].some(term => value.includes(term))
}

function isCritical(log) {
  return isSecurityAction(log?.action_type) || isFailure(log)
}

function getActionBadgeClass(action) {
  const value = String(action || '').toUpperCase()

  if (value === 'TOKEN_REFRESH') return 'token'
  if (value.includes('FAILED') || value.includes('REJECT') || value.includes('REVOKE') || value.includes('DELETE')) return 'danger'
  if (value.includes('LEDGER')) return 'governance'
  if (value.includes('PASSWORD')) return 'warning'
  if (value.includes('LOGIN') || value.includes('LOGOUT')) return 'auth'
  if (value.includes('CREATE') || value.includes('INSERT')) return 'success'
  if (value.includes('UPDATE') || value.includes('MODIFY')) return 'update'

  return 'default'
}

function formatDate(raw, includeSeconds = true) {
  if (!raw) return '—'

  const date = new Date(raw)

  if (Number.isNaN(date.getTime())) return String(raw)

  try {
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...(includeSeconds ? { second: '2-digit' } : {}),
      hour12: false
    }).format(date)
  } catch {
    return String(raw)
  }
}

function formatRange(first, last) {
  if (!first) return 'Time range unavailable'
  if (!last || first === last) return formatDate(first)
  return `${formatDate(first)} – ${formatDate(last)}`
}

function displayActor(log) {
  return (
    log?.actor_username ||
    log?.username ||
    log?.user_id ||
    (isGroup(log) ? 'Grouped actor' : 'System process')
  )
}

function displayRole(log) {
  return log?.actor_role || log?.role || log?.designation || '—'
}

function displaySummary(log) {
  if (isGroup(log)) {
    return `Grouped successful token refreshes · ${log.event_count ?? 0} original events`
  }

  if (log?.summary) return log.summary

  const outcome = getOutcome(log)

  if (outcome === 'FAILED') {
    return log.error_type
      ? `Operation failed · ${log.error_type}`
      : 'Operation failed'
  }

  const action = String(log?.action_type || '').toUpperCase()
  if (action === 'LOGIN') return 'Authentication event recorded'
  if (action === 'TOKEN_REFRESH') return 'Token refresh event recorded'

  return log?.endpoint || log?.target_entity || 'Audit event recorded'
}

function displayTarget(log) {
  if (isGroup(log)) return 'Authentication service'
  return log?.target_id ? `#${log.target_id}` : log?.target_entity || 'Global'
}

function displaySequence(log) {
  if (isGroup(log)) {
    return log.first_sequence_id && log.last_sequence_id
      ? `#${log.first_sequence_id}–#${log.last_sequence_id}`
      : 'Grouped'
  }
  return log?.sequence_id != null ? `#${log.sequence_id}` : '—'
}

function displayEventId(log) {
  return log?.id ?? log?.sequence_id ?? '—'
}

function displayIp(log) {
  return log?.ip_address || 'Not recorded'
}

function displayDevice(log) {
  return log?.device_id || log?.machine_name || 'Not recorded'
}

function getJustification(log) {
  return log?.change_reason ||
    log?.justification ||
    log?.extra_metadata?.justification ||
    'No justification recorded'
}

function toggleSetValue(source, id) {
  const next = new Set(source.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  source.value = next
}

function selectEvent(log) {
  selectedEvent.value = log
  mobileInspectorOpen.value = true
}

async function toggleRow(log) {
  if (isGroup(log)) {
    await toggleGroup(log)
    return
  }

  toggleSetValue(expandedRows, log.id)
  selectEvent(log)
}

async function toggleGroup(group) {
  const id = group.id

  if (expandedRows.value.has(id)) {
    toggleSetValue(expandedRows, id)
    return
  }

  toggleSetValue(expandedRows, id)
  selectEvent(group)

  if (groupEvents.value[id]) return

  const groupStart = group.group_start
  const groupUserId = group.group_user_id

  if (!groupStart) {
    groupErrors.value = {
      ...groupErrors.value,
      [id]: 'The backend did not provide a group start time.'
    }
    return
  }

  groupLoading.value = new Set([...groupLoading.value, id])

  try {
    const params = new URLSearchParams({ group_start: groupStart })

    if (groupUserId != null) {
      params.set('group_user_id', String(groupUserId))
    }

    if (group.endpoint) {
      params.set('endpoint', group.endpoint)
    }

    const data = await apiGet(
      `/status_audit/system-logs/group-events?${params.toString()}`
    )

    groupEvents.value = {
      ...groupEvents.value,
      [id]: Array.isArray(data.items) ? data.items : []
    }
  } catch (error) {
    console.error('Failed to load original group events:', error)
    groupErrors.value = {
      ...groupErrors.value,
      [id]: error.message || 'Unable to load original events.'
    }
  } finally {
    const next = new Set(groupLoading.value)
    next.delete(id)
    groupLoading.value = next
  }
}

function toggleRawView(id) {
  toggleSetValue(rawViews, id)
}

function parseDiffs(rawDiffs) {
  if (!rawDiffs) return []

  let data = rawDiffs

  if (typeof data === 'string') {
    try {
      data = JSON.parse(data)
    } catch {
      return [{ field: 'Raw value', oldValue: '—', newValue: data }]
    }
  }

  if (Array.isArray(data)) {
    return data.map((item, index) => {
      if (item && typeof item === 'object') {
        return {
          field: item.field || item.key || `Change ${index + 1}`,
          oldValue: item.from ?? item.old ?? item.old_value ?? '—',
          newValue: item.to ?? item.new ?? item.new_value ?? item.value ?? '—'
        }
      }
      return { field: `Change ${index + 1}`, oldValue: '—', newValue: item }
    })
  }

  if (typeof data !== 'object') return []

  return Object.entries(data).map(([field, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const hasOld = 'from' in value || 'old' in value || 'old_value' in value
      const hasNew = 'to' in value || 'new' in value || 'new_value' in value

      if (hasOld || hasNew) {
        return {
          field,
          oldValue: value.from ?? value.old ?? value.old_value ?? '—',
          newValue: value.to ?? value.new ?? value.new_value ?? '—'
        }
      }
    }
    return { field, oldValue: '—', newValue: value }
  })
}

function jsonValue(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

async function copyToClipboard(value) {
  if (value === null || value === undefined || value === '') return
  try {
    await navigator.clipboard.writeText(String(value))
  } catch (error) {
    console.error('Clipboard copy failed:', error)
  }
}

function closeInspector() {
  mobileInspectorOpen.value = false
}

function exportCurrentView() {
  if (!logs.value.length) return
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(logs.value, null, 2))
  const downloadAnchor = document.createElement('a')
  downloadAnchor.setAttribute("href", dataStr)
  downloadAnchor.setAttribute("download", `audit_logs_page_${currentPage.value}.json`)
  document.body.appendChild(downloadAnchor)
  downloadAnchor.click()
  downloadAnchor.remove()
}

function toggleAutoRefresh() {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  if (autoRefreshEnabled.value) {
    autoRefreshTimer = setInterval(() => {
      if (!loading.value) fetchLogs()
    }, 15000)
  } else {
    clearInterval(autoRefreshTimer)
  }
}

function handleGlobalKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    searchInputRef.value?.focus()
  }
  if (e.key === 'Escape' && mobileInspectorOpen.value) {
    closeInspector()
  }
}

onMounted(() => {
  fetchLogs()
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  clearInterval(autoRefreshTimer)
  if (requestController) requestController.abort()
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<template>
  <div class="audit-console-view">
    <!-- Header -->
    <header class="view-header">
      <div class="header-titles">
        <div class="breadcrumb-trail">Security Command <span>/</span> Immutable Audit Ledger</div>
        <h1>System Audit &amp; Compliance</h1>
        <p>Real-time telemetry, cryptographic verification, and deep forensic event inspection.</p>
      </div>

      <div class="header-actions">
        <button class="action-btn poll-btn" type="button" :class="{ active: autoRefreshEnabled }" @click="toggleAutoRefresh" title="Toggle 15s auto-poll">
          <span>{{ autoRefreshEnabled ? '🟢 Auto-Sync On' : '⚪ Auto-Sync Off' }}</span>
        </button>

        <button class="action-btn export-btn" type="button" :disabled="!logs.length" @click="exportCurrentView" title="Export visible records">
          <span>⬇ Export JSON</span>
        </button>

        <div class="live-status-pill">
          <span class="pulse-dot"></span>
          <span>Live Feed Active</span>
        </div>
        <button class="action-btn refresh-btn" type="button" :disabled="loading" @click="fetchLogs">
          <span :class="{ spinning: loading }">↻</span>
          <span>Sync Feed</span>
        </button>
      </div>
    </header>

    <!-- Metrics Grid -->
    <section class="metrics-grid">
      <article class="metric-card">
        <div class="metric-top">
          <span class="metric-label">MATCHING EVENTS</span>
          <span class="metric-icon cyan">▤</span>
        </div>
        <div class="metric-value">{{ totalEvents.toLocaleString() }}</div>
        <div class="metric-foot">Original stream items matched</div>
        <div class="metric-bar cyan-bar"></div>
      </article>

      <article class="metric-card">
        <div class="metric-top">
          <span class="metric-label">FAILURES ON PAGE</span>
          <span class="metric-icon red">!</span>
        </div>
        <div class="metric-value">{{ visibleFailureCount }}</div>
        <div class="metric-foot">Detected errors or rejections</div>
        <div class="metric-bar red-bar"></div>
      </article>

      <article class="metric-card">
        <div class="metric-top">
          <span class="metric-label">SECURITY ACTIONS</span>
          <span class="metric-icon blue">⬡</span>
        </div>
        <div class="metric-value">{{ visibleSecurityCount }}</div>
        <div class="metric-foot">Governance &amp; state changes</div>
        <div class="metric-bar blue-bar"></div>
      </article>

      <article class="metric-card integrity-card">
        <div class="metric-top">
          <span class="metric-label">LEDGER CRYPTOGRAPHY</span>
          <span class="metric-icon violet">◇</span>
        </div>
        <div class="integrity-badge-wrap">
          <LedgerIntegrityBadge />
        </div>
      </article>
    </section>

    <!-- Workspace Grid -->
    <div class="workspace-grid">
      <section class="activity-panel">
        <div class="panel-heading">
          <div>
            <h2>Event Stream Matrix</h2>
            <p>Grouped token refreshes remain cryptographically chained to their primary source records.</p>
          </div>
          <div class="record-badge">
            <span>{{ totalLogs.toLocaleString() }}</span> records indexed
          </div>
        </div>

        <div class="tab-strip">
          <button type="button" :class="{ selected: activeTab === 'all' }" @click="setTab('all')">All Events</button>
          <button type="button" :class="{ selected: activeTab === 'security' }" @click="setTab('security')">Security Events</button>
          <button type="button" :class="{ selected: activeTab === 'authentication' }" @click="setTab('authentication')">Authentication</button>
          <button type="button" :class="{ selected: activeTab === 'ledger' }" @click="setTab('ledger')">Ledger Updates</button>
        </div>

        <div class="filter-panel">
          <div class="search-box">
            <span class="search-symbol">⌕</span>
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              type="search"
              placeholder="Filter by operator username, action, or record ID (Ctrl+K)..."
              @input="handleSearchDebounced"
            />
            <button v-if="searchQuery" type="button" @click="clearSearch" aria-label="Clear search">×</button>
          </div>

          <select v-model="selectedAction" aria-label="Filter by action" @change="applyFilters">
            <option value="">All actions</option>
            <option value="TOKEN_REFRESH">Token refresh</option>
            <option value="LOGIN">Login</option>
            <option value="LOGOUT">Logout</option>
            <option value="LOGIN_FAILED">Failed login</option>
            <option value="UPDATE_LEDGER">Ledger update</option>
            <option value="USER_REVOKE">User revocation</option>
            <option value="PASSWORD_CHANGE">Password change</option>
            <option value="AUTHORITY_REJECT">Authority rejection</option>
            <option value="RESOLVE_INCIDENT">Resolve incident</option>
          </select>

          <select v-model="selectedOutcome" aria-label="Filter by outcome" @change="applyFilters">
            <option value="">All outcomes</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
          </select>

          <select v-model="selectedPeriod" aria-label="Filter by period" @change="applyFilters">
            <option value="all">All time</option>
            <option value="hour">Last hour</option>
            <option value="day">Last 24 hours</option>
            <option value="week">Last 7 days</option>
          </select>
        </div>

        <div v-if="errorMessage" class="error-banner" role="alert">
          <span>Unable to load audit records: {{ errorMessage }}</span>
          <button type="button" @click="fetchLogs">Retry</button>
        </div>

        <div class="table-scroll">
          <table class="event-table">
            <thead>
              <tr>
                <th class="expand-column"></th>
                <th>SEQUENCE</th>
                <th>TIMESTAMP (IST)</th>
                <th>OPERATOR</th>
                <th>ACTION</th>
                <th>OUTCOME</th>
                <th>SUMMARY</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading && logs.length === 0">
                <td colspan="7" class="table-message" aria-live="polite">
                  <span class="loading-spinner" aria-hidden="true"></span> Loading secure audit entries...
                </td>
              </tr>
              <tr v-else-if="logs.length === 0">
                <td colspan="7" class="table-message">No audit records match your search criteria.</td>
              </tr>

              <template v-for="log in logs" :key="log.id">
                <tr
                  class="event-row"
                  tabindex="0"
                  role="button"
                  :aria-expanded="expandedRows.has(log.id)"
                  :aria-controls="`detail-${log.id}`"
                  :class="{
                    'selected-row': selectedEvent?.id === log.id,
                    'critical-row': isCritical(log),
                    'group-row': isGroup(log)
                  }"
                  @click="toggleRow(log)"
                  @keydown.enter.prevent="toggleRow(log)"
                  @keydown.space.prevent="toggleRow(log)"
                >
                  <td class="expand-column">
                    <span class="row-chevron" :class="{ expanded: expandedRows.has(log.id) }">›</span>
                  </td>
                  <td>
                    <span class="sequence-text">{{ displaySequence(log) }}</span>
                  </td>
                  <td class="timestamp-cell">
                    <template v-if="isGroup(log)">
                      <span>{{ formatDate(log.first_timestamp, false) }}</span>
                      <small>to {{ formatDate(log.last_timestamp, false) }}</small>
                    </template>
                    <template v-else>
                      {{ formatDate(log.timestamp) }}
                    </template>
                  </td>
                  <td>
                    <div class="actor-name">{{ displayActor(log) }}</div>
                    <div class="actor-role">{{ displayRole(log) }}</div>
                  </td>
                  <td>
                    <span class="action-badge" :class="getActionBadgeClass(log.action_type)">
                      {{ log.action_type || 'UNKNOWN' }}
                    </span>
                    <small v-if="isGroup(log)" class="group-count">{{ log.event_count }} original events</small>
                  </td>
                  <td>
                    <span
                      class="outcome-badge"
                      :class="isFailure(log) ? 'outcome-failed' : getOutcome(log) === 'SUCCESS' ? 'outcome-success' : 'outcome-unknown'"
                    >
                      {{ isGroup(log) ? 'SUCCESS GROUP' : getOutcome(log) || 'UNKNOWN' }}
                    </span>
                  </td>
                  <td class="summary-cell">
                    <div>{{ displaySummary(log) }}</div>
                    <small v-if="isGroup(log)">Select to load original records</small>
                    <small v-else>{{ displayTarget(log) }}</small>
                  </td>
                </tr>

                <!-- Expanded Group Row -->
                <tr v-if="isGroup(log) && expandedRows.has(log.id)" :id="`detail-${log.id}`" class="group-detail-row">
                  <td colspan="7">
                    <div class="group-detail">
                      <div class="group-detail-heading">
                        <div>
                          <strong>Original token refresh events</strong>
                          <p>{{ formatRange(log.first_timestamp, log.last_timestamp) }}</p>
                        </div>
                        <span>{{ groupEvents[log.id]?.length ?? log.event_count ?? 0 }} loaded</span>
                      </div>

                      <div v-if="groupLoading.has(log.id)" class="group-loading">
                        <span class="loading-spinner"></span> Loading original audit events...
                      </div>
                      <div v-else-if="groupErrors[log.id]" class="group-error">
                        {{ groupErrors[log.id] }}
                        <button type="button" @click.stop="toggleGroup(log)">Retry</button>
                      </div>
                      <div v-else-if="groupEvents[log.id]?.length" class="original-events">
                        <button
                          v-for="event in groupEvents[log.id]"
                          :key="event.id"
                          type="button"
                          class="original-event"
                          @click.stop="selectEvent(event)"
                        >
                          <span class="original-sequence">#{{ event.sequence_id ?? '—' }}</span>
                          <span>{{ formatDate(event.timestamp) }}</span>
                          <span class="original-outcome">{{ getOutcome(event) || 'UNKNOWN' }}</span>
                          <span class="original-endpoint">{{ event.endpoint || 'Endpoint not recorded' }}</span>
                          <span class="inspect-arrow">Inspect →</span>
                        </button>
                      </div>
                      <div v-else class="group-loading">No original events found for this group.</div>
                    </div>
                  </td>
                </tr>

                <!-- Expanded Standard Row -->
                <tr v-if="isGroup(log) && expandedRows.has(log.id)" :id="`detail-${log.id}`" class="group-detail-row">
                  <td colspan="7">
                    <div class="inline-detail">
                      <div>
                        <span>EVENT ID</span>
                        <strong>{{ displayEventId(log) }}</strong>
                      </div>
                      <div>
                        <span>TARGET</span>
                        <strong>{{ displayTarget(log) }}</strong>
                      </div>
                      <div>
                        <span>NETWORK ORIGIN</span>
                        <strong>{{ displayIp(log) }}</strong>
                      </div>
                      <div>
                        <span>DEVICE</span>
                        <strong>{{ displayDevice(log) }}</strong>
                      </div>
                      <button type="button" @click.stop="selectEvent(log)">
                        Open evidence inspector →
                      </button>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>

        <footer class="pagination-footer">
          <span>Showing {{ rangeStart }}–{{ rangeEnd }} of {{ totalLogs.toLocaleString() }} records</span>

          <div class="pagination-actions">
            <label>
              Rows
              <select v-model.number="pageLimit" @change="applyFilters">
                <option :value="25">25</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
              </select>
            </label>

            <button type="button" :disabled="currentPage <= 1 || loading" @click="changePage(currentPage - 1)">
              Previous
            </button>
            <span>Page {{ currentPage }} / {{ maxPages }}</span>
            <button type="button" :disabled="currentPage >= maxPages || loading" @click="changePage(currentPage + 1)">
              Next
            </button>
          </div>
        </footer>
      </section>

      <!-- Inspector Drawer -->
      <aside 
        class="inspector" 
        :class="{ 'inspector-mobile-open': mobileInspectorOpen }"
        aria-label="Event Evidence Inspector"
        :aria-hidden="!mobileInspectorOpen"
      >
        <div class="inspector-header">
          <div>
            <div class="eyebrow">FORENSIC EVIDENCE</div>
            <h2>Event Inspector</h2>
          </div>
          <button class="close-inspector" type="button" @click="closeInspector" aria-label="Close inspector">×</button>
        </div>

        <template v-if="selectedEvent">
          <div class="inspected-event-heading">
            <span class="action-badge" :class="getActionBadgeClass(selectedEvent.action_type)">
              {{ selectedEvent.action_type || 'UNKNOWN' }}
            </span>
            <button type="button" class="copy-id" @click="copyToClipboard(displayEventId(selectedEvent))">
              {{ displaySequence(selectedEvent) }} ⧉
            </button>
          </div>

          <div class="inspected-timestamp">
            {{ isGroup(selectedEvent)
              ? formatRange(selectedEvent.first_timestamp, selectedEvent.last_timestamp)
              : formatDate(selectedEvent.timestamp)
            }}
          </div>

          <div class="inspector-status" :class="{ failed: isFailure(selectedEvent) }">
            <span class="status-dot"></span>
            {{ isGroup(selectedEvent) ? `${selectedEvent.event_count} successful events` : selectedOutcomeLabel }}
          </div>

          <div v-if="isGroup(selectedEvent)" class="inspector-callout">
            This is a display group. Expand it in the stream to inspect individual original records.
          </div>

          <div class="inspector-section">
            <h3>ACTOR &amp; CONTEXT</h3>
            <div class="detail-line"><span>Operator</span><strong>{{ displayActor(selectedEvent) }}</strong></div>
            <div class="detail-line"><span>Role</span><strong>{{ displayRole(selectedEvent) }}</strong></div>
            <div class="detail-line"><span>User ID</span><strong>{{ selectedEvent.user_id ?? 'Not recorded' }}</strong></div>
            <div class="detail-line"><span>Target</span><strong>{{ displayTarget(selectedEvent) }}</strong></div>
            <div class="detail-line"><span>IP Address</span><strong>{{ displayIp(selectedEvent) }}</strong></div>
            <div class="detail-line"><span>Device</span><strong>{{ displayDevice(selectedEvent) }}</strong></div>
          </div>

          <div class="inspector-section">
            <h3>EVENT DETAILS</h3>
            <div class="detail-line"><span>Event ID</span><strong>{{ displayEventId(selectedEvent) }}</strong></div>
            <div class="detail-line"><span>Sequence ID</span><strong>{{ selectedEvent.sequence_id ?? 'Not recorded' }}</strong></div>
            <div class="detail-line"><span>Category</span><strong>{{ selectedEvent.category || 'Not recorded' }}</strong></div>
            <div class="detail-line"><span>Endpoint</span><strong class="break-value">{{ selectedEvent.endpoint || 'Not recorded' }}</strong></div>
            <div class="detail-line"><span>HTTP Method</span><strong>{{ selectedEvent.http_method || 'Not recorded' }}</strong></div>
            <div class="detail-line"><span>Status Code</span><strong>{{ selectedEvent.status_code ?? selectedMetadata.status_code ?? 'Not recorded' }}</strong></div>
          </div>

          <div class="inspector-section">
            <h3>OPERATIONAL JUSTIFICATION</h3>
            <p class="justification-value">{{ getJustification(selectedEvent) }}</p>
            <p class="summary-value">{{ displaySummary(selectedEvent) }}</p>
          </div>

          <div class="inspector-section">
            <h3>INTEGRITY EVIDENCE</h3>
            <div class="hash-field">
              <span>Previous Hash</span>
              <code>{{ selectedEvent.prev_hash || 'Not provided by API' }}</code>
              <button v-if="selectedEvent.prev_hash" type="button" @click="copyToClipboard(selectedEvent.prev_hash)">Copy</button>
            </div>
            <div class="hash-field">
              <span>Record Hash</span>
              <code>{{ selectedEvent.record_hash || 'Not provided by API' }}</code>
              <button v-if="selectedEvent.record_hash" type="button" @click="copyToClipboard(selectedEvent.record_hash)">Copy</button>
            </div>
          </div>

          <div class="inspector-section">
            <h3>FIELD-LEVEL CHANGES</h3>
            <div v-if="parseDiffs(selectedEvent.detailed_diffs).length" class="inspector-diffs">
              <div v-for="delta in parseDiffs(selectedEvent.detailed_diffs)" :key="delta.field" class="inspector-diff">
                <strong>{{ delta.field }}</strong>
                <div class="old-value">{{ jsonValue(delta.oldValue) }}</div>
                <div class="new-value">{{ jsonValue(delta.newValue) }}</div>
              </div>
            </div>
            <div v-else class="inspector-empty">No field-level changes provided for this event.</div>
          </div>

          <div class="inspector-section">
            <div class="raw-heading">
              <h3>RAW EVENT JSON</h3>
              <button type="button" @click="toggleRawView(selectedEvent.id)">
                {{ rawViews.has(selectedEvent.id) ? 'Hide' : 'Show JSON' }}
              </button>
            </div>
            <pre v-if="rawViews.has(selectedEvent.id)" class="raw-json">{{ JSON.stringify(selectedEvent, null, 2) }}</pre>
          </div>
        </template>

        <div v-else class="inspector-empty-state">
          <div class="inspector-empty-icon">◇</div>
          <h3>No event selected</h3>
          <p>Select a row from the audit stream to inspect its metadata, evidence, and cryptographic hashes.</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<!-- Unscoped global override to completely kill the parent layout container's blue background -->
<style>
/* Theme-aware global shell */
html, body, #app {
  background-color: var(--app-bg) !important;
  margin: 0;
  padding: 0;
  width: 100%;
  min-height: 100vh;
}
</style>

<style scoped>
.audit-console-view {
  --bg-primary: var(--app-bg);
  --panel: var(--surface);
  --border: var(--border-main);
  --border-strong: var(--accent);
  --text: var(--text-primary);
  --muted: var(--text-muted);
  --cyan: var(--accent);
  --blue: var(--accent);
  --green: var(--text-success);
  --red: var(--text-danger);
  --amber: var(--text-warning);
  --violet: var(--accent);

  width: 100%;
  min-height: 100vh;
  margin: 0;
  
  background-color: var(--app-bg);
  color: var(--text);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 13px;
  padding: 32px;
  box-sizing: border-box;
}

.audit-console-view *,
.audit-console-view *::before,
.audit-console-view *::after {
  box-sizing: border-box;
}

button, input, select {
  font: inherit;
  color: inherit;
}

.audit-console-view table,
.audit-console-view thead,
.audit-console-view tbody,
.audit-console-view tr,
.audit-console-view th,
.audit-console-view td {
  background-color: transparent !important;
}

.audit-console-view thead tr,
.audit-console-view thead th {
  background: var(--surface-2) !important;
}

.audit-console-view tr.event-row:hover {
  background: var(--hover-bg) !important;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
  gap: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.breadcrumb-trail {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 6px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.breadcrumb-trail span {
  color: var(--cyan);
  padding: 0 6px;
}

.view-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}

.view-header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.poll-btn.active {
  border-color: var(--green);
  background: var(--surface-success);
  color: var(--text-success);
}

.live-status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--surface-success);
  border: 1px solid var(--border-success);
  border-radius: 20px;
  color: var(--text-success);
  font-size: 11px;
  font-weight: 700;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  background: var(--text-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-2);
  color: var(--text);
  cursor: pointer;
  font-weight: 600;
  box-shadow: var(--shadow);
  transition: all 0.2s ease;
}

.action-btn:hover:not(:disabled) {
  border-color: var(--cyan);
  background: var(--hover-bg);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(280px, 1.2fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  position: relative;
  padding: 14px 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--panel);
  box-shadow: var(--shadow);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 84px;
}

.metric-card:hover {
  border-color: var(--border-strong);
}

.metric-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.metric-label {
  color: var(--muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.metric-icon {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  font-size: 11px;
}

.metric-icon.cyan { color: var(--cyan); background: var(--catalog-accent-soft); border: 1px solid var(--catalog-card-border); }
.metric-icon.red { color: var(--red); background: var(--surface-danger); border: 1px solid var(--border-danger); }
.metric-icon.blue { color: var(--blue); background: var(--catalog-accent-soft); border: 1px solid var(--catalog-card-border); }
.metric-icon.violet { color: var(--violet); background: var(--catalog-accent-soft); border: 1px solid var(--catalog-card-border); }

.metric-value {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  line-height: 1.2;
}

.metric-foot {
  margin-top: 2px;
  color: var(--muted);
  font-size: 10px;
}

.metric-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
}
.cyan-bar { background: var(--cyan); }
.red-bar { background: var(--red); }
.blue-bar { background: var(--blue); }

.integrity-card {
  justify-content: center;
  padding: 10px 16px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  gap: 20px;
  align-items: start;
}

.activity-panel {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--panel);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 22px 14px;
}

.panel-heading h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.panel-heading p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 11px;
}

.record-badge {
  padding: 5px 10px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
}

.record-badge span {
  font-weight: 800;
  color: var(--text-primary);
}

.tab-strip {
  display: flex;
  gap: 6px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}

.tab-strip button {
  position: relative;
  padding: 10px 14px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  font-weight: 600;
  transition: color 0.2s ease;
}

.tab-strip button:hover {
  color: var(--text-primary);
}

.tab-strip button.selected {
  color: var(--cyan);
}

.tab-strip button.selected::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 10px;
  right: 10px;
  height: 2px;
  background: var(--cyan);
  border-radius: 2px 2px 0 0;
}

.filter-panel {
  display: grid;
  grid-template-columns: minmax(200px, 2fr) repeat(3, minmax(120px, 1fr));
  gap: 10px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  transition: all 0.2s ease;
}

.search-box:focus-within {
  border-color: var(--cyan);
}

.search-symbol {
  color: var(--muted);
  font-size: 16px;
}

.search-box input {
  width: 100%;
  padding: 8px 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  font-size: 12px;
}

.filter-panel select,
.pagination-actions select {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  outline: none;
  cursor: pointer;
}

.filter-panel select:focus,
.pagination-actions select:focus {
  border-color: var(--cyan);
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--surface-danger);
  border-bottom: 1px solid var(--border-danger);
  color: var(--text-danger);
  font-size: 12px;
}

.error-banner button {
  padding: 5px 10px;
  border: 1px solid var(--border-danger);
  border-radius: 6px;
  background: var(--surface-danger);
  color: var(--text-danger);
  cursor: pointer;
  font-weight: 600;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.event-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.event-table th {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-align: left;
  white-space: nowrap;
}

.event-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
  vertical-align: middle;
}

.expand-column {
  width: 32px;
  text-align: center !important;
}

.event-row {
  cursor: pointer;
  transition: background 0.15s ease;
}

.event-row:hover {
  background: var(--hover-bg) !important;
}

.event-row.selected-row {
  background: var(--active-bg) !important;
}

.event-row.critical-row {
  box-shadow: inset 3px 0 var(--red);
}

.row-chevron {
  display: inline-block;
  color: var(--muted);
  font-size: 18px;
  transition: transform 0.2s ease;
}

.row-chevron.expanded {
  transform: rotate(90deg);
  color: var(--cyan);
}

.sequence-text {
  font-family: monospace;
  color: var(--cyan);
  font-weight: 600;
}

.timestamp-cell {
  white-space: nowrap;
}

.timestamp-cell small,
.group-count {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 10px;
}

.actor-name {
  font-weight: 700;
  color: var(--text-primary);
}

.actor-role {
  margin-top: 2px;
  color: var(--muted);
  font-size: 10px;
}

.action-badge, .outcome-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.action-badge.token { background: var(--catalog-accent-soft); color: var(--cyan); border: 1px solid var(--catalog-card-border); }
.action-badge.danger, .outcome-failed { background: var(--surface-danger); color: var(--text-danger); border: 1px solid var(--border-danger); }
.action-badge.governance { background: var(--surface-warning); color: var(--text-warning); border: 1px solid var(--border-warning); }
.action-badge.success, .outcome-success { background: var(--surface-success); color: var(--text-success); border: 1px solid var(--border-success); }
.action-badge.default, .outcome-unknown { background: var(--surface-2); color: var(--muted); border: 1px solid var(--border); }

.group-detail-row td {
  padding: 0;
  background: var(--surface-2) !important;
}

.group-detail,
.inline-detail {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.group-detail-heading strong { font-size: 12px; font-weight: 700; color: var(--text-primary); }

.original-event {
  display: grid;
  grid-template-columns: 80px minmax(130px, 1fr) 75px minmax(130px, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.original-event:hover {
  background: var(--hover-bg);
  border-color: var(--cyan);
}

.inline-detail strong { color: var(--text-primary); font-size: 12px; }

.pagination-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  color: var(--muted);
  font-size: 11px;
  background: var(--surface-2);
  border-top: 1px solid var(--border);
}

.pagination-actions button {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-weight: 600;
}

.inspector {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--panel);
  box-shadow: var(--shadow);
  padding: 20px;
  position: sticky;
  top: 24px;
  height: calc(100vh - 48px);
  overflow-y: auto;
}

.inspector-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.inspector-header h2 { color: var(--text-primary); }

.copy-id, .hash-field button, .inspector-diff, .raw-json, .hash-field code {
  background: var(--surface-2);
  border-color: var(--border);
  color: var(--text);
}

.detail-line strong { color: var(--text-primary); }
.justification-value { color: var(--text); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

@media (max-width: 1350px) {
  .workspace-grid { grid-template-columns: minmax(0, 1fr); }
  .inspector {
    position: fixed;
    z-index: 50;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(420px, 92vw);
    height: 100vh;
    border-radius: 0;
    transform: translateX(105%);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .inspector.inspector-mobile-open { transform: translateX(0); }
}
</style>