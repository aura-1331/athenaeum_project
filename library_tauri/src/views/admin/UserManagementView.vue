<template>
  <div class="admin-container">
    <!-- Header -->
    <header class="admin-header">
      <div>
        <span class="system-tag">GOVERNANCE // PERSONNEL_REGISTRY</span>
        <h1 class="page-title">User & Access Management</h1>
      </div>
      <button 
        v-if="canProvision" 
        class="action-btn primary"
        @click="openProvisionModal"
      >
        + PROVISION OPERATOR
      </button>
    </header>

    <!-- Navigation Tabs -->
    <div class="tabs-bar">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'users' }" 
        @click="activeTab = 'users'"
      >
        OPERATOR LEDGER ({{ users.length }})
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'requests' }" 
        @click="activeTab = 'requests'"
      >
        ACCESS QUEUE ({{ pendingRequests.length }})
      </button>
    </div>

    <!-- Page Status Notices -->
    <div v-if="errorMessage" class="banner error-banner">
      {{ errorMessage }}
      <button class="banner-close" @click="errorMessage = ''">&times;</button>
    </div>
    <div v-if="successMessage" class="banner success-banner">
      {{ successMessage }}
      <button class="banner-close" @click="successMessage = ''">&times;</button>
    </div>

    <!-- TAB 1: OPERATOR LEDGER -->
    <section v-if="activeTab === 'users'" class="table-card">
      <div v-if="loading" class="state-message">SYNCING_PERSONNEL_DATA...</div>
      <table v-else-if="users.length > 0" class="data-table">
        <thead>
          <tr>
            <th>OPERATOR ID</th>
            <th>NAME</th>
            <th>EMAIL</th>
            <th>ROLE</th>
            <th>STATUS</th>
            <th v-if="isChief">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.user_id">
            <td class="mono code-cell">{{ user.operator_id || 'N/A' }}</td>
            <td class="strong-cell">{{ user.name }}</td>
            <td class="mono muted-cell">{{ user.email }}</td>
            <td>
              <span class="badge" :class="roleBadgeClass(user.role)">
                {{ user.role }}
              </span>
            </td>
            <td>
              <span class="status-indicator" :class="user.status.toLowerCase()">
                {{ user.status }}
              </span>
            </td>
            <td v-if="isChief">
              <button
                v-if="user.status !== 'REVOKED' && user.role !== 'The Chief'"
                class="table-btn danger"
                @click="revokeUser(user.user_id, user.name)"
              >
                REVOKE
              </button>
              <span v-else class="muted-text">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="state-message">No registered operators found.</div>
    </section>

    <!-- TAB 2: ACCESS QUEUE -->
    <section v-if="activeTab === 'requests'" class="table-card">
      <div v-if="loading" class="state-message">SYNCING_ACCESS_QUEUE...</div>
      <table v-else-if="pendingRequests.length > 0" class="data-table">
        <thead>
          <tr>
            <th>APPLICANT</th>
            <th>EMAIL / ORG</th>
            <th>REQUESTED ROLE</th>
            <th>PURPOSE</th>
            <th>STATUS</th>
            <th>DECISION</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="req in pendingRequests" :key="req.request_id">
            <td class="strong-cell">{{ req.full_name }}</td>
            <td>
              <div>{{ req.email }}</div>
              <small class="muted-cell">{{ req.organization || 'Independent' }}</small>
            </td>
            <td>
              <span class="badge" :class="roleBadgeClass(req.requested_role)">
                {{ req.requested_role }}
              </span>
            </td>
            <td class="purpose-cell">{{ req.purpose || 'No purpose stated.' }}</td>
            <td>
              <span class="status-indicator pending">{{ req.status }}</span>
            </td>
            <td class="actions-cell">
              <!-- Chief Decisions -->
              <template v-if="isChief">
                <button 
                  class="table-btn success" 
                  @click="handleChiefDecision(req.request_id, 'APPROVE')"
                >
                  APPROVE
                </button>
                <button 
                  class="table-btn danger" 
                  @click="handleChiefDecision(req.request_id, 'REJECT')"
                >
                  REJECT
                </button>
              </template>

              <!-- Keeper Recommendations -->
              <template v-else-if="isKeeper">
                <button 
                  class="table-btn outline-success" 
                  @click="handleKeeperRecommendation(req.request_id, 'APPROVE')"
                >
                  REC_APPROVE
                </button>
                <button 
                  class="table-btn outline-danger" 
                  @click="handleKeeperRecommendation(req.request_id, 'REJECT')"
                >
                  REC_REJECT
                </button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="state-message">No pending access requests in queue.</div>
    </section>

    <!-- PROVISION OPERATOR MODAL -->
    <div v-if="showModal" class="modal-backdrop" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <span class="system-tag">AUTHORIZATION // ENROLLMENT</span>
            <h2 class="modal-title">Provision New Operator</h2>
          </div>
          <button class="close-btn" @click="showModal = false">&times;</button>
        </div>

        <!-- MODAL ERROR BANNER -->
        <div v-if="modalError" class="modal-error-banner">
          {{ modalError }}
        </div>

        <form class="form-grid" @submit.prevent="submitProvision">
          <div class="form-group full">
            <label>FULL NAME</label>
            <input v-model="form.name" type="text" placeholder="e.g. Eleanor Vance" required />
          </div>

          <div class="form-group full">
            <label>PRIMARY EMAIL</label>
            <input v-model="form.email" type="email" placeholder="e.g. evance@athenaeum.org" required />
          </div>

          <div class="form-group">
            <label>AUTHORIZATION LEVEL</label>
            <select v-model="form.role" required>
              <option v-for="r in availableRoles" :key="r" :value="r">
                {{ r }}
              </option>
            </select>
          </div>

<div class="form-group">
  <label>INITIAL PASSPHRASE</label>
  <div class="password-input-wrapper">
    <input 
      v-model="form.password" 
      :type="showPassword ? 'text' : 'password'" 
      placeholder="Min. 12 characters..." 
      minlength="12"
      required 
    />
    <button
      type="button"
      class="password-toggle-btn"
      :title="showPassword ? 'Hide passphrase' : 'Show passphrase'"
      tabindex="-1"
      @click="showPassword = !showPassword"
    >
      <EyeOff v-if="showPassword" :size="16" :stroke-width="1.5" />
      <Eye v-else :size="16" :stroke-width="1.5" />
    </button>
  </div>
  <span class="field-hint">
    Min. 12 chars with uppercase, lowercase, number & symbol
  </span>
</div>

          <div class="modal-actions">
            <button type="button" class="action-btn cancel" @click="showModal = false">
              ABORT
            </button>
            <button type="submit" class="action-btn primary" :disabled="submitting">
              {{ submitting ? 'COMMITTING...' : 'PROVISION_ACCOUNT' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff } from 'lucide-vue-next'

const auth = useAuthStore()

const activeTab = ref('users')
const users = ref([])
const pendingRequests = ref([])
const loading = ref(false)
const submitting = ref(false)
const showModal = ref(false)
const showPassword = ref(false)

const errorMessage = ref('')
const successMessage = ref('')
const modalError = ref('')

const form = ref({
  name: '',
  email: '',
  role: 'The Seeker',
  password: ''
})

const currentUserRole = computed(() => auth.userRole || auth.role || auth.user?.role || '')
const isChief = computed(() => currentUserRole.value === 'The Chief')
const isKeeper = computed(() => currentUserRole.value === 'The Keeper')
const canProvision = computed(() => isChief.value || isKeeper.value)

const availableRoles = computed(() => {
  if (isChief.value) {
    return ['The Keeper', 'The Seeker', 'Temporary Seeker']
  }
  if (isKeeper.value) {
    return ['The Seeker', 'Temporary Seeker']
  }
  return []
})

function roleBadgeClass(role) {
  if (!role) return ''
  if (role.includes('Chief')) return 'badge-chief'
  if (role.includes('Keeper')) return 'badge-keeper'
  if (role.includes('Temporary')) return 'badge-temp'
  return 'badge-seeker'
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [usersRes, reqsRes] = await Promise.all([
      axios.get('/admin/users'),
      axios.get('/admin/access-requests')
    ])
    users.value = usersRes.data || []
    pendingRequests.value = reqsRes.data || []
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Failed to sync administrative records.'
  } finally {
    loading.value = false
  }
}

function openProvisionModal() {
  modalError.value = ''
  showPassword.value = false
  form.value = {
    name: '',
    email: '',
    role: isChief.value ? 'The Keeper' : 'The Seeker',
    password: ''
  }
  showModal.value = true
}

async function submitProvision() {
  submitting.value = true
  modalError.value = ''
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const res = await axios.post('/admin/create-user', null, {
      params: {
        name: form.value.name,
        email: form.value.email,
        role: form.value.role,
        password: form.value.password
      }
    })
    successMessage.value = `Operator provisioned. Assigned Operator ID: ${res.data.operator_id}`
    showModal.value = false
    await loadData()
  } catch (err) {
    modalError.value = err.response?.data?.detail || 'Account provisioning failed.'
  } finally {
    submitting.value = false
  }
}

async function revokeUser(userId, name) {
  if (!confirm(`Confirm revocation of access for ${name}?`)) return
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await axios.post(`/chief/revoke-user/${userId}`)
    successMessage.value = `Access revoked for ${name}.`
    await loadData()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Failed to revoke access.'
  }
}

async function handleChiefDecision(requestId, decision) {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const res = await axios.post(`/chief/decide-request/${requestId}`, { decision })
    successMessage.value = res.data?.message || `Request marked as ${decision}.`
    await loadData()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Decision action failed.'
  }
}

async function handleKeeperRecommendation(requestId, recommendation) {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const res = await axios.post(`/keeper/recommend-request/${requestId}`, { recommendation })
    successMessage.value = res.data?.message || 'Recommendation recorded.'
    await loadData()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Recommendation action failed.'
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.admin-container {
  padding: 36px 48px;
  color: #e2e4e9;
  font-family: 'JetBrains Mono', monospace;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
}

.system-tag {
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
  letter-spacing: 1.5px;
}

.page-title {
  font-family: 'Cinzel', serif;
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  margin: 6px 0 0 0;
}

.tabs-bar {
  display: flex;
  gap: 12px;
  border-bottom: 1px solid #22252e;
  margin-bottom: 24px;
}

.tab-btn {
  background: none;
  border: none;
  color: #717887;
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  padding: 10px 18px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.tab-btn.active {
  color: #d4af37;
  border-bottom-color: #d4af37;
}

.banner {
  padding: 12px 18px;
  border-radius: 4px;
  font-size: 11px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-banner {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid #ef4444;
  color: #fca5a5;
}

.success-banner {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid #10b981;
  color: #6ee7b7;
}

.banner-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
}

.table-card {
  background: #16181f;
  border: 1px solid #22252e;
  border-radius: 8px;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}

.data-table th {
  background: #111216;
  color: #626a7a;
  padding: 12px 16px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #22252e;
}

.data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #1c1e27;
}

.mono { font-family: inherit; }
.code-cell { color: #d4af37; font-weight: 700; }
.strong-cell { color: #ffffff; font-weight: 600; }
.muted-cell { color: #717887; font-size: 11px; }
.purpose-cell { max-width: 260px; color: #a3a8b4; font-size: 11px; }

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.badge-chief { background: rgba(212, 175, 55, 0.15); color: #d4af37; border: 1px solid #d4af37; }
.badge-keeper { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid #3b82f6; }
.badge-seeker { background: rgba(107, 114, 128, 0.2); color: #9ca3af; border: 1px solid #4b5563; }
.badge-temp { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid #f59e0b; }

.status-indicator {
  font-size: 10px;
  font-weight: 700;
}
.status-indicator.approved { color: #10b981; }
.status-indicator.revoked { color: #ef4444; }
.status-indicator.pending { color: #f59e0b; }

.table-btn {
  background: none;
  border: 1px solid transparent;
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 6px;
}

.table-btn.danger { background: rgba(239, 68, 68, 0.1); border-color: #ef4444; color: #ef4444; }
.table-btn.danger:hover { background: #ef4444; color: #ffffff; }

.table-btn.success { background: rgba(16, 185, 129, 0.1); border-color: #10b981; color: #10b981; }
.table-btn.success:hover { background: #10b981; color: #ffffff; }

.table-btn.outline-success { border-color: #10b981; color: #10b981; }
.table-btn.outline-danger { border-color: #ef4444; color: #ef4444; }

.state-message {
  padding: 48px;
  text-align: center;
  color: #626a7a;
  font-size: 12px;
}

.action-btn {
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
}

.action-btn.primary {
  background: #d4af37;
  border: none;
  color: #0b0c10;
}

.action-btn.primary:hover {
  background: #e5c158;
}

.action-btn.cancel {
  background: none;
  border: 1px solid #2e333d;
  color: #e2e4e9;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 11, 15, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-card {
  width: 90%;
  max-width: 520px;
  background: #16181f;
  border: 1px solid #22252e;
  border-radius: 8px;
  padding: 28px;
  color: #e2e4e9;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.modal-title {
  font-family: 'Cinzel', serif;
  font-size: 18px;
  color: #ffffff;
  margin: 4px 0 0 0;
}

.close-btn {
  background: none;
  border: none;
  color: #626a7a;
  font-size: 24px;
  cursor: pointer;
}

.modal-error-banner {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid #ef4444;
  color: #fca5a5;
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 11px;
  margin-bottom: 18px;
  font-family: inherit;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.form-group.full {
  grid-column: span 2;
}

.form-group label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
  margin-bottom: 6px;
}

.form-group input,
.form-group select {
  width: 100%;
  background: #111216;
  border: 1px solid #22252e;
  color: #e2e4e9;
  padding: 9px 12px;
  border-radius: 4px;
  font-family: inherit;
  font-size: 12px;
  box-sizing: border-box;
}

.password-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.password-input-wrapper input {
  padding-right: 36px;
}

.password-toggle-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: #717887;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  transition: color 0.15s ease;
}

.password-toggle-btn:hover {
  color: #e2e4e9;
}

.field-hint {
  display: block;
  font-size: 9px;
  color: #8b949e;
  margin-top: 6px;
  line-height: 1.3;
}

.modal-actions {
  grid-column: span 2;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 14px;
}
.form-group {
  display: flex;
  flex-direction: column;
}

.password-input-wrapper {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.password-input-wrapper input {
  width: 100%;
  box-sizing: border-box;
  padding-right: 40px; /* Reserves space so text does not slide under the icon */
}

.password-toggle-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  padding: 4px;
  color: #717887;
  cursor: pointer;
  line-height: 0;
  transition: color 0.15s ease;
}

.password-toggle-btn:hover {
  color: #e2e4e9;
}

.field-hint {
  display: block;
  font-size: 10px;
  color: #8b949e;
  margin-top: 6px;
  line-height: 1.3;
}
</style>