<template>
  <div class="approval-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">GOVERNANCE // CHIEF AUTHORIZATION</div>
        <h1>Approval Center</h1>
        <p>Review and decide on pending catalogue submissions.</p>
      </div>
      <button class="refresh-btn" @click="loadAll" :disabled="loading">
        {{ loading ? 'SYNCING...' : 'REFRESH' }}
      </button>
    </header>

    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="notice" class="notice-banner">{{ notice }}</div>

    <section class="metrics">
      <div class="metric">
        <span>PENDING WORKS</span>
        <strong>{{ pendingWorks.length }}</strong>
      </div>
      <div class="metric">
        <span>PENDING ITEMS</span>
        <strong>{{ pendingItems.length }}</strong>
      </div>
      <div class="metric">
        <span>TOTAL QUEUE</span>
        <strong>{{ pendingWorks.length + pendingItems.length }}</strong>
      </div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <div>
          <span class="section-code">01 //</span>
          <h2>Work Approval Queue</h2>
        </div>
        <span class="request-count">{{ pendingWorks.length }} PENDING</span>
      </div>

      <div v-if="loading && !pendingWorks.length" class="empty">RETRIEVING PENDING WORKS...</div>
      <div v-else-if="!pendingWorks.length" class="empty">NO PENDING WORK SUBMISSIONS.</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>WORK</th>
              <th>AUTHOR</th>
              <th>LANGUAGE</th>
              <th>PROPOSED BY</th>
              <th>STATUS</th>
              <th>DECISION</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="work in pendingWorks" :key="work.work_id">
              <td>
                <div class="strong">{{ work.title || 'Untitled' }}</div>
                <small class="muted">WORK #{{ work.work_id }} · {{ work.category || 'Unclassified' }}</small>
              </td>
              <td>{{ work.author || 'Unknown' }}</td>
              <td>{{ work.language || '—' }}</td>
              <td>
                <div>{{ work.proposer_name || 'Operator #' + work.proposed_by }}</div>
                <small class="muted">{{ work.proposal_reason || 'No reason supplied.' }}</small>
              </td>
              <td><span class="status pending">PENDING</span></td>
              <td class="actions">
                <button class="action approve" :disabled="busy" @click="decideWork(work, 'APPROVE')">APPROVE</button>
                <button class="action reject" :disabled="busy" @click="decideWork(work, 'REJECT')">REJECT</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <div>
          <span class="section-code">02 //</span>
          <h2>Item Approval Queue</h2>
        </div>
        <span class="request-count">{{ pendingItems.length }} PENDING</span>
      </div>

      <div v-if="loading && !pendingItems.length" class="empty">RETRIEVING PENDING ITEMS...</div>
      <div v-else-if="!pendingItems.length" class="empty">NO PENDING ITEM SUBMISSIONS.</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ITEM</th>
              <th>WORK</th>
              <th>ACCESSION</th>
              <th>AUTHOR</th>
              <th>STATUS</th>
              <th>DECISION</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pendingItems" :key="item.serial_no">
              <td>
                <div class="strong">SERIAL #{{ item.serial_no }}</div>
                <small class="muted">{{ item.call_no || 'No call number' }}</small>
              </td>
              <td>
                <div class="strong">{{ item.title || 'Untitled' }}</div>
                <small class="muted">WORK #{{ item.work_id }}</small>
              </td>
              <td>{{ item.accession_no || '—' }}</td>
              <td>{{ item.author || 'Unknown' }}</td>
              <td><span class="status pending">PENDING</span></td>
              <td class="actions">
                <button class="action approve" :disabled="busy" @click="decideItem(item, 'APPROVE')">APPROVE</button>
                <button class="action reject" :disabled="busy" @click="decideItem(item, 'REJECT')">REJECT</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'

const pendingWorks = ref([])
const pendingItems = ref([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [worksRes, itemsRes] = await Promise.all([
      axios.get('/catalogue/pending-works'),
      axios.get('/catalogue/pending-items')
    ])
    pendingWorks.value = Array.isArray(worksRes.data) ? worksRes.data : []
    pendingItems.value = Array.isArray(itemsRes.data) ? itemsRes.data : []
  } catch (err) {
    console.error('Approval Center load failed:', err)
    error.value = err.response?.data?.detail || 'Unable to load approval queues.'
  } finally {
    loading.value = false
  }
}

async function decideWork(work, action) {
  const reason = window.prompt(`${action === 'APPROVE' ? 'Approval' : 'Rejection'} reason for “${work.title || 'Untitled'}”:`, '')
  if (reason === null) return
  if (!reason.trim()) {
    error.value = 'A decision reason is required.'
    return
  }
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await axios.post(`/catalogue/approve/${work.work_id}`, null, {
      params: { action, reason: reason.trim() }
    })
    notice.value = `Work “${work.title || 'Untitled'}” ${action === 'APPROVE' ? 'approved' : 'rejected'}.`
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to process the Work decision.'
  } finally {
    busy.value = false
  }
}

async function decideItem(item, action) {
  const reason = window.prompt(`${action === 'APPROVE' ? 'Approval' : 'Rejection'} reason for Item #${item.serial_no}:`, '')
  if (reason === null) return
  if (!reason.trim()) {
    error.value = 'A decision reason is required.'
    return
  }
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await axios.post(`/catalogue/approve-item/${item.serial_no}`, null, {
      params: { action, reason: reason.trim() }
    })
    notice.value = `Item #${item.serial_no} ${action === 'APPROVE' ? 'approved' : 'rejected'}.`
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to process the Item decision.'
  } finally {
    busy.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.approval-page { min-height:100%; padding:34px 42px 50px; color:var(--text-primary,#eadfcf); }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; gap:24px; margin-bottom:26px; }
.eyebrow,.section-code { font:600 11px/1.4 "JetBrains Mono",monospace; letter-spacing:2px; opacity:.62; }
h1 { margin:7px 0 5px; font-size:29px; letter-spacing:.8px; font-weight:500; }
.page-header p { margin:0; opacity:.58; }
.refresh-btn { border:1px solid rgba(190,160,105,.42); background:rgba(190,160,105,.08); color:inherit; padding:10px 15px; cursor:pointer; }
.refresh-btn:disabled,.action:disabled { opacity:.45; cursor:not-allowed; }
.error-banner,.notice-banner { margin-bottom:18px; padding:12px 15px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.04); }
.error-banner { border-color:rgba(190,90,90,.45); }
.notice-banner { border-color:rgba(110,170,120,.4); }
.metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:18px; }
.metric { padding:17px 18px; border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.025); }
.metric span { display:block; font:600 10px/1.4 "JetBrains Mono",monospace; letter-spacing:1.5px; opacity:.55; }
.metric strong { display:block; margin-top:6px; font-size:25px; font-weight:500; }
.panel { margin-top:18px; border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.018); }
.panel-title { display:flex; justify-content:space-between; align-items:center; padding:18px 20px; border-bottom:1px solid rgba(255,255,255,.08); }
.panel-title h2 { display:inline; margin:0 0 0 8px; font-size:17px; font-weight:500; }
.request-count { font:600 10px/1 "JetBrains Mono",monospace; letter-spacing:1px; opacity:.55; }
.empty { padding:35px 20px; text-align:center; opacity:.48; font:600 11px/1.4 "JetBrains Mono",monospace; letter-spacing:1.5px; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; }
th,td { padding:13px 14px; text-align:left; border-bottom:1px solid rgba(255,255,255,.07); vertical-align:middle; font-size:13px; }
th { font:600 10px/1.4 "JetBrains Mono",monospace; letter-spacing:1px; opacity:.52; }
tr:last-child td { border-bottom:0; }
.strong { font-weight:600; }
.muted { display:block; margin-top:3px; font-size:11px; opacity:.45; }
.status { display:inline-block; padding:5px 8px; border:1px solid rgba(190,160,105,.4); font:600 9px/1 "JetBrains Mono",monospace; letter-spacing:1px; }
.status.pending { background:rgba(190,160,105,.08); }
.actions { white-space:nowrap; }
.action { padding:8px 10px; margin-right:6px; border:1px solid rgba(255,255,255,.18); background:transparent; color:inherit; font:600 10px/1 "JetBrains Mono",monospace; cursor:pointer; }
.action.approve { border-color:rgba(110,170,120,.5); }
.action.reject { border-color:rgba(190,90,90,.5); }
@media (max-width:800px) { .approval-page{padding:24px 18px 40px}.metrics{grid-template-columns:1fr}.page-header{flex-direction:column} }
</style>
