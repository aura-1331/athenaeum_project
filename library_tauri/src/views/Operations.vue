<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from "vue"
import axios from 'axios' // 🚀 1. Import the Hybrid Engine

const showHistory = ref(false)
const historyData = ref([])
const loading = ref(false)

// 🔍 2. FETCH HISTORY (Natural)
async function fetchStatusHistory() {
  loading.value = true
  try {
    // 🚀 Uses main.js for Base URL and Token automatically
    const res = await axios.get('/status_audit/recent') 
    historyData.value = res.data
  } catch (err) {
    console.error("❌ Failed to load operations history:", err)
  } finally {
    loading.value = false
  }
}

function openHistory() {
  showHistory.value = true
}

// 🔄 3. AUTO-LOAD ON OPEN
watch(showHistory, (isOpen) => {
  if (isOpen) fetchStatusHistory()
})

onMounted(() => {
  window.addEventListener("open-history", openHistory)
})

onBeforeUnmount(() => {
  window.removeEventListener("open-history", openHistory)
})
</script>

<template>
<div class="operations-root">
  <h2>Operations Console</h2>

  <Transition name="slide">
    <div v-if="showHistory" class="drawer">
      <div class="drawer-header">
        <h3>Institutional Audit Feed</h3>
        <button @click="showHistory = false" class="close-btn">×</button>
      </div>

      <div v-if="loading" class="msg">Syncing with Ledger...</div>
      
      <div v-else class="history-list">
        <div v-for="log in historyData" :key="log.id" class="history-item">
          <span class="acc-tag">#{{ log.accession_no }}</span>
          <div class="status-change">
            {{ log.old_status }} ➔ <span class="new-status">{{ log.new_status }}</span>
          </div>
          <small class="meta">{{ log.changed_by }} • {{ new Date(log.changed_at).toLocaleTimeString() }}</small>
        </div>
        
        <div v-if="!historyData.length" class="empty">No recent operations detected.</div>
      </div>
    </div>
  </Transition>
</div>
</template>

<style scoped>
.operations-root { padding: 16px; color: white; }

.drawer {
  position: fixed;
  right: 0;
  top: 0;
  width: 420px;
  height: 100%;
  background: #111;
  border-left: 2px solid #fbbf24; /* Archival Gold Border */
  padding: 20px;
  z-index: 1000;
  box-shadow: -10px 0 30px rgba(0,0,0,0.5);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #333;
  padding-bottom: 15px;
  margin-bottom: 20px;
}

.history-item {
  background: #1a1a1a;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid #222;
}

.acc-tag { color: #fbbf24; font-weight: 800; font-size: 12px; }
.new-status { color: #2dd4bf; font-weight: bold; }
.meta { color: #666; font-size: 11px; display: block; margin-top: 5px; }

.close-btn { background: none; border: none; color: #666; font-size: 24px; cursor: pointer; }
.close-btn:hover { color: white; }

/* Animation */
.slide-enter-active, .slide-leave-active { transition: transform 0.3s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>