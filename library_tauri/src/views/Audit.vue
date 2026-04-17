<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue"
import axios from 'axios' // 🚀 1. Import the Hybrid Engine

const rows = ref([])
const loading = ref(false)

let timer = null
let lastTopId = null 

// 🚀 2. THE HYBRID LOAD FUNCTION
async function loadAudit(initial = false) {
  try {
    if (initial) loading.value = true

    // ✅ Clean Axios call: No manual headers, no full URL
    const res = await axios.get("/status_audit/")
    
    // Axios puts the JSON data inside .data
    const incoming = res.data || []

    if (!incoming.length) {
      rows.value = []
      return
    }

    const newestId = incoming[0].id

    /*
      Only update UI when something actually changed.
      This keeps the "Stream" smooth and professional.
    */
    if (initial || newestId !== lastTopId) {
      rows.value = incoming
      lastTopId = newestId
    }
  } catch (err) {
    console.error("❌ Audit Stream failed:", err)
    // If token expires during polling, the natural guard handles it
  } finally {
    loading.value = false
  }
}

/*
  Polling Logic
*/
function startPolling() {
  timer = setInterval(() => {
    loadAudit(false)
  }, 10000) // Checks for library updates every 10 seconds
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(() => {
  loadAudit(true)
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="audit-wrapper">
    <h2 class="title">Status Audit Stream</h2>

    <table class="audit-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Accession</th>
          <th>Old</th>
          <th>New</th>
          <th>Changed By</th>
          <th>Time</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td>{{ row.id }}</td>
          <td>{{ row.accession_no }}</td>
          <td class="muted">{{ row.old_status }}</td>
          <td>{{ row.new_status }}</td>
          <td>{{ row.changed_by }}</td>
          <td class="muted">{{ row.changed_at }}</td>
        </tr>

        <tr v-if="!loading && rows.length === 0">
          <td colspan="6" class="empty">No audit records</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.audit-wrapper {
  padding:14px;
}

.title {
  font-size:18px;
  font-weight:600;
  margin-bottom:12px;
}

.audit-table {
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}

.audit-table th {
  background:#1e1e1e;
  padding:10px;
  text-align:left;
}

.audit-table td {
  padding:9px;
  border-bottom:1px solid #2a2a2a;
}

.muted {
  color:#9a9a9a;
}

.empty {
  text-align:center;
  padding:20px;
  color:#777;
}
</style>