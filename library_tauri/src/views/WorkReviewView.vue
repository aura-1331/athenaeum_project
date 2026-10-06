<template>
  <div class="dk">
    <!-- Header -->
    <header class="dk-head">
      <div>
        <p class="dk-org">Athenaeum Orbis</p>
        <h1>Work #{{ workId }}</h1>
        <p class="dk-sub">{{ subtitle }}</p>
      </div>
      <button type="button" class="dk-btn dk-btn-ghost" @click="goBack">
        <span class="dk-btn-icon">←</span> Back to Docket
      </button>
    </header>

    <!-- Error Banner -->
    <div v-if="error" class="dk-msg dk-msg-error" role="alert">
      <div class="dk-msg-content">
        <span class="dk-msg-symbol">⚠️</span>
        <span>{{ error }}</span>
      </div>
      <button type="button" class="dk-msg-close" aria-label="Dismiss" @click="error = ''">×</button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="dk-empty">
      <div class="dk-spin"></div>
      <strong>Opening archive record…</strong>
      <span>Gathering catalogue data and edit history</span>
    </div>

    <!-- Missing State -->
    <div v-else-if="!data" class="dk-empty dk-empty-error">
      <span class="dk-empty-icon">📭</span>
      <strong>This work could not be opened</strong>
      <span>It may not exist in the collection, or it may belong to another desk.</span>
    </div>

    <!-- Main Content -->
    <template v-else>
      <!-- Overview Summary Strip -->
      <section class="ir-strip">
        <div class="ir-strip-main">
          <h2>{{ data.values.title || 'Untitled Work' }}</h2>
          <div class="ir-meta">
            <span v-if="data.values.author" class="ir-meta-item">
              <span class="ir-meta-label">Author</span>
              <strong>{{ data.values.author }}</strong>
            </span>
            <span v-if="data.proposer_name" class="ir-meta-item">
              <span class="ir-meta-label">Proposed by</span>
              <strong>{{ data.proposer_name }}</strong>
            </span>
            <span class="ir-meta-item ir-meta-copies">
              <span class="ir-badge-dot"></span>
              {{ data.item_count }} {{ data.item_count === 1 ? 'copy' : 'copies' }} attached
            </span>
          </div>
        </div>
        <div class="ir-strip-aside">
          <span class="ir-pill" :class="statusClass">
            <span class="ir-pill-bullet"></span>
            {{ statusLabel }}
          </span>
        </div>
      </section>

      <!-- Two-column Workspace -->
      <div class="ir-grid">
        <!-- LEFT: Book Details & Rejection Notice -->
        <div class="ir-col">
          <!-- Rejection Alert Card -->
          <section v-if="data.status === 'REJECTED'" class="ir-card ir-alert">
            <div class="ir-alert-header">
              <span class="ir-alert-icon">↩</span>
              <div>
                <h3>Sent back by The Chief</h3>
                <p v-if="data.rejection_reason" class="ir-alert-text">{{ data.rejection_reason }}</p>
              </div>
            </div>

            <p v-if="data.legacy_rejection" class="ir-hint ir-alert-note">
              Sent back before specific field marking existed, so every field is open for revision.
            </p>
            <div v-else-if="data.correction" class="ir-correction-callout">
              <span class="ir-correction-title">Requested updates:</span>
              <div class="ir-correction-chips">
                <span
                  v-for="f in data.correction.fields"
                  :key="f"
                  class="ir-chip ir-chip-alert"
                >
                  {{ fieldLabel(f) }}
                </span>
              </div>
            </div>
          </section>

          <!-- Core Record Details -->
          <section class="ir-card ir-details-card">
            <div class="ir-card-header">
              <div>
                <h3>Work details</h3>
                <p v-if="isReviewMode" class="ir-hint">
                  Press <strong>Needs fix</strong> on any detail that must be corrected. Only selected fields will unlock for editing.
                </p>
                <p v-else-if="canCorrect" class="ir-hint">
                  Only highlighted fields are open for editing. All other values remain locked.
                </p>
                <p v-else class="ir-hint">
                  Catalogue records are archived and locked in read-only mode.
                </p>
              </div>
            </div>

            <div class="wg-list">
              <div v-for="g in GROUPS" :key="g.title" class="wg">
                <div class="wg-header">
                  <h4 class="wg-title">{{ g.title }}</h4>
                  <span class="wg-line"></span>
                </div>

                <div class="wg-grid">
                  <div
                    v-for="key in g.keys"
                    :key="key"
                    class="wf"
                    :class="[fieldClass(key), { 'wf-wide': FIELD_BY_KEY[key].wide }]"
                  >
                    <div class="wf-top">
                      <label class="wf-label" :for="`f-${key}`">
                        {{ FIELD_BY_KEY[key].label }}
                      </label>

                      <!-- Reviewer Fix Checkbox -->
                      <label v-if="isReviewMode" class="wf-fix">
                        <input
                          v-model="ticks[key]"
                          type="checkbox"
                          :aria-label="`Needs correction: ${FIELD_BY_KEY[key].label}`"
                        />
                        <span class="wf-fix-badge">
                          <span class="wf-fix-check">✓</span> Needs fix
                        </span>
                      </label>

                      <!-- Keeper Highlight Flag -->
                      <span v-else-if="isMarked(key)" class="ir-flag">
                        Action required
                      </span>
                    </div>

                    <!-- Editable Input vs Static Display -->
                    <template v-if="isEditable(key)">
                      <textarea
                        v-if="FIELD_BY_KEY[key].type === 'textarea'"
                        :id="`f-${key}`"
                        v-model="form[key]"
                        class="wf-control"
                        rows="3"
                        :placeholder="`Enter ${FIELD_BY_KEY[key].label.toLowerCase()}…`"
                      ></textarea>
                      <input
                        v-else
                        :id="`f-${key}`"
                        v-model="form[key]"
                        class="wf-control"
                        :type="FIELD_BY_KEY[key].type"
                        :placeholder="`Enter ${FIELD_BY_KEY[key].label.toLowerCase()}…`"
                      />
                    </template>
                    <div v-else class="wf-display-box">
                      <p class="wf-val" :class="{ empty: !form[key] }">
                        {{ form[key] || '—' }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- RIGHT: Decision / Resubmission & History -->
        <div class="ir-col">
          <!-- Chief Decision Panel -->
          <section v-if="isReviewMode" class="ir-card ir-act ir-act-chief">
            <div class="ir-panel-header">
              <span class="ir-panel-badge">Reviewer Action</span>
              <h3>Your decision</h3>
              <p class="ir-hint">Evaluate the entry and provide instructions if sending back.</p>
            </div>

            <label class="ir-field" for="reason">
              <span class="ir-field-label">
                Decision reason <mark class="ir-req">(required)</mark>
              </span>
              <textarea
                id="reason"
                v-model="reason"
                rows="3"
                maxlength="2000"
                placeholder="Share your review comments or justification for the Keeper…"
              ></textarea>
            </label>

            <label class="ir-field" for="cnote">
              <span class="ir-field-label">Correction note <small>(optional)</small></span>
              <textarea
                id="cnote"
                v-model="correctionNote"
                rows="2"
                maxlength="2000"
                placeholder="Specific guidance on what to adjust. Never modifies catalogue records directly."
              ></textarea>
            </label>

            <div class="ir-review-status-bar">
              <span class="ir-status-indicator" :class="{ 'has-marks': markedCount > 0 }"></span>
              <p class="ir-status-msg">
                {{ markedCount
                  ? `${markedCount} ${markedCount === 1 ? 'field' : 'fields'} flagged for revision.`
                  : 'Check any field on the left if revisions are required.' }}
              </p>
            </div>

            <div class="dk-actions">
              <button
                type="button"
                class="dk-btn dk-btn-main"
                :disabled="busy"
                @click="approve"
              >
                <span>{{ busy ? 'Saving…' : 'Approve Work' }}</span>
              </button>
              <button
                type="button"
                class="dk-btn dk-btn-danger"
                :disabled="busy || !markedCount"
                @click="sendBack"
              >
                <span>{{ busy ? 'Saving…' : 'Send back for correction' }}</span>
              </button>
            </div>
          </section>

          <!-- Keeper Resubmission Panel -->
          <section v-if="canCorrect" class="ir-card ir-act ir-act-keeper">
            <div class="ir-panel-header">
              <span class="ir-panel-badge ir-badge-amber">Editor Action</span>
              <h3>Your resubmission</h3>
              <p class="ir-hint">Submit the corrected entry for final appraisal.</p>
            </div>

            <label class="ir-field" for="knote">
              <span class="ir-field-label">Note to The Chief <small>(optional)</small></span>
              <textarea
                id="knote"
                v-model="keeperNote"
                rows="3"
                maxlength="2000"
                placeholder="Explain the adjustments made, or why a value was preserved…"
              ></textarea>
            </label>

            <div class="ir-safe-notice">
              <span class="ir-safe-icon">🔒</span>
              <span>All editor notes are permanently logged in the audit record.</span>
            </div>

            <div class="dk-actions">
              <button
                type="button"
                class="dk-btn dk-btn-main"
                :disabled="busy"
                @click="resubmit"
              >
                <span>{{ busy ? 'Resubmitting…' : 'Resubmit for review' }}</span>
              </button>
            </div>
          </section>

          <!-- Audit Timeline & History -->
          <section class="ir-card ir-history-card">
            <button
              type="button"
              class="ir-toggle"
              :aria-expanded="historyOpen"
              @click="historyOpen = !historyOpen"
            >
              <div class="ir-toggle-left">
                <span class="ir-toggle-icon">📜</span>
                <span class="ir-toggle-title">Record History</span>
                <span class="ir-toggle-count">{{ events.length }}</span>
              </div>
              <span class="ir-toggle-btn-label">{{ historyOpen ? 'Collapse' : 'Expand' }}</span>
            </button>

            <div v-if="historyOpen" class="ir-history-body">
              <div v-if="!events.length" class="ir-empty-history">
                <span>No recorded actions on this work yet.</span>
              </div>

              <ol v-else class="ir-tl">
                <li
                  v-for="event in events"
                  :key="event.id"
                  class="ir-tl-item"
                  :class="event.type.toLowerCase()"
                >
                  <div class="ir-tl-marker">
                    <span class="ir-tl-dot"></span>
                    <span class="ir-tl-stem"></span>
                  </div>

                  <div class="ir-tl-card">
                    <div class="ir-tl-head">
                      <div class="ir-tl-primary">
                        <strong class="ir-tl-title">{{ eventTitle(event) }}</strong>
                        <span v-if="event.actor" class="ir-tl-actor">by {{ event.actor }}</span>
                      </div>
                      <time class="ir-tl-time">{{ fmtWhen(event.at) }}</time>
                    </div>

                    <p v-if="event.reason" class="ir-tl-reason">{{ event.reason }}</p>

                    <div
                      v-if="event.flagged_fields && event.flagged_fields.length"
                      class="ir-tl-chips"
                    >
                      <span class="ir-tl-chips-caption">Flagged:</span>
                      <span
                        v-for="f in event.flagged_fields"
                        :key="f"
                        class="ir-chip ir-chip-subtle"
                      >
                        {{ fieldLabel(f) }}
                      </span>
                    </div>

                    <div v-if="event.correction_note" class="ir-tl-note">
                      <strong class="ir-tl-note-tag">Correction Note:</strong>
                      <span>{{ event.correction_note }}</span>
                    </div>

                    <!-- Visual Field Diff -->
                    <div v-if="diffRows(event.changes).length" class="dk-diff-container">
                      <span class="dk-diff-caption">Updated Values</span>
                      <ul class="dk-diff">
                        <li v-for="row in diffRows(event.changes)" :key="row.field">
                          <span class="dk-diff-l">{{ row.label }}</span>
                          <div class="dk-diff-vals">
                            <del class="dk-diff-old">{{ showValue(row.from) }}</del>
                            <span class="dk-diff-arrow">→</span>
                            <ins class="dk-diff-new">{{ showValue(row.to) }}</ins>
                          </div>
                        </li>
                      </ul>
                    </div>
                  </div>
                </li>
              </ol>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const { userRole } = storeToRefs(useAuthStore())

const workId = computed(() => Number(route.params.id))
const isChief = computed(() => userRole.value === 'The Chief')

const FIELDS = [
  { key: 'title', label: 'Title', type: 'text', wide: true },
  { key: 'author', label: 'Author', type: 'text' },
  { key: 'category', label: 'Category', type: 'text' },
  { key: 'language', label: 'Language', type: 'text' },
  { key: 'publisher', label: 'Publisher', type: 'text' },
  { key: 'year', label: 'Year', type: 'number' },
  { key: 'isbn', label: 'ISBN', type: 'text' },
  { key: 'ddc', label: 'DDC', type: 'text' },
  { key: 'call_no', label: 'Call no.', type: 'text' },
  { key: 'translation_compilation', label: 'Translation / compilation', type: 'text' },
  { key: 'genre', label: 'Genre', type: 'text' },
  { key: 'original_language', label: 'Original language', type: 'text' },
  { key: 'notes', label: 'Notes', type: 'textarea', wide: true },
  { key: 'proposal_reason', label: 'Why this was proposed', type: 'textarea', wide: true }
]
const FIELD_LABELS = Object.fromEntries(FIELDS.map((f) => [f.key, f.label]))
const FIELD_BY_KEY = Object.fromEntries(FIELDS.map((f) => [f.key, f]))

const GROUPS = [
  { title: 'Identification', keys: ['title', 'author', 'publisher', 'year', 'isbn'] },
  {
    title: 'Classification',
    keys: ['category', 'genre', 'language', 'original_language', 'translation_compilation', 'ddc', 'call_no']
  },
  { title: 'Notes', keys: ['notes', 'proposal_reason'] }
]

const loading = ref(true)
const busy = ref(false)
const error = ref('')
const data = ref(null)
const events = ref([])
const historyOpen = ref(typeof window !== 'undefined' && window.innerWidth >= 980)

const emptyForm = () => Object.fromEntries(FIELDS.map((f) => [f.key, '']))
const form = ref(emptyForm())
const ticks = ref(Object.fromEntries(FIELDS.map((f) => [f.key, false])))
const reason = ref('')
const correctionNote = ref('')
const keeperNote = ref('')

function fieldLabel(key) {
  return FIELD_LABELS[key] || key
}

// ---- Mode Assessment ----
const isReviewMode = computed(() => isChief.value && data.value?.status === 'PENDING')
const canCorrect = computed(
  () => !isChief.value && (data.value?.editable_fields || []).length > 0
)

const subtitle = computed(() => {
  if (isReviewMode.value) return 'Read the complete record, mark any discrepancies, and submit your final verdict.'
  if (canCorrect.value) return 'Revise the highlighted fields and return the updated work for Chief evaluation.'
  return 'A permanent, read-only record of this catalogue entry and its editorial timeline.'
})

const statusLabel = computed(() => {
  const s = data.value?.status
  if (s === 'PENDING') return 'Under Review'
  if (s === 'REJECTED') return 'Returned for Fixes'
  if (s === 'APPROVED') return 'Approved & Catalogued'
  return s || ''
})

const statusClass = computed(() => {
  const s = data.value?.status
  return s === 'REJECTED' ? 'bad' : s === 'PENDING' ? 'wait' : 'ok'
})

const editableSet = computed(() => new Set(data.value?.editable_fields || []))
const markedSet = computed(() =>
  data.value?.correction ? new Set(data.value.correction.fields) : new Set()
)

function isEditable(key) {
  return editableSet.value.has(key)
}

function isMarked(key) {
  if (isReviewMode.value) return !!ticks.value[key]
  return markedSet.value.has(key)
}

function fieldClass(key) {
  return {
    'is-marked': isMarked(key),
    'is-open': !isReviewMode.value && isEditable(key)
  }
}

const markedCount = computed(() => Object.values(ticks.value).filter(Boolean).length)

// ---- Data Operations ----
async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get(`/catalogue/review/work/${workId.value}`)
    data.value = res.data
    const filled = emptyForm()
    for (const f of FIELDS) {
      const v = res.data.values?.[f.key]
      filled[f.key] = v === null || v === undefined ? '' : String(v)
    }
    form.value = filled
    ticks.value = Object.fromEntries(FIELDS.map((f) => [f.key, false]))
    await loadHistory()
  } catch (err) {
    data.value = null
    error.value = err.response?.data?.detail || 'Unable to open this work.'
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    const res = await axios.get(`/catalogue/history/work/${workId.value}`)
    events.value = Array.isArray(res.data) ? res.data : []
  } catch {
    events.value = []
  }
}

// ---- Chief Actions ----
async function approve() {
  const text = reason.value.trim()
  if (!text) {
    error.value = 'A reason is required before approving.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/approve/${workId.value}`, null, {
      params: { action: 'APPROVE', reason: text }
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to approve this record.'
  } finally {
    busy.value = false
  }
}

async function sendBack() {
  const text = reason.value.trim()
  const fields = Object.keys(ticks.value).filter((key) => ticks.value[key])
  if (!fields.length) {
    error.value = 'Please flag at least one field requiring correction.'
    return
  }
  if (!text) {
    error.value = 'A review explanation is required.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/review/work/${workId.value}/request-correction`, {
      fields,
      reason: text,
      correction_note: correctionNote.value.trim() || null
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to return this record.'
  } finally {
    busy.value = false
  }
}

// ---- Keeper Action ----
async function resubmit() {
  const changes = {}
  for (const key of data.value.editable_fields) {
    changes[key] = form.value[key]
  }
  if ('title' in changes && !String(changes.title).trim()) {
    error.value = 'Title cannot be left empty.'
    return
  }
  if ('language' in changes && !String(changes.language).trim()) {
    error.value = 'Language cannot be left empty.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/review/work/${workId.value}/resubmit-corrected`, {
      changes,
      note: keeperNote.value.trim() || null
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to resubmit this work.'
  } finally {
    busy.value = false
  }
}

function goBack() {
  router.push('/docket')
}

// ---- Audit Helpers ----
const EVENT_TITLES = {
  SUBMITTED: 'Record Submitted',
  APPROVED: 'Approved & Archiving',
  REJECTED: 'Returned for Revision',
  RESUBMITTED: 'Resubmitted for Review',
  NOTE: 'Desk Note'
}

function eventTitle(event) {
  if (event.type === 'NOTE') {
    return event.note_kind === 'KEEPER_NOTE' ? 'Note from Keeper' : 'Note from Chief'
  }
  return EVENT_TITLES[event.type] || event.type
}

function diffRows(changes) {
  if (!changes || typeof changes !== 'object') return []
  return Object.entries(changes).map(([field, value]) => ({
    field,
    label: fieldLabel(field),
    from: value?.from,
    to: value?.to
  }))
}

function showValue(value) {
  return value === null || value === undefined || value === '' ? '(empty)' : String(value)
}

function fmtWhen(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

onMounted(load)
</script>

<style scoped>
/* ==========================================================================
   Design Tokens & Modern Archival Palette
   ========================================================================== */
.dk {
  --ink: #192231;
  --ink-secondary: #4a5568;
  --mu: #6b778c;
  --ln: #e2e8f0;
  --ln-soft: #edf2f7;
  --bg: #f7f9fb;
  --card-bg: #ffffff;
  --surface-raised: #fbfcfd;

  /* Accent: Deep Library Spruce */
  --ac: #17544a;
  --ac-hover: #11423a;
  --acs: #edf7f5;
  --ac-border: #bfe3dc;

  /* Attention / Danger: Tuscan Terra Cotta */
  --at: #c0452d;
  --at-hover: #a33822;
  --ats: #fdf3f0;
  --at-border: #f7c9be;

  /* Waiting / Amber: Antique Ochre */
  --pg: #a37213;
  --pgs: #fef9ed;
  --pg-border: #f5deb2;

  /* Approved / Success: Botanical Sage */
  --dn: #26734d;
  --dns: #edf7f2;
  --dn-border: #bce3cf;

  /* Elevation Shadows */
  --sh-sm: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03);
  --sh-md: 0 4px 12px -2px rgba(15, 23, 42, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.04);
  --sh-lg: 0 10px 24px -4px rgba(15, 23, 42, 0.08), 0 4px 10px -2px rgba(15, 23, 42, 0.04);

  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 24px 48px;
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  font-size: 14px;
  line-height: 1.5;
  box-sizing: border-box;
  background-color: var(--bg);
  min-height: 100vh;
}

@media (prefers-color-scheme: dark) {
  .dk {
    --ink: #e8ecf2;
    --ink-secondary: #a9b5c7;
    --mu: #8692a6;
    --ln: #2b3548;
    --ln-soft: #202838;
    --bg: #0f141d;
    --card-bg: #18202d;
    --surface-raised: #1d2737;

    --ac: #65b8ad;
    --ac-hover: #7ec7be;
    --acs: #132727;
    --ac-border: #1f4341;

    --at: #ec826f;
    --at-hover: #f19888;
    --ats: #2d1816;
    --at-border: #4d2621;

    --pg: #e3b555;
    --pgs: #2d2412;
    --pg-border: #4a3a1b;

    --dn: #6bc99c;
    --dns: #12281e;
    --dn-border: #1c4532;

    --sh-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
    --sh-md: 0 4px 12px rgba(0, 0, 0, 0.35);
    --sh-lg: 0 10px 24px rgba(0, 0, 0, 0.45);
  }
}

/* ==========================================================================
   Header & Navigation
   ========================================================================== */
.dk-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--ln);
}

.dk-org {
  margin: 0 0 4px;
  color: var(--ac);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.dk h1 {
  font: 700 28px/1.15 "Charter", "Georgia", serif;
  margin: 0 0 6px;
  letter-spacing: -0.01em;
  color: var(--ink);
}

.dk-sub {
  margin: 0;
  color: var(--mu);
  font-size: 14px;
  max-width: 65ch;
  line-height: 1.5;
}

/* ==========================================================================
   Buttons & Inputs
   ========================================================================== */
.dk-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 18px;
  border: 1px solid var(--ln);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--ink);
  font: inherit;
  font-weight: 600;
  font-size: 13.5px;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  box-shadow: var(--sh-sm);
}

.dk-btn:hover:not(:disabled) {
  border-color: var(--mu);
  transform: translateY(-1px);
  box-shadow: var(--sh-md);
}

.dk-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.dk-btn-ghost {
  border-color: var(--ln);
  background: var(--card-bg);
}

.dk-btn-main {
  background: var(--ac);
  border-color: var(--ac);
  color: #ffffff;
}

.dk-btn-main:hover:not(:disabled) {
  background: var(--ac-hover);
  border-color: var(--ac-hover);
}

.dk-btn-danger {
  background: var(--ats);
  color: var(--at);
  border-color: var(--at-border);
}

.dk-btn-danger:hover:not(:disabled) {
  background: var(--at);
  color: #ffffff;
  border-color: var(--at);
}

.dk-btn-icon {
  font-size: 15px;
  line-height: 1;
}

.dk-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
}

.dk button:focus-visible,
.dk input:focus-visible,
.dk textarea:focus-visible {
  outline: 2px solid var(--ac);
  outline-offset: 2px;
}

/* ==========================================================================
   Alerts & Notifications
   ========================================================================== */
.dk-msg {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  border-radius: 10px;
  margin-bottom: 18px;
  border: 1px solid transparent;
  box-shadow: var(--sh-sm);
  animation: slideDown 0.25s ease-out;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.dk-msg-content {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 500;
}

.dk-msg-symbol {
  font-size: 16px;
}

.dk-msg-close {
  border: 0;
  background: none;
  color: inherit;
  font-size: 20px;
  cursor: pointer;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 4px;
  opacity: 0.7;
}

.dk-msg-close:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.05);
}

.dk-msg-error {
  background: var(--ats);
  border-color: var(--at-border);
  color: var(--at);
}

/* ==========================================================================
   Loading & Empty States
   ========================================================================== */
.dk-empty {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 64px 24px;
  background: var(--card-bg);
  border: 1px dashed var(--ln);
  border-radius: 12px;
  text-align: center;
  color: var(--mu);
}

.dk-empty strong {
  color: var(--ink);
  font-size: 17px;
  font-weight: 600;
}

.dk-empty-error {
  border-color: var(--at-border);
  background: var(--ats);
}

.dk-empty-icon {
  font-size: 32px;
  margin-bottom: 4px;
}

.dk-spin {
  width: 26px;
  height: 26px;
  border: 3px solid var(--ln);
  border-top-color: var(--ac);
  border-radius: 50%;
  animation: dk-spin 0.75s linear infinite;
  margin-bottom: 6px;
}

@keyframes dk-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .dk-spin { animation: none; }
}

/* ==========================================================================
   Top Summary Banner
   ========================================================================== */
.ir-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 18px 24px;
  margin-bottom: 18px;
  border: 1px solid var(--ln);
  border-radius: 12px;
  background: var(--card-bg);
  box-shadow: var(--sh-sm);
}

.ir-strip h2 {
  font: 700 22px/1.25 "Charter", "Georgia", serif;
  margin: 0 0 6px;
  color: var(--ink);
}

.ir-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 18px;
  color: var(--ink-secondary);
  font-size: 13.5px;
}

.ir-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ir-meta-label {
  color: var(--mu);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ir-meta-copies {
  background: var(--surface-raised);
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--ln);
  font-size: 12.5px;
}

.ir-badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ac);
  display: inline-block;
}

.ir-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
}

.ir-pill-bullet {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.ir-pill.bad {
  background: var(--ats);
  color: var(--at);
  border-color: var(--at-border);
}

.ir-pill.bad .ir-pill-bullet {
  background: var(--at);
}

.ir-pill.wait {
  background: var(--pgs);
  color: var(--pg);
  border-color: var(--pg-border);
}

.ir-pill.wait .ir-pill-bullet {
  background: var(--pg);
}

.ir-pill.ok {
  background: var(--dns);
  color: var(--dn);
  border-color: var(--dn-border);
}

.ir-pill.ok .ir-pill-bullet {
  background: var(--dn);
}

/* ==========================================================================
   Two-Column Grid Layout
   ========================================================================== */
.ir-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: start;
}

.ir-col {
  display: grid;
  gap: 18px;
  min-width: 0;
}

@media (min-width: 980px) {
  .ir-grid {
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.95fr);
    gap: 22px;
  }
  .ir-act {
    position: sticky;
    top: 20px;
  }
}

/* ==========================================================================
   General Cards
   ========================================================================== */
.ir-card {
  border: 1px solid var(--ln);
  border-radius: 12px;
  background: var(--card-bg);
  padding: 20px 22px;
  box-shadow: var(--sh-sm);
}

.ir-card h3 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.ir-hint {
  margin: 0 0 10px;
  color: var(--mu);
  font-size: 13px;
  line-height: 1.45;
}

/* ==========================================================================
   Rejection Card Styles
   ========================================================================== */
.ir-alert {
  border-color: var(--at-border);
  background: linear-gradient(180deg, var(--ats) 0%, var(--card-bg) 100%);
}

.ir-alert-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.ir-alert-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--at);
  color: #fff;
  border-radius: 50%;
  font-size: 16px;
  font-weight: bold;
  flex-shrink: 0;
  margin-top: 1px;
}

.ir-alert-text {
  margin: 2px 0 8px;
  font-size: 14px;
  color: var(--ink);
  line-height: 1.45;
}

.ir-alert-note {
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 6px;
}

.ir-correction-callout {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--at-border);
}

.ir-correction-title {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: var(--at);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.ir-correction-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* ==========================================================================
   Groupings & Fields
   ========================================================================== */
.wg-list {
  display: grid;
  gap: 22px;
  margin-top: 14px;
}

.wg-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.wg-title {
  margin: 0;
  color: var(--ac);
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.wg-line {
  flex: 1;
  height: 1px;
  background: var(--ln);
}

.wg-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px 16px;
}

.wf {
  display: grid;
  gap: 6px;
  align-content: start;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-raised);
  border: 1px solid var(--ln-soft);
  transition: all 0.15s ease;
}

.wf-wide {
  grid-column: 1 / -1;
}

.wf-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  min-height: 22px;
}

.wf-label {
  color: var(--ink-secondary);
  font-size: 12.5px;
  font-weight: 600;
}

.wf-display-box {
  padding: 4px 0;
}

.wf-val {
  margin: 0;
  color: var(--ink);
  font-weight: 500;
  font-size: 13.5px;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  line-height: 1.45;
}

.wf-val.empty {
  color: var(--mu);
  font-weight: 400;
  font-style: italic;
}

.wf-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--ln);
  border-radius: 7px;
  background: var(--card-bg);
  color: var(--ink);
  font: inherit;
  font-size: 13.5px;
  box-sizing: border-box;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.wf-control:focus {
  border-color: var(--ac);
  box-shadow: 0 0 0 3px var(--acs);
  outline: none;
}

textarea.wf-control {
  resize: vertical;
  min-height: 64px;
  max-height: 180px;
  line-height: 1.45;
}

/* Field Highlight States */
.wf.is-open {
  background: var(--acs);
  border-color: var(--ac-border);
  box-shadow: 0 0 0 1px var(--ac);
}

.wf.is-marked {
  background: var(--ats);
  border-color: var(--at-border);
  box-shadow: 0 0 0 1px var(--at);
}

/* "Needs Fix" Toggle Control */
.wf-fix {
  position: relative;
  cursor: pointer;
  user-select: none;
}

.wf-fix input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.wf-fix-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border: 1px solid var(--ln);
  border-radius: 999px;
  color: var(--mu);
  background: var(--card-bg);
  font-size: 11.5px;
  font-weight: 600;
  transition: all 0.15s ease;
}

.wf-fix-check {
  display: none;
  font-size: 10px;
}

.wf-fix:hover .wf-fix-badge {
  border-color: var(--at);
  color: var(--at);
}

.wf-fix input:checked + .wf-fix-badge {
  background: var(--at);
  border-color: var(--at);
  color: #ffffff;
}

.wf-fix input:checked + .wf-fix-badge .wf-fix-check {
  display: inline;
}

.wf-fix input:focus-visible + .wf-fix-badge {
  outline: 2px solid var(--ac);
  outline-offset: 2px;
}

.ir-flag {
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--ats);
  border: 1px solid var(--at-border);
  color: var(--at);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

/* ==========================================================================
   Right Panel Decision Cards
   ========================================================================== */
.ir-act-chief {
  border-top: 4px solid var(--ac);
}

.ir-act-keeper {
  border-top: 4px solid var(--pg);
}

.ir-panel-header {
  margin-bottom: 14px;
}

.ir-panel-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--acs);
  color: var(--ac);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.ir-badge-amber {
  background: var(--pgs);
  color: var(--pg);
}

.ir-field {
  display: grid;
  gap: 5px;
  margin-bottom: 12px;
}

.ir-field-label {
  color: var(--ink-secondary);
  font-size: 12.5px;
  font-weight: 600;
}

.ir-req {
  background: none;
  color: var(--at);
  font-size: 11.5px;
  font-weight: 600;
}

.ir-field textarea {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--ln);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--ink);
  font: inherit;
  font-size: 13.5px;
  resize: vertical;
  min-height: 60px;
  max-height: 160px;
  box-sizing: border-box;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.ir-field textarea:focus {
  border-color: var(--ac);
  box-shadow: 0 0 0 3px var(--acs);
  outline: none;
}

.ir-review-status-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--ln);
  border-radius: 8px;
  margin-top: 4px;
}

.ir-status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--mu);
  flex-shrink: 0;
}

.ir-status-indicator.has-marks {
  background: var(--at);
  box-shadow: 0 0 0 3px var(--ats);
}

.ir-status-msg {
  margin: 0;
  font-size: 12.5px;
  color: var(--ink-secondary);
  font-weight: 500;
}

.ir-safe-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--surface-raised);
  border-radius: 6px;
  color: var(--mu);
  font-size: 12px;
  margin-top: 8px;
}

.ir-safe-icon {
  font-size: 14px;
}

/* ==========================================================================
   History & Timeline
   ========================================================================== */
.ir-history-card {
  padding: 16px 20px;
}

.ir-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 4px 0;
  border: 0;
  background: none;
  color: var(--ink);
  font: inherit;
  cursor: pointer;
}

.ir-toggle-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ir-toggle-icon {
  font-size: 16px;
}

.ir-toggle-title {
  font-size: 15px;
  font-weight: 700;
}

.ir-toggle-count {
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--surface-raised);
  border: 1px solid var(--ln);
  color: var(--mu);
  font-size: 11px;
  font-weight: 700;
}

.ir-toggle-btn-label {
  color: var(--ac);
  font-size: 13px;
  font-weight: 600;
}

.ir-history-body {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--ln);
}

.ir-empty-history {
  padding: 24px 0;
  text-align: center;
  color: var(--mu);
  font-size: 13px;
}

.ir-tl {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 16px;
  max-height: 480px;
  overflow-y: auto;
  padding-right: 4px;
}

.ir-tl-item {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 12px;
}

.ir-tl-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ir-tl-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--ac);
  box-shadow: 0 0 0 3px var(--acs);
  margin-top: 4px;
}

.ir-tl-stem {
  flex: 1;
  width: 2px;
  background: var(--ln);
  margin-top: 6px;
}

.ir-tl-item:last-child .ir-tl-stem {
  display: none;
}

.ir-tl-item.rejected .ir-tl-dot {
  background: var(--at);
  box-shadow: 0 0 0 3px var(--ats);
}

.ir-tl-item.resubmitted .ir-tl-dot {
  background: var(--pg);
  box-shadow: 0 0 0 3px var(--pgs);
}

.ir-tl-item.note .ir-tl-dot {
  background: var(--mu);
  box-shadow: 0 0 0 3px var(--surface-raised);
}

.ir-tl-card {
  padding: 12px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--ln);
  border-radius: 9px;
  display: grid;
  gap: 6px;
}

.ir-tl-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.ir-tl-primary {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.ir-tl-title {
  color: var(--ink);
  font-size: 13.5px;
  font-weight: 700;
}

.ir-tl-actor {
  color: var(--mu);
  font-size: 12.5px;
}

.ir-tl-time {
  color: var(--mu);
  font-size: 11.5px;
  white-space: nowrap;
}

.ir-tl-reason {
  margin: 2px 0 0;
  padding: 8px 12px;
  border-left: 3px solid var(--ac);
  background: var(--card-bg);
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--ink);
}

.ir-tl-item.rejected .ir-tl-reason {
  border-left-color: var(--at);
  background: var(--ats);
}

.ir-tl-note {
  margin: 2px 0 0;
  padding: 8px 12px;
  border-left: 3px solid var(--pg);
  background: var(--pgs);
  border-radius: 0 6px 6px 0;
  font-size: 12.5px;
}

.ir-tl-note-tag {
  display: block;
  font-size: 11px;
  color: var(--pg);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}

.ir-tl-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.ir-tl-chips-caption {
  font-size: 12px;
  color: var(--mu);
  font-weight: 500;
}

.ir-chip {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
}

.ir-chip-alert {
  background: var(--ats);
  color: var(--at);
  border: 1px solid var(--at-border);
}

.ir-chip-subtle {
  background: var(--card-bg);
  border: 1px solid var(--ln);
  color: var(--ink-secondary);
}

/* ==========================================================================
   Visual Diffs
   ========================================================================== */
.dk-diff-container {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--ln);
}

.dk-diff-caption {
  display: block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--mu);
  margin-bottom: 6px;
}

.dk-diff {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.dk-diff li {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 10px;
  align-items: center;
  font-size: 12.5px;
}

.dk-diff-l {
  color: var(--mu);
  font-weight: 500;
}

.dk-diff-vals {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dk-diff-arrow {
  color: var(--mu);
  font-size: 12px;
}

.dk-diff del {
  background: var(--ats);
  color: var(--at);
  border: 1px solid var(--at-border);
  padding: 1px 7px;
  border-radius: 4px;
  text-decoration: line-through;
  overflow-wrap: anywhere;
}

.dk-diff ins {
  background: var(--dns);
  color: var(--dn);
  border: 1px solid var(--dn-border);
  padding: 1px 7px;
  border-radius: 4px;
  text-decoration: none;
  overflow-wrap: anywhere;
  font-weight: 600;
}

/* ==========================================================================
   Responsive Adaptations
   ========================================================================== */
@media (max-width: 640px) {
  .dk {
    padding: 16px 14px 32px;
  }
  .dk-head {
    flex-direction: column;
    align-items: flex-start;
  }
  .ir-strip {
    flex-direction: column;
    align-items: flex-start;
  }
  .dk-diff li {
    grid-template-columns: 1fr;
    gap: 3px;
  }
  .ir-meta {
    gap: 6px 12px;
  }
}
</style>
