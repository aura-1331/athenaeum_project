<template>
  <div class="incidents-page">
    <main class="incidents-main">

      <!-- ==============================
           PAGE HEADER
           ============================== -->
      <header class="incidents-header">
        <div>
          <div class="eyebrow">
            <span class="live-pulse"></span>
            EXECUTIVE CLEARANCE // SECURITY & ARCHIVE INCIDENTS
          </div>
          <h1 class="page-title">Incidents Management</h1>
          <p class="page-subtitle">
            Cryptographic ledger breaches, physical archival damage, and unresolved asset exceptions.
          </p>
        </div>

        <div class="header-actions">
          <button
            class="btn secondary"
            :disabled="loading || historyLoading || breachesLoading"
            @click="refreshAll"
          >
            <span :class="{ 'spinning': loading || breachesLoading }">🔄</span>
            Refresh Feeds
          </button>
          <button class="btn primary" @click="openReportModal">
            + Report Item Incident
          </button>
        </div>
      </header>

      <!-- ERROR BANNER -->
      <div v-if="errorMessage" class="alert error">
        {{ errorMessage }}
      </div>

      <!-- ==============================
           SECTION 1: SYSTEM INTEGRITY BREACHES (LEDGER ALERTS)
           ============================== -->
      <section class="breach-panel">
        <div class="breach-header collapsible-header" @click="isBreachesOpen = !isBreachesOpen">
          <div class="breach-title">
            <span class="expand-chevron">
              {{ isBreachesOpen ? '▾' : '▸' }}
            </span>
            <span class="shield-icon">🛡️</span>
            <div>
              <h3>Ledger Cryptographic Breaches</h3>
              <p>Tamper events detected by automated hash chain verification.</p>
            </div>
          </div>
          <div class="breach-counter">
            <span class="breach-badge" :class="securityBreaches.length > 0 ? 'breach-crit' : 'breach-ok'">
              {{ securityBreaches.length }} UNRESOLVED {{ securityBreaches.length === 1 ? 'BREACH' : 'BREACHES' }}
            </span>
          </div>
        </div>

        <!-- COLLAPSIBLE BREACH CONTENT -->
        <div v-show="isBreachesOpen" class="collapsible-body">
          <div v-if="breachesLoading" class="state compact">
            <span class="spinner-dot"></span>
            <span>Inspecting ledger incident register...</span>
          </div>

          <div v-else-if="securityBreaches.length === 0" class="breach-empty">
            <span class="ok-icon">✓</span>
            <div>
              <strong>Ledger Integrity Intact</strong>
              <p>No cryptographic tampering or broken chain links detected.</p>
            </div>
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width: 80px;">INCIDENT</th>
                  <th style="width: 100px;">SEVERITY</th>
                  <th style="width: 130px;">COMPROMISED NODE</th>
                  <th>BREACH CLASSIFICATION</th>
                  <th>DETECTED TIMESTAMP</th>
                  <th style="width: 100px; text-align: right;">STATUS</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in securityBreaches" :key="b.id" class="breach-row">
                  <td class="font-mono text-amber">#SEC-{{ b.id }}</td>
                  <td>
                    <span class="severity-badge critical">{{ b.severity }}</span>
                  </td>
                  <td>
                    <span class="node-pill">#{{ b.compromised_node }}</span>
                  </td>
                  <td>
                    <div class="breach-desc">
                      <strong>{{ b.incident_type }}</strong>
                      <span>{{ b.details }}</span>
                    </div>
                  </td>
                  <td class="font-mono text-muted text-xs">
                    {{ formatDate(b.detected_at) }}
                  </td>
                  <td style="text-align: right;">
                    <span class="status-pill open">OPEN</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ==============================
           SECTION 2: PHYSICAL ARCHIVE INCIDENTS
           ============================== -->
      <section class="panel" style="margin-top: 24px;">
        <div class="panel-header collapsible-header" @click="isActiveItemsOpen = !isActiveItemsOpen">
          <div class="panel-header-left">
            <span class="expand-chevron">
              {{ isActiveItemsOpen ? '▾' : '▸' }}
            </span>
            <div>
              <div class="sub-eyebrow">PHYSICAL REPOSITORY</div>
              <h3 class="panel-title">Active Item Incidents ({{ incidents.length }})</h3>
            </div>
          </div>
          <span class="feed-tag">Live stream: <code>/incidents/open</code></span>
        </div>

        <!-- COLLAPSIBLE ACTIVE ITEMS CONTENT -->
        <div v-show="isActiveItemsOpen" class="collapsible-body">
          <div v-if="loading" class="state compact">
            <span class="spinner-dot"></span>
            <span>Loading repository alerts...</span>
          </div>

          <div v-else-if="incidents.length === 0" class="state empty">
            <span>🛡️</span>
            <strong>No open repository incidents</strong>
            <p>No missing or damaged items awaiting resolution.</p>
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width: 80px;">TICKET</th>
                  <th style="width: 110px;">SERIAL</th>
                  <th style="width: 130px;">TYPE</th>
                  <th style="width: 110px;">SEVERITY</th>
                  <th>REPORTED</th>
                  <th>STATUS</th>
                  <th style="text-align: right;">ACTION</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="inc in incidents" :key="inc.incident_id">
                  <td class="font-mono text-amber">#{{ inc.incident_id }}</td>
                  <td class="font-mono text-cyan">{{ inc.serial_no }}</td>
                  <td>
                    <span :class="['type-badge', inc.incident_type?.toLowerCase()]">
                      {{ inc.incident_type }}
                    </span>
                  </td>
                  <td>
                    <span :class="['severity-badge', inc.severity?.toLowerCase()]">
                      {{ inc.severity }}
                    </span>
                  </td>
                  <td class="font-mono text-muted text-xs">{{ formatDate(inc.reported_at) }}</td>
                  <td>
                    <span class="status-pill open">{{ inc.status }}</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="btn resolve-btn" @click.stop="openResolveModal(inc)">
                      Resolve
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ==============================
           SECTION 3: ARCHIVE INCIDENT HISTORY & FILTERS
           ============================== -->
      <section class="panel history-panel" style="margin-top: 24px;">
        <div class="panel-header collapsible-header" @click="isHistoryOpen = !isHistoryOpen">
          <div class="panel-header-left">
            <span class="expand-chevron">
              {{ isHistoryOpen ? '▾' : '▸' }}
            </span>
            <div>
              <div class="sub-eyebrow">HISTORICAL RECORD</div>
              <h3 class="panel-title">Incident Audit History</h3>
            </div>
          </div>
          <div class="history-total-tag">
            {{ historyTotal }} RECORDS LOGGED
          </div>
        </div>

        <!-- COLLAPSIBLE HISTORY CONTENT -->
        <div v-show="isHistoryOpen" class="collapsible-body">
          <!-- FILTER STRIP -->
          <div class="history-filter-strip">
            <div class="filter-group-search">
              <input
                v-model="historyFilters.search"
                type="text"
                placeholder="Search serial, accession, description..."
                @keyup.enter="applyHistoryFilters"
                class="dark-input"
              />
            </div>

            <select v-model="historyFilters.incident_type" class="dark-select">
              <option value="">ALL TYPES</option>
              <option value="MISSING">MISSING</option>
              <option value="DAMAGED">DAMAGED</option>
            </select>

            <select v-model="historyFilters.severity" class="dark-select">
              <option value="">ALL SEVERITIES</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
            </select>

            <input v-model="historyFilters.date_from" type="date" class="dark-input date-input" />
            <input v-model="historyFilters.date_to" type="date" class="dark-input date-input" />

            <button class="btn primary btn-sm" :disabled="historyLoading" @click="applyHistoryFilters">
              Apply
            </button>
            <button class="btn secondary btn-sm" :disabled="historyLoading" @click="clearHistoryFilters">
              Clear
            </button>
          </div>

          <!-- HISTORY FEED -->
          <div v-if="historyLoading" class="state compact">
            <span class="spinner-dot"></span>
            <span>Loading historical logs...</span>
          </div>

          <div v-else-if="incidentHistory.length === 0" class="state empty">
            <p>No historical incidents match the selected filter criteria.</p>
          </div>

          <div v-else class="history-feed">
            <article
              v-for="item in incidentHistory"
              :key="item.incident_id"
              class="history-card"
              :class="{ 'is-expanded': expandedCards.has(item.incident_id) }"
            >
              <!-- CLICKABLE ACCORDION ROW -->
              <div class="history-card-top" @click="toggleExpand(item.incident_id)">
                <div class="history-id-block">
                  <span class="expand-chevron">
                    {{ expandedCards.has(item.incident_id) ? '▾' : '▸' }}
                  </span>
                  <span class="history-tag">#{{ item.incident_id }}</span>
                  <span class="history-acc">{{ item.accession_no || 'NO ACCESSION' }}</span>
                  <span class="history-serial">Serial #{{ item.serial_no }}</span>
                </div>
                <div class="history-badges">
                  <span :class="['type-badge', item.incident_type?.toLowerCase()]">{{ item.incident_type }}</span>
                  <span :class="['severity-badge', item.severity?.toLowerCase()]">{{ item.severity }}</span>
                  <span class="status-pill resolved">{{ item.status }}</span>
                </div>
              </div>

              <!-- EXPANDABLE DETAILS -->
              <div v-show="expandedCards.has(item.incident_id)" class="history-card-body">
                <div class="history-meta-row">
                  <div>
                    <span class="meta-label">REPORTED BY</span>
                    <span class="meta-val">{{ item.reported_by_name || `User #${item.reported_by}` }}</span>
                  </div>
                  <div>
                    <span class="meta-label">REPORTED AT</span>
                    <span class="meta-val font-mono">{{ formatDate(item.reported_at) }}</span>
                  </div>
                  <div>
                    <span class="meta-label">RESOLVED AT</span>
                    <span class="meta-val font-mono">{{ item.resolved_at ? formatDate(item.resolved_at) : 'Active' }}</span>
                  </div>
                  <div v-if="item.assigned_to_name || item.assigned_to">
                    <span class="meta-label">ASSIGNED TO</span>
                    <span class="meta-val">{{ item.assigned_to_name || `User #${item.assigned_to}` }}</span>
                  </div>
                </div>

                <div v-if="item.description" class="history-note-box">
                  <span class="note-label">DESCRIPTION</span>
                  <p>{{ item.description }}</p>
                </div>

                <div v-if="item.resolution_notes" class="history-note-box resolution">
                  <span class="note-label text-amber">RESOLUTION NOTES</span>
                  <p>{{ item.resolution_notes }}</p>
                </div>
              </div>
            </article>
          </div>

          <!-- PAGINATION -->
          <div v-if="!historyLoading && historyTotal > 0" class="pagination-bar">
            <span class="text-xs text-muted">
              Showing {{ historyStartRecord }}–{{ historyEndRecord }} of {{ historyTotal }}
            </span>
            <div class="pagination-actions">
              <button
                class="btn-page"
                :disabled="historyPage <= 1 || historyLoading"
                @click="changeHistoryPage(historyPage - 1)"
              >
                ← Prev
              </button>
              <span class="page-count">{{ historyPage }} / {{ historyTotalPages }}</span>
              <button
                class="btn-page"
                :disabled="historyPage >= historyTotalPages || historyLoading"
                @click="changeHistoryPage(historyPage + 1)"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- RESOLVE INCIDENT MODAL -->
    <div v-if="resolveIncident" class="modal-backdrop" @click.self="closeResolveModal">
      <div class="dark-modal">
        <div class="modal-header">
          <h3>Resolve Archive Incident #{{ resolveIncident.incident_id }}</h3>
          <button class="close-x" @click="closeResolveModal">✕</button>
        </div>
        <div class="modal-body">
          <div class="modal-item-summary">
            <div><span>SERIAL</span><strong>{{ resolveIncident.serial_no }}</strong></div>
            <div><span>TYPE</span><strong>{{ resolveIncident.incident_type }}</strong></div>
            <div><span>SEVERITY</span><strong>{{ resolveIncident.severity }}</strong></div>
          </div>
          <div class="field-block">
            <label>RESOLUTION DOCUMENTATION (MANDATORY)</label>
            <textarea
              v-model="resolutionNotes"
              rows="4"
              placeholder="State the forensic cause, item repair status, or location justification..."
              class="dark-textarea"
            ></textarea>
          </div>
          <div v-if="modalError" class="alert error">{{ modalError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn secondary" @click="closeResolveModal">Cancel</button>
          <button
            class="btn primary"
            :disabled="submitting || !resolutionNotes.trim()"
            @click="resolveSelectedIncident"
          >
            {{ submitting ? 'Committing...' : 'Confirm Resolution' }}
          </button>
        </div>
      </div>
    </div>

    <!-- REPORT INCIDENT MODAL -->
    <div v-if="showReportModal" class="modal-backdrop" @click.self="closeReportModal">
      <div class="dark-modal">
        <div class="modal-header">
          <h3>Record Archive Item Incident</h3>
          <button class="close-x" @click="closeReportModal">✕</button>
        </div>
        <div class="modal-body">
          <div class="modal-grid">
            <div class="field-block">
              <label>ITEM SERIAL NUMBER</label>
              <input v-model.number="reportForm.serial_no" type="number" min="1" class="dark-input" />
            </div>
            <div class="field-block">
              <label>INCIDENT TYPE</label>
              <select v-model="reportForm.incident_type" class="dark-select">
                <option value="MISSING">MISSING</option>
                <option value="DAMAGED">DAMAGED</option>
              </select>
            </div>
            <div class="field-block full">
              <label>SEVERITY RATING</label>
              <select v-model="reportForm.severity" class="dark-select">
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
              </select>
            </div>
            <div class="field-block full">
              <label>INCIDENT DESCRIPTION</label>
              <textarea
                v-model="reportForm.description"
                rows="4"
                placeholder="Detail physical damages, last known station, or handling operator..."
                class="dark-textarea"
              ></textarea>
            </div>
          </div>
          <div v-if="modalError" class="alert error">{{ modalError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn secondary" @click="closeReportModal">Cancel</button>
          <button
            class="btn primary"
            :disabled="submitting || !reportForm.serial_no || !reportForm.description.trim()"
            @click="reportIncident"
          >
            {{ submitting ? 'Registering...' : 'Register Incident' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import { useAuthStore } from "@/stores/auth.ts"

interface Incident {
  incident_id: number
  serial_no: number
  incident_type: string
  severity: string
  status: string
  reported_at: string
}

interface IncidentHistory {
  incident_id: number
  serial_no: number
  accession_no: string | null
  incident_type: string
  severity: string
  status: string
  reported_by: number
  reported_by_name: string | null
  assigned_to: number | null
  assigned_to_name: string | null
  description: string | null
  resolution_notes: string | null
  reported_at: string
  resolved_at: string | null
}

interface SecurityBreach {
  id: number
  incident_type: string
  severity: string
  compromised_node: number
  detected_at: string
  details: string
  resolved: boolean
}

const router = useRouter()
const authStore = useAuthStore()
const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

// COLLAPSIBLE STATE FLAGS
const isBreachesOpen = ref(true)
const isActiveItemsOpen = ref(true)
const isHistoryOpen = ref(true)
const expandedCards = ref<Set<number>>(new Set())

function toggleExpand(id: number) {
  if (expandedCards.value.has(id)) {
    expandedCards.value.delete(id)
  } else {
    expandedCards.value.add(id)
  }
}

// SECURITY BREACHES DATA
const securityBreaches = ref<SecurityBreach[]>([])
const breachesLoading = ref(true)

// ARCHIVE ITEM INCIDENTS DATA
const incidents = ref<Incident[]>([])
const incidentHistory = ref<IncidentHistory[]>([])
const historyPage = ref(1)
const historyPageSize = ref(25)
const historyTotal = ref(0)

const historyFilters = reactive({
  search: "",
  incident_type: "",
  severity: "",
  date_from: "",
  date_to: "",
  sort: "newest"
})

const historyTotalPages = computed(() => {
  if (!historyTotal.value) return 1
  return Math.ceil(historyTotal.value / historyPageSize.value)
})

const historyStartRecord = computed(() => {
  if (!historyTotal.value) return 0
  return (historyPage.value - 1) * historyPageSize.value + 1
})

const historyEndRecord = computed(() => {
  return Math.min(historyPage.value * historyPageSize.value, historyTotal.value)
})

const historyLoading = ref(true)
const submitting = ref(false)
const loading = ref(true)

const errorMessage = ref("")
const modalError = ref("")
const resolveIncident = ref<Incident | null>(null)
const resolutionNotes = ref("")
const showReportModal = ref(false)

const reportForm = reactive({
  serial_no: null as number | null,
  incident_type: "MISSING",
  severity: "MEDIUM",
  description: ""
})

function getAuthConfig() {
  const token =
    authStore.token ||
    authStore.accessToken ||
    authStore.access_token ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("token")
  if (!token) {
    router.push("/login")
    return null
  }
  return { headers: { Authorization: `Bearer ${token}` } }
}

async function fetchSecurityBreaches() {
  breachesLoading.value = true
  try {
    const config = getAuthConfig()
    if (!config) return
    const res = await axios.get(`${baseUrl}/status_audit/security-incidents`, config)
    securityBreaches.value = res.data?.incidents || []
  } catch (err: any) {
    console.error("Failed to load security breaches:", err)
  } finally {
    breachesLoading.value = false
  }
}

async function fetchIncidents() {
  loading.value = true
  errorMessage.value = ""
  try {
    const config = getAuthConfig()
    if (!config) return
    const response = await axios.get(`${baseUrl}/incidents/open`, config)
    incidents.value = Array.isArray(response.data) ? response.data : []
  } catch (err: any) {
    if (err.response?.status === 401) {
      router.push("/login")
      return
    }
    console.error("Failed to load incidents:", err)
    errorMessage.value = err.response?.data?.detail || "Unable to load archive incidents."
  } finally {
    loading.value = false
  }
}

function formatDate(value: string) {
  if (!value) return "—"
  try {
    const d = new Date(value)
    if (isNaN(d.getTime())) return value
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    }).format(d)
  } catch {
    return value
  }
}

function openResolveModal(incident: Incident) {
  resolveIncident.value = incident
  resolutionNotes.value = ""
  modalError.value = ""
}

function closeResolveModal() {
  resolveIncident.value = null
  resolutionNotes.value = ""
  modalError.value = ""
}

async function resolveSelectedIncident() {
  if (!resolveIncident.value || !resolutionNotes.value.trim()) return
  submitting.value = true
  modalError.value = ""
  try {
    const config = getAuthConfig()
    if (!config) return
    await axios.patch(
      `${baseUrl}/incidents/resolve/${resolveIncident.value.incident_id}`,
      { resolution_notes: resolutionNotes.value.trim() },
      config
    )
    closeResolveModal()
    await refreshAll()
  } catch (err: any) {
    if (err.response?.status === 401) {
      router.push("/login")
      return
    }
    console.error("Failed to resolve incident:", err)
    modalError.value = err.response?.data?.detail || "Unable to resolve the incident."
  } finally {
    submitting.value = false
  }
}

function openReportModal() {
  modalError.value = ""
  showReportModal.value = true
}

function closeReportModal() {
  showReportModal.value = false
  modalError.value = ""
  reportForm.serial_no = null
  reportForm.incident_type = "MISSING"
  reportForm.severity = "MEDIUM"
  reportForm.description = ""
}

async function reportIncident() {
  if (!reportForm.serial_no || !reportForm.description.trim()) return
  submitting.value = true
  modalError.value = ""
  try {
    const config = getAuthConfig()
    if (!config) return
    await axios.post(
      `${baseUrl}/incidents/report`,
      {
        serial_no: reportForm.serial_no,
        incident_type: reportForm.incident_type,
        severity: reportForm.severity,
        description: reportForm.description.trim()
      },
      config
    )
    closeReportModal()
    await refreshAll()
  } catch (err: any) {
    if (err.response?.status === 401) {
      router.push("/login")
      return
    }
    console.error("Failed to report incident:", err)
    modalError.value = err.response?.data?.detail || "Unable to report the incident."
  } finally {
    submitting.value = false
  }
}

async function fetchIncidentHistory() {
  historyLoading.value = true
  try {
    const config = getAuthConfig()
    if (!config) return

    const params: Record<string, any> = {
      page: historyPage.value,
      page_size: historyPageSize.value,
      sort: historyFilters.sort
    }
    if (historyFilters.search.trim()) params.search = historyFilters.search.trim()
    if (historyFilters.incident_type) params.incident_type = historyFilters.incident_type
    if (historyFilters.severity) params.severity = historyFilters.severity
    if (historyFilters.date_from) params.date_from = historyFilters.date_from
    if (historyFilters.date_to) params.date_to = historyFilters.date_to

    const response = await axios.get(`${baseUrl}/incidents/history`, {
      ...config,
      params
    })
    const data = response.data
    if (Array.isArray(data)) {
      incidentHistory.value = data
      historyTotal.value = data.length
    } else {
      incidentHistory.value = data.items || data.records || data.results || []
      historyTotal.value = Number(data.total) || Number(data.total_count) || incidentHistory.value.length
    }
  } catch (err: any) {
    if (err.response?.status === 401) {
      router.push("/login")
      return
    }
    console.error("Failed to load incident history:", err)
    incidentHistory.value = []
    historyTotal.value = 0
  } finally {
    historyLoading.value = false
  }
}

async function refreshAll() {
  await Promise.all([
    fetchSecurityBreaches(),
    fetchIncidents(),
    fetchIncidentHistory()
  ])
}

function applyHistoryFilters() {
  historyPage.value = 1
  fetchIncidentHistory()
}

function clearHistoryFilters() {
  historyFilters.search = ""
  historyFilters.incident_type = ""
  historyFilters.severity = ""
  historyFilters.date_from = ""
  historyFilters.date_to = ""
  historyFilters.sort = "newest"
  historyPage.value = 1
  fetchIncidentHistory()
}

function changeHistoryPage(page: number) {
  if (page < 1 || page > historyTotalPages.value) return
  historyPage.value = page
  fetchIncidentHistory()
}

watch(historyPageSize, () => {
  historyPage.value = 1
  fetchIncidentHistory()
})

onMounted(refreshAll)
</script>

<style scoped>
.incidents-page {
  min-height: 100%;
  padding: 32px 40px;
  background: var(--content-bg, #0b0c10);
  color: var(--text-primary, #e2e8f0);
  font-family: inherit;
}

.incidents-main {
  max-width: 1400px;
  margin: 0 auto;
}

/* HEADER */
.incidents-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 28px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--accent, #b8925a);
  margin-bottom: 6px;
}

.live-pulse {
  width: 7px;
  height: 7px;
  background: #ef4444;
  border-radius: 50%;
  box-shadow: 0 0 8px #ef4444;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary, #ffffff);
  margin: 0 0 6px 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-muted, #64748b);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* BUTTONS */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn.primary {
  background: var(--button-bg, #1e293b);
  border: 1px solid var(--border-main, #334155);
  color: var(--accent, #38bdf8);
}

.btn.primary:hover:not(:disabled) {
  background: var(--hover-bg, #334155);
}

.btn.secondary {
  background: var(--surface, #12141a);
  border: 1px solid var(--border-main, #1e222d);
  color: var(--text-primary, #cbd5e1);
}

.btn.secondary:hover:not(:disabled) {
  background: var(--hover-bg, #1e222d);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.resolve-btn {
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.resolve-btn:hover {
  background: #2563eb;
  color: #ffffff;
}

/* COLLAPSIBLE HEADERS & CHEVRONS */
.collapsible-header {
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}

.collapsible-header:hover {
  background: var(--hover-bg, rgba(255, 255, 255, 0.04));
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.expand-chevron {
  font-size: 15px;
  color: var(--accent, #f59e0b);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  cursor: pointer;
  font-weight: 700;
  transition: transform 0.15s ease;
}

.collapsible-header:hover .expand-chevron,
.history-card-top:hover .expand-chevron {
  transform: scale(1.25);
}

/* BREACH PANEL (RED HERO) */
.breach-panel {
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.05);
}

.breach-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(239, 68, 68, 0.08);
  border-bottom: 1px solid rgba(239, 68, 68, 0.2);
}

.breach-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.shield-icon {
  font-size: 22px;
}

.breach-title h3 {
  margin: 0;
  font-size: 15px;
  color: #ef4444;
  font-weight: 700;
}

.breach-title p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
}

.breach-badge {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 4px 10px;
  border-radius: 4px;
  font-family: monospace;
}

.breach-crit {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.35);
}

.breach-ok {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.breach-empty {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
}

.ok-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
}

.breach-empty strong {
  color: var(--text-primary, #f1f5f9);
  font-size: 14px;
  display: block;
}

.breach-empty p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-muted, #64748b);
}

.breach-desc strong {
  display: block;
  font-size: 12px;
  color: #ef4444;
  font-family: monospace;
}

.breach-desc span {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

/* PANELS & TABLES */
.panel {
  background: var(--surface, #12141a);
  border: 1px solid var(--border-main, #1e222d);
  border-radius: 10px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-main, #1e222d);
  background: var(--surface-2, transparent);
}

.sub-eyebrow {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.08em;
}

.panel-title {
  margin: 3px 0 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #ffffff);
}

.feed-tag {
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.feed-tag code {
  color: var(--accent, #38bdf8);
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  background: var(--table-header, rgba(0, 0, 0, 0.2));
  color: var(--text-muted, #64748b);
  font-size: 10px;
  font-weight: 700;
  padding: 10px 18px;
  border-bottom: 1px solid var(--border-main, #1e222d);
  letter-spacing: 0.05em;
  text-align: left;
}

.data-table td {
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-main, #181b24);
  color: var(--text-muted, #94a3b8);
  vertical-align: middle;
}

.data-table tr:hover {
  background: var(--hover-bg, rgba(255, 255, 255, 0.02));
}

.breach-row {
  background: rgba(239, 68, 68, 0.03);
}

/* BADGES & PILLS */
.node-pill {
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent, #f59e0b);
  background: rgba(184, 146, 90, 0.12);
  border: 1px solid rgba(184, 146, 90, 0.3);
  padding: 2px 7px;
  border-radius: 4px;
}

.severity-badge {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 4px;
  text-transform: uppercase;
}

.severity-badge.critical,
.severity-badge.high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.severity-badge.medium {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.severity-badge.low {
  background: rgba(100, 116, 139, 0.15);
  color: var(--text-muted, #94a3b8);
}

.type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}

.type-badge.missing {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.type-badge.damaged {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.status-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}

.status-pill.open {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.status-pill.resolved {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

/* HISTORY ACCORDION & FILTERS */
.history-total-tag {
  font-family: monospace;
  font-size: 11px;
  color: var(--accent, #f59e0b);
  font-weight: 700;
}

.history-filter-strip {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  background: var(--surface-2, rgba(0, 0, 0, 0.15));
  border-bottom: 1px solid var(--border-main, #1e222d);
  flex-wrap: wrap;
}

.filter-group-search {
  flex: 1;
  min-width: 220px;
}

.dark-input,
.dark-select {
  background: var(--content-bg, #12141a);
  border: 1px solid var(--border-main, #1e222d);
  border-radius: 6px;
  padding: 7px 12px;
  color: var(--text-primary, #f1f5f9);
  font-size: 12px;
  outline: none;
}

.dark-input:focus,
.dark-select:focus {
  border-color: var(--accent, #3b82f6);
}

.date-input {
  width: 130px;
}

.history-feed {
  display: flex;
  flex-direction: column;
}

.history-card {
  border-bottom: 1px solid var(--border-main, #181b24);
  transition: background 0.15s ease;
}

.history-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
}

.history-card-top:hover {
  background: var(--hover-bg, rgba(255, 255, 255, 0.03));
}

.history-card.is-expanded {
  background: var(--hover-bg, rgba(255, 255, 255, 0.02));
}

.history-card-body {
  padding: 0 20px 16px 36px;
}

.history-id-block {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.history-tag {
  color: var(--accent, #f59e0b);
  font-family: monospace;
  font-weight: 700;
  font-size: 12px;
}

.history-acc {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #f1f5f9);
}

.history-serial {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.history-badges {
  display: flex;
  gap: 6px;
}

.history-meta-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--surface-2, rgba(0, 0, 0, 0.15));
  border: 1px solid var(--border-main, rgba(255, 255, 255, 0.05));
  border-radius: 6px;
}

.meta-label {
  display: block;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}

.meta-val {
  font-size: 11px;
  color: var(--text-primary, #cbd5e1);
}

.history-note-box {
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--surface-2, rgba(0, 0, 0, 0.15));
  border-left: 2px solid var(--border-main, #334155);
  border-radius: 0 6px 6px 0;
}

.history-note-box.resolution {
  border-left-color: var(--accent, #f59e0b);
}

.note-label {
  display: block;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.history-note-box p {
  margin: 0;
  font-size: 12px;
  color: var(--text-primary, #cbd5e1);
  line-height: 1.5;
}

/* PAGINATION */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--surface-2, rgba(0, 0, 0, 0.15));
  border-top: 1px solid var(--border-main, #1e222d);
}

.btn-page {
  background: var(--surface, #161822);
  border: 1px solid var(--border-main, #282d3c);
  color: var(--text-primary, #cbd5e1);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.btn-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-count {
  font-family: monospace;
  font-size: 11px;
  color: var(--accent, #38bdf8);
  margin: 0 8px;
}

/* MODAL */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.dark-modal {
  width: min(540px, 92%);
  background: var(--surface, #12141a);
  border: 1px solid var(--border-main, #1e222d);
  border-radius: 10px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-main, #1e222d);
}

.modal-header h3 {
  margin: 0;
  font-size: 15px;
  color: var(--text-primary, #ffffff);
}

.close-x {
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  font-size: 16px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  background: var(--surface-2, rgba(0, 0, 0, 0.15));
  border-top: 1px solid var(--border-main, #1e222d);
  border-radius: 0 0 10px 10px;
}

.modal-item-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 16px;
  padding: 10px;
  background: var(--surface-2, rgba(0, 0, 0, 0.15));
  border: 1px solid var(--border-main, rgba(255, 255, 255, 0.05));
  border-radius: 6px;
}

.modal-item-summary span {
  display: block;
  font-size: 9px;
  color: var(--text-muted, #64748b);
  font-weight: 700;
}

.modal-item-summary strong {
  font-size: 13px;
  color: var(--text-primary, #f1f5f9);
}

.modal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-block.full {
  grid-column: span 2;
}

.field-block label {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.05em;
}

.dark-textarea {
  width: 100%;
  background: var(--content-bg, #0e1015);
  border: 1px solid var(--border-main, #1e222d);
  border-radius: 6px;
  padding: 10px;
  color: var(--text-primary, #f1f5f9);
  font-size: 12px;
  resize: vertical;
  outline: none;
}

.dark-textarea:focus {
  border-color: var(--accent, #3b82f6);
}

/* UTILITIES */
.font-mono { font-family: monospace; }
.text-amber { color: var(--accent, #f59e0b); }
.text-cyan { color: #38bdf8; }
.text-muted { color: var(--text-muted, #64748b); }
.text-xs { font-size: 11px; }

.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted, #64748b);
  padding: 30px;
}

.state.compact {
  padding: 20px;
  flex-direction: row;
}

.spinner-dot {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-main, #1e222d);
  border-top-color: var(--accent, #3b82f6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinning {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.alert.error {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border-radius: 6px;
  font-size: 12px;
  margin-top: 10px;
}
</style>