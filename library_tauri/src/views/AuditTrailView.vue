<template>
  <div class="audit-page-container">
    <header class="workspace-title-block">
      <div class="header-meta">SYSTEM MANAGEMENT // SECURITY</div>
      <h1 class="page-title">Audit Trail Ledger</h1>
      <p class="page-subtitle">
        Immutable transactional tracking history. Click any telemetry row sequence to view precise field differences, reason parameters, and operator context.
      </p>
    </header>

    <div class="filter-controls-row">
      <input 
        type="text" 
        v-model="actorQuery" 
        @input="fetchLogs" 
        placeholder="Filter by operator username..." 
        class="search-input" 
      />
      <select v-model="actionQuery" @change="fetchLogs" class="filter-dropdown">
        <option value="">-- ALL ACTIONS --</option>
        <option value="CREATE">CREATE</option>
        <option value="UPDATE">UPDATE</option>
        <option value="DELETE">DELETE</option>
      </select>
    </div>

    <div class="table-card">
      <table class="audit-data-table">
        <thead>
          <tr>
            <th style="width: 50px;"></th>
            <th>TIMESTAMP</th>
            <th>OPERATOR</th>
            <th>ROLE</th>
            <th>ACTION</th>
            <th>TARGET ID</th>
            <th class="text-left">SUMMARY COMPONENT</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="table-notice">Retrieving encrypted log sequence...</td>
          </tr>
          <tr v-else-if="logs.length === 0">
            <td colspan="7" class="table-notice">No actionable log telemetry entries recorded.</td>
          </tr>
          
          <template v-else v-for="log in logs" :key="log.id">
            <tr class="table-row main-row" @click="toggleRow(log.id)" :class="{ 'row-active': expandedRows.has(log.id) }">
              <td>
                <span class="chevron-icon" :class="{ 'chevron-rotated': expandedRows.has(log.id) }">▶</span>
              </td>
              <td class="font-mono text-muted unique-size">{{ log.timestamp }}</td>
              <td class="font-bold text-accent">{{ log.actor_username }}</td>
              <td class="font-mono text-magenta unique-size">{{ log.actor_role }}</td>
              <td>
                <span class="type-badge" :class="log.action_type.toLowerCase()">
                  {{ log.action_type }}
                </span>
              </td>
              <td class="font-mono text-blue font-bold">#{{ log.target_id || 'SYSTEM' }}</td>
              <td class="text-left desc-cell">{{ log.summary }}</td>
            </tr>

            <tr v-if="expandedRows.has(log.id)" class="details-expansion-tray">
              <td colspan="7">
                <div class="tray-inner-wrapper">
                  <div class="meta-grid-specs">
                    <div class="spec-card">
                      <span class="spec-label">OPERATOR ACCOUNT:</span>
                      <span class="spec-value text-accent">{{ log.actor_username }} (ID: #{{ log.user_id }})</span>
                    </div>
                    <div class="spec-card">
                      <span class="spec-label">NETWORK ORIGIN:</span>
                      <span class="spec-value text-blue">{{ log.ip_address }}</span>
                    </div>
                    <div class="spec-card">
                      <span class="spec-label">TERMINAL SPECIFICATION:</span>
                      <span class="spec-value text-muted">{{ log.device_id }}</span>
                    </div>
                    <div class="spec-card" style="grid-column: span 3;">
                      <span class="spec-label text-warning">OPERATIONAL JUSTIFICATION / REASON:</span>
                      <span class="spec-value justification-text">{{ log.change_reason }}</span>
                    </div>
                  </div>

                  <div class="diff-telemetry-section">
                    <div class="diff-header-title">FIELD DIFF MONITOR TRACKING VALUES:</div>
                    <ul class="diff-bullet-list" v-if="log.detailed_diffs && log.detailed_diffs.length > 0">
                      <li v-for="(diff, index) in log.detailed_diffs" :key="index" class="diff-item-line">
                        {{ diff }}
                      </li>
                    </ul>
                    <div v-else class="text-muted font-italic unique-size" style="padding-left: 4px;">
                      No field variances detected or row layout structural definition change.
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(true)
const logs = ref([])
const actorQuery = ref('')
const actionQuery = ref('')
const expandedRows = ref(new Set())

async function fetchLogs() {
  loading.value = true
  try {
    let url = `/status_audit/system-logs?limit=100`
    if (actionQuery.value) url += `&action_filter=${actionQuery.value}`
    if (actorQuery.value) url += `&actor_filter=${actorQuery.value}`
    
    const response = await axios.get(url)
    logs.value = response.data
  } catch (err) {
    console.error("Failed to parse system log footprint arrays:", err)
  } finally {
    loading.value = false
  }
}

function toggleRow(id) {
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id)
  } else {
    expandedRows.value.add(id)
  }
}

onMounted(() => fetchLogs())
</script>

<style scoped>
.audit-page-container {
  padding: 40px;
  background-color: #0f1013;
  min-height: 100%;
  color: #e2e4e9;
}

.workspace-title-block {
  margin-bottom: 32px;
}

.header-meta {
  font-size: 11px;
  font-weight: 700;
  color: #d97706;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 13px;
  color: #626a7a;
  margin: 0;
  max-width: 700px;
  line-height: 1.5;
}

.filter-controls-row {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.search-input {
  flex-grow: 1;
  background-color: #16181f;
  border: 1px solid #22252e;
  border-radius: 6px;
  padding: 12px 16px;
  color: #ffffff;
  font-size: 13px;
}

.search-input:focus, .filter-dropdown:focus {
  outline: none;
  border-color: #d97706;
}

.filter-dropdown {
  width: 220px;
  background-color: #16181f;
  border: 1px solid #22252e;
  border-radius: 6px;
  padding: 12px 16px;
  color: #ffffff;
  font-size: 13px;
}

.table-card {
  background-color: #16181f;
  border: 1px solid #22252e;
  border-radius: 8px;
  overflow: hidden;
}

.audit-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.audit-data-table th {
  background-color: #12141a;
  color: #626a7a;
  font-size: 11px;
  font-weight: 700;
  padding: 14px 20px;
  border-bottom: 1px solid #22252e;
  text-transform: uppercase;
  text-align: center;
}

.audit-data-table td {
  padding: 14px 20px;
  border-bottom: 1px solid #1c1f26;
  color: #a3a8b4;
  text-align: center;
  vertical-align: middle;
}

.main-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.main-row:hover {
  background-color: rgba(255, 255, 255, 0.02);
}

.row-active {
  background-color: rgba(217, 119, 6, 0.03) !important;
}

.chevron-icon {
  display: inline-block;
  font-size: 9px;
  color: #626a7a;
  transition: transform 0.2s ease;
}

.chevron-rotated {
  transform: rotate(90deg);
  color: #d97706;
}

.table-notice {
  padding: 32px;
  color: #626a7a;
  font-style: italic;
}

.type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  display: inline-block;
}

.type-badge.create { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.type-badge.update { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.type-badge.delete { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

.desc-cell {
  color: #cbd5e1 !important;
  line-height: 1.4;
}

/* Expansion Details Styling */
.details-expansion-tray td {
  padding: 0 !important;
  background-color: #111217;
  border-bottom: 1px solid #22252e;
}

.tray-inner-wrapper {
  padding: 24px 40px;
  text-align: left;
}

.meta-grid-specs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.spec-card {
  background-color: #16181f;
  border: 1px solid #22252e;
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.spec-label {
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
  letter-spacing: 0.5px;
}

.spec-value {
  font-size: 13px;
  font-family: monospace;
}

.justification-text {
  font-family: inherit !important;
  color: #e2e4e9;
  line-height: 1.4;
}

.diff-telemetry-section {
  background-color: #16181f;
  border: 1px solid #22252e;
  border-radius: 6px;
  padding: 16px;
}

.diff-header-title {
  font-size: 11px;
  font-weight: 700;
  color: #626a7a;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.diff-bullet-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.diff-item-line {
  font-family: monospace;
  font-size: 12px;
  color: #10b981;
  padding-left: 12px;
  position: relative;
}

.diff-item-line::before {
  content: "➔";
  position: absolute;
  left: 0;
  color: #d97706;
}

.text-left { text-align: left !important; }
.font-mono { font-family: monospace; }
.font-bold { font-weight: 600; }
.text-muted { color: #626a7a; }
.text-warning { color: #d97706; }
.text-accent { color: #f3f4f6; }
.text-magenta { color: #f472b6; }
.text-blue { color: #60a5fa; }
.unique-size { font-size: 12px; }
</style>