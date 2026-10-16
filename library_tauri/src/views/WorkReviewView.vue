<template>
  <div class="app-container review-page">
    <header class="app-header">
      <div class="brand">
        <div class="brand-logo">AO</div>
        <div>
          <h1>{{ isReviewMode ? 'Work Review Dossier' : canCorrect ? 'Work Correction Dossier' : 'Work Record Dossier' }}</h1>
          <p>Athenaeum Orbis · Catalogue governance and review history</p>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <span class="badge" :class="{ 'badge-warning': data?.status !== 'APPROVED' }">{{ data ? statusLabel : 'Opening record' }}</span>
        <button type="button" class="review-back" style="margin-right:8px" :disabled="!data" @click="previewOpen = true">Preview</button>
        <button type="button" class="review-back" @click="goBack">← Back to Docket</button>
      </div>
    </header>

    <div v-if="error" class="review-error" role="alert">{{ error }}</div>
    <div v-if="previewOpen" class="preview-overlay" @click.self="previewOpen = false">
      <div class="preview-card" role="dialog" aria-modal="true" aria-label="Record preview">
        <div class="preview-top">
          <span class="preview-tag">Catalogue preview - read only</span>
          <button type="button" class="preview-close" aria-label="Close preview" @click="previewOpen = false">&times;</button>
        </div>
        <h2 class="preview-title">{{ form.title || 'Untitled Work' }}</h2>
        <p class="preview-author">{{ form.author || 'Author not recorded' }}</p>
        <div class="preview-meta">
          <span>Work #{{ workId }}</span><span>{{ statusLabel }}</span><span>{{ data?.item_count ?? 0 }} copy(ies) attached</span>
        </div>
        <dl class="preview-rows">
          <div v-for="row in previewRows" :key="row.label" class="preview-row"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></div>
        </dl>
        <div v-if="form.notes" class="preview-block"><strong>Notes</strong><p>{{ form.notes }}</p></div>
        <div v-if="form.proposal_reason" class="preview-block"><strong>Why this was proposed</strong><p>{{ form.proposal_reason }}</p></div>
        <div v-if="data?.status === 'REJECTED' && data?.rejection_reason" class="preview-block preview-reject"><strong>Returned by The Chief</strong><p>{{ data.rejection_reason }}</p></div>
        <p v-if="canCorrect" class="preview-hint">This shows your current edits. Nothing is saved until you resubmit.</p>
        <div class="preview-footer"><button type="button" class="btn-secondary" @click="previewOpen = false">Close preview</button></div>
      </div>
    </div>
    <div v-if="rejectDialogOpen" class="reject-overlay" @click.self="rejectDialogOpen = false" @keydown.esc="rejectDialogOpen = false">
      <div class="reject-dialog" role="alertdialog" aria-modal="true" aria-labelledby="reject-title">
        <div class="reject-icon">!</div>
        <h3 id="reject-title">Reject this Work permanently?</h3>
        <p class="reject-sub"><strong>{{ data?.values?.title || 'Untitled Work' }}</strong> - Work #{{ workId }}</p>
        <ul class="reject-points">
          <li>The Keeper will not be able to correct or resubmit this Work.</li>
          <li>The Work stays on record as permanently rejected, with your reason.</li>
          <li>If the Keeper should fix it, choose Return for Correction instead.</li>
        </ul>
        <div class="reject-reason"><span>Your recorded reason</span><p>{{ reason }}</p></div>
        <label class="reject-ack"><input type="checkbox" v-model="rejectAck" /> I understand the Keeper cannot resubmit this Work.</label>
        <div class="reject-actions">
          <button type="button" class="btn-secondary" autofocus @click="rejectDialogOpen = false">Cancel</button>
          <button type="button" class="reject-confirm" :disabled="!rejectAck || busy" @click="rejectFinal">{{ busy ? 'Rejecting...' : 'Reject permanently' }}</button>
        </div>
      </div>
    </div>
    <div v-if="loading" class="review-loading"><strong>Opening archive record…</strong><span>Loading catalogue data and audit history.</span></div>
    <div v-else-if="!data" class="review-empty">This Work could not be opened. It may not exist or you may not have access.</div>

    <template v-else>
      <section class="review-summary">
        <div>
          <h2>{{ data.values.title || 'Untitled Work' }}</h2>
          <div class="review-summary-meta">
            <span v-if="data.values.author"><strong>Author:</strong> {{ data.values.author }}</span>
            <span v-if="data.proposer_name"><strong>Proposed by:</strong> {{ data.proposer_name }}</span>
            <span><strong>Copies:</strong> {{ data.item_count }} attached</span>
            <span><strong>Work ID:</strong> #{{ workId }}</span>
          </div>
          <p class="review-description">{{ subtitle }}</p>
        </div>
        <span class="review-status" :class="statusClass">{{ statusLabel }}</span>
      </section>

      <section v-if="data.status === 'REJECTED'" class="review-alert">
        <strong>Returned by The Chief</strong>
        <p>{{ data.rejection_reason || 'No reason was recorded on this legacy correction.' }}</p>
        <p v-if="data.legacy_rejection" style="margin-top:8px">This older return has no field-level correction list; all correctable fields may be revised.</p>
        <template v-else-if="data.final_rejection">
          <p style="margin-top:8px"><strong>Final rejection:</strong> this Work is read-only and cannot be resubmitted.</p>
        </template>
        <template v-else-if="data.correction?.fields?.length">
          <div class="review-chips"><span v-for="f in data.correction.fields" :key="f" class="review-chip">{{ fieldLabel(f) }}</span></div>
        </template>
      </section>

      <div class="review-layout">
        <main class="review-main">
          <section v-for="group in GROUPS" :key="group.title" class="card">
            <div class="card-header"><h2>{{ group.title }}</h2></div>
            <div class="card-body">
              <div class="review-fields">
                <div v-for="key in group.keys" :key="key" class="review-field" :class="[fieldClass(key), { wide: FIELD_BY_KEY[key].wide }]">
                  <div class="review-field-head">
                    <label :for="`review-${key}`">{{ FIELD_BY_KEY[key].label }}</label>
                    <label v-if="isReviewMode" class="review-needs-fix">
                      <input v-model="ticks[key]" type="checkbox" :aria-label="`Needs correction: ${FIELD_BY_KEY[key].label}`" /> Needs fix
                    </label>
                    <span v-else-if="isMarked(key)" class="badge badge-warning">Correction requested</span>
                  </div>
                  <template v-if="isEditable(key)">
                    <textarea v-if="FIELD_BY_KEY[key].type === 'textarea'" :id="`review-${key}`" v-model="form[key]" rows="3" :placeholder="`Enter ${FIELD_BY_KEY[key].label.toLowerCase()}…`"></textarea>
                    <template v-else-if="FIELD_BY_KEY[key].type === 'combo'">
                    <select :id="`review-${key}`" :value="comboSelectValue(key)" @change="onComboSelect(key, $event.target.value)">
                      <option value="" disabled>Select {{ FIELD_BY_KEY[key].label.toLowerCase() }}...</option>
                      <option v-for="o in comboOptions(key)" :key="o" :value="o">{{ o }}</option>
                      <option value="__other__">Other (type new)...</option>
                    </select>
                    <input v-if="comboIsOther(key)" type="text" v-model="form[key]" autocomplete="off" :placeholder="`Type new ${FIELD_BY_KEY[key].label.toLowerCase()}...`" />
                  </template>
                  <select v-else-if="FIELD_BY_KEY[key].type === 'select'" :id="`review-${key}`" v-model="form[key]">
                      <option value="" disabled>Select {{ FIELD_BY_KEY[key].label.toLowerCase() }}...</option>
                      <option v-if="form[key] && !FIELD_BY_KEY[key].options.includes(form[key])" :value="form[key]" disabled>{{ form[key] }} (not allowed)</option>
                      <option v-for="opt in FIELD_BY_KEY[key].options" :key="opt" :value="opt">{{ opt }}</option>
                    </select><input v-else :id="`review-${key}`" v-model="form[key]" :type="FIELD_BY_KEY[key].type" :placeholder="`Enter ${FIELD_BY_KEY[key].label.toLowerCase()}…`" />
                  </template>
                  <div v-else class="review-value" :class="{ empty: !form[key] }">{{ form[key] || '—' }}</div>
                </div>
              </div>
            </div>
          </section>
        </main>

        <aside class="review-side">
          <section v-if="isReviewMode" class="card review-panel">
            <div class="card-header"><h2>Reviewer Decision</h2></div>
            <div class="card-body">
              <span class="review-panel-badge">Chief authority</span>
              <h3>Validate this Work</h3>
              <p>Review the submitted bibliographic data. Mark any field requiring correction before returning it to The Keeper.</p>
              <label class="review-input-label" for="review-reason">Decision reason <span>(required)</span>
                <textarea id="review-reason" v-model="reason" rows="4" maxlength="2000" placeholder="Record the basis for approval or return…"></textarea>
              </label>
              <label class="review-input-label" for="review-correction-note">Correction note <span>(optional)</span>
                <textarea id="review-correction-note" v-model="correctionNote" rows="3" maxlength="2000" placeholder="Specific guidance for The Keeper…"></textarea>
              </label>
              <div class="review-danger-note">{{ markedCount ? `${markedCount} field(s) selected for correction.` : 'No fields marked. Approval may proceed; returning for correction requires at least one marked field.' }}</div>
              <div class="review-actions">
                <button type="button" class="btn-primary" :disabled="busy || !reason.trim()" @click="approve">{{ busy ? 'Saving…' : 'Approve Work' }}</button>
                <button type="button" class="btn-secondary" :disabled="busy || !markedCount || !reason.trim()" @click="sendBack">{{ busy ? 'Saving…' : 'Return for Correction' }}</button>
                <button type="button" class="btn-danger" :disabled="busy || !reason.trim()" @click="rejectFinal">Reject Work Permanently</button>
              </div>
              <p class="review-description">Final rejection closes this submission. Use “Return for Correction” when The Keeper should be allowed to revise and resubmit the same Work.</p>
            </div>
          </section>

          <section v-if="canCorrect" class="card review-panel">
            <div class="card-header"><h2>Keeper Resubmission</h2></div>
            <div class="card-body">
              <span class="review-panel-badge amber">Correction response</span>
              <h3>Submit the same Work again</h3>
              <p>Only fields marked by The Chief can be changed. The original Work ID and review history are retained.</p>
              <label class="review-input-label" for="keeper-note">Note to The Chief <span>(optional)</span>
                <textarea id="keeper-note" v-model="keeperNote" rows="4" maxlength="2000" placeholder="Explain the changes made or why a value was preserved…"></textarea>
              </label>
              <div class="review-danger-note">Resubmission returns this same record to Pending review. It does not create a duplicate Work.</div>
              <div class="review-actions"><button type="button" class="btn-primary" :disabled="busy" @click="resubmit">{{ busy ? 'Resubmitting…' : 'Resubmit for Review' }}</button></div>
            </div>
          </section>

          <section class="card">
            <button type="button" class="review-history-toggle" :aria-expanded="historyOpen" @click="historyOpen = !historyOpen">
              <span>Record Audit History · {{ events.length }}</span><span>{{ historyOpen ? 'Collapse −' : 'Expand +' }}</span>
            </button>
            <div v-if="historyOpen" class="card-body" style="padding:0">
              <div v-if="!events.length" class="review-empty" style="margin:16px">No review events are available for this Work.</div>
              <ol v-else class="review-history-list">
                <li v-for="event in events" :key="event.id" class="review-history-item">
                  <div class="review-history-head"><strong>{{ eventTitle(event) }}</strong><time>{{ fmtWhen(event.at) }}</time></div>
                  <div v-if="event.actor" class="review-history-actor">{{ event.actor }}<span v-if="event.actor_role"> · {{ event.actor_role }}</span></div>
                  <p v-if="event.reason" class="review-history-reason">{{ event.reason }}</p>
                  <div v-if="event.flagged_fields?.length" class="review-chips"><span v-for="field in event.flagged_fields" :key="field" class="review-chip">{{ fieldLabel(field) }}</span></div>
                  <p v-if="event.correction_note" class="review-history-reason"><strong>Correction note:</strong> {{ event.correction_note }}</p>
                  <div v-if="diffRows(event.changes).length" class="review-history-diff">
                    <div v-for="row in diffRows(event.changes)" :key="row.field" class="review-diff-row"><strong>{{ row.label }}</strong><del>{{ showValue(row.from) }}</del><ins>{{ showValue(row.to) }}</ins></div>
                  </div>
                </li>
              </ol>
            </div>
          </section>
        </aside>
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
  { key: 'category', label: 'Category', type: 'select', options: ['Fiction', 'Non-Fiction', 'Reference', 'Religious', 'Poetry'] },
  { key: 'language', label: 'Language', type: 'combo' },
  { key: 'publisher', label: 'Publisher', type: 'text' },
  { key: 'year', label: 'Year', type: 'number' },
  { key: 'isbn', label: 'ISBN', type: 'text' },
  { key: 'ddc', label: 'DDC', type: 'text' },
  { key: 'call_no', label: 'Call no.', type: 'text' },
  { key: 'translation_compilation', label: 'Translation / compilation', type: 'text' },
  { key: 'genre', label: 'Genre', type: 'combo' },
  { key: 'original_language', label: 'Original language', type: 'combo' },
  { key: 'notes', label: 'Notes', type: 'textarea', wide: true },
  { key: 'proposal_reason', label: 'Why this was proposed', type: 'textarea', wide: true }
]
const FIELD_LABELS = Object.fromEntries(FIELDS.map(f => [f.key, f.label]))
const FIELD_BY_KEY = Object.fromEntries(FIELDS.map(f => [f.key, f]))
const GROUPS = [
  { title: 'A. Identification', keys: ['title', 'author', 'publisher', 'year', 'isbn'] },
  { title: 'B. Classification', keys: ['category', 'genre', 'language', 'original_language', 'translation_compilation', 'ddc', 'call_no'] },
  { title: 'C. Notes & Proposal Context', keys: ['notes', 'proposal_reason'] }
]

const loading = ref(true)
const busy = ref(false)
const error = ref('')
const data = ref(null)
const events = ref([])
const historyOpen = ref(true)
const emptyForm = () => Object.fromEntries(FIELDS.map(f => [f.key, '']))
const form = ref(emptyForm())
const ticks = ref(Object.fromEntries(FIELDS.map(f => [f.key, false])))
const reason = ref('')
const correctionNote = ref('')
const keeperNote = ref('')
const fieldOptions = ref({ original_languages: [], genres: [] })
const LANGUAGE_CHOICES = ['Malayalam', 'English', 'Multi -Lingual', 'German', 'French']
function comboOptions(key) {
  if (key === 'language') return LANGUAGE_CHOICES
  if (key === 'original_language') return fieldOptions.value.original_languages || []
  if (key === 'genre') return fieldOptions.value.genres || []
  return []
}
async function loadFieldOptions() {
  try {
    const res = await axios.get('/catalogue/review/field-options')
    fieldOptions.value = { ...fieldOptions.value, ...(res.data || {}) }
  } catch (err) {
    console.error('Field options failed:', err)
  }
}
onMounted(loadFieldOptions)
const comboOther = ref({})
function comboIsOther(key) {
  const v = form.value[key]
  return !!comboOther.value[key] || (!!v && !comboOptions(key).includes(v))
}
function comboSelectValue(key) {
  if (comboIsOther(key)) return '__other__'
  return form.value[key] || ''
}
function onComboSelect(key, val) {
  if (val === '__other__') {
    comboOther.value = { ...comboOther.value, [key]: true }
    if (comboOptions(key).includes(form.value[key])) form.value[key] = ''
  } else {
    comboOther.value = { ...comboOther.value, [key]: false }
    form.value[key] = val
  }
}
const previewOpen = ref(false)
const previewRows = computed(() => FIELDS
  .filter(f => !['title', 'author', 'notes', 'proposal_reason'].includes(f.key))
  .map(f => ({ label: f.label, value: form.value[f.key] }))
  .filter(r => r.value))
const rejectDialogOpen = ref(false)
const rejectAck = ref(false)

function fieldLabel(key) { return FIELD_LABELS[key] || key }
const isReviewMode = computed(() => isChief.value && data.value?.status === 'PENDING')
const canCorrect = computed(() => !isChief.value && (data.value?.editable_fields || []).length > 0)
const subtitle = computed(() => isReviewMode.value
  ? 'Validate the submitted bibliographic record, mark discrepancies, and record a reasoned decision.'
  : canCorrect.value
    ? 'Revise the requested fields and resubmit this same Work for Chief review.'
    : 'Read-only catalogue record with its decision and correction history.')
const statusLabel = computed(() => {
  const status = data.value?.status
  if (status === 'PENDING') return 'Pending Chief Review'
  if (status === 'REJECTED') return 'Returned for Correction'
  if (status === 'APPROVED') return 'Approved & Catalogued'
  return status || 'Unknown status'
})
const statusClass = computed(() => data.value?.status === 'REJECTED' ? 'bad' : data.value?.status === 'PENDING' ? 'wait' : '')
const editableSet = computed(() => new Set(data.value?.editable_fields || []))
const markedSet = computed(() => new Set(data.value?.correction?.fields || []))
const markedCount = computed(() => Object.values(ticks.value).filter(Boolean).length)
function isEditable(key) { return editableSet.value.has(key) && canCorrect.value }
function isMarked(key) { return isReviewMode.value ? !!ticks.value[key] : markedSet.value.has(key) }
function fieldClass(key) { return { marked: isMarked(key), open: !isReviewMode.value && isEditable(key) } }

async function load() {
  loading.value = true
  error.value = ''
  if (!Number.isInteger(workId.value) || workId.value <= 0) {
    data.value = null
    error.value = 'A valid Work ID is required.'
    loading.value = false
    return
  }
  try {
    const response = await axios.get(`/catalogue/review/work/${workId.value}`)
    data.value = response.data
    const filled = emptyForm()
    for (const field of FIELDS) {
      const value = response.data.values?.[field.key]
      filled[field.key] = value === null || value === undefined ? '' : String(value)
    }
    form.value = filled
    ticks.value = Object.fromEntries(FIELDS.map(f => [f.key, false]))
    await loadHistory()
  } catch (err) {
    data.value = null
    error.value = err.response?.data?.detail || 'Unable to open this Work.'
  } finally { loading.value = false }
}
async function loadHistory() {
  try {
    const response = await axios.get(`/catalogue/history/work/${workId.value}`)
    events.value = Array.isArray(response.data) ? response.data : []
  } catch {
    events.value = []
  }
}
async function approve() {
  const text = reason.value.trim()
  if (!text) { error.value = 'A reason is required before approving.'; return }
  if (!isReviewMode.value) { error.value = 'This Work is not awaiting a Chief decision.'; return }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/approve/${workId.value}`, null, { params: { action: 'APPROVE', reason: text } })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to approve this Work.'
  } finally { busy.value = false }
}
async function rejectFinal() {
  const text = reason.value.trim()
  if (!text) { error.value = 'A reason is required before rejecting.'; return }
  if (!isReviewMode.value) { error.value = 'This Work is not awaiting a Chief decision.'; return }
  if (!rejectDialogOpen.value) { rejectAck.value = false; rejectDialogOpen.value = true; return }
  rejectDialogOpen.value = false
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/approve/${workId.value}`, null, { params: { action: 'REJECT', reason: text } })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to reject this Work.'
  } finally { busy.value = false }
}
async function sendBack() {
  const text = reason.value.trim()
  const fields = Object.keys(ticks.value).filter(key => ticks.value[key])
  if (!isReviewMode.value) { error.value = 'This Work is not awaiting a Chief decision.'; return }
  if (!fields.length) { error.value = 'Mark at least one field requiring correction.'; return }
  if (!text) { error.value = 'A review explanation is required.'; return }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/review/work/${workId.value}/request-correction`, {
      fields, reason: text, correction_note: correctionNote.value.trim() || null
    })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to return this Work for correction.'
  } finally { busy.value = false }
}
async function resubmit() {
  if (!canCorrect.value) { error.value = 'This Work is not available for correction by the current role.'; return }
  const changes = {}
  for (const key of data.value.editable_fields || []) changes[key] = form.value[key]
  if ('title' in changes && !String(changes.title || '').trim()) { error.value = 'Title cannot be empty.'; return }
  if ('language' in changes && !String(changes.language || '').trim()) { error.value = 'Language cannot be empty.'; return }
  busy.value = true
  error.value = ''
  try {
    await axios.post(`/catalogue/review/work/${workId.value}/resubmit-corrected`, { changes, note: keeperNote.value.trim() || null })
    router.push('/docket')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to resubmit this Work.'
  } finally { busy.value = false }
}
function goBack() { router.push('/docket') }
const EVENT_TITLES = {
  SUBMITTED: 'Submission Created', APPROVED: 'Approved / Direct Registration',
  REJECTED: 'Returned for Correction', RESUBMITTED: 'Resubmitted for Review', NOTE: 'Desk Note'
}
function eventTitle(event) {
  if (event.type === 'NOTE') return event.note_kind === 'KEEPER_NOTE' ? 'Note from Keeper' : 'Note from Chief'
  if (event.decision_action === 'REJECT_FINAL') return 'Finally Rejected'
  if (event.decision_action === 'RETURN_FOR_CORRECTION') return 'Returned for Correction'
  return EVENT_TITLES[event.type] || event.type
}
function diffRows(changes) {
  if (!changes || typeof changes !== 'object') return []
  return Object.entries(changes).map(([field, value]) => ({ field, label: fieldLabel(field), from: value?.from, to: value?.to }))
}
function showValue(value) { return value === null || value === undefined || value === '' ? '(empty)' : String(value) }
function fmtWhen(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
onMounted(load)
</script>

<style scoped>
/* Modern, clean, professional cataloguing interface */
* { box-sizing: border-box; }
body { margin: 0; background: #f8fafc; font-family: Inter, system-ui, -apple-system, sans-serif; color: #0f172a; }

.app-container { max-width: 1400px; margin: 0 auto; padding: 24px; min-height: 100vh; background: #f8fafc; }

.app-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand-logo { width: 44px; height: 44px; background: #1ea253; color: #0d0e0e; border-radius: 10px; display: grid; place-items: center; font-weight: 700; font-size: 16px; }
.brand h1 { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
.brand p { margin: 2px 0 0; font-size: 12px; color: #64748b; }

.badge { padding: 6px 12px; background: #dcfce7; color: #166534; font-size: 12px; font-weight: 600; border-radius: 99px; }
.badge-warning { background: #fee2e2; color: #991b1b; }
.badge-sub { font-size: 11px; color: #64748b; font-weight: 500; }

.workspace { display: grid; grid-template-columns: 1fr 380px; gap: 24px; }
.form-column { display: flex; flex-direction: column; gap: 20px; }
.sidebar-column { display: flex; flex-direction: column; gap: 20px; }

.card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); overflow: hidden; }
.card-header { padding: 16px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
.card-header h2 { margin: 0; font-size: 14px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; }
.card-body { padding: 20px; }

.intake-card { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; margin-bottom: 24px; background: #ffffff; }
.intake-label strong { display: block; font-size: 13px; color: #0f172a; }
.intake-label span { font-size: 11px; color: #64748b; }
.intake-input-group { display: flex; gap: 10px; width: 60%; }
.intake-input-group input { flex: 1; height: 38px; border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 12px; font-size: 13px; outline: none; }
.intake-input-group button { height: 38px; background: #2563eb; color: #fff; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; font-size: 12px; cursor: pointer; }
.intake-input-group button:hover { background: #1d4ed8; }

.field-group { display: flex; flex-direction: column; gap: 6px; position: relative; }
.field-group label { font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; }
.field-group input, .field-group select, .field-group textarea { width: 100%; height: 38px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; padding: 0 12px; font-size: 13px; color: #0f172a; outline: none; }
.field-group input:focus, .field-group select:focus, .field-group textarea:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
.field-group textarea { height: auto; padding: 10px 12px; resize: vertical; }
.field-group small { font-size: 11px; color: #16a34a; }

.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid-4col { display: grid; grid-template-columns: 1.5fr 0.8fr 0.8fr 1fr; gap: 12px; }

.primary-title-group input { font-size: 18px; font-weight: 600; height: 44px; }

.suggestion-container { position: relative; }
.input-with-lock { position: relative; }
.lock-badge { position: absolute; right: 10px; top: 10px; font-size: 11px; color: #16a34a; font-weight: 600; }
.suggestions-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 4px; z-index: 50; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); max-height: 200px; overflow-y: auto; }
.suggestion-header { padding: 8px 12px; font-size: 10px; font-weight: 700; color: #64748b; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; }
.suggestion-row { padding: 10px 12px; display: flex; justify-content: space-between; cursor: pointer; border-bottom: 1px solid #f1f5f9; font-size: 12px; }
.suggestion-row:hover { background: #f8fafc; }
.suggestion-row .sub-text { color: #64748b; }

.stat-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; flex-direction: column; justify-content: center; }
.stat-box span { font-size: 10px; font-weight: 600; color: #64748b; text-transform: uppercase; }
.stat-box strong { font-size: 15px; color: #0f172a; margin-top: 4px; }

.inline-action-input { display: flex; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; height: 38px; }
.inline-action-input input { border: none; flex: 1; height: 100%; padding: 0 12px; outline: none; }
.inline-action-input button { border: none; background: #f1f5f9; border-left: 1px solid #cbd5e1; padding: 0 12px; font-size: 11px; font-weight: 700; color: #2563eb; cursor: pointer; }
.inline-action-input button:hover { background: #e2e8f0; }

.preview-banner { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-top: 16px; font-size: 12px; }
.preview-banner span { color: #64748b; }
.preview-banner strong { color: #0f172a; display: block; margin-top: 2px; }

.genre-section { margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 16px; }
.genre-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.custom-input { margin-top: 10px; }
.genre-chips-container { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.chip { padding: 4px 10px; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 99px; font-size: 11px; font-weight: 500; }
.empty-text { font-size: 12px; color: #94a3b8; }

.evidence-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 16px; }
.warning-box { background: #fff5f5; border-color: #fecaca; }
.evidence-title { display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-bottom: 8px; }
.evidence-title span { color: #64748b; font-weight: 600; }
.evidence-title strong { color: #16a34a; }
.warning-box .evidence-title strong { color: #dc2626; }
.success-text { font-size: 12px; color: #16a34a; margin: 0; }
.warning-text { font-size: 12px; color: #991b1b; margin: 0 0 8px 0; }
.conflict-matches { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.match-btn { display: flex; flex-direction: column; text-align: left; padding: 8px 10px; background: #fff; border: 1px solid #fecaca; border-radius: 6px; cursor: pointer; }
.match-btn:hover { background: #fff1f2; }
.match-btn strong { font-size: 12px; color: #991b1b; }
.match-btn span { font-size: 11px; color: #7f1d1d; }
.checkbox-label { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 11px; color: #7f1d1d; font-weight: 600; cursor: pointer; }

.readiness-container { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; }
.readiness-header { display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 8px; }
.progress-bar-wrap { height: 6px; background: #e2e8f0; border-radius: 99px; overflow: hidden; margin-bottom: 12px; }
.progress-fill { height: 100%; background: #16a34a; border-radius: 99px; }
.readiness-item { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid #e2e8f0; }
.readiness-item:last-child { border-bottom: none; }
.status-icon { width: 20px; height: 20px; border-radius: 4px; background: #e2e8f0; color: #64748b; display: grid; place-items: center; font-size: 11px; font-weight: 700; }
.status-icon.checked { background: #dcfce7; color: #166534; }
.readiness-item strong { display: block; font-size: 11px; text-transform: uppercase; color: #334155; }
.readiness-item small { display: block; font-size: 10px; color: #64748b; }

.conflicts-register { margin-top: 14px; border-top: 1px solid #e2e8f0; padding-top: 10px; }
.conflicts-register h4 { margin: 0 0 6px 0; font-size: 11px; color: #334155; text-transform: uppercase; }
.conflict-row { display: flex; flex-direction: column; gap: 2px; font-size: 11px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; }
.conflict-row strong { color: #0f172a; }
.conflict-row span { color: #64748b; }

.action-card .card-body { display: flex; flex-direction: column; gap: 14px; }
.record-summary-preview h3 { margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #0f172a; }
.record-summary-preview p { margin: 0; font-size: 12px; color: #64748b; }

.gate-status { padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
.gate-status span { display: block; font-size: 10px; font-weight: 600; color: #64748b; text-transform: uppercase; }
.gate-status strong { display: block; font-size: 12px; color: #166534; margin-top: 2px; }
.gate-held strong { color: #991b1b; }

.btn-primary { width: 100%; height: 42px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.sub-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.btn-secondary { height: 38px; background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }
.btn-secondary:hover { background: #e2e8f0; }
.btn-danger { height: 38px; background: #fff5f5; color: #dc2626; border: 1px solid #fecaca; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }
.btn-danger:hover { background: #fee2e2; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.6); display: grid; place-items: center; z-index: 100; padding: 20px; }
.modal-card { width: min(480px, 100%); background: #fff; border-radius: 12px; padding: 24px; position: relative; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-close { position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 20px; color: #64748b; cursor: pointer; }
.modal-card h2 { margin: 0 0 8px 0; font-size: 18px; color: #0f172a; }
.modal-card p { margin: 0 0 16px 0; font-size: 13px; color: #64748b; }
.modal-item-preview { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
.modal-item-preview span { display: block; font-size: 10px; font-weight: 600; color: #64748b; }
.modal-item-preview strong { display: block; font-size: 15px; color: #0f172a; margin-top: 2px; }
.modal-item-preview small { display: block; font-size: 11px; color: #64748b; margin-top: 2px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.toast-notification { position: fixed; right: 24px; bottom: 24px; width: min(360px, calc(100vw - 48px)); background: #0f172a; color: #fff; border-radius: 10px; padding: 16px; z-index: 110; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2); }
.toast-notification strong { display: block; font-size: 13px; color: #4ade80; }
.toast-notification span { display: block; font-size: 12px; color: #94a3b8; margin-top: 4px; }


/* Title candidates are inline so they cannot be clipped by card overflow. */
.title-input-wrapper { display: flex; align-items: stretch; width: 100%; min-width: 0; }
.title-input-wrapper input { flex: 1; min-width: 0; }
.field-clear-btn { flex: 0 0 auto; border: 1px solid #cbd5e1; border-left: 0; border-radius: 0 8px 8px 0; padding: 0 10px; background: #f8fafc; color: #475569; font-size: 11px; cursor: pointer; }
.title-input-wrapper input:has(+ .field-clear-btn) { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.input-with-lock input { padding-right: 112px; }
.author-clear-btn { position: absolute; right: 48px; top: 6px; min-height: 26px; border: 0; border-radius: 5px; margin: 0; padding: 0 6px; }
.lookup-help { display: block; color: #64748b; font-size: 11px; line-height: 1.4; }
.lookup-message { margin: 2px 0 0; padding: 8px 10px; border: 1px solid #dbeafe; border-radius: 7px; background: #eff6ff; color: #1e40af; font-size: 11px; line-height: 1.4; }
.title-candidate-list { display: grid; gap: 7px; margin-top: 8px; }
.title-candidate-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border: 1px solid #dbe4ee; border-radius: 8px; background: #fbfdff; }
.title-candidate-copy { display: grid; gap: 3px; min-width: 0; }
.title-candidate-copy strong { color: #0f172a; font-size: 13px; overflow-wrap: anywhere; }
.title-candidate-copy small { color: #64748b; font-size: 11px; line-height: 1.35; }
.title-use-btn { flex: 0 0 auto; min-height: 32px; border: 1px solid #bbf7d0; border-radius: 7px; padding: 0 11px; background: #f0fdf4; color: #166534; font-size: 11px; font-weight: 700; cursor: pointer; }
.author-suggestions-dropdown { box-sizing: border-box; overflow-y: auto; overscroll-behavior: contain; padding: 0; background: #fff; border: 1px solid #cbd5e1; border-radius: 10px; box-shadow: 0 14px 32px rgba(15, 23, 42, .22); color: #0f172a; }
.author-suggestions-dropdown .suggestion-header { position: sticky; top: 0; z-index: 1; padding: 9px 12px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; color: #475569; font-size: 10px; font-weight: 800; letter-spacing: .05em; }
.author-suggestions-dropdown .external-suggestion-header { top: 0; background: #ecfdf5; color: #166534; }
.author-suggestion-button { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; width: 100%; padding: 10px 12px; border: 0; border-bottom: 1px solid #eef2f7; background: #fff; text-align: left; cursor: pointer; white-space: normal; }
.author-suggestion-button:hover, .author-suggestion-button:focus-visible { background: #f8fafc; outline: 2px solid #93c5fd; outline-offset: -2px; }
.suggestion-main { display: block; max-width: 100%; color: #0f172a; font-size: 13px; font-weight: 700; overflow-wrap: anywhere; }
.suggestion-meta, .suggestion-detail { display: block; color: #64748b; font-size: 11px; line-height: 1.35; overflow-wrap: anywhere; }
.external-author-button .suggestion-main { color: #166534; }
.suggestion-empty { padding: 10px 12px; color: #64748b; background: #fff; font-size: 11px; line-height: 1.45; overflow-wrap: anywhere; }
@media (max-width: 640px) { .title-candidate-row { align-items: flex-start; flex-direction: column; } .title-use-btn { align-self: flex-start; } }


/* Chief review desk additions: same bright dossier palette, with review-specific controls. */
.review-page { max-width: 1500px; }
.review-back { background: #fff; border: 1px solid #cbd5e1; color: #334155; border-radius: 8px; padding: 9px 13px; font-weight: 650; cursor: pointer; }
.review-layout { display:grid; grid-template-columns:minmax(0,1.7fr) minmax(300px,.9fr); gap:22px; align-items:start; }
.review-main,.review-side { display:flex; flex-direction:column; gap:18px; min-width:0; }
.review-summary { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; padding:18px 20px; margin-bottom:20px; border:1px solid #dbe4ee; border-radius:12px; background:#fff; }
.review-summary h2 { margin:0 0 8px; color:#0f172a; font-size:21px; }
.review-summary-meta { display:flex; flex-wrap:wrap; gap:8px 16px; color:#64748b; font-size:12px; }
.review-summary-meta strong { color:#334155; }
.review-status { flex:0 0 auto; padding:6px 11px; border-radius:999px; font-size:11px; font-weight:750; background:#dcfce7; color:#166534; }
.review-status.wait { background:#fef3c7; color:#92400e; }
.review-status.bad { background:#fee2e2; color:#991b1b; }
.review-description { margin:7px 0 0; color:#64748b; font-size:12px; line-height:1.55; }
.review-fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px 16px; }
.review-field { min-width:0; display:flex; flex-direction:column; gap:7px; }
.review-field.wide { grid-column:1 / -1; }
.review-field-head { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }
.review-field-head label { font-size:11px; font-weight:750; color:#475569; text-transform:uppercase; letter-spacing:.035em; }
.review-field input,.review-field textarea { width:100%; min-width:0; border:1px solid #cbd5e1; border-radius:8px; background:#fff; padding:10px 12px; font-size:13px; color:#0f172a; outline:none; }
.review-field input { min-height:38px; }
.review-field textarea { min-height:80px; resize:vertical; }
.review-field input:focus,.review-field textarea:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.review-value { min-height:38px; padding:10px 12px; overflow-wrap:anywhere; white-space:pre-wrap; border:1px solid #e2e8f0; border-radius:8px; background:#f8fafc; color:#334155; font-size:13px; }
.review-value.empty { color:#94a3b8; font-style:italic; }
.review-needs-fix { display:inline-flex; gap:6px; align-items:center; padding:4px 7px; border:1px solid #fed7aa; background:#fff7ed; border-radius:6px; font-size:10px; font-weight:700; color:#9a3412; cursor:pointer; text-transform:none; letter-spacing:0; }
.review-needs-fix input { width:auto; min-height:auto; margin:0; accent-color:#ea580c; }
.review-field.marked .review-value,.review-field.marked input,.review-field.marked textarea { border-color:#fb923c; background:#fff7ed; }
.review-field.open .review-value { border-color:#f59e0b; background:#fffbeb; }
.review-alert { border:1px solid #fecaca; background:#fff7f7; border-radius:10px; padding:14px 16px; margin-bottom:18px; color:#7f1d1d; }
.review-alert strong { display:block; margin-bottom:5px; font-size:13px; }
.review-alert p { margin:0; font-size:12px; line-height:1.6; white-space:pre-wrap; }
.review-chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
.review-chip { display:inline-flex; background:#ffedd5; color:#9a3412; border-radius:999px; padding:4px 8px; font-size:10px; font-weight:700; }
.review-panel-badge { display:inline-block; font-size:10px; font-weight:750; color:#166534; background:#dcfce7; border-radius:999px; padding:5px 9px; margin-bottom:10px; text-transform:uppercase; letter-spacing:.04em; }
.review-panel-badge.amber { background:#fef3c7; color:#92400e; }
.review-panel h3 { margin:0 0 5px; font-size:17px; color:#0f172a; }
.review-panel p { color:#64748b; font-size:12px; line-height:1.6; }
.review-panel label.review-input-label { display:flex; flex-direction:column; gap:7px; margin-top:14px; font-size:11px; font-weight:750; color:#475569; text-transform:uppercase; letter-spacing:.03em; }
.review-panel textarea { width:100%; border:1px solid #cbd5e1; border-radius:8px;background: #fff; padding:10px 12px; resize:vertical; font-size:13px; color:#0f172a; text-transform:none; letter-spacing:normal; font-weight:400; }
.review-actions { display:flex; flex-direction:column; gap:9px; margin-top:16px; }
.review-actions .btn-primary,.review-actions .btn-secondary,.review-actions .btn-danger { width:100%; min-height:40px; }
.review-danger-note { background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:8px; padding:10px 12px; font-size:11px; line-height:1.5; margin-top:12px; }
.review-history-toggle { display:flex; align-items:center; justify-content:space-between; width:100%; background:#f8fafc; border:0; border-bottom:1px solid #e2e8f0; padding:15px 18px; cursor:pointer; color:#0f172a; font-size:13px; font-weight:750; }
.review-history-list { margin:0; padding:16px 18px 18px 30px; display:flex; flex-direction:column; gap:15px; }
.review-history-item { padding-left:8px; border-left:2px solid #cbd5e1; }
.review-history-head { display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:6px; }
.review-history-head strong { font-size:12px; color:#0f172a; }
.review-history-head time,.review-history-actor { font-size:10px; color:#64748b; }
.review-history-reason { white-space:pre-wrap; overflow-wrap:anywhere; margin:8px 0 0; font-size:12px; line-height:1.6; color:#475569; }
.review-history-diff { margin-top:8px; display:grid; gap:5px; }
.review-diff-row { background:#f8fafc; border:1px solid #e2e8f0; border-radius:7px; padding:7px 9px; font-size:11px; overflow-wrap:anywhere; }
.review-diff-row del { color:#b91c1c; display:block; margin-top:3px; }
.review-diff-row ins { color:#166534; display:block; margin-top:3px; text-decoration:none; }
.review-empty { border:1px dashed #cbd5e1; border-radius:9px; padding:20px; color:#64748b; text-align:center; font-size:12px; }
.review-error { border:1px solid #fecaca; background:#fef2f2; color:#991b1b; padding:12px 14px; border-radius:9px; font-size:12px; margin-bottom:16px; }
.review-loading { display:flex; gap:10px; align-items:center; padding:26px; color:#64748b; background:#fff; border:1px solid #e2e8f0; border-radius:12px; }
@media(max-width:1050px) { .review-layout { grid-template-columns:1fr; } }
@media(max-width:640px) { .review-page { padding:12px; } .review-summary { flex-direction:column; } .review-fields { grid-template-columns:1fr; } .review-field.wide { grid-column:auto; } .app-header { align-items:flex-start; gap:12px; flex-wrap:wrap; } }


/* Reject permanently dialog */
.reject-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.65); display: grid; place-items: center; z-index: 3000; padding: 20px; animation: reject-fade .15s ease-out; }
.reject-dialog { width: min(480px, 100%); background: #fff; border-radius: 14px; padding: 26px; box-shadow: 0 24px 48px rgba(0,0,0,.35); animation: reject-pop .18s ease-out; }
.reject-icon { width: 44px; height: 44px; border-radius: 50%; background: #fee2e2; color: #b91c1c; font-weight: 800; font-size: 22px; display: grid; place-items: center; margin-bottom: 12px; }
.reject-dialog h3 { margin: 0 0 4px; font-size: 18px; color: #0f172a; }
.reject-sub { margin: 0 0 12px; font-size: 12px; color: #64748b; }
.reject-points { margin: 0 0 14px; padding-left: 18px; font-size: 12px; line-height: 1.7; color: #475569; }
.reject-reason { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; margin-bottom: 14px; }
.reject-reason span { font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b; letter-spacing: .04em; }
.reject-reason p { margin: 4px 0 0; font-size: 12px; color: #0f172a; white-space: pre-wrap; overflow-wrap: anywhere; }
.reject-ack { display: flex; gap: 8px; align-items: center; font-size: 12px; color: #7f1d1d; font-weight: 600; margin-bottom: 16px; cursor: pointer; }
.reject-actions { display: flex; justify-content: flex-end; gap: 10px; }
.reject-actions .btn-secondary { padding: 0 18px; }
.reject-confirm { height: 38px; padding: 0 18px; border: 0; border-radius: 8px; background: #b91c1c; color: #fff; font-weight: 700; font-size: 12px; cursor: pointer; transition: transform .15s ease, filter .15s ease; }
.reject-confirm:not(:disabled):hover { filter: brightness(1.1); transform: translateY(-1px); }
.reject-confirm:not(:disabled):active { transform: translateY(1px) scale(.97); }
.reject-confirm:disabled { opacity: .45; cursor: not-allowed; }
@keyframes reject-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes reject-pop { from { opacity: 0; transform: scale(.96); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .reject-overlay, .reject-dialog { animation: none; } }
/* Record preview */
.preview-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.6); display: grid; place-items: center; z-index: 2500; padding: 20px; overflow-y: auto; }
.preview-card { width: min(640px, 100%); max-height: 90vh; overflow-y: auto; background: #fff; border-radius: 14px; padding: 26px 28px; box-shadow: 0 24px 48px rgba(0,0,0,.3); border-top: 6px solid #1ea253; }
.preview-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.preview-tag { font-size: 10px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: #166534; background: #dcfce7; padding: 4px 10px; border-radius: 99px; }
.preview-close { background: none; border: 0; font-size: 24px; line-height: 1; color: #64748b; cursor: pointer; }
.preview-title { margin: 0 0 4px; font-size: 24px; color: #0f172a; overflow-wrap: anywhere; }
.preview-author { margin: 0 0 12px; font-size: 14px; color: #475569; }
.preview-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.preview-meta span { font-size: 11px; color: #334155; background: #f1f5f9; border-radius: 99px; padding: 4px 10px; }
.preview-rows { margin: 0 0 14px; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.preview-row { display: grid; grid-template-columns: 170px 1fr; gap: 12px; padding: 9px 14px; border-bottom: 1px solid #eef2f7; font-size: 13px; }
.preview-row:last-child { border-bottom: 0; }
.preview-row dt { color: #64748b; font-weight: 600; }
.preview-row dd { margin: 0; color: #0f172a; overflow-wrap: anywhere; }
.preview-block { margin-bottom: 12px; padding: 10px 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; }
.preview-block p { margin: 4px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; color: #334155; }
.preview-reject { background: #fff7f7; border-color: #fecaca; color: #7f1d1d; }
.preview-hint { font-size: 11px; color: #92400e; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 8px 12px; }
.preview-footer { display: flex; justify-content: flex-end; margin-top: 10px; }
.preview-footer .btn-secondary { padding: 0 18px; }
@media (max-width: 560px) { .preview-row { grid-template-columns: 1fr; gap: 2px; } }
.review-field select { width:100%; min-width:0; min-height:38px; border:1px solid #cbd5e1; border-radius:8px; background:#fff; padding:9px 12px; font-size:13px; color:#0f172a; outline:none; cursor:pointer; }
.review-field select:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.review-field.marked select { border-color:#fb923c; background:#fff7ed; }</style>
