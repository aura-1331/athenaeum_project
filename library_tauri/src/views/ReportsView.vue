<template>
  <div class="reports-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">SYSTEM MANAGEMENT // REPORTING</div>
        <h1>Reports</h1>
        <p>Review accession history and system activity.</p>
      </div>

      <button
        class="refresh-btn"
        type="button"
        :disabled="loading"
        @click="refreshCurrentReport"
      >
        <RefreshCw :size="16" :class="{ spinning: loading }" />
        Refresh
      </button>
    </header>

    <!-- REPORT TABS -->
    <div class="report-tabs">
      <button
        type="button"
        :class="{ active: activeReport === 'accessions' }"
        @click="switchReport('accessions')"
      >
        ACCESSIONS
      </button>

      <button
        type="button"
        :class="{ active: activeReport === 'activity' }"
        @click="switchReport('activity')"
      >
        ACTIVITY
      </button>
    </div>

    <!-- TOOLBAR -->
    <section class="toolbar">
      <div class="toolbar-left">
        <label>
          <span>SEARCH</span>
          <div class="search-box">
            <Search :size="15" />
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="
                activeReport === 'accessions'
                  ? 'Search accession or status...'
                  : 'Search action, entity or details...'
              "
            />
          </div>
        </label>
      </div>

      <div class="toolbar-right">
        <label>
          <span>ROWS</span>
          <select v-model.number="pageSize" @change="changePageSize">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </label>
      </div>
    </section>

    <!-- ERROR -->
    <div v-if="errorMessage" class="error-state">
      <AlertTriangle :size="17" />
      <span>{{ errorMessage }}</span>
    </div>

    <!-- LOADING -->
    <section v-if="loading" class="state-panel">
      <Loader2 :size="24" class="spinning" />
      <span>Loading report...</span>
    </section>

    <!-- ACCESSIONS -->
    <section v-else-if="activeReport === 'accessions'" class="report-panel">
      <div class="panel-heading">
        <div>
          <span class="panel-label">STATUS AUDIT</span>
          <h2>Accession History</h2>
        </div>

        <div class="record-count">
          {{ filteredAccessions.length }} visible
          <span>/ {{ totalRecords }} records</span>
        </div>
      </div>

      <div v-if="filteredAccessions.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ACCESSION</th>
              <th>OLD STATUS</th>
              <th>NEW STATUS</th>
              <th>CHANGED BY</th>
              <th>CHANGED AT</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="row in filteredAccessions" :key="accessionKey(row)">
              <td class="mono strong">{{ row.accession_no || "—" }}</td>

              <td>
                <span class="status-badge">
                  {{ row.old_status || "—" }}
                </span>
              </td>

              <td>
                <span class="status-badge new-status">
                  {{ row.new_status || "—" }}
                </span>
              </td>

              <td class="mono">
                {{ row.changed_by ?? "—" }}
              </td>

              <td class="mono muted">
                {{ formatDate(row.changed_at) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="empty-state">
        <FileText :size="25" />
        <strong>No accession records found</strong>
        <span>There are no records matching the current search.</span>
      </div>
    </section>

    <!-- ACTIVITY -->
    <section v-else class="report-panel">
      <div class="panel-heading">
        <div>
          <span class="panel-label">SYSTEM ACTIVITY</span>
          <h2>Activity Report</h2>
        </div>

        <div class="record-count">
          {{ filteredActivity.length }} visible
          <span>/ {{ totalRecords }} records</span>
        </div>
      </div>

      <div v-if="filteredActivity.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>USER</th>
              <th>ACTION</th>
              <th>ENTITY</th>
              <th>ENTITY ID</th>
              <th>DETAILS</th>
              <th>TIMESTAMP</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="row in filteredActivity" :key="row.log_id">
              <td class="mono strong">
                #{{ row.log_id }}
              </td>

              <td class="mono">
                {{ row.user_id ?? "—" }}
              </td>

              <td>
                <span class="action-badge">
                  {{ row.action || "—" }}
                </span>
              </td>

              <td class="mono">
                {{ row.entity || "—" }}
              </td>

              <td class="mono">
                {{ row.entity_id ?? "—" }}
              </td>

              <td class="details-cell">
                {{ row.details || "—" }}
              </td>

              <td class="mono muted">
                {{ formatDate(row.timestamp) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="empty-state">
        <Activity :size="25" />
        <strong>No activity records found</strong>
        <span>There are no records matching the current search.</span>
      </div>
    </section>

    <!-- PAGINATION -->
    <footer v-if="totalRecords > 0" class="pagination">
      <div class="pagination-info">
        Showing
        <strong>{{ pageStart }}</strong>
        –
        <strong>{{ pageEnd }}</strong>
        of
        <strong>{{ totalRecords }}</strong>
      </div>

      <div class="pagination-controls">
        <button
          type="button"
          :disabled="currentPage === 1 || loading"
          @click="goToPage(currentPage - 1)"
        >
          <ChevronLeft :size="16" />
          Previous
        </button>

        <span class="page-number">
          PAGE {{ currentPage }} / {{ totalPages }}
        </span>

        <button
          type="button"
          :disabled="currentPage >= totalPages || loading"
          @click="goToPage(currentPage + 1)"
        >
          Next
          <ChevronRight :size="16" />
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import axios from "axios"
import {
  Activity,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  RefreshCw,
  Search
} from "lucide-vue-next"

interface AccessionRecord {
  accession_no: string | null
  old_status: string | null
  new_status: string | null
  changed_by: number | null
  changed_at: string | null
}

interface ActivityRecord {
  log_id: number
  user_id: number
  action: string
  entity: string
  entity_id: number | null
  details: string | null
  timestamp: string | null
}

const activeReport = ref<"accessions" | "activity">("accessions")

const accessions = ref<AccessionRecord[]>([])
const activity = ref<ActivityRecord[]>([])

const loading = ref(false)
const errorMessage = ref("")

const currentPage = ref(1)
const pageSize = ref(50)

const accessionTotal = ref(0)
const activityTotal = ref(0)

const searchQuery = ref("")

const totalRecords = computed(() =>
  activeReport.value === "accessions"
    ? accessionTotal.value
    : activityTotal.value
)

const totalPages = computed(() =>
  Math.max(1, Math.ceil(totalRecords.value / pageSize.value))
)

const pageStart = computed(() => {
  if (!totalRecords.value) return 0
  return (currentPage.value - 1) * pageSize.value + 1
})

const pageEnd = computed(() => {
  if (!totalRecords.value) return 0
  return Math.min(
    currentPage.value * pageSize.value,
    totalRecords.value
  )
})

const filteredAccessions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) return accessions.value

  return accessions.value.filter((row) =>
    [
      row.accession_no,
      row.old_status,
      row.new_status,
      row.changed_by,
      row.changed_at
    ]
      .filter((value) => value !== null && value !== undefined)
      .some((value) =>
        String(value).toLowerCase().includes(query)
      )
  )
})

const filteredActivity = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) return activity.value

  return activity.value.filter((row) =>
    [
      row.log_id,
      row.user_id,
      row.action,
      row.entity,
      row.entity_id,
      row.details,
      row.timestamp
    ]
      .filter((value) => value !== null && value !== undefined)
      .some((value) =>
        String(value).toLowerCase().includes(query)
      )
  )
})

async function fetchAccessions() {
  const offset = (currentPage.value - 1) * pageSize.value

  const response = await axios.get("/reports/accessions", {
    params: {
      limit: pageSize.value,
      offset
    }
  })

  accessions.value = response.data.items || []
  accessionTotal.value = response.data.total || 0
}

async function fetchActivity() {
  const offset = (currentPage.value - 1) * pageSize.value

  const response = await axios.get("/reports/activity", {
    params: {
      limit: pageSize.value,
      offset
    }
  })

  activity.value = response.data.items || []
  activityTotal.value = response.data.total || 0
}

async function fetchReport() {
  loading.value = true
  errorMessage.value = ""

  try {
    if (activeReport.value === "accessions") {
      await fetchAccessions()
    } else {
      await fetchActivity()
    }
  } catch (error: any) {
    console.error("Reports error:", error)

    errorMessage.value =
      error.response?.data?.detail ||
      "Unable to load report."
  } finally {
    loading.value = false
  }
}

async function switchReport(
  report: "accessions" | "activity"
) {
  if (activeReport.value === report) return

  activeReport.value = report
  currentPage.value = 1
  searchQuery.value = ""

  await fetchReport()
}

async function goToPage(page: number) {
  if (
    page < 1 ||
    page > totalPages.value ||
    page === currentPage.value
  ) {
    return
  }

  currentPage.value = page
  await fetchReport()
}

async function changePageSize() {
  currentPage.value = 1
  await fetchReport()
}

async function refreshCurrentReport() {
  await fetchReport()
}

function accessionKey(row: AccessionRecord) {
  return `${row.accession_no}-${row.changed_at}-${row.changed_by}`
}

function formatDate(value: string | null) {
  if (!value) return "—"

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleString()
}

watch(searchQuery, () => {
  // Search is intentionally client-side within the current page.
  // Server-side filtering can be added later when needed.
})

onMounted(() => {
  fetchReport()
})
</script>

<style scoped>
.reports-page {
  min-height: 100%;
  padding: 32px;
  background: #0f1013;
  color: #e5e7eb;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.eyebrow {
  margin-bottom: 8px;
  color: #d97706;
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.page-header h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-header p {
  margin: 7px 0 0;
  color: #8b909b;
  font-size: 13px;
}

.refresh-btn,
.pagination button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid #2a2d35;
  background: #16181f;
  color: #cfd2d8;
  padding: 9px 13px;
  font-size: 12px;
  cursor: pointer;
}

.refresh-btn:hover,
.pagination button:hover:not(:disabled) {
  border-color: #d97706;
  color: #f59e0b;
}

.refresh-btn:disabled,
.pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.report-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 18px;
  border-bottom: 1px solid #22252e;
}

.report-tabs button {
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #777d88;
  padding: 11px 18px;
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  cursor: pointer;
}

.report-tabs button:hover {
  color: #cfd2d8;
}

.report-tabs button.active {
  border-bottom-color: #d97706;
  color: #f59e0b;
}

.toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
}

.toolbar label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toolbar label > span {
  color: #676d78;
  font-family: monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 360px;
  border: 1px solid #292c34;
  background: #13151a;
  padding: 9px 11px;
  color: #666c77;
}

.search-box:focus-within {
  border-color: #8a5009;
}

.search-box input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #e5e7eb;
  font-size: 12px;
}

.search-box input::placeholder {
  color: #555b65;
}

.toolbar select {
  min-width: 90px;
  border: 1px solid #292c34;
  background: #13151a;
  color: #cfd2d8;
  padding: 9px 10px;
  outline: none;
}

.error-state {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 14px;
  border: 1px solid #5b2525;
  background: #211417;
  color: #ef9a9a;
  padding: 12px 14px;
  font-size: 12px;
}

.state-panel,
.empty-state {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid #22252e;
  background: #16181f;
  color: #747a85;
}

.empty-state strong {
  color: #b9bdc5;
  font-size: 13px;
}

.empty-state span {
  font-size: 12px;
}

.report-panel {
  border: 1px solid #22252e;
  background: #16181f;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 20px;
  border-bottom: 1px solid #22252e;
}

.panel-label {
  display: block;
  margin-bottom: 5px;
  color: #676d78;
  font-family: monospace;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.panel-heading h2 {
  margin: 0;
  color: #e4e6ea;
  font-size: 16px;
  font-weight: 600;
}

.record-count {
  color: #d2d5db;
  font-family: monospace;
  font-size: 11px;
}

.record-count span {
  color: #666c77;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 850px;
}

th {
  padding: 10px 14px;
  border-bottom: 1px solid #252832;
  background: #13151a;
  color: #6f7580;
  font-family: monospace;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-align: left;
  white-space: nowrap;
}

td {
  padding: 12px 14px;
  border-bottom: 1px solid #20232b;
  color: #bfc3ca;
  font-size: 12px;
  vertical-align: middle;
}

tbody tr:hover {
  background: #191b21;
}

tbody tr:last-child td {
  border-bottom: 0;
}

.mono {
  font-family: monospace;
  font-size: 11px;
}

.strong {
  color: #e1e3e7;
  font-weight: 600;
}

.muted {
  color: #777d88;
}

.status-badge,
.action-badge {
  display: inline-flex;
  align-items: center;
  border: 1px solid #30343d;
  background: #13151a;
  color: #aeb3bc;
  padding: 4px 7px;
  font-family: monospace;
  font-size: 9px;
  letter-spacing: 0.04em;
}

.new-status {
  border-color: #59400d;
  color: #e4a12a;
}

.action-badge {
  border-color: #34363f;
  color: #c7cad0;
}

.details-cell {
  max-width: 360px;
  color: #8d929c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-top: 14px;
}

.pagination-info {
  color: #777d88;
  font-family: monospace;
  font-size: 10px;
}

.pagination-info strong {
  color: #bfc3ca;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-number {
  min-width: 110px;
  color: #777d88;
  font-family: monospace;
  font-size: 10px;
  text-align: center;
}

.spinning {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 800px) {
  .reports-page {
    padding: 20px;
  }

  .page-header,
  .toolbar,
  .pagination {
    flex-direction: column;
    align-items: stretch;
  }

  .search-box {
    width: 100%;
  }

  .refresh-btn {
    align-self: flex-start;
  }

  .pagination-controls {
    justify-content: space-between;
  }
}
</style>