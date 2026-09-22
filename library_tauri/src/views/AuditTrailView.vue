<template>
  <div class="audit-page-container">
    
    <header class="ledger-header">
      <div class="header-left">
        <div class="header-badge">
          <span class="live-pulse"></span>
          <span>SECURITY & COMPLIANCE // AUDIT LOG</span>
        </div>
        <h1 class="page-title">Forensic Audit Ledger</h1>
        <p class="page-subtitle">
          Tamper-evident operational event stream. Inspect field-level deltas, cryptographic identifiers, operator justifications, and terminal context.
        </p>

        <!-- Ledger Cryptographic Verification Badge -->
        <div style="margin-top: 14px;">
          <LedgerIntegrityBadge />
        </div>
      </div>

      <div class="kpi-strip">
        <div class="kpi-card">
          <span class="kpi-label">TOTAL LOGGED</span>
          <span class="kpi-val">{{ totalLogs }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">CRITICAL ACTIONS</span>
          <span class="kpi-val text-red">{{ deleteCount }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">ACTIVE ACTORS</span>
          <span class="kpi-val text-blue">{{ uniqueActorsCount }}</span>
        </div>
      </div>
    </header>

    <div class="controls-panel">
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
        </svg>
        <input 
          type="text" 
          v-model="searchQuery" 
          @input="handleSearchDebounced" 
          placeholder="Filter by operator, record ID, or action keywords..." 
          class="search-input" 
        />
        <button v-if="searchQuery" @click="clearSearch" class="clear-btn">✕</button>
      </div>

      <div class="filter-actions">
        <select v-model="selectedAction" @change="fetchLogs" class="filter-dropdown">
          <option value="">ALL ACTION TYPES</option>
          <option value="CREATE">CREATE (Record Initialized)</option>
          <option value="UPDATE">UPDATE (State Modified)</option>
          <option value="DELETE">DELETE (Record Decommissioned)</option>
          <option value="AUTH">AUTH (Authentication Event)</option>
        </select>

        <button @click="fetchLogs" class="btn-refresh" :disabled="loading" title="Refresh Log Stream">
          <svg class="icon-refresh" :class="{ 'spinning': loading }" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
          </svg>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <div class="table-card">
      <table class="audit-data-table">
        <thead>
          <tr>
            <th style="width: 44px;"></th>
            <th style="width: 80px;" class="text-center">NODE</th>
            <th class="text-left">TIMESTAMP (IST)</th>
            <th class="text-left">OPERATOR</th>
            <th>ROLE</th>
            <th>ACTION</th>
            <th>TARGET ENTITY</th>
            <th class="text-left">OPERATION SUMMARY</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="table-notice">
              <div class="loading-state">
                <span class="spinner-dot"></span>
                <span>Retrieving encrypted audit sequence...</span>
              </div>
            </td>
          </tr>

          <tr v-else-if="logs.length === 0">
            <td colspan="8" class="table-notice">
              <div class="empty-state">
                <span class="empty-icon">🛡️</span>
                <p>No audit events match the specified filter query.</p>
              </div>
            </td>
          </tr>
          
          <template v-else v-for="log in logs" :key="log.id">
            <tr 
              class="table-row main-row" 
              @click="toggleRow(log.id)" 
              :class="{ 'row-active': expandedRows.has(log.id) }"
            >
              <td class="text-center">
                <span class="chevron-icon" :class="{ 'chevron-rotated': expandedRows.has(log.id) }">▶</span>
              </td>
              <td class="text-center">
                <span class="node-pill">#{{ log.sequence_id ?? '—' }}</span>
              </td>
              <td class="font-mono text-muted text-left">
                {{ formatDate(log.timestamp) }}
              </td>
              <td class="text-left">
                <div class="actor-cell">
                  <span class="actor-name">{{ log.actor_username || 'system_daemon' }}</span>
                  <span class="actor-id">#{{ log.user_id || 'SYS' }}</span>
                </div>
              </td>
              <td>
                <span class="role-pill">{{ log.actor_role || 'OPERATOR' }}</span>
              </td>
              <td>
                <span class="type-badge" :class="getActionBadgeClass(log.action_type)">
                  {{ log.action_type }}
                </span>
              </td>
              <td>
                <span class="target-badge" @click.stop="copyToClipboard(log.target_id)">
                  {{ log.target_id ? `#${log.target_id}` : 'GLOBAL' }}
                  <span class="copy-hint" title="Copy ID">📋</span>
                </span>
              </td>
              <td class="text-left desc-cell">
                <span class="summary-text">{{ log.summary || 'Operational transaction committed.' }}</span>
              </td>
            </tr>

            <tr v-if="expandedRows.has(log.id)" class="details-expansion-tray">
              <td colspan="8">
                <div class="tray-inner-wrapper">
                  
                  <div class="meta-grid-specs">
                    <div class="spec-card">
                      <span class="spec-label">TERMINAL & DEVICE ID</span>
                      <span class="spec-value text-mono">{{ log.device_id || 'TERMINAL-LOCAL' }}</span>
                    </div>
                    <div class="spec-card">
                      <span class="spec-label">NETWORK ORIGIN (IP)</span>
                      <span class="spec-value text-mono text-blue">{{ log.ip_address || '127.0.0.1' }}</span>
                    </div>
                    <div class="spec-card">
                      <span class="spec-label">EVENT TRANSACTION ID</span>
                      <span class="spec-value text-mono text-muted text-xs">{{ log.id }}</span>
                    </div>
                    <div class="spec-card span-3 justification-card">
                      <span class="spec-label text-amber">MANDATORY OPERATIONAL JUSTIFICATION</span>
                      <p class="justification-text">
                        {{ log.change_reason || 'No audit justification comment provided.' }}
                      </p>
                    </div>
                  </div>

                  <div class="diff-inspector">
                    <div class="diff-inspector-header">
                      <div class="diff-title">
                        <svg class="diff-icon" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 01-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 110-2h4a1 1 0 011 1v4a1 1 0 11-2 0V6.414l-2.293 2.293a1 1 0 11-1.414-1.414L13.586 5H12zm-9 7a1 1 0 112 0v1.586l2.293-2.293a1 1 0 011.414 1.414L6.414 15H8a1 1 0 110 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 110-2h1.586l-2.293-2.293a1 1 0 011.414-1.414L15 13.586V12a1 1 0 011-1z" clip-rule="evenodd"/>
                        </svg>
                        <span>FIELD-LEVEL STATE DELTA</span>
                      </div>
                      <button class="raw-toggle-btn" @click="toggleRawView(log.id)">
                        {{ rawViews.has(log.id) ? 'View Visual Delta' : 'View Raw JSON' }}
                      </button>
                    </div>

                    <div v-if="!rawViews.has(log.id)">
                      <div v-if="log.detailed_diffs && Object.keys(log.detailed_diffs).length > 0" class="diff-table-wrap">
                        <table class="diff-table">
                          <thead>
                            <tr>
                              <th style="width: 25%;">FIELD NAME</th>
                              <th style="width: 37.5%;">PREVIOUS VALUE</th>
                              <th style="width: 37.5%;">COMMITTED VALUE</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(delta, fieldName) in parseDiffs(log.detailed_diffs)" :key="fieldName">
                              <td class="field-key">{{ fieldName }}</td>
                              <td class="val-old">
                                <code>{{ delta.oldValue !== undefined ? delta.oldValue : 'null' }}</code>
                              </td>
                              <td class="val-new">
                                <code>{{ delta.newValue !== undefined ? delta.newValue : 'null' }}</code>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <div v-else class="diff-empty">
                        No individual column variances detected for this operation type.
                      </div>
                    </div>

                    <div v-else class="raw-json-block">
                      <pre><code>{{ JSON.stringify(log, null, 2) }}</code></pre>
                    </div>
                  </div>

                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <div class="pagination-footer">
        <span class="pagination-info">Showing page {{ currentPage }} ({{ logs.length }} records loaded)</span>
        <div class="pagination-controls">
          <button class="btn-page" :disabled="currentPage <= 1 || loading" @click="changePage(currentPage - 1)">
            ← Previous
          </button>
          <span class="page-indicator">{{ currentPage }}</span>
          <button class="btn-page" :disabled="logs.length < pageLimit || loading" @click="changePage(currentPage + 1)">
            Next →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import LedgerIntegrityBadge from '@/components/LedgerIntegrityBadge.vue'

const authStore = useAuthStore()

const loading = ref(true)
const logs = ref([])
const totalLogs = ref(0)
const searchQuery = ref('')
const selectedAction = ref('')
const expandedRows = ref(new Set())
const rawViews = ref(new Set())

const currentPage = ref(1)
const pageLimit = ref(50)
let debounceTimer = null

const maxPages = computed(() => Math.ceil(totalLogs.value / pageLimit.value) || 1)

const deleteCount = computed(() => logs.value.filter(l => (l.action_type || '').toUpperCase() === 'DELETE').length)
const uniqueActorsCount = computed(() => new Set(logs.value.map(l => l.actor_username || l.user_id)).size)

function getToken() {
  return authStore.accessToken || ''

}

async function fetchLogs() {
  loading.value = true
  try {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    const offset = (currentPage.value - 1) * pageLimit.value
    let url = `${baseUrl}/status_audit/system-logs?limit=${pageLimit.value}&offset=${offset}`
    
    if (selectedAction.value) url += `&action_filter=${encodeURIComponent(selectedAction.value)}`
    if (searchQuery.value) url += `&actor_filter=${encodeURIComponent(searchQuery.value)}`

    const token = getToken()

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || `Server error ${response.status}`)
    }

    const data = await response.json()
    logs.value = data.items || []
    totalLogs.value = data.total || 0
  } catch (err) {
    console.error("Failed to load audit telemetry stream:", err)
    logs.value = []
    totalLogs.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearchDebounced() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchLogs()
  }, 350)
}

function clearSearch() {
  searchQuery.value = ''
  currentPage.value = 1
  fetchLogs()
}

function changePage(newPage) {
  if (newPage < 1 || newPage > maxPages.value) return
  currentPage.value = newPage
  fetchLogs()
}

function toggleRow(id) {
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id)
  } else {
    expandedRows.value.add(id)
  }
}

function toggleRawView(id) {
  if (rawViews.value.has(id)) {
    rawViews.value.delete(id)
  } else {
    rawViews.value.add(id)
  }
}

function getActionBadgeClass(action) {
  if (!action) return 'default'
  const a = action.toLowerCase()
  if (a.includes('create') || a.includes('insert')) return 'create'
  if (a.includes('update') || a.includes('modify') || a.includes('patch')) return 'update'
  if (a.includes('delete') || a.includes('remove') || a.includes('revoke')) return 'delete'
  if (a.includes('auth') || a.includes('login') || a.includes('token')) return 'auth'
  return 'default'
}

function formatDate(raw) {
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    if (isNaN(d.getTime())) return raw

    const parts = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      weekday: 'long',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).formatToParts(d)

    const m = {}
    for (const { type, value } of parts) {
      m[type] = value
    }

    return `${m.day}-${m.month}-${m.year} ${m.weekday.toUpperCase()} ${m.hour}:${m.minute}:${m.second}`
  } catch {
    return raw
  }
}

function parseDiffs(rawDiffs) {
  if (!rawDiffs) return {}
  if (typeof rawDiffs === 'object' && !Array.isArray(rawDiffs)) {
    const formatted = {}
    for (const [k, v] of Object.entries(rawDiffs)) {
      if (v && typeof v === 'object') {
        const oldVal = v.from !== undefined ? v.from : (v.old !== undefined ? v.old : '—')
        const newVal = v.to !== undefined ? v.to : (v.new !== undefined ? v.new : JSON.stringify(v))
        formatted[k] = { oldValue: oldVal, newValue: newVal }
      } else {
        formatted[k] = { oldValue: '—', newValue: String(v) }
      }
    }
    return formatted
  }
  
  if (Array.isArray(rawDiffs)) {
    const formatted = {}
    rawDiffs.forEach((item, idx) => {
      formatted[`Delta #${idx + 1}`] = { oldValue: '—', newValue: typeof item === 'object' ? JSON.stringify(item) : String(item) }
    })
    return formatted
  }
  return {}
}

function copyToClipboard(text) {
  if (!text) return
  navigator.clipboard.writeText(String(text))
}

onMounted(() => fetchLogs())
</script>

<style scoped>
/* CONTAINER */
.audit-page-container {
  padding: 32px 40px;
  background-color: #0b0c10;
  min-height: 100vh;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", monospace, sans-serif;
}

/* HEADER & KPIS */
.ledger-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 28px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #f59e0b;
  margin-bottom: 6px;
}

.live-pulse {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 8px #10b981;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  margin: 0 0 6px 0;
}

.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  max-width: 680px;
  line-height: 1.5;
}

.kpi-strip {
  display: flex;
  gap: 12px;
}

.kpi-card {
  background: rgba(18, 20, 26, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 10px 16px;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.05em;
}

.kpi-val {
  font-size: 20px;
  font-weight: 700;
  color: #f1f5f9;
  font-family: monospace;
}

/* CONTROLS */
.controls-panel {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.search-wrap {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 14px;
  width: 16px;
  height: 16px;
  color: #64748b;
}

.search-input {
  width: 100%;
  background-color: #12141a;
  border: 1px solid #1e222d;
  border-radius: 8px;
  padding: 10px 36px 10px 38px;
  color: #ffffff;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s ease;
}

.search-input:focus {
  border-color: #3b82f6;
}

.clear-btn {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
}

.filter-actions {
  display: flex;
  gap: 12px;
}

.filter-dropdown {
  background-color: #12141a;
  border: 1px solid #1e222d;
  border-radius: 8px;
  padding: 10px 14px;
  color: #cbd5e1;
  font-size: 13px;
  outline: none;
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #1e222d;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 10px 16px;
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: #282d3c;
  color: #ffffff;
}

.icon-refresh {
  width: 14px;
  height: 14px;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* TABLE */
.table-card {
  background-color: #12141a;
  border: 1px solid #1e222d;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}

.audit-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.audit-data-table th {
  background-color: #0e1015;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  padding: 12px 18px;
  border-bottom: 1px solid #1e222d;
  letter-spacing: 0.04em;
  text-align: center;
}

.audit-data-table td {
  padding: 12px 18px;
  border-bottom: 1px solid #181b24;
  color: #94a3b8;
  vertical-align: middle;
  text-align: center;
}

.main-row {
  cursor: pointer;
  transition: background 0.12s ease;
}

.main-row:hover {
  background-color: rgba(255, 255, 255, 0.02);
}

.row-active {
  background-color: rgba(59, 130, 246, 0.05) !important;
}

.chevron-icon {
  display: inline-block;
  font-size: 9px;
  color: #64748b;
  transition: transform 0.2s ease;
}

.chevron-rotated {
  transform: rotate(90deg);
  color: #3b82f6;
}

/* NODE PILL */
.node-pill {
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.25);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  display: inline-block;
}

/* CELL COMPONENTS */
.actor-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.actor-name {
  color: #f1f5f9;
  font-weight: 600;
}

.actor-id {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.role-pill {
  font-size: 10px;
  font-weight: 700;
  color: #ec4899;
  background: rgba(236, 72, 153, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  display: inline-block;
}

.type-badge.create { background: rgba(16, 185, 129, 0.12); color: #10b981; }
.type-badge.update { background: rgba(59, 130, 246, 0.12); color: #3b82f6; }
.type-badge.delete { background: rgba(239, 68, 68, 0.12); color: #ef4444; }
.type-badge.auth   { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
.type-badge.default{ background: rgba(255, 255, 255, 0.08); color: #cbd5e1; }

.target-badge {
  font-family: monospace;
  font-weight: 600;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.08);
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.target-badge:hover .copy-hint {
  opacity: 1;
}

.copy-hint {
  opacity: 0.4;
  font-size: 10px;
}

.summary-text {
  color: #cbd5e1;
  line-height: 1.4;
}

/* EXPANSION DRAWER */
.details-expansion-tray td {
  padding: 0 !important;
  background-color: #0c0e12;
  border-bottom: 1px solid #1e222d;
}

.tray-inner-wrapper {
  padding: 20px 28px;
  text-align: left;
}

.meta-grid-specs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}

.spec-card {
  background: #12141a;
  border: 1px solid #1e222d;
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.span-3 {
  grid-column: span 3;
}

.spec-label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.05em;
}

.justification-card {
  background: rgba(245, 158, 11, 0.03);
  border-color: rgba(245, 158, 11, 0.2);
}

.justification-text {
  margin: 0;
  font-size: 13px;
  color: #f1f5f9;
  line-height: 1.5;
}

/* DIFF INSPECTOR */
.diff-inspector {
  background: #12141a;
  border: 1px solid #1e222d;
  border-radius: 8px;
  overflow: hidden;
}

.diff-inspector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #0e1015;
  border-bottom: 1px solid #1e222d;
}

.diff-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
}

.diff-icon {
  width: 14px;
  height: 14px;
  color: #3b82f6;
}

.raw-toggle-btn {
  background: none;
  border: 1px solid #282d3c;
  color: #94a3b8;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.raw-toggle-btn:hover {
  color: #ffffff;
  border-color: #3b82f6;
}

.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.diff-table th {
  background: #101217;
  color: #64748b;
  font-size: 10px;
  font-weight: 700;
  padding: 8px 14px;
  border-bottom: 1px solid #1e222d;
  text-align: left;
}

.diff-table td {
  padding: 8px 14px;
  border-bottom: 1px solid #181b24;
  text-align: left;
  vertical-align: top;
}

.field-key {
  font-family: monospace;
  font-weight: 600;
  color: #cbd5e1;
}

.val-old {
  background: rgba(239, 68, 68, 0.06);
  color: #fca5a5;
  font-family: monospace;
}

.val-new {
  background: rgba(16, 185, 129, 0.06);
  color: #6ee7b7;
  font-family: monospace;
}

.diff-empty {
  padding: 16px;
  color: #64748b;
  font-size: 12px;
  font-style: italic;
  text-align: center;
}

.raw-json-block {
  padding: 14px;
  max-height: 280px;
  overflow-y: auto;
  background: #090a0d;
}

.raw-json-block pre {
  margin: 0;
  font-family: monospace;
  font-size: 11.5px;
  color: #a5b4fc;
}

/* PAGINATION FOOTER */
.pagination-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #0e1015;
  border-top: 1px solid #1e222d;
}

.pagination-info {
  font-size: 12px;
  color: #64748b;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-page {
  background: #161822;
  border: 1px solid #282d3c;
  color: #cbd5e1;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.btn-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-indicator {
  font-family: monospace;
  font-size: 12px;
  font-weight: 700;
  color: #38bdf8;
}

/* UTILITY HELPERS */
.text-left { text-align: left !important; }
.text-center { text-align: center !important; }
.text-mono { font-family: monospace; }
.text-muted { color: #64748b; }
.text-blue { color: #60a5fa; }
.text-amber { color: #f59e0b; }
.text-red { color: #f87171; }
.text-xs { font-size: 11px; }

.loading-state, .empty-state {
  padding: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #64748b;
}

.spinner-dot {
  width: 20px;
  height: 20px;
  border: 2px solid #1e222d;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>