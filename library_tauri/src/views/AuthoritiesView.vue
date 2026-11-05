<script setup>
import {
  computed,
  onMounted,
  onBeforeUnmount,
  reactive,
  ref
} from 'vue'

import { useAuthStore } from '@/stores/auth'
import { API_BASE } from '@/config'

// ============================================================
// STATE
// ============================================================

const authorities = ref([])
const loading = ref(false)
const errorMessage = ref('')
const searchQuery = ref('')
const statusFilter = ref('')
const selectedAuthority = ref(null)

const actionLoading = ref(false)
const actionType = ref('')
const actionMessage = ref('')
const actionFailed = ref(false)

const toast = ref({
  visible: false,
  type: 'success',
  message: ''
})

let toastTimer = null

const editForm = reactive({
  preferred_name: '',
  full_name: '',
  malayalam_name: '',
  authority_code: '',
  authority_type: '',
  notes: ''
})

const newVariant = reactive({
  variant_name: '',
  variant_type: 'OTHER',
  notes: ''
})

const filters = [
  { label: 'ALL', value: '' },
  { label: 'PROVISIONAL', value: 'PROVISIONAL' },
  { label: 'VERIFIED', value: 'VERIFIED' },
  { label: 'REJECTED', value: 'REJECTED' }
]

// ============================================================
// NAME VALIDATION AND NORMALIZATION
// ============================================================

function normalizeEnglishName(value) {
  return String(value || '')
    .replace(/[^A-Za-z0-9 .,'’()\-&]/g, '')
    .toUpperCase()
}

function normalizeFullName(value) {
  return String(value || '')
    .replace(/[^A-Za-z0-9 .,'’()\-&]/g, '')
    .trim()
}

function normalizeMalayalamName(value) {
  return String(value || '')
    .replace(/[^\u0D00-\u0D7F\s]/gu, '')
}

function normalizeVariantName(value) {
  return String(value || '').toUpperCase()
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'success') {
  if (toastTimer) {
    clearTimeout(toastTimer)
  }

  toast.value = {
    visible: true,
    type,
    message: String(message || 'Action completed.')
  }

  toastTimer = setTimeout(() => {
    toast.value.visible = false
    toastTimer = null
  }, 3500)
}

// ============================================================
// COMPUTED VALUES
// ============================================================

const provisionalCount = computed(() =>
  authorities.value.filter(
    item => item.status === 'PROVISIONAL'
  ).length
)

const verifiedCount = computed(() =>
  authorities.value.filter(
    item => item.status === 'VERIFIED'
  ).length
)

const rejectedCount = computed(() =>
  authorities.value.filter(
    item => item.status === 'REJECTED'
  ).length
)

const typeOptions = computed(() => [
  'PERSON', 'HISTORICAL', 'TRADITIONAL', 'CORPORATE',
  'FAMILY', 'UNKNOWN', 'ANONYMOUS', 'UNCONTROLLED'
])

const filteredAuthorities = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return authorities.value.filter(authority => {
    const matchesStatus =
      !statusFilter.value ||
      authority.status === statusFilter.value

    if (!matchesStatus) return false
    if (!query) return true

    return (
      String(authority.authority_code || '')
        .toLowerCase()
        .includes(query) ||
      String(authority.preferred_name || '')
        .toLowerCase()
        .includes(query) ||
      String(authority.full_name || '')
        .toLowerCase()
        .includes(query) ||
      String(authority.malayalam_name || '')
        .toLowerCase()
        .includes(query) ||
      String(authority.authority_type || '')
        .toLowerCase()
        .includes(query)
    )
  })
})

const currentIndex = computed(() => {
  if (!selectedAuthority.value) return -1

  return filteredAuthorities.value.findIndex(
    authority =>
      authority.authority_id ===
      selectedAuthority.value.authority_id
  )
})

const hasPrev = computed(() => currentIndex.value > 0)

const hasNext = computed(() =>
  currentIndex.value >= 0 &&
  currentIndex.value < filteredAuthorities.value.length - 1
)

const isDirty = computed(() => {
  const authority = selectedAuthority.value

  if (
    !authority ||
    authority.status !== 'PROVISIONAL'
  ) {
    return false
  }

  return (
    editForm.preferred_name !==
      normalizeEnglishName(authority.preferred_name || '') ||
    editForm.full_name !==
      (authority.full_name || '') ||
    editForm.malayalam_name !==
      (authority.malayalam_name || '') ||
    editForm.authority_type !==
      (authority.authority_type || '') ||
    editForm.notes !==
      (authority.notes || '')
  )
})

// ============================================================
// STATUS ACTION DIALOG
// ============================================================

const dlg = reactive({
  open: false,
  type: 'VERIFY',
  variantId: null,
  variantName: ''
})

const dlgTitle = computed(() => ({
  VERIFY: 'Verify this authority?',
  REJECT: 'Reject this authority?',
  REOPEN: 'Reopen for provisional review?',
  DELVARIANT: 'Delete this variant?'
}[dlg.type]))

const dlgText = computed(() => ({
  VERIFY:
    'Verifying formally confirms this person or body. The action is recorded in the audit trail permanently and cannot be erased.',
  REJECT:
    'A rejected authority cannot be linked to new works. The action is recorded in the audit trail permanently.',
  REOPEN:
    'The record returns to PROVISIONAL so it can be edited again. The earlier action stays in the audit trail.',
  DELVARIANT: 'The variant name is removed from this authority. The deletion is recorded in the audit trail.'
}[dlg.type]))

const dlgConfirm = computed(() => ({
  VERIFY: 'Verify',
  REJECT: 'Reject',
  REOPEN: 'Reopen',
  DELVARIANT: 'Delete'
}[dlg.type]))

function askAction(type) {
  if (actionLoading.value) return

  dlg.type = type
  dlg.open = true
}

function closeDialog() {
  dlg.open = false
}

async function submitDialog() {
  if (actionLoading.value) {
    return
  }

  const type = dlg.type
  dlg.open = false

  if (type === 'DELVARIANT') {
    await deleteVariant(dlg.variantId)
  } else if (type === 'VERIFY') {
    await verifyAuthority()
  } else if (type === 'REJECT') {
    await rejectAuthority()
  } else if (type === 'REOPEN') {
    await reopenAuthority()
  }
}

// ============================================================
// KEYBOARD NAVIGATION
// ============================================================

async function goRelative(delta) {
  if (actionLoading.value || dlg.open) return

  const next =
    filteredAuthorities.value[currentIndex.value + delta]

  if (!next) return

  if (
    isDirty.value &&
    !window.confirm(
      'Discard your unsaved changes and open the next record?'
    )
  ) {
    return
  }

  await openAuthority(next)
}

function onKeydown(event) {
  if (!selectedAuthority.value) return

  if (event.key === 'Escape') {
    if (dlg.open) {
      closeDialog()
    } else {
      closeAuthority()
    }

    return
  }

  const tag = event.target?.tagName || ''

  if (
    ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(tag) ||
    dlg.open
  ) {
    return
  }

  if (event.key === 'ArrowLeft') {
    goRelative(-1)
  } else if (event.key === 'ArrowRight') {
    goRelative(1)
  }
}

// ============================================================
// AUTHENTICATION
// ============================================================

function getAccessToken() {
  const authStore = useAuthStore()

  if (authStore.accessToken) {
    return authStore.accessToken
  }

  try {
    const auth = JSON.parse(
      localStorage.getItem('auth') || '{}'
    )

    return (
      auth?.accessToken ||
      auth?.token ||
      auth?.user?.accessToken ||
      null
    )
  } catch {
    return null
  }
}

// ============================================================
// API REQUEST HELPER
// ============================================================

async function apiRequest(path, options = {}) {
  const token = getAccessToken()

  if (!token) {
    throw new Error(
      'AUTH SESSION EXPIRED // Please log in again.'
    )
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  })

  let body = null

  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    let cleanMessage = ''

    if (Array.isArray(body?.detail)) {
      cleanMessage = body.detail
        .map(err => {
          const field = err.loc
            ? err.loc[err.loc.length - 1]
            : ''

          return (
            `VALIDATION ERROR // ${String(field).toUpperCase()}: ` +
            `${err.msg}`
          )
        })
        .join(' | ')
    } else if (typeof body?.detail === 'string') {
      cleanMessage = body.detail
    } else if (body?.message) {
      cleanMessage =
        typeof body.message === 'string'
          ? body.message
          : JSON.stringify(body.message)
    } else {
      cleanMessage = `REQUEST FAILED // HTTP ${response.status}`
    }

    const error = new Error(cleanMessage)
    error.status = response.status

    throw error
  }

  return body
}

// ============================================================
// FETCH AUTHORITY REGISTRY
// ============================================================

async function fetchAuthorities() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''

  const limit = 100
  let offset = 0
  let total = Infinity
  const allAuthorities = []
  const seenAuthorityIds = new Set()

  try {
    while (offset < total) {
      const response = await apiRequest(
        `/authority/?limit=${limit}&offset=${offset}`
      )

      const pageItems = Array.isArray(response?.data)
        ? response.data
        : Array.isArray(response)
          ? response
          : []

      // Read the total record count from the API response.
      if (offset === 0) {
        const reportedTotal = response?.total

        if (
          reportedTotal !== null &&
          reportedTotal !== undefined &&
          reportedTotal !== '' &&
          Number.isFinite(Number(reportedTotal)) &&
          Number(reportedTotal) >= 0
        ) {
          total = Number(reportedTotal)
        } else {
          total = pageItems.length < limit
            ? pageItems.length
            : Infinity
        }
      }

      if (pageItems.length === 0) break

      let addedThisBatch = 0

      for (const authority of pageItems) {
        const id = authority?.authority_id

        if (id !== null && id !== undefined) {
          const key = String(id)

          if (seenAuthorityIds.has(key)) continue

          seenAuthorityIds.add(key)
        }

        allAuthorities.push(authority)
        addedThisBatch++
      }

      if (allAuthorities.length >= total) break

      // Stop safely if the API returns duplicate records.
      if (addedThisBatch === 0) break

      // Move to the next batch.
      offset += pageItems.length

      if (pageItems.length < limit) break

      if (offset > 1000000) {
        throw new Error(
          'Pagination stopped because the registry exceeded the safety limit.'
        )
      }
    }

    authorities.value = allAuthorities

    if (
      Number.isFinite(total) &&
      allAuthorities.length < total
    ) {
      errorMessage.value =
        `Loaded ${allAuthorities.length} of ${total} authorities. ` +
        'Some records may be unavailable. Please retry.'
    }
  } catch (error) {
    authorities.value = []
    errorMessage.value =
      error.message || 'Unable to load authorities.'

    showToast(errorMessage.value, 'error')
  } finally {
    loading.value = false
  }
}

// ============================================================
// OPEN AUTHORITY DETAIL
// ============================================================

async function openAuthority(authority) {
  selectedAuthority.value = {
    ...authority,
    variants: [],
    works: []
  }

  actionMessage.value = ''
  actionFailed.value = false

  editForm.preferred_name =
    normalizeEnglishName(authority.preferred_name || '')

  editForm.full_name =
    authority.full_name || ''

  editForm.malayalam_name =
    authority.malayalam_name || ''

  editForm.authority_code =
    authority.authority_code || ''

  editForm.authority_type =
    authority.authority_type || ''

  editForm.notes = authority.notes || ''

  newVariant.variant_name = ''
  newVariant.variant_type = 'OTHER'
  newVariant.notes = ''

  try {
    const detail = await apiRequest(
      `/authority/${authority.authority_id}`
    )

    if (
      selectedAuthority.value?.authority_id !==
      authority.authority_id
    ) {
      return
    }

    selectedAuthority.value = detail

    editForm.preferred_name =
      normalizeEnglishName(detail.preferred_name || '')

    editForm.full_name =
      detail.full_name || ''

    editForm.malayalam_name =
      detail.malayalam_name || ''

    editForm.authority_code =
      detail.authority_code || ''

    editForm.authority_type =
      detail.authority_type || ''

    editForm.notes = detail.notes || ''
  } catch (error) {
    if (
      selectedAuthority.value?.authority_id ===
      authority.authority_id
    ) {
      actionFailed.value = true
      actionMessage.value =
        error.message || 'Unable to load authority details.'

      showToast(actionMessage.value, 'error')
    }
  }
}

function closeAuthority() {
  if (actionLoading.value) return

  selectedAuthority.value = null
  actionMessage.value = ''
  actionFailed.value = false
}

// ============================================================
// STATUS TRANSITIONS
// ============================================================

async function verifyAuthority() {
  if (
    !selectedAuthority.value ||
    selectedAuthority.value.status !== 'PROVISIONAL'
  ) {
    return
  }

  actionLoading.value = true
  actionType.value = 'VERIFY'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(
      `/authority/${selectedAuthority.value.authority_id}/verify`,
      {
        method: 'PATCH',
        body: JSON.stringify({ reason: 'Verified via UI' })
      }
    )

    if (data?.authority) {
      selectedAuthority.value = {
        ...selectedAuthority.value,
        ...data.authority
      }
    }

    actionMessage.value =
      data?.message || 'Authority verified successfully.'

    showToast(actionMessage.value)
    await fetchAuthorities()
  } catch (error) {
    actionFailed.value = true
    actionMessage.value =
      error.message || 'Verification failed.'

    showToast(actionMessage.value, 'error')
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

async function rejectAuthority() {
  if (
    !selectedAuthority.value ||
    selectedAuthority.value.status !== 'PROVISIONAL'
  ) {
    return
  }

  actionLoading.value = true
  actionType.value = 'REJECT'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(
      `/authority/${selectedAuthority.value.authority_id}/reject`,
      {
        method: 'PATCH',
        body: JSON.stringify({ reason: 'Rejected via UI' })
      }
    )

    if (data?.authority) {
      selectedAuthority.value = {
        ...selectedAuthority.value,
        ...data.authority
      }
    }

    actionMessage.value =
      data?.message || 'Authority rejected.'

    showToast(actionMessage.value)
    await fetchAuthorities()
  } catch (error) {
    actionFailed.value = true
    actionMessage.value =
      error.message || 'Rejection failed.'

    showToast(actionMessage.value, 'error')
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

async function reopenAuthority() {
  if (
    !selectedAuthority.value ||
    selectedAuthority.value.status === 'PROVISIONAL'
  ) {
    return
  }

  actionLoading.value = true
  actionType.value = 'REOPEN'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(
      `/authority/${selectedAuthority.value.authority_id}/reopen`,
      {
        method: 'PATCH',
        body: JSON.stringify({ reason: 'Reopened via UI' })
      }
    )

    if (data?.authority) {
      selectedAuthority.value = {
        ...selectedAuthority.value,
        ...data.authority
      }
    }

    actionMessage.value =
      data?.message ||
      'Authority reopened for provisional review.'

    showToast(actionMessage.value)
    await fetchAuthorities()
  } catch (error) {
    actionFailed.value = true
    actionMessage.value =
      error.message || 'Reopening failed.'

    showToast(actionMessage.value, 'error')
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

// ============================================================
// EDIT AUTHORITY DETAILS
// ============================================================

async function saveAuthorityDetails() {
  if (
    !selectedAuthority.value ||
    selectedAuthority.value.status !== 'PROVISIONAL'
  ) {
    return
  }

  const authorityId = selectedAuthority.value.authority_id

  actionLoading.value = true
  actionType.value = 'UPDATE'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    const data = await apiRequest(
      `/authority/${authorityId}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          preferred_name: normalizeEnglishName(
            editForm.preferred_name
          ).trim(),
          full_name: normalizeFullName(
            editForm.full_name
          ).trim(),
          malayalam_name: normalizeMalayalamName(
            editForm.malayalam_name
          ).trim(),
          authority_code: editForm.authority_code,
          authority_type: editForm.authority_type,
          notes: editForm.notes,
          reason: 'Updated via UI'
        })
      }
    )

    if (
      selectedAuthority.value?.authority_id === authorityId &&
      data?.authority
    ) {
      selectedAuthority.value = {
        ...selectedAuthority.value,
        ...data.authority
      }
    }

    editForm.preferred_name = normalizeEnglishName(
      editForm.preferred_name
    ).trim()

    editForm.full_name = normalizeFullName(
      editForm.full_name
    ).trim()

    editForm.malayalam_name = normalizeMalayalamName(
      editForm.malayalam_name
    ).trim()

    actionMessage.value = 'Record details updated successfully.'

    showToast(actionMessage.value)
    await fetchAuthorities()
  } catch (error) {
    actionFailed.value = true
    actionMessage.value =
      error.message || 'Failed to update record.'

    showToast(actionMessage.value, 'error')
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

// ============================================================
// VARIANT MANAGEMENT
// ============================================================

async function addVariant() {
  const authority = selectedAuthority.value

  const variantName = normalizeVariantName(
    newVariant.variant_name
  ).trim()

  if (!authority) return

  if (authority.status !== 'PROVISIONAL') {
    actionFailed.value = true
    actionMessage.value =
      'Only provisional authorities can be edited.'

    showToast(actionMessage.value, 'error')
    return
  }

  if (!variantName) {
    actionFailed.value = true
    actionMessage.value = 'Enter a variant name.'

    showToast(actionMessage.value, 'error')
    return
  }

  const authorityId = authority.authority_id

  actionLoading.value = true
  actionType.value = 'ADD_VARIANT'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    await apiRequest(
      `/authority/${authorityId}/variants`,
      {
        method: 'POST',
        body: JSON.stringify({
          variant_name: variantName,
          variant_type: newVariant.variant_type || 'OTHER',
          reason: 'Variant added via UI'
        })
      }
    )

    newVariant.variant_name = ''
    newVariant.variant_type = 'OTHER'
    newVariant.notes = ''

    actionMessage.value = 'Variant added successfully.'
    showToast(actionMessage.value)

    const detail = await apiRequest(
      `/authority/${authorityId}`
    )

    if (
      selectedAuthority.value?.authority_id === authorityId
    ) {
      selectedAuthority.value = detail
    }
  } catch (error) {
    actionFailed.value = true
    actionMessage.value =
      error.message || 'Failed to add variant.'

    showToast(actionMessage.value, 'error')
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

function askVariantDelete(variantId, variantName) {
  const authority = selectedAuthority.value

  if (!authority || actionLoading.value) return

  if (authority.status !== 'PROVISIONAL') {
    actionFailed.value = true
    actionMessage.value =
      'Only provisional authorities can be edited.'

    showToast(actionMessage.value, 'error')
    return
  }

  dlg.type = 'DELVARIANT'
  dlg.variantId = variantId
  dlg.variantName = variantName
  dlg.open = true
}

async function deleteVariant(variantId) {
  const authority = selectedAuthority.value

  if (!authority) return

  const authorityId = authority.authority_id

  actionLoading.value = true
  actionType.value = 'DEL_VARIANT'
  actionMessage.value = ''
  actionFailed.value = false

  try {
    await apiRequest(
      `/authority/${authorityId}/variants/${variantId}`,
      {
        method: 'DELETE',
        body: JSON.stringify({ reason: 'Variant deleted via UI' })
      }
    )

    actionMessage.value = 'Variant deleted successfully.'
    showToast(actionMessage.value)

    const detail = await apiRequest(
      `/authority/${authorityId}`
    )

    if (
      selectedAuthority.value?.authority_id === authorityId
    ) {
      selectedAuthority.value = detail
    }
  } catch (error) {
    actionFailed.value = true
    actionMessage.value =
      error.message || 'Failed to delete variant.'

    showToast(actionMessage.value, 'error')
  } finally {
    actionLoading.value = false
    actionType.value = ''
  }
}

// ============================================================
// HELPERS
// ============================================================

function resetFilters() {
  searchQuery.value = ''
  statusFilter.value = ''
}

function statusClass(status) {
  return String(status || '')
    .toLowerCase()
    .replace(/\s+/g, '-')
}

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString()
}

// ============================================================
// LIFECYCLE
// ============================================================

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  fetchAuthorities()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)

  if (toastTimer) {
    clearTimeout(toastTimer)
  }
})
</script>

<template>
  <div class="authority-page">

    <!-- LIST VIEW MODE -->
    <template v-if="!selectedAuthority">
      <!-- HEADER -->
      <header class="page-header">
        <div>
          <div class="eyebrow">CLASSIFICATION // REGISTRY</div>
          <h1>Authorities</h1>
          <p class="subtitle">
            Controlled authority records and verification status across the catalogue.
          </p>
        </div>

        <div class="header-meta">
          <div class="meta-label">REGISTRY</div>
          <div class="meta-value">{{ filteredAuthorities.length }}</div>
        </div>
      </header>

      <!-- METRICS -->
      <section class="metrics">
        <div class="metric-card">
          <div class="metric-label">TOTAL AUTHORITIES</div>
          <div class="metric-value">{{ authorities.length }}</div>
        </div>

        <div class="metric-card provisional">
          <div class="metric-label">PROVISIONAL</div>
          <div class="metric-value">{{ provisionalCount }}</div>
        </div>

        <div class="metric-card verified">
          <div class="metric-label">VERIFIED</div>
          <div class="metric-value">{{ verifiedCount }}</div>
        </div>

        <div class="metric-card rejected">
          <div class="metric-label">REJECTED</div>
          <div class="metric-value">{{ rejectedCount }}</div>
        </div>
      </section>

      <!-- TOOLBAR -->
      <section class="toolbar">
        <div class="search-box">
          <span class="search-icon">⌕</span>

          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search authority code or preferred name..."
          />

          <button
            v-if="searchQuery"
            class="clear-search"
            type="button"
            @click="searchQuery = ''"
          >
            ×
          </button>
        </div>

        <div class="filters">
          <button
            v-for="filter in filters"
            :key="filter.value"
            type="button"
            class="filter-button"
            :class="[
              statusClass(filter.value) || 'all',
              { active: statusFilter === filter.value }
            ]"
            @click="statusFilter = filter.value"
          >
            {{ filter.label }}
          </button>
        </div>
      </section>

      <!-- REGISTRY ERROR -->
      <div v-if="errorMessage" class="error-banner">
        <div>
          <strong>REQUEST FAILED</strong>
          <span>{{ errorMessage }}</span>
        </div>

        <button type="button" @click="fetchAuthorities">
          RETRY
        </button>
      </div>

      <!-- LOADING -->
      <div v-if="loading" class="state-panel">
        <div class="state-code">LOADING</div>
        <div class="state-text">Loading authority registry...</div>
      </div>

      <!-- EMPTY -->
      <div
        v-else-if="!filteredAuthorities.length"
        class="state-panel"
      >
        <div class="state-code">NO RECORDS</div>

        <div class="state-text">
          No authorities match the current search or filter.
        </div>

        <button
          v-if="searchQuery || statusFilter"
          type="button"
          class="reset-button"
          @click="resetFilters"
        >
          RESET FILTERS
        </button>
      </div>

      <!-- REGISTRY TABLE -->
      <section v-else class="registry-panel">
        <div class="table-head">
          <div>AUTHORITY CODE</div>
          <div>PREFERRED NAME</div>
          <div>TYPE</div>
          <div>STATUS</div>
          <div></div>
        </div>

        <div
          v-for="authority in filteredAuthorities"
          :key="authority.authority_id"
          class="authority-row"
          @click="openAuthority(authority)"
        >
          <div class="authority-code">
            {{ authority.authority_code }}
          </div>

          <div class="authority-name">
            <div>
              {{ normalizeEnglishName(authority.preferred_name) }}
            </div>
            <div v-if="authority.full_name" class="authority-name-full">
              {{ authority.full_name }}
            </div>
            <div
              v-if="authority.malayalam_name"
              class="authority-name-malayalam"
            >
              {{ authority.malayalam_name }}
            </div>
          </div>

          <div class="authority-type">
            {{ authority.authority_type }}
          </div>

          <div>
            <span
              class="status-badge"
              :class="statusClass(authority.status)"
            >
              {{ authority.status }}
            </span>
          </div>

          <div class="row-action">
            VIEW →
          </div>
        </div>
      </section>
    </template>

    <!-- FULL-PAGE WORKSPACE DETAIL VIEW -->
    <template v-else>
      <div class="workspace-view">
        <!-- WORKSPACE HEADER -->
        <header class="workspace-header">
          <div class="workspace-nav-left">
            <button
              type="button"
              class="back-btn"
              @click="closeAuthority"
            >
              ← BACK TO REGISTRY
            </button>
            <span v-if="isDirty" class="dirty-badge">
              Unsaved changes
            </span>
          </div>

          <div class="workspace-pagination">
            <button
              type="button"
              class="nav-btn"
              :disabled="!hasPrev || actionLoading"
              @click="goRelative(-1)"
            >
              &#8249; PREV
            </button>
            <span class="nav-count">
              {{ currentIndex >= 0 ? currentIndex + 1 : '-' }} / {{ filteredAuthorities.length }}
            </span>
            <button
              type="button"
              class="nav-btn"
              :disabled="!hasNext || actionLoading"
              @click="goRelative(1)"
            >
              NEXT &#8250;
            </button>
          </div>
        </header>

        <!-- INLINE ACTION MESSAGE -->
        <div
          v-if="actionMessage"
          class="action-message"
          :class="{ failure: actionFailed }"
        >
          {{ actionMessage }}
        </div>

        <div class="workspace-title-block">
          <div>
            <div class="eyebrow">AUTHORITY RECORD MANAGEMENT</div>
            <h2>{{ normalizeEnglishName(selectedAuthority.preferred_name) }}</h2>
            <div v-if="selectedAuthority.full_name" class="workspace-name-full">
              Full Name: <strong>{{ selectedAuthority.full_name }}</strong>
            </div>
            <div v-if="selectedAuthority.malayalam_name" class="workspace-name-malayalam">
              {{ selectedAuthority.malayalam_name }}
            </div>
            <div class="workspace-code">{{ selectedAuthority.authority_code }}</div>
          </div>

          <div class="workspace-actions-top">
            <template v-if="selectedAuthority.status === 'PROVISIONAL'">
              <button
                type="button"
                class="action-button verify"
                :disabled="actionLoading"
                @click="askAction('VERIFY')"
              >
                <span>VERIFY AUTHORITY</span>
              </button>
              <button
                type="button"
                class="action-button reject"
                :disabled="actionLoading"
                @click="askAction('REJECT')"
              >
                <span>REJECT AUTHORITY</span>
              </button>
            </template>
            <template v-else>
              <div class="status-message">
                Status: <strong>{{ selectedAuthority.status }}</strong>
              </div>
              <button
                type="button"
                class="action-button reopen"
                :disabled="actionLoading"
                @click="askAction('REOPEN')"
              >
                <span>↺ REOPEN FOR REVIEW</span>
              </button>
            </template>
          </div>
        </div>

        <!-- TWO COLUMN MASTER GRID -->
        <div class="workspace-grid">
          
          <!-- LEFT COLUMN: CORE ATTRIBUTES & EDITING -->
          <div class="col-main">
            <section class="detail-section">
              <div class="section-header-flex">
                <div class="section-title">CORE ATTRIBUTES</div>
                <span class="status-badge" :class="statusClass(selectedAuthority.status)">
                  {{ selectedAuthority.status }}
                </span>
              </div>

              <!-- EDITABLE PROVISIONAL FORM -->
              <form
                v-if="selectedAuthority.status === 'PROVISIONAL'"
                class="edit-form"
                @submit.prevent="saveAuthorityDetails"
              >
                <div class="form-grid">
                  <div class="form-field">
                    <label>PREFERRED NAME — ENGLISH</label>
                    <input
                      :value="editForm.preferred_name"
                      type="text"
                      autocomplete="off"
                      required
                      placeholder="e.g. A. P. J. ABDUL KALAM"
                      @input="editForm.preferred_name = normalizeEnglishName($event.target.value)"
                    />
                  </div>

                  <div class="form-field">
                    <label>FULL FORM OF NAME (UNABBREVIATED)</label>
                    <input
                      :value="editForm.full_name"
                      type="text"
                      autocomplete="off"
                      placeholder="e.g. Avul Pakir Jainulabdeen Abdul Kalam"
                      @input="editForm.full_name = normalizeFullName($event.target.value)"
                    />
                  </div>

                  <div class="form-field">
                    <label>PREFERRED NAME — MALAYALAM</label>
                    <input
                      :value="editForm.malayalam_name"
                      type="text"
                      autocomplete="off"
                      placeholder="മലയാളത്തിലുള്ള പേര്"
                      @input="editForm.malayalam_name = normalizeMalayalamName($event.target.value)"
                    />
                  </div>

                  <div class="form-field">
                    <label>AUTHORITY CODE</label>
                    <input v-model="editForm.authority_code" type="text" readonly class="disabled-input" />
                  </div>

                  <div class="form-field">
                    <label>AUTHORITY TYPE</label>
                    <select v-model="editForm.authority_type">
                      <option v-for="opt in typeOptions" :key="opt" :value="opt">
                        {{ opt }}
                      </option>
                    </select>
                  </div>

                  <div class="form-field">
                    <label>RECORD ID</label>
                    <input :value="selectedAuthority.authority_id" disabled class="disabled-input" />
                  </div>
                </div>

                <button type="submit" class="save-button" :disabled="actionLoading">
                  <span>{{ actionLoading && actionType === 'UPDATE' ? 'SAVING...' : 'SAVE CHANGES' }}</span>
                </button>
              </form>

              <!-- READ-ONLY VIEW -->
              <div v-else class="read-only-grid">
                <div class="readonly-item">
                  <span class="readonly-label">AUTHORITY ID</span>
                  <span class="readonly-value">{{ selectedAuthority.authority_id }}</span>
                </div>
                <div class="readonly-item">
                  <span class="readonly-label">TYPE</span>
                  <span class="readonly-value">{{ selectedAuthority.authority_type }}</span>
                </div>
                <div class="readonly-item">
                  <span class="readonly-label">CREATED</span>
                  <span class="readonly-value">{{ formatDate(selectedAuthority.created_at) }}</span>
                </div>
                <div class="readonly-item">
                  <span class="readonly-label">UPDATED</span>
                  <span class="readonly-value">{{ formatDate(selectedAuthority.updated_at) }}</span>
                </div>
              </div>
            </section>
          </div>

          <!-- RIGHT COLUMN: VARIANTS & CONNECTED WORKS -->
          <div class="col-side">
            <!-- VARIANT NAMES -->
            <section class="detail-section">
              <div class="section-title">VARIANT NAMES & ALIASES</div>

              <div v-if="selectedAuthority.variants?.length" class="variant-list">
                <div
                  v-for="variant in selectedAuthority.variants"
                  :key="variant.variant_id"
                  class="variant-item-card"
                >
                  <div class="variant-content">
                    <div class="variant-name-text">
                      {{ normalizeVariantName(variant.variant_name) }}
                    </div>
                    <div v-if="variant.variant_type" class="variant-type-pill">
                      {{ variant.variant_type }}
                    </div>
                  </div>

                  <button
                    v-if="selectedAuthority.status === 'PROVISIONAL'"
                    type="button"
                    class="variant-delete-btn"
                    :disabled="actionLoading"
                    title="Delete variant"
                    @click.stop="askVariantDelete(variant.variant_id, variant.variant_name)"
                  >
                    REMOVE
                  </button>
                </div>
              </div>
              <div v-else class="muted">No variant names registered.</div>

              <!-- ADD VARIANT FORM -->
              <form
                v-if="selectedAuthority.status === 'PROVISIONAL'"
                class="add-variant-box"
                @submit.prevent="addVariant"
              >
                <div class="form-field">
                  <label>ALIAS / VARIANT NAME</label>
                  <input
                    :value="newVariant.variant_name"
                    type="text"
                    placeholder="Enter alias name..."
                    maxlength="255"
                    required
                    @input="newVariant.variant_name = normalizeVariantName($event.target.value)"
                  />
                </div>

                <div class="form-field">
                  <label>VARIANT TYPE</label>
                  <select v-model="newVariant.variant_type" required>
                    <option value="ALTERNATE_NAME">ALTERNATE_NAME</option>
                    <option value="INITIALISM">INITIALISM</option>
                    <option value="PEN NAME">PEN NAME</option>
                    <option value="TRANSLITERATION">TRANSLITERATION</option>
                    <option value="TRANSLATED_NAME">TRANSLATED_NAME</option>
                    <option value="FORMER_NAME">FORMER_NAME</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>

                <button
                  type="submit"
                  class="add-variant-btn"
                  :disabled="actionLoading || !newVariant.variant_name.trim()"
                >
                  <span>{{ actionLoading && actionType === 'ADD_VARIANT' ? 'ADDING...' : '+ ADD VARIANT' }}</span>
                </button>
              </form>
            </section>

            <!-- CONNECTED WORKS -->
            <section class="detail-section">
              <div class="section-title">
                CONNECTED WORKS ({{ selectedAuthority.works?.length || 0 }})
              </div>

              <div v-if="selectedAuthority.works?.length" class="works-list">
                <div
                  v-for="work in selectedAuthority.works"
                  :key="`${work.work_id}-${work.sequence_no}`"
                  class="work-row"
                >
                  <div class="work-id">{{ work.work_id }}</div>
                  <div class="work-info">
                    <strong>{{ work.title || 'Untitled work' }}</strong>
                    <span>{{ work.relationship_type }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="muted">No works connected to this authority.</div>
            </section>
          </div>

        </div>

        <!-- BOTTOM FULL-WIDTH AUDIT NOTES & LOG SECTION -->
        <section class="audit-section-full">
          <div class="section-title">AUDIT LOG & SYSTEM NOTES</div>
          
          <div class="audit-log-container">
            <textarea
              v-if="selectedAuthority.status === 'PROVISIONAL'"
              v-model="editForm.notes"
              rows="6"
              class="notes-area"
              placeholder="Cataloguing notes and audit logs..."
            ></textarea>
            <div v-else class="notes-display-box">
              {{ selectedAuthority.notes || 'No notes logged.' }}
            </div>
          </div>

          <div v-if="selectedAuthority.verified_at" class="verification-audit-bar">
            <span>VERIFIED AT: <strong>{{ formatDate(selectedAuthority.verified_at) }}</strong></span>
            <span>VERIFIED BY USER ID: <strong>{{ selectedAuthority.verified_by }}</strong></span>
          </div>
        </section>

      </div>
    </template>

    <!-- STATUS ACTION DIALOG -->
    <div v-if="dlg.open" class="dlg-overlay" @click.self="closeDialog">
      <div class="dlg" :class="'dlg-' + dlg.type.toLowerCase()" role="alertdialog" aria-modal="true">
        <h3>{{ dlgTitle }}</h3>
        <p class="dlg-name">
          <strong>{{ normalizeEnglishName(selectedAuthority.preferred_name) }}</strong> &middot; {{ selectedAuthority.authority_code }}
        </p>
        <p class="dlg-text">{{ dlgText }}</p>
        <div class="dlg-actions">
          <button type="button" class="dlg-cancel" @click="closeDialog">Cancel</button>
          <button
            type="button"
            class="dlg-confirm"
            :disabled="actionLoading"
            @click="submitDialog"
          >
            {{ dlgConfirm }}
          </button>
        </div>
      </div>
    </div>

    <!-- AUTO-DISMISSING TOAST -->
    <Transition name="toast">
      <div
        v-if="toast.visible"
        class="authority-toast"
        :class="`authority-toast--${toast.type}`"
        role="status"
        aria-live="polite"
      >
        {{ toast.message }}
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.authority-page {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2.5rem;
  max-width: 1500px;
  margin: 0 auto;
  font-family: inherit;
  color: var(--text-primary);
  background-color: var(--app-bg);
  min-height: 100vh;
}

/* HEADER */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-main);
  padding-bottom: 1.5rem;
}

.eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--accent);
  margin-bottom: 0.5rem;
}

.page-header h1 {
  font-size: 2.25rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.subtitle {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin: 0;
}

.header-meta {
  background: var(--surface);
  border: 1px solid var(--border-main);
  padding: 0.75rem 1.25rem;
  border-radius: 6px;
  text-align: right;
  box-shadow: var(--shadow);
}

.meta-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent);
}

/* METRICS */
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.metric-card {
  background: var(--surface);
  border: 1px solid var(--border-main);
  padding: 1.25rem;
  border-radius: 8px;
  box-shadow: var(--shadow);
  border-left: 4px solid var(--accent);
}

.metric-card.provisional {
  border-left-color: var(--accent);
}

.metric-card.verified {
  border-left-color: var(--text-success);
}

.metric-card.rejected {
  border-left-color: var(--text-danger);
}

.metric-label {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
}

/* TOOLBAR */
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: space-between;
  align-items: center;
  background: var(--surface);
  padding: 1rem;
  border: 1px solid var(--border-main);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 280px;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  color: var(--text-muted);
  font-size: 1.1rem;
}

.search-box input {
  width: 100%;
  padding: 0.625rem 2.25rem 0.625rem 2.25rem;
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--text-primary);
  outline: none;
}

.search-box input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--catalog-accent-soft);
}

.clear-search {
  position: absolute;
  right: 0.75rem;
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--text-muted);
  cursor: pointer;
}

.filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-button {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-button:hover {
  background: var(--hover-bg);
}

.filter-button.active {
  background: var(--accent);
  color: var(--button-text);
  border-color: var(--accent);
}

/* ERROR & STATES */
.error-banner {
  background: var(--surface-danger);
  border: 1px solid var(--border-danger);
  color: var(--text-danger);
  padding: 1rem;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-banner button {
  background: var(--text-danger);
  color: var(--button-text);
  border: none;
  padding: 0.375rem 0.75rem;
  font-weight: 700;
  font-size: 0.75rem;
  border-radius: 4px;
  cursor: pointer;
}

.state-panel {
  background: var(--surface);
  border: 1px solid var(--border-main);
  padding: 3rem;
  text-align: center;
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.state-code {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.state-text {
  font-size: 1rem;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.reset-button {
  background: var(--accent);
  color: var(--button-text);
  border: none;
  padding: 0.5rem 1rem;
  font-weight: 700;
  font-size: 0.75rem;
  border-radius: 6px;
  cursor: pointer;
}

/* REGISTRY TABLE */
.registry-panel {
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.table-head {
  display: grid;
  grid-template-columns: 180px 1fr 150px 130px 90px;
  background: var(--surface-2);
  padding: 0.875rem 1.25rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-main);
  align-items: center;
}

.authority-row {
  display: grid;
  grid-template-columns: 180px 1fr 150px 130px 90px;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-main);
  align-items: center;
  cursor: pointer;
  transition: background-color 0.15s;
}

.authority-row:hover {
  background-color: var(--hover-bg);
}

.authority-code {
  font-family: monospace;
  font-weight: 600;
  color: var(--accent);
}

.authority-name {
  font-weight: 600;
  color: var(--text-primary);
}

.authority-name-full {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-weight: normal;
}

.authority-name-malayalam {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-weight: 400;
  margin-top: 0.125rem;
}

.authority-type {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  font-size: 0.65rem;
  font-weight: 700;
  border-radius: 9999px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.status-badge.provisional {
  background: var(--surface-warning);
  color: var(--text-warning);
  border: 1px solid var(--border-warning);
}

.status-badge.verified {
  background: var(--surface-success);
  color: var(--text-success);
  border: 1px solid var(--border-success);
}

.status-badge.rejected {
  background: var(--surface-danger);
  color: var(--text-danger);
  border: 1px solid var(--border-danger);
}

.row-action {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--accent);
  text-align: right;
}

/* FULL-PAGE WORKSPACE VIEW */
.workspace-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface);
  padding: 1rem 1.5rem;
  border: 1px solid var(--border-main);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.back-btn {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  color: var(--text-primary);
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 6px;
  cursor: pointer;
}

.back-btn:hover {
  background: var(--hover-bg);
}

.dirty-badge {
  background: var(--surface-warning);
  color: var(--text-warning);
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  margin-left: 1rem;
  border: 1px solid var(--border-warning);
}

.workspace-pagination {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.nav-btn {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  color: var(--text-primary);
  padding: 0.375rem 0.75rem;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 4px;
  cursor: pointer;
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.nav-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
}

.workspace-title-block {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: var(--surface);
  border: 1px solid var(--border-main);
  padding: 1.75rem;
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.workspace-title-block h2 {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0.25rem 0;
}

.workspace-name-full {
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.workspace-name-malayalam {
  font-size: 1rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.workspace-code {
  font-family: monospace;
  font-size: 0.85rem;
  color: var(--accent);
}

.workspace-actions-top {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

/* MASTER GRID */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

@media (max-width: 1024px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

.col-main, .col-side {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.detail-section {
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: var(--shadow);
}

.section-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

/* READ-ONLY METADATA GRID */
.read-only-grid {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  padding: 1.25rem;
  border-radius: 6px;
}

.readonly-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px dashed var(--border-main);
  padding-bottom: 0.5rem;
}

.readonly-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.readonly-label {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.readonly-value {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 0.9rem;
}

/* FORM ELEMENTS */
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field label {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

.form-field input,
.form-field select,
.form-field textarea {
  padding: 0.625rem;
  border: 1px solid var(--border-main);
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
  background: var(--surface-2);
  color: var(--text-primary);
}

.form-field input:focus,
.form-field select:focus,
.form-field textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--catalog-accent-soft);
}

.disabled-input {
  background: var(--surface-2) !important;
  color: var(--text-muted);
  cursor: not-allowed;
  opacity: 0.7;
}

/* VARIANT CARDS */
.variant-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.variant-item-card {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  padding: 0.875rem 1rem;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.variant-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.variant-name-text {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 0.95rem;
}

.variant-type-pill {
  font-size: 0.65rem;
  background: var(--surface);
  color: var(--accent);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  width: fit-content;
  font-weight: 700;
  letter-spacing: 0.05em;
  border: 1px solid var(--border-main);
}

.variant-delete-btn {
  background: var(--surface-danger);
  color: var(--text-danger);
  border: 1px solid var(--border-danger);
  padding: 0.375rem 0.625rem;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 4px;
  cursor: pointer;
}

.variant-delete-btn:hover {
  opacity: 0.85;
}

.add-variant-box {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  padding: 1.25rem;
  border-radius: 6px;
}

/* BUTTONS */
.save-button,
.add-variant-btn,
.action-button {
  background: var(--accent);
  color: var(--button-text);
  border: none;
  padding: 0.75rem 1rem;
  font-weight: 700;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.save-button:hover,
.add-variant-btn:hover,
.action-button.verify:hover {
  opacity: 0.9;
}

.action-button.reject {
  background: var(--text-danger);
  color: var(--button-text);
}

.action-button.reject:hover {
  opacity: 0.9;
}

.action-button.reopen {
  background: var(--surface-2);
  color: var(--text-primary);
  border: 1px solid var(--border-main);
}

.action-button.reopen:hover {
  background: var(--hover-bg);
}

/* CONNECTED WORKS */
.works-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.work-row {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  padding: 0.75rem 1rem;
  border-radius: 6px;
  display: flex;
  gap: 1rem;
  align-items: center;
}

.work-id {
  font-family: monospace;
  background: var(--surface);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  color: var(--accent);
  font-size: 0.8rem;
  font-weight: 700;
  border: 1px solid var(--border-main);
}

.work-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.work-info strong {
  color: var(--text-primary);
  font-size: 0.9rem;
}

.work-info span {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* BOTTOM FULL-WIDTH AUDIT SECTION */
.audit-section-full {
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 8px;
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  box-shadow: var(--shadow);
}

.notes-area {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  color: var(--text-primary);
  padding: 1rem;
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.9rem;
  outline: none;
}

.notes-display-box {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  padding: 1rem;
  border-radius: 6px;
  font-family: monospace;
  white-space: pre-wrap;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.verification-audit-bar {
  display: flex;
  justify-content: space-between;
  background: var(--surface-2);
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.75rem;
  color: var(--text-muted);
  border: 1px solid var(--border-main);
}

.verification-audit-bar strong {
  color: var(--text-primary);
}

/* DIALOG & TOAST */
.dlg-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.dlg {
  background: var(--surface);
  border: 1px solid var(--border-main);
  padding: 2rem;
  border-radius: 8px;
  width: 100%;
  max-width: 450px;
  box-shadow: var(--shadow);
}

.dlg h3 {
  margin-top: 0;
  color: var(--text-primary);
}

.dlg-name {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.dlg-text {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.dlg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.dlg-cancel {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
  font-weight: bold;
  border-radius: 4px;
  cursor: pointer;
}

.dlg-confirm {
  background: var(--accent);
  color: var(--button-text);
  border: none;
  padding: 0.5rem 1rem;
  font-weight: bold;
  border-radius: 4px;
  cursor: pointer;
}

.authority-toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  background: var(--surface);
  color: var(--text-primary);
  padding: 0.875rem 1.25rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  z-index: 200;
  border: 1px solid var(--border-main);
  border-left: 4px solid var(--accent);
  box-shadow: var(--shadow);
}

.authority-toast--error {
  border-left-color: var(--text-danger);
}

.action-message {
  padding: 0.75rem 1.5rem;
  background: var(--surface-success);
  color: var(--text-success);
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid var(--border-success);
}

.action-message.failure {
  background: var(--surface-danger);
  color: var(--text-danger);
  border-color: var(--border-danger);
}

.muted {
  color: var(--text-muted);
  font-size: 0.85rem;
  font-style: italic;
}
</style>