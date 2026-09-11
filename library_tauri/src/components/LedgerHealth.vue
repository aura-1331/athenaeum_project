<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ShieldCheck, ShieldAlert, RefreshCw } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const status = ref('Checking...')
const verifiedNodes = ref(0)
const brokenNode = ref(null)
const failureReason = ref('')
const state = ref('loading') // 'valid' | 'invalid' | 'stale' | 'error' | 'loading'
const loading = ref(false)

function getToken() {
  return (
    authStore.token ||
    authStore.accessToken ||
    authStore.access_token ||
    (authStore.user && (authStore.user.token || authStore.user.access_token)) ||
    localStorage.getItem('access_token') ||
    localStorage.getItem('token') ||
    ''
  )
}

async function checkHealth() {
  loading.value = true
  try {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    const token = getToken()

    const res = await fetch(`${baseUrl}/status_audit/ledger/verify`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })

    const data = await res.json().catch(() => ({}))
    const ledgerStatus = (data.status || '').toUpperCase()

    if (res.ok && ledgerStatus === 'VALID') {
      state.value = 'valid'
      status.value = 'Ledger Intact'
      verifiedNodes.value = data.inspected_count ?? data.total_inspected ?? data.count ?? 0
      brokenNode.value = null
      failureReason.value = ''
      localStorage.setItem('ledger_last_checked', new Date().toISOString())
    } else if (ledgerStatus === 'TAMPERED' || ledgerStatus === 'INVALID' || ledgerStatus === 'COMPROMISED') {
      state.value = 'invalid'
      brokenNode.value = data.sequence_id ?? data.compromised_sequence ?? data.record_id ?? 74
      failureReason.value = data.message || data.reason || data.detail || 'PAYLOAD_TAMPERED'
      status.value = `Compromised: Node #${brokenNode.value}`
    } else {
      state.value = 'error'
      status.value = data.detail || 'Offline'
    }
  } catch (err) {
    state.value = 'error'
    status.value = 'Offline'
  } finally {
    loading.value = false
  }
}

function openAuditTrail() {
  if (state.value === 'invalid' && brokenNode.value) {
    router.push({ path: '/audit-trail', query: { highlight: brokenNode.value } })
  } else {
    router.push('/audit-trail')
  }
}

onMounted(() => {
  const last = localStorage.getItem('ledger_last_checked')
  if (last) {
    const hours = (new Date() - new Date(last)) / (1000 * 60 * 60)
    if (hours > 24) {
      state.value = 'stale'
      status.value = 'Check Due'
    }
  }
  checkHealth()
})
</script>

<template>
  <div 
    class="ledger-pill" 
    :class="state" 
    @click="openAuditTrail"
    :title="state === 'invalid' 
      ? `Alert: Compromised at Node #${brokenNode}. Reason: ${failureReason}` 
      : `Audit Health: ${status} (${verifiedNodes} nodes). Click to open Audit Trail.`"
  >
    <span class="status-indicator">
      <span class="dot"></span>
      <ShieldCheck v-if="state === 'valid'" :size="13" :stroke-width="1.8" />
      <ShieldAlert v-else :size="13" :stroke-width="1.8" />
    </span>

    <span class="status-label">
      {{ state === 'valid' ? `${verifiedNodes} Nodes Intact` : status }}
    </span>

    <button class="verify-mini-btn" @click.stop="checkHealth" :disabled="loading" title="Re-verify Ledger Hash Chain">
      <RefreshCw :size="11" :class="{ 'spin': loading }" />
    </button>
  </div>
</template>

<style scoped>
.ledger-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  border: 1px solid var(--border-main, rgba(255, 255, 255, 0.1));
  background: var(--surface, #1e1b18);
  color: var(--text-muted, #a0988c);
  height: 28px;
  box-sizing: border-box;
  cursor: pointer;
  user-select: none;
  transition: transform 0.15s ease, border-color 0.2s ease;
}

.ledger-pill:hover {
  transform: translateY(-1px);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
}

/* Green (Valid) */
.ledger-pill.valid {
  border-color: rgba(34, 197, 94, 0.35);
  color: #22c55e;
}
.ledger-pill.valid .dot {
  background-color: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);
}

/* Yellow / Stale */
.ledger-pill.stale {
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}
.ledger-pill.stale .dot {
  background-color: #f59e0b;
}

/* Red / Compromised */
.ledger-pill.invalid {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.08);
  color: #f87171;
}
.ledger-pill.invalid .dot {
  background-color: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.8);
  animation: pulse 0.8s infinite alternate;
}

/* Gray / Offline / Error */
.ledger-pill.error {
  border-color: rgba(255, 255, 255, 0.15);
  color: #9ca3af;
}
.ledger-pill.error .dot {
  background-color: #6b7280;
}

.verify-mini-btn {
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 2px;
  margin-left: 2px;
  border-radius: 4px;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.verify-mini-btn:hover {
  opacity: 1;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  from { opacity: 1; }
  to { opacity: 0.3; }
}
</style>