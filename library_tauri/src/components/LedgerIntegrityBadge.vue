<template>
  <div class="ledger-badge-container" :class="statusClass">
    <div class="badge-main">
      <span class="status-dot" :class="{ 'pulse-green': status === 'VALID', 'pulse-red': status === 'TAMPERED' || status === 'INVALID', 'spinning': verifying }"></span>
      
      <div class="badge-info">
        <span class="badge-status-text">
          {{ statusLabel }}
        </span>
        <span v-if="status === 'VALID'" class="badge-meta">
          {{ recordCount }} records intact <span class="divider">|</span> Head: <code>{{ truncatedHash }}</code>
        </span>
        <span v-else-if="status === 'TAMPERED' || status === 'INVALID'" class="badge-meta text-danger">
          {{ errorMessage || 'Cryptographic chain verification failed!' }}
        </span>
        <span v-else-if="status === 'ERROR'" class="badge-meta text-muted">
          {{ errorMessage || 'Ledger verification service unreachable' }}
        </span>
      </div>
    </div>

    <button 
      class="verify-btn" 
      @click="verifyLedger" 
      :disabled="verifying"
      title="Re-verify cryptographic chain hashes"
    >
      <svg class="verify-icon" :class="{ 'spinning': verifying }" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
      </svg>
      <span>{{ verifying ? 'Verifying...' : 'Verify Chain' }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const verifying = ref(false)
const status = ref('IDLE')
const recordCount = ref(0)
const headHash = ref('')
const errorMessage = ref('')

const statusLabel = computed(() => {
  if (verifying.value) return 'VERIFYING HASH CHAIN...'
  if (status.value === 'VALID') return 'CHAIN CRYPTOGRAPHICALLY VALID'
  if (status.value === 'TAMPERED' || status.value === 'INVALID') return 'SECURITY ALERT: LEDGER TAMPERED'
  if (status.value === 'ERROR') return 'VERIFICATION OFFLINE'
  return 'LEDGER STATUS UNKNOWN'
})

const statusClass = computed(() => {
  if (verifying.value) return 'status-verifying'
  if (status.value === 'VALID') return 'status-valid'
  if (status.value === 'TAMPERED' || status.value === 'INVALID') return 'status-tampered'
  if (status.value === 'ERROR') return 'status-error'
  return ''
})

const truncatedHash = computed(() => {
  if (!headHash.value) return 'GENESIS'
  if (headHash.value.length <= 16) return headHash.value
  return `${headHash.value.slice(0, 8)}...${headHash.value.slice(-6)}`
})

function getToken() {
  return authStore.accessToken || ''
}

async function verifyLedger() {
  verifying.value = true
  errorMessage.value = ''
  try {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    const token = getToken()

    const response = await fetch(`${baseUrl}/status_audit/ledger/verify`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${response.status}`)
    }

    const data = await response.json()
    const ledgerStatus = (data.status || '').toUpperCase()

    if (ledgerStatus === 'VALID') {
      status.value = 'VALID'
      recordCount.value = data.inspected_count ?? data.total_inspected ?? data.count ?? 0
      headHash.value = data.latest_head_hash || data.head_hash || ''
    } else {
      status.value = 'TAMPERED'
      errorMessage.value = data.message || data.detail || 'Hash verification failed on chain integrity.'
    }
  } catch (err) {
    status.value = 'ERROR'
    errorMessage.value = err.message || 'Verification endpoint unreachable'
  } finally {
    verifying.value = false
  }
}

onMounted(() => {
  verifyLedger()
})
</script>

<style scoped>
.ledger-badge-container {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(18, 20, 26, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 8px 14px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace, sans-serif;
  transition: all 0.2s ease;
}

.badge-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.badge-status-text {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.badge-meta {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.badge-meta code {
  color: #38bdf8;
  font-family: monospace;
}

.divider {
  color: #334155;
  margin: 0 4px;
}

.status-valid {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.04);
}
.status-valid .badge-status-text {
  color: #10b981;
}

.status-tampered {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
}
.status-tampered .badge-status-text {
  color: #ef4444;
}

.status-error {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.04);
}
.status-error .badge-status-text {
  color: #f59e0b;
}

.status-verifying .badge-status-text {
  color: #38bdf8;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
  flex-shrink: 0;
}

.pulse-green {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.pulse-red {
  background: #ef4444;
  box-shadow: 0 0 10px #ef4444;
  animation: flash 1s infinite alternate;
}

.verify-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.verify-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  border-color: #38bdf8;
}

.verify-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.verify-icon {
  width: 12px;
  height: 12px;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

.text-danger {
  color: #f87171 !important;
}

.text-muted {
  color: #64748b !important;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes flash {
  from { opacity: 1; }
  to { opacity: 0.4; }
}
</style>