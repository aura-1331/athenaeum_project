<template>
  <div
    class="system-status"
    :class="`status-${status}`"
    :title="tooltipText"
    aria-label="System status"
  >
    <span class="status-dot"></span>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import axios from "axios"

const status = ref("healthy")


let poller = null

const tooltipText = computed(() => {
  if (status.value === "healthy") {
    return "System Network Healthy — all monitored services are operational."
  }

  if (status.value === "database") {
    return "Database Unavailable — the archive database cannot be reached."
  }

  if (status.value === "backend") {
    return "Backend Unavailable — the application server cannot be reached."
  }

  if (status.value === "ledger") {
    return "Ledger Integrity Alert — a confirmed integrity incident requires attention."
  }

  return "System Service Degraded — a monitored service requires attention."
})

async function checkSystemStatus() {
  try {
    const response = await axios.get("/health/", {
      timeout: 5000,
    })

    const data = response?.data || {}

    // Infrastructure checks come first.
    if (data.database?.status === "error") {
      status.value = "database"
      return
    }

    if (data.backend?.status !== "ok") {
      status.value = "backend"
      return
    }

    // Infrastructure is healthy, so now check the confirmed
    // ledger-integrity security signal.
    try {
      const securityResponse = await axios.get(
        "/status_audit/global-status",
        {
          timeout: 5000,
        }
      )

      const securityData = securityResponse?.data || {}
      

      if (securityData.ledger_integrity === "BREACH") {
        status.value = "ledger"
        return
      }

      if (securityData.ledger_integrity === "UNKNOWN") {
        status.value = "degraded"
        return
      }
    } catch (securityError) {
      // A failure to read the security signal is not itself
      // evidence of a ledger breach.
      status.value = "degraded"
      return
    }

    status.value = "healthy"
  } catch (error) {
    /*
     * If /health/ itself cannot be reached, the browser can only
     * establish that the backend is unavailable. It cannot conclude
     * that PostgreSQL or the ledger is unavailable.
     */
    status.value = "backend"
  }
}
onMounted(() => {
  checkSystemStatus()

  poller = window.setInterval(checkSystemStatus, 30000)
})

onUnmounted(() => {
  if (poller) {
    window.clearInterval(poller)
  }
})
</script>

<style scoped>
.system-status {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: default;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: block;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.status-healthy .status-dot {
  background: #4ade80;
}

.status-degraded .status-dot,
.status-backend .status-dot,
.status-database .status-dot {
  background: #f59e0b;
  animation: status-pulse 2s ease-in-out infinite;
}

.status-ledger .status-dot {
  background: #ef4444;
  animation: status-pulse 1.2s ease-in-out infinite;
}

@keyframes status-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0.45;
    transform: scale(1.35);
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-dot {
    animation: none !important;
  }
}
</style>