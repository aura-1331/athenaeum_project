<template>
  <div class="dk">
    <header class="dk-head">
      <div>
        <p class="dk-org">Athenaeum Orbis</p>
        <h1>Item #{{ itemId }}</h1>
        <p class="dk-sub">{{ subtitle }}</p>
      </div>
      <button type="button" class="dk-btn" @click="goBack">? Docket</button>
    </header>

    <div v-if="error" class="dk-msg dk-msg-error" role="alert">
      <span>{{ error }}</span>
      <button type="button" aria-label="Dismiss" @click="error = ''">?</button>
    </div>
    <div v-if="notice" class="dk-msg dk-msg-ok" role="status">
      <span>{{ notice }}</span>
      <button type="button" aria-label="Dismiss" @click="notice = ''">?</button>
    </div>

    <div v-if="loading" class="dk-empty">
      <div class="dk-spin"></div>
      <strong>Loading item?</strong>
    </div>

    <div v-else-if="!data" class="dk-empty">
      <strong>This item could not be opened</strong>
      <span>It may not exist, or it may belong to someone else.</span>
    </div>

    <template v-else>
      <!-- One slim strip: which book, and where it stands -->
      <section class="ir-strip">
        <div class="ir-strip-main">
          <h2>{{ data.work.title || 'Untitled' }}</h2>
          <p class="ir-meta">
            <span v-if="data.work.author">By {{ data.work.author }}</span>
            <span v-if="data.work.language">{{ data.work.language }}</span>
            <span v-if="data.work.category">{{ data.work.category }}</span>
          </p>
        </div>
        <span class="ir-pill" :class="statusClass">{{ statusLabel }}</span>
      </section>

      <div class="ir-grid">
        <!-- LEFT: the item itself -->
        <div class="ir-col">
          <section v-if="data.status === 'REJECTED'" class="ir-card ir-alert">
            <h3>Sent back by The Chief</h3>
            <p v-if="data.rejection_reason">{{ data.rejection_reason }}</p>
            <p v-if="data.legacy_rejection" class="ir-hint">
              Sent back before field marking existed, so every fixable field is open.
            </p>
            <p v-else-if="data.correction" class="ir-hint">
              Fix: <strong>{{ data.correction.fields.map(fieldLabel).join(', ') }}</strong>
            </p>
          </section>

          <section class="ir-card">
            <h3>Item details</h3>
            <p v-if="isReviewMode" class="ir-hint">
              Tick <strong>Needs correction</strong> on any field the Keeper must fix.
              Only ticked fields will be open for editing.
            </p>
            <p v-else-if="canCorrect" class="ir-hint">
              Only the highlighted fields can be changed. The rest are locked.
            </p>

            <div class="ir-fields">
              <div class="ir-row" :class="rowClass('work_id')">
                <div class="ir-label">
                  <label for="f-work">{{ fieldLabel('work_id') }}</label>
                  <label v-if="isReviewMode" class="ir-tick">
                    <input v-model="ticks.work_id" type="checkbox" /> Needs correction
                  </label>
                  <span v-else-if="isMarked('work_id')" class="ir-flag">Needs correction</span>
                </div>
                <input
                  id="f-work"
                  v-model="form.work_id"
                  type="number"
                  min="1"
                  :disabled="!isEditable('work_id')"
                />
                <p v-if="isEditable('work_id') && newWork" class="ir-sub">
                  {{ newWork.error || `${newWork.title} ? ${newWork.author || 'Unknown'} (${newWork.language})` }}
                </p>
              </div>

              <div class="ir-row" :class="rowClass('language_id')">
                <div class="ir-label">
                  <label for="f-lang">{{ fieldLabel('language_id') }}</label>
                  <label v-if="isReviewMode" class="ir-tick">
                    <input v-model="ticks.language_id" type="checkbox" /> Needs correction
                  </label>
                  <span v-else-if="isMarked('language_id')" class="ir-flag">Needs correction</span>
                </div>
                <select id="f-lang" v-model="form.language_id" :disabled="!isEditable('language_id')">
                  <option v-for="opt in languageOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>

            <dl class="ir-facts">
              <div><dt>Accession no.</dt><dd>{{ data.accession_no || '?' }}</dd></div>
              <div><dt>Call no.</dt><dd>{{ data.call_no || '?' }}</dd></div>
              <div><dt>Proposed by</dt><dd>{{ data.proposer_name || '?' }}</dd></div>
            </dl>
            <p class="ir-sub">Accession and call numbers are set by the system and update by themselves if the Work changes.</p>
          </section>
        </div>

        <!-- RIGHT: decision / resubmission, then history -->
        <div class="ir-col">
          <section v-if="isReviewMode" class="ir-card ir-act">
            <h3>Your decision</h3>
            <label class="ir-field" for="reason">
              <span>Reason (required, the Keeper will see it)</span>
              <textarea id="reason" v-model="reason" rows="2" maxlength="2000"></textarea>
            </label>
            <label class="ir-field" for="cnote">
              <span>Correction note (optional, used only when sending back)</span>
              <textarea
                id="cnote"
                v-model="correctionNote"
                rows="2"
                maxlength="2000"
                placeholder="Explain what to fix. Never changes the catalogue."
              ></textarea>
            </label>
            <p class="ir-hint">
              {{ markedCount
                ? `${markedCount} field(s) marked for correction.`
                : 'Tick a field on the left to send this back.' }}
            </p>
            <div class="dk-actions">
              <button type="button" class="dk-btn dk-btn-main" :disabled="busy" @click="approve">
                {{ busy ? 'Saving?' : 'Approve' }}
              </button>
              <button
                type="button"
                class="dk-btn dk-btn-danger"
                :disabled="busy || !markedCount"
                @click="sendBack"
              >
                {{ busy ? 'Saving?' : 'Send back for correction' }}
              </button>
            </div>
          </section>

          <section v-if="canCorrect" class="ir-card ir-act">
            <h3>Your resubmission</h3>
            <label class="ir-field" for="knote">
              <span>Note to The Chief (optional)</span>
              <textarea
                id="knote"
                v-model="keeperNote"
                rows="2"
                maxlength="2000"
                placeholder="What did you change, or why did nothing need changing?"
              ></textarea>
            </label>
            <p class="ir-hint">Notes are saved permanently and cannot be edited or deleted.</p>
            <div class="dk-actions">
              <button type="button" class="dk-btn dk-btn-main" :disabled="busy" @click="resubmit">
                {{ busy ? 'Resubmitting?' : 'Resubmit for review' }}
              </button>
            </div>
          </section>

          <section class="ir-card">
            <button type="button" class="ir-toggle" :aria-expanded="historyOpen" @click="historyOpen = !historyOpen">
              <span>History <small>({{ events.length }})</small></span>
              <span>{{ historyOpen ? 'Hide' : 'Show' }}</span>
            </button>
            <template v-if="historyOpen">
              <p v-if="!events.length" class="ir-hint">No history recorded yet.</p>
              <ol v-else class="ir-tl">
                <li v-for="event in events" :key="event.id" :class="event.type.toLowerCase()">
                  <i aria-hidden="true"></i>
                  <div>
                    <p class="ir-tl-head">
                      <strong>{{ eventTitle(event) }}</strong>
                      <span v-if="event.actor"> by {{ event.actor }}</span>
                      <time>{{ fmtWhen(event.at) }}</time>
                    </p>
                    <p v-if="event.reason" class="ir-tl-reason">{{ event.reason }}</p>
                    <p v-if="event.flagged_fields && event.flagged_fields.length" class="ir-tl-chips">
                      Marked:
                      <span v-for="f in event.flagged_fields" :key="f" class="ir-chip">{{ fieldLabel(f) }}</span>
                    </p>
                    <p v-if="event.correction_note" class="ir-tl-reason ir-tl-note">
                      Correction note: {{ event.correction_note }}
                    </p>
                    <ul v-if="diffRows(event.changes).length" class="dk-diff">
                      <li v-for="row in diffRows(event.changes)" :key="row.field">
                        <span class="dk-diff-l">{{ row.label }}</span>
                        <del>{{ showValue(row.from) }}</del>
                        <ins>{{ showValue(row.to) }}</ins>
                      </li>
                    </ul>
                  </div>
                </li>
              </ol>
            </template>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const { userRole } = storeToRefs(useAuthStore())

const itemId = computed(() => Number(route.params.id))
const isChief = computed(() => userRole.value === 'The Chief')

const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const data = ref(null)
const events = ref([])
const historyOpen = ref(typeof window !== 'undefined' && window.innerWidth >= 980)

const form = ref({ work_id: '', language_id: '' })
const ticks = ref({ work_id: false, language_id: false })
const reason = ref('')
const correctionNote = ref('')
const keeperNote = ref('')
const newWork = ref(null)

const languageOptions = [
  { value: 'ML', label: 'Malayalam (ML)' },
  { value: 'EN', label: 'English (EN)' },
  { value: 'MU', label: 'Multilingual (MU)' },
  { value: 'GE', label: 'German (GE)' }
]

const FIELD_LABELS = {
  work_id: 'Authorized Work ID',
  language_id: 'Copy language',
  accession_no: 'Accession no.',
  call_no: 'Call no.'
}

function fieldLabel(key) {
  return FIELD_LABELS[key] || key
}

// ---- What mode are we in? ----
const isReviewMode = computed(
  () => isChief.value && data.value?.status === 'PENDING'
)
const canCorrect = computed(
  () => !isChief.value && (data.value?.editable_fields || []).length > 0
)

const subtitle = computed(() => {
  if (isReviewMode.value) return 'Read the full record, mark anything that needs fixing, then decide.'
  if (canCorrect.value) return 'Fix the highlighted fields and send it back for review.'
  return 'A read-only view of this item and its history.'
})

const statusLabel = computed(() => {
  const s = data.value?.status
  if (s === 'PENDING') return 'Waiting for review'
  if (s === 'REJECTED') return 'Sent back'
  if (s === 'AVAILABLE') return 'On the shelf'
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
function rowClass(key) {
  return {
    'ir-marked': isMarked(key),
    'ir-open': !isReviewMode.value && isEditable(key),
    'ir-locked': !isReviewMode.value && !isEditable(key)
  }
}

const markedCount = computed(
  () => Object.values(ticks.value).filter(Boolean).length
)

// ---- Loading ----
async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get(`/catalogue/review/item/${itemId.value}`)
    data.value = res.data
    form.value = {
      work_id: String(res.data.work_id ?? ''),
      language_id: res.data.language_id || ''
    }
    ticks.value = { work_id: false, language_id: false }
    await loadHistory()
  } catch (err) {
    data.value = null
    error.value = err.response?.data?.detail || 'Unable to load this item.'
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    const res = await axios.get(`/catalogue/history/item/${itemId.value}`)
    events.value = Array.isArray(res.data) ? res.data : []
  } catch {
    events.value = []
  }
}

// Live preview of a different Work while the Keeper edits the Work ID.
watch(
  () => form.value.work_id,
  async (value) => {
    newWork.value = null
    if (!isEditable('work_id') || !value) return
    if (String(value) === String(data.value?.work_id)) return
    try {
      const res = await axios.get(`/catalogue/work/${value}`)
      newWork.value = res.data
    } catch {
      newWork.value = { error: 'No catalogued Work was found with that ID.' }
    }
  }
)

// ---- Chief actions ----
async function approve() {
  const text = reason.value.trim()
  if (!text) {
    error.value = 'A reason is required.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/approve-item/${itemId.value}`, null, {
      params: { action: 'APPROVE', reason: text }
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to approve this item.'
  } finally {
    busy.value = false
  }
}

async function sendBack() {
  const text = reason.value.trim()
  const fields = Object.keys(ticks.value).filter((key) => ticks.value[key])
  if (!fields.length) {
    error.value = 'Tick at least one field that needs correction.'
    return
  }
  if (!text) {
    error.value = 'A reason is required.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/review/item/${itemId.value}/request-correction`, {
      fields,
      reason: text,
      correction_note: correctionNote.value.trim() || null
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to send this item back.'
  } finally {
    busy.value = false
  }
}

// ---- Keeper action ----
async function resubmit() {
  const changes = {}
  for (const key of data.value.editable_fields) {
    changes[key] = form.value[key]
  }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/review/item/${itemId.value}/resubmit-corrected`, {
      changes,
      note: keeperNote.value.trim() || null
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to resubmit this item.'
  } finally {
    busy.value = false
  }
}

function goBack() {
  router.push('/docket')
}

// ---- History helpers ----
const EVENT_TITLES = {
  SUBMITTED: 'Submitted',
  APPROVED: 'Approved',
  REJECTED: 'Sent back',
  RESUBMITTED: 'Resubmitted',
  NOTE: 'Note'
}

function eventTitle(event) {
  if (event.type === 'NOTE') {
    return event.note_kind === 'KEEPER_NOTE' ? 'Note from the Keeper' : 'Note from the Chief'
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
.dk{--ink:#1c2430;--mu:#667085;--ln:#dfe3ea;--bg:#f4f6f8;--sf:#fff;--ac:#1f5f5b;--acs:#e3f0ee;--at:#b4432f;--ats:#fbeae6;--pg:#9a6a00;--pgs:#fbf1d9;--dn:#2d7a52;--dns:#e4f3ea;
width:100%;max-width:1180px;margin:0 auto;padding:20px 20px 36px;color:var(--ink);font-size:14px;line-height:1.45;box-sizing:border-box}
@media (prefers-color-scheme:dark){.dk{--ink:#e6e9ef;--mu:#9aa4b5;--ln:#2d3547;--bg:#131822;--sf:#1a2130;--ac:#7cc4bd;--acs:#1d3535;--at:#f0937f;--ats:#3a2420;--pg:#e5b94f;--pgs:#38301a;--dn:#78c79c;--dns:#1b3326}}
.dk h1{font:600 26px/1.1 Georgia,"Times New Roman",serif;margin:2px 0 4px}
.dk-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px}
.dk-org{margin:0;color:var(--ac);font-weight:600;font-size:12px}
.dk-sub{margin:0;color:var(--mu);max-width:60ch}
.dk-btn{min-height:36px;padding:0 14px;border:1px solid var(--ln);border-radius:8px;background:var(--sf);color:var(--ink);font:inherit;font-weight:500;cursor:pointer}
.dk-btn:hover:not(:disabled){border-color:var(--mu)}
.dk-btn:disabled{opacity:.55;cursor:not-allowed}
.dk-btn-main{background:var(--ac);border-color:var(--ac);color:var(--sf)}
.dk-btn-danger{color:var(--at);border-color:var(--at)}
.dk button:focus-visible,.dk input:focus-visible,.dk textarea:focus-visible,.dk select:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.dk-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.dk-msg{display:flex;justify-content:space-between;gap:12px;padding:8px 14px;border-radius:8px;margin-bottom:10px;border:1px solid}
.dk-msg button{border:0;background:none;color:inherit;font-size:18px;cursor:pointer}
.dk-msg-error{background:var(--ats);border-color:var(--at);color:var(--at)}
.dk-msg-ok{background:var(--dns);border-color:var(--dn);color:var(--dn)}
.dk-empty{display:grid;justify-items:center;gap:6px;padding:40px 16px;border:1px dashed var(--ln);border-radius:8px;text-align:center;color:var(--mu)}
.dk-empty strong{color:var(--ink);font-size:15px}
.dk-spin{width:22px;height:22px;border:2px solid var(--ln);border-top-color:var(--ac);border-radius:50%;animation:dk-spin .8s linear infinite}
@keyframes dk-spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.dk-spin{animation:none}}

.ir-strip{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 16px;margin-bottom:12px;border:1px solid var(--ln);border-radius:10px;background:var(--sf)}
.ir-strip h2{font:600 20px/1.2 Georgia,serif;margin:0}
.ir-meta{display:flex;flex-wrap:wrap;gap:2px 14px;margin:2px 0 0;color:var(--mu);font-size:13px}
.ir-pill{flex:none;padding:3px 12px;border-radius:99px;font-size:12px;font-weight:600;white-space:nowrap}
.ir-pill.bad{background:var(--ats);color:var(--at)}
.ir-pill.wait{background:var(--pgs);color:var(--pg)}
.ir-pill.ok{background:var(--dns);color:var(--dn)}

.ir-grid{display:grid;grid-template-columns:1fr;gap:12px;align-items:start}
.ir-col{display:grid;gap:12px;min-width:0}
@media (min-width:980px){
  .ir-grid{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:16px}
  .ir-act{position:sticky;top:12px}
}
.ir-card{border:1px solid var(--ln);border-radius:10px;background:var(--sf);padding:12px 16px}
.ir-card h3{margin:0 0 6px;font-size:14px;font-weight:600}
.ir-alert{border-color:var(--at);background:var(--ats)}
.ir-alert p{margin:0 0 2px}
.ir-hint{margin:0 0 8px;color:var(--mu);font-size:13px}
.ir-sub{margin:4px 0 0;color:var(--mu);font-size:12px}

.ir-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.ir-row{display:grid;gap:4px;align-content:start;padding:8px 10px;border:1px solid var(--ln);border-radius:8px}
.ir-row input[type=number],.ir-row select{width:100%;padding:7px 10px;border:1px solid var(--ln);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;box-sizing:border-box}
.ir-row input:disabled,.ir-row select:disabled{opacity:.6;cursor:not-allowed}
.ir-label{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.ir-label>label:first-child{color:var(--mu);font-size:12px;font-weight:600}
.ir-flag{padding:1px 8px;border-radius:99px;background:var(--ats);color:var(--at);font-size:11px;font-weight:600}
.ir-tick{display:flex;align-items:center;gap:6px;color:var(--at);font-size:12px;font-weight:600;cursor:pointer}
.ir-marked{border-color:var(--at);background:var(--ats)}
.ir-open{border-color:var(--ac)}

.ir-facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px 16px;margin:12px 0 0;padding-top:10px;border-top:1px solid var(--ln)}
.ir-facts dt{color:var(--mu);font-size:12px}
.ir-facts dd{margin:0;font-weight:600;overflow-wrap:anywhere}

.ir-field{display:grid;gap:3px;margin-bottom:8px}
.ir-field span{color:var(--mu);font-size:12px}
.ir-field textarea{width:100%;padding:7px 10px;border:1px solid var(--ln);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;resize:vertical;min-height:52px;max-height:150px;box-sizing:border-box}

.ir-toggle{display:flex;justify-content:space-between;align-items:center;width:100%;padding:0;border:0;background:none;color:var(--ink);font:inherit;font-weight:600;cursor:pointer}
.ir-toggle small{color:var(--mu);font-weight:400}
.ir-toggle span:last-child{color:var(--mu);font-weight:400;font-size:12px}
.ir-tl{list-style:none;margin:10px 0 0;padding:0;display:grid;gap:10px;max-height:420px;overflow:auto}
.ir-tl li{display:grid;grid-template-columns:12px 1fr;gap:8px}
.ir-tl i{width:10px;height:10px;margin-top:6px;border-radius:50%;background:var(--ac)}
.ir-tl .rejected i{background:var(--at)}
.ir-tl .resubmitted i{background:var(--pg)}
.ir-tl .note i{background:var(--mu)}
.ir-tl-head{margin:0;font-size:13px}
.ir-tl-head time{margin-left:8px;color:var(--mu);font-size:12px}
.ir-tl-reason{margin:3px 0 0;padding:4px 10px;border-left:3px solid var(--ln);background:var(--bg);border-radius:0 6px 6px 0;font-size:13px}
.ir-tl .rejected .ir-tl-reason{border-left-color:var(--at);background:var(--ats)}
.ir-tl-note{border-left-color:var(--pg);background:var(--pgs)}
.ir-tl-chips{margin:4px 0 0;color:var(--mu);font-size:12px}
.ir-chip{display:inline-block;margin:0 4px 0 6px;padding:1px 8px;border-radius:99px;background:var(--ats);color:var(--at);font-size:12px;font-weight:600}
.dk-diff{list-style:none;margin:4px 0 0;padding:0;display:grid;gap:3px}
.dk-diff li{display:grid;grid-template-columns:130px 1fr 1fr;gap:8px;align-items:baseline;font-size:12px}
.dk-diff-l{color:var(--mu)}
.dk-diff del{background:var(--ats);color:var(--at);padding:1px 6px;border-radius:4px;text-decoration:line-through;overflow-wrap:anywhere}
.dk-diff ins{background:var(--dns);color:var(--dn);padding:1px 6px;border-radius:4px;text-decoration:none;overflow-wrap:anywhere}
@media (max-width:640px){
  .dk{padding:14px 12px 28px}
  .dk-diff li{grid-template-columns:1fr}
  .ir-strip{flex-direction:column;align-items:flex-start}
  .dk-actions .dk-btn{flex:1}
}
</style>
