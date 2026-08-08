<template>
  <div class="incidents-page">
    <main class="incidents-main">
      <header class="incidents-header">
        <div>
          <div class="eyebrow">ARCHIVE MANAGEMENT</div>
          <h1>Archive Incidents</h1>
          <p>Review and resolve open archive incidents.</p>
        </div>
        <div class="header-actions">
          <button class="btn secondary" :disabled="loading" @click="fetchIncidents">
            {{ loading ? "Refreshing..." : "Refresh" }}
          </button>
          <button class="btn primary" @click="openReportModal">Report Incident</button>
        </div>
      </header>

      <div v-if="errorMessage" class="alert error">{{ errorMessage }}</div>

      <section class="summary-card">
        <div class="summary-count">
          <span>OPEN INCIDENTS</span><strong>{{ incidents.length }}</strong>
        </div>
        <div class="summary-meta">Live data from <code>/incidents/open</code></div>
      </section>

      <section class="panel">
        <div v-if="loading" class="state">Loading archive incidents...</div>

        <div v-else-if="incidents.length === 0" class="state empty">
          <strong>No open incidents</strong>
          <span>The archive currently has no unresolved incidents.</span>
        </div>

        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Incident</th><th>Serial</th><th>Type</th><th>Severity</th>
                <th>Reported</th><th>Status</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="incident in incidents" :key="incident.incident_id">
                <td class="incident-id">#{{ incident.incident_id }}</td>
                <td class="serial">{{ incident.serial_no }}</td>
                <td><span :class="['type-badge', incident.incident_type.toLowerCase()]">{{ incident.incident_type }}</span></td>
                <td><span :class="['severity-badge', incident.severity.toLowerCase()]">{{ incident.severity }}</span></td>
                <td class="date-cell">{{ formatDate(incident.reported_at) }}</td>
                <td><span class="status-badge">{{ incident.status }}</span></td>
                <td class="action-col">
                  <button class="btn resolve" @click="openResolveModal(incident)">Resolve</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <div v-if="resolveIncident" class="modal-backdrop" @click.self="closeResolveModal">
      <section class="modal">
        <div class="modal-header">
          <div>
            <div class="eyebrow">INCIDENT #{{ resolveIncident.incident_id }}</div>
            <h2>Resolve Incident</h2>
          </div>
          <button class="close-btn" @click="closeResolveModal">×</button>
        </div>

        <div class="incident-detail">
          <div><span>Serial</span><strong>{{ resolveIncident.serial_no }}</strong></div>
          <div><span>Type</span><strong>{{ resolveIncident.incident_type }}</strong></div>
          <div><span>Severity</span><strong>{{ resolveIncident.severity }}</strong></div>
        </div>

        <label class="field">
          <span>Resolution notes</span>
          <textarea v-model="resolutionNotes" rows="5" placeholder="Describe why this incident is being resolved..."></textarea>
        </label>

        <div v-if="modalError" class="alert error">{{ modalError }}</div>

        <div class="modal-actions">
          <button class="btn secondary" :disabled="submitting" @click="closeResolveModal">Cancel</button>
          <button class="btn primary" :disabled="submitting || !resolutionNotes.trim()" @click="resolveSelectedIncident">
            {{ submitting ? "Resolving..." : "Resolve Incident" }}
          </button>
        </div>
      </section>
    </div>

    <div v-if="showReportModal" class="modal-backdrop" @click.self="closeReportModal">
      <section class="modal">
        <div class="modal-header">
          <div><div class="eyebrow">ARCHIVE INCIDENT</div><h2>Report Incident</h2></div>
          <button class="close-btn" @click="closeReportModal">×</button>
        </div>

        <div v-if="modalError" class="alert error">{{ modalError }}</div>

        <div class="form-grid">
          <label class="field">
            <span>Serial number</span>
            <input v-model.number="reportForm.serial_no" type="number" min="1" placeholder="Item serial number" />
          </label>
          <label class="field">
            <span>Incident type</span>
            <select v-model="reportForm.incident_type">
              <option value="MISSING">MISSING</option>
              <option value="DAMAGED">DAMAGED</option>
            </select>
          </label>
          <label class="field">
            <span>Severity</span>
            <select v-model="reportForm.severity">
              <option value="LOW">LOW</option><option value="MEDIUM">MEDIUM</option><option value="HIGH">HIGH</option>
            </select>
          </label>
          <label class="field full">
            <span>Description</span>
            <textarea v-model="reportForm.description" rows="5" placeholder="Describe the incident..."></textarea>
          </label>
        </div>

        <div class="modal-actions">
          <button class="btn secondary" :disabled="submitting" @click="closeReportModal">Cancel</button>
          <button class="btn primary" :disabled="submitting || !reportForm.serial_no || !reportForm.description.trim()" @click="reportIncident">
            {{ submitting ? "Reporting..." : "Report Incident" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
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

const router = useRouter()
const authStore = useAuthStore()
const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

const incidents = ref<Incident[]>([])
const loading = ref(true)
const submitting = ref(false)
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
  const token = authStore.accessToken || authStore.access_token
  if (!token) {
    router.push("/login")
    return null
  }
  return { headers: { Authorization: `Bearer ${token}` } }
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
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric", month: "short", day: "2-digit",
    hour: "2-digit", minute: "2-digit"
  }).format(date)
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
    await fetchIncidents()
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
//   if (submitting.value) return
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
    await axios.post(`${baseUrl}/incidents/report`, {
      serial_no: reportForm.serial_no,
      incident_type: reportForm.incident_type,
      severity: reportForm.severity,
      description: reportForm.description.trim()
    }, config)
    closeReportModal()
    await fetchIncidents()
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

onMounted(fetchIncidents)
</script>

<style scoped>
.incidents-page {
  min-height: 100%;
  box-sizing: border-box;
  padding: 32px;
  background: var(--content-bg, #0a0908);
  color: var(--text-primary, #f5eee0);
}
.incidents-main { width: 100%; max-width: 1500px; margin: 0 auto; }
.incidents-header { display:flex; justify-content:space-between; align-items:flex-end; gap:24px; margin-bottom:24px; }
.eyebrow { color:var(--accent,#b8925a); font-size:11px; font-weight:700; letter-spacing:2px; margin-bottom:8px; }
h1,h2 { margin:0; color:var(--text-primary,#f5eee0); font-family:Georgia,serif; font-weight:500; }
h1 { font-size:34px; } h2 { font-size:25px; }
.incidents-header p { margin:8px 0 0; color:var(--text-muted,#b8a88a); font-size:14px; }
.header-actions,.modal-actions { display:flex; align-items:center; gap:10px; }
.btn { border:1px solid var(--border-main,rgba(184,146,90,.18)); border-radius:7px; padding:10px 16px; font:inherit; font-size:13px; font-weight:650; cursor:pointer; }
.btn:disabled { opacity:.45; cursor:not-allowed; }
.btn.primary { background:var(--button-bg,#1f221b); color:var(--button-text,#f5eee0); }
.btn.secondary { background:var(--surface,#141210); color:var(--text-primary,#f5eee0); }
.btn.resolve { padding:7px 12px; background:transparent; color:var(--accent,#b8925a); border-color:var(--accent,#b8925a); }
.summary-card,.panel { background:var(--surface,#141210); border:1px solid var(--border-main,rgba(184,146,90,.12)); border-radius:12px; box-shadow:var(--shadow,0 8px 30px rgba(0,0,0,.45)); }
.summary-card { display:flex; justify-content:space-between; align-items:center; padding:20px 24px; margin-bottom:18px; }
.summary-count { display:flex; align-items:baseline; gap:16px; }
.summary-count span { color:var(--text-muted,#b8a88a); font-size:11px; font-weight:700; letter-spacing:1.5px; }
.summary-count strong { font:500 30px Georgia,serif; }
.summary-meta { color:var(--text-muted,#b8a88a); font-size:12px; }
.summary-meta code { color:var(--accent,#b8925a); }
.panel { overflow:hidden; }
.table-wrap { overflow-x:auto; }
table { width:100%; min-width:850px; border-collapse:collapse; }
th { background:var(--table-header,#1a1815); color:var(--text-muted,#b8a88a); padding:14px 16px; text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:1px; }
td { padding:16px; border-top:1px solid var(--border-main,rgba(184,146,90,.12)); font-size:13px; }
tbody tr:hover { background:var(--hover-bg,rgba(184,146,90,.08)); }
.incident-id { color:var(--accent,#b8925a); font-family:monospace; font-weight:700; }
.serial { font-family:monospace; }
.type-badge,.severity-badge,.status-badge { display:inline-flex; border-radius:999px; padding:5px 9px; font-size:10px; font-weight:800; letter-spacing:.6px; }
.type-badge.missing { background:rgba(220,38,38,.1); color:#dc2626; }
.type-badge.damaged { background:rgba(234,179,8,.12); color:#d89b00; }
.severity-badge.low { color:#6b7280; background:rgba(107,114,128,.12); }
.severity-badge.medium { color:#b7791f; background:rgba(183,121,31,.12); }
.severity-badge.high { color:#dc2626; background:rgba(220,38,38,.1); }
.status-badge { color:var(--accent,#b8925a); background:var(--active-bg,rgba(184,146,90,.15)); }
.date-cell { color:var(--text-muted,#b8a88a); }
.action-col { text-align:right; }
.state { min-height:300px; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:8px; color:var(--text-muted,#b8a88a); font-size:14px; }
.state.empty strong { color:var(--text-primary,#f5eee0); font:500 20px Georgia,serif; }
.alert { padding:12px 14px; border-radius:8px; margin-bottom:18px; font-size:13px; }
.alert.error { color:#dc2626; background:rgba(220,38,38,.08); border:1px solid rgba(220,38,38,.2); }
.modal-backdrop { position:fixed; inset:0; z-index:1000; display:flex; align-items:center; justify-content:center; padding:24px; background:rgba(0,0,0,.62); }
.modal { width:min(620px,100%); max-height:calc(100vh - 48px); overflow-y:auto; box-sizing:border-box; padding:24px; background:var(--surface,#141210); color:var(--text-primary,#f5eee0); border:1px solid var(--border-main,rgba(184,146,90,.18)); border-radius:14px; box-shadow:0 24px 70px rgba(0,0,0,.5); }
.modal-header { display:flex; justify-content:space-between; gap:20px; margin-bottom:22px; }
.close-btn { width:34px; height:34px; border:1px solid var(--border-main,rgba(184,146,90,.18)); border-radius:7px; background:transparent; color:var(--text-muted,#b8a88a); font-size:22px; cursor:pointer; }
.incident-detail { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:20px; }
.incident-detail > div { padding:12px; border:1px solid var(--border-main,rgba(184,146,90,.12)); border-radius:8px; background:var(--surface-2,#1b1815); }
.incident-detail span { display:block; color:var(--text-muted,#b8a88a); font-size:10px; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px; }
.incident-detail strong { font-size:13px; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.field { display:flex; flex-direction:column; gap:7px; }
.field.full { grid-column:1/-1; }
.field > span { color:var(--text-muted,#b8a88a); font-size:11px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; }
.field input,.field select,.field textarea { width:100%; box-sizing:border-box; background:var(--content-bg,#0a0908); color:var(--text-primary,#f5eee0); border:1px solid var(--border-main,rgba(184,146,90,.18)); border-radius:7px; padding:10px 11px; font:inherit; font-size:13px; outline:none; }
.field input:focus,.field select:focus,.field textarea:focus { border-color:var(--accent,#b8925a); }
.field textarea { resize:vertical; min-height:110px; }
.modal-actions { justify-content:flex-end; margin-top:22px; }
@media(max-width:768px) {
  .incidents-page { padding:18px; }
  .incidents-header { align-items:flex-start; flex-direction:column; }
  .header-actions { width:100%; }
  .header-actions .btn { flex:1; }
  .summary-card { align-items:flex-start; flex-direction:column; gap:12px; }
  .incident-detail,.form-grid { grid-template-columns:1fr; }
  .field.full { grid-column:auto; }
  .modal-backdrop { padding:12px; }
  .modal { padding:18px; }
}
</style>
