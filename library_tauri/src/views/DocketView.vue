<template>
  <div class="dk">
    <header class="dk-head">
      <div>
        <p class="dk-org">Athenaeum Orbis</p>
        <h1>Docket</h1>
        <p class="dk-sub">
          {{ user_role === 'The Keeper'
            ? 'Follow each submission from review to the shelf, and fix anything sent back.'
            : 'Work through matters waiting for your decision, one at a time.' }}
        </p>
      </div>
      <button type="button" class="dk-btn" :disabled="loading" @click="loadAll">
        {{ loading ? 'Syncing…' : 'Refresh' }}
      </button>
    </header>

    <div v-if="error" class="dk-msg dk-msg-error" role="alert">
      <span>{{ error }}</span>
      <button type="button" aria-label="Dismiss" @click="error = ''">×</button>
    </div>
    <div v-if="notice" class="dk-msg dk-msg-ok" role="status">
      <span>{{ notice }}</span>
      <button type="button" aria-label="Dismiss" @click="notice = ''">×</button>
    </div>

    <!-- ============ THE CHIEF: REVIEW DESK ============ -->
    <section v-if="user_role === 'The Chief'" class="cd">
      <div v-if="loading && !docketMatters.length" class="dk-empty">
        <div class="dk-spin"></div>
        <strong>Loading matters…</strong>
      </div>

      <div v-else-if="!deskMatter" class="dk-empty">
        <strong>All clear</strong>
        <span>
          {{ decidedCount ? `You decided ${decidedCount} ${decidedCount === 1 ? 'matter' : 'matters'} this session. ` : '' }}New matters will appear here when they need a decision.
        </span>
      </div>

      <template v-else>
        <div class="cd-progress">
          <div class="cd-bar"><span :style="{ width: (decidedCount + deskQueue.length ? (decidedCount / (decidedCount + deskQueue.length)) * 100 : 0) + '%' }"></span></div>
          <p><strong>{{ deskQueue.length }}</strong> waiting · <strong>{{ decidedCount }}</strong> decided this session</p>
        </div>

        <div class="cd-grid">
          <ol class="cd-rail" aria-label="Waiting matters">
            <li v-for="(m, i) in deskQueue" :key="m.key">
              <button type="button" class="cd-chip" :class="[`age-${ageTone(m.since)}`, { on: i === deskPos }]" :aria-current="i === deskPos" @click="deskPick(i)">
                <small>{{ m.type === 'WORK' ? 'Work' : 'Item' }} #{{ m.type === 'WORK' ? m.work_id : m.serial_no }}</small>
                <span>{{ m.title || 'Untitled' }}</span>
                <em class="cd-age-txt">{{ ageLabel(m.since) }}</em>
              </button>
            </li>
          </ol>

          <article class="cd-card">
            <div class="cd-nav">
              <span class="cd-kind">{{ deskMatter.type === 'WORK' ? 'Work' : 'Item' }} #{{ deskMatter.type === 'WORK' ? deskMatter.work_id : deskMatter.serial_no }}</span>
              <span class="cd-pos">{{ deskPos + 1 }} of {{ deskQueue.length }}</span>
              <span v-if="deskMatter.since" class="cd-age" :class="`age-${ageTone(deskMatter.since)}`">{{ ageLabel(deskMatter.since) }}</span>
              <span class="cd-arrows">
                <button type="button" class="dk-btn" :disabled="deskPos <= 0" aria-label="Previous matter" @click="deskGo(-1)">←</button>
                <button type="button" class="dk-btn" :disabled="deskPos >= deskQueue.length - 1" aria-label="Next matter" @click="deskGo(1)">→</button>
              </span>
            </div>

            <h2>{{ deskMatter.title || 'Untitled' }}</h2>

            <dl class="cd-fields">
              <div v-for="f in deskFields" :key="f[0]"><dt>{{ f[0] }}</dt><dd>{{ f[1] }}</dd></div>
            </dl>

            <div class="dk-note" v-if="deskMatter.proposal_reason">
              <h3>Why this was proposed</h3>
              <p>{{ deskMatter.proposal_reason }}</p>
            </div>
            <div class="dk-note" v-else-if="deskMatter.type === 'ITEM'">
              <h3>Copy of Work #{{ deskMatter.work_id }}</h3>
              <p>This item is a physical copy waiting to be added to the catalogue.</p>
            </div>

            <div v-if="deskResubmission" class="cd-resub">
              <h3>
                Resubmitted after correction
                <small>{{ fmtWhen(deskResubmission.at) }}<template v-if="deskResubmission.actor"> by {{ deskResubmission.actor }}</template></small>
              </h3>
              <p v-if="deskResubmission.rejection" class="cd-was">
                {{ deskResubmission.rejection.actor || 'The Chief' }} sent it back: {{ deskResubmission.rejection.reason }}
              </p>
              <ul v-if="deskResubmission.rows.length" class="dk-diff">
                <li v-for="row in deskResubmission.rows" :key="row.field">
                  <span class="dk-diff-l">{{ row.label }}</span>
                  <del>{{ showValue(row.from) }}</del>
                  <ins>{{ showValue(row.to) }}</ins>
                </li>
              </ul>
              <p v-else-if="deskResubmission.isItem" class="cd-was">This item was resubmitted without edits.</p>
              <p v-else-if="!deskResubmission.recorded" class="cd-was">The changed fields were not recorded for this resubmission.</p>
              <p v-else class="cd-was">No fields were changed since it was sent back.</p>
            </div>

            <div class="cd-decide">
              <button type="button" class="dk-btn dk-btn-main cd-big" @click="openItemReview(deskMatter)">
                Open full review form <kbd>A</kbd>
              </button>
            </div>

            <p class="cd-keys"><kbd>J</kbd> next · <kbd>K</kbd> previous · <kbd>A</kbd> open the review form</p>
          </article>
        </div>
      </template>
    </section>

    <!-- ============ THE KEEPER: SUBMISSION TRACKER ============ -->
    <template v-else>
      <nav class="dk-tabs" aria-label="Docket views">
        <button
          v-for="t in [
            { id: 'ATTENTION', label: 'Sent back', n: attentionCount, cls: 'attn' },
            { id: 'IN_PROGRESS', label: 'In review', n: inProgressCount, cls: 'prog' },
            { id: 'RESOLVED', label: 'Completed', n: resolvedCount, cls: 'done' }
          ]"
          :key="t.id"
          type="button"
          class="dk-tab"
          :class="[t.cls, { on: activeDocketFilter === t.id }]"
          :aria-pressed="activeDocketFilter === t.id"
          @click="selectDocketFilter(t.id)"
        >
          <strong>{{ t.n }}</strong>
          <span>{{ t.label }}</span>
        </button>
      </nav>

      <div class="dk-bar">
        <span>
          {{ visibleDocketMatters.length ? `${docketPageStart}–${docketPageEnd} of ${visibleDocketMatters.length}` : 'Nothing here' }}
        </span>
        <label class="dk-sort">
          Sort by
          <select :value="docketSort" @change="changeDocketSort($event.target.value)">
            <option value="NEWEST">Newest first</option>
            <option value="OLDEST">Oldest first</option>
            <option value="PRIORITY">Priority</option>
            <option value="WORK">Work ID</option>
            <option value="ITEM">Item no.</option>
          </select>
        </label>
      </div>

      <div v-if="loading && !docketMatters.length" class="dk-empty">
        <div class="dk-spin"></div>
        <strong>Loading your submissions…</strong>
      </div>

      <div v-else-if="!paginatedDocketMatters.length" class="dk-empty">
        <strong>
          {{ activeDocketFilter === 'ATTENTION' ? 'Nothing was sent back'
            : activeDocketFilter === 'IN_PROGRESS' ? 'Nothing is in review'
            : 'No completed submissions yet' }}
        </strong>
        <span>Your submissions show up here as their status changes.</span>
      </div>

      <ul v-else class="kt-list">
        <li v-for="matter in paginatedDocketMatters" :key="matter.key" class="kt-card" :class="[`s-${String(matter.status || '').toLowerCase()}`, ageClassFor(matter)]">
          <div class="kt-top">
            <div>
              <span class="kt-ref">{{ matter.type === 'WORK' ? 'Work' : 'Item' }} #{{ matter.type === 'WORK' ? matter.work_id : matter.serial_no }}</span>
              <h2>{{ matter.title || 'Untitled' }}</h2>
              <p class="kt-meta">
                <span v-if="matter.author">{{ matter.author }}</span>
                <span v-if="matter.language">{{ matter.language }}</span>
                <span v-if="matter.category">{{ matter.category }}</span>
                <span v-if="matter.accession_no">Accession {{ matter.accession_no }}</span>
                <span v-if="ageClassFor(matter)">{{ ageLabel(matter.since) }}</span>
              </p>
            </div>
            <span class="dk-pill">{{ matter.status }}</span>
          </div>

          <ol class="kt-steps" aria-label="Progress">
            <li v-for="s in trackerSteps(matter)" :key="s.label" :class="s.state">
              <i aria-hidden="true"></i><span>{{ s.label }}</span>
            </li>
          </ol>

          <div v-if="matter.approval_reason" class="kt-msg" :class="{ bad: matter.status === 'REJECTED' }">
            <h3>{{ matter.status === 'REJECTED' ? 'Sent back with this note from The Chief' : 'Note from The Chief' }}</h3>
            <p>{{ matter.approval_reason }}</p>
          </div>

          <div class="kt-history">
            <button type="button" class="dk-link" :aria-expanded="!!historyOpen[matter.key]" @click="toggleHistory(matter)">
              {{ historyOpen[matter.key] ? 'Hide history' : 'Show history' }}
            </button>

            <template v-if="historyOpen[matter.key]">
              <p v-if="historyLoading[matter.key]" class="kt-hint">Loading history…</p>
              <p v-else-if="historyFailed[matter.key]" class="kt-hint">History is unavailable right now. Try Refresh.</p>
              <p v-else-if="!(historyCache[matter.key] || []).length" class="kt-hint">No history has been recorded for this matter.</p>
              <ol v-else class="tl">
                <li v-for="event in historyCache[matter.key]" :key="event.id" :class="event.type.toLowerCase()">
                  <i aria-hidden="true"></i>
                  <div>
                    <p class="tl-head">
                      <strong>{{ EVENT_TITLES[event.type] || event.type }}</strong>
                      <span v-if="event.actor"> by {{ event.actor }}</span>
                      <time>{{ fmtWhen(event.at) }}</time>
                    </p>
                    <p v-if="event.reason" class="tl-reason">{{ event.reason }}</p>
                    <p v-if="event.flagged_fields && event.flagged_fields.length" class="tl-chips">
                      Marked for correction:
                      <span v-for="f in event.flagged_fields" :key="f" class="tl-chip">{{ FLAG_LABELS[f] || f }}</span>
                    </p>
                    <p v-if="event.correction_note" class="tl-reason tl-note">Correction note: {{ event.correction_note }}</p>
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
          </div>

          <div v-if="matter.status === 'REJECTED'" class="dk-actions">
            <button type="button" class="dk-btn dk-btn-main" @click="openItemReview(matter)">
              Open correction form
            </button>
          </div>
        </li>
      </ul>

      <div v-if="docketTotalPages > 1" class="dk-pager">
        <button type="button" class="dk-btn" :disabled="docketPage <= 1" @click="changeDocketPage(docketPage - 1)">Previous</button>
        <span>Page {{ docketPage }} of {{ docketTotalPages }}</span>
        <button type="button" class="dk-btn" :disabled="docketPage >= docketTotalPages" @click="changeDocketPage(docketPage + 1)">Next</button>
      </div>
    </template>
    <div v-if="pendingSend" class="dk-toast" role="status">
      <span class="dk-toast-bar" :style="{ width: (pendingSend.left / 8) * 100 + '%' }"></span>
      <span class="dk-toast-text">
        {{ pendingSend.action === 'APPROVE' ? 'Approving' : 'Rejecting' }} {{ pendingSend.name }} in {{ pendingSend.left }}s
      </span>
      <button type="button" class="dk-btn" @click="undoPending">Undo <kbd>U</kbd></button>
    </div>
  </div>
</template>






<script setup>

import {

  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch

} from 'vue'



import axios from 'axios'

import { useRoute, useRouter } from 'vue-router'

import { storeToRefs } from 'pinia'

import { useAuthStore } from '@/stores/auth'



const authStore = useAuthStore()

const { userRole: user_role } = storeToRefs(authStore)

const router = useRouter()

const route = useRoute()





const pendingWorks = ref([])

const pendingItems = ref([])



const loading = ref(false)

const busy = ref(false)



const error = ref('')

const notice = ref('')








const totalMatters = computed(

  () =>

    pendingWorks.value.length +

    pendingItems.value.length

)



  const activeDocketFilter = ref('ATTENTION')
const docketSort = ref('NEWEST')
const docketPage = ref(1)
const docketPageSize = 12
const expandedMatterKey = ref(null)
const docketFilterWasSelected = ref(false)

function sinceTime(since) {
  const t = new Date(since).getTime()
  return Number.isNaN(t) ? 0 : t
}

// Yellow = fresh, then amber, orange and red as a matter waits longer.
function ageTone(since) {
  const days = (Date.now() - sinceTime(since)) / 86400000
  if (!sinceTime(since) || days < 1) return 'a1'
  if (days < 3) return 'a2'
  if (days < 7) return 'a3'
  return 'a4'
}

function ageLabel(since) {
  if (!sinceTime(since)) return ''
  const hours = Math.floor((Date.now() - sinceTime(since)) / 3600000)
  if (hours < 1) return 'Just arrived'
  if (hours < 24) return `${hours}h waiting`
  const days = Math.floor(hours / 24)
  return `${days} ${days === 1 ? 'day' : 'days'} waiting`
}

function ageClassFor(matter) {
  return ['REJECTED', 'PENDING'].includes(matter.status) && matter.since
    ? `age-${ageTone(matter.since)}`
    : ''
}

function matterKey(type, identifier) {
  return `${type}:${identifier}`
}

function matterPriority(status) {
  if (status === 'REJECTED') return 0
  if (status === 'PENDING') return 1
  if (status === 'AVAILABLE' || status === 'APPROVED') return 2
  return 3
}

function makeKeeperMatters(rows) {
  const matters = []
  const seen = new Set()

  for (const row of rows) {
    let matter = null

    if (row.work_status === 'REJECTED') {
      const key = matterKey('WORK', row.work_id)
      if (seen.has(key)) continue
      seen.add(key)
      matter = {
        key,
        type: 'WORK',
        work_id: row.work_id,
        serial_no: row.serial_no,
        accession_no: row.accession_no,
        title: row.title,
        author: row.author,
        category: row.category,
        language: row.language,
        publisher: row.publisher,
        year: row.year,
        isbn: row.isbn,
        ddc: row.ddc,
        call_no: row.call_no,
        translation_compilation: row.translation_compilation,
        genre: row.genre,
        original_language: row.original_language,
        notes: row.notes,
        proposal_reason: row.proposal_reason,
        approval_reason: row.approval_reason,
        status: 'REJECTED',
        item_status: row.item_status,
        item_is_deleted: row.item_is_deleted
      }
    } else if (row.item_status === 'REJECTED') {
      const key = matterKey('ITEM', row.serial_no)
      if (seen.has(key)) continue
      seen.add(key)
      matter = {
        key,
        type: 'ITEM',
        work_id: row.work_id,
        serial_no: row.serial_no,
        accession_no: row.accession_no,
        title: row.title,
        author: row.author,
        category: row.category,
        language: row.language,
        status: 'REJECTED',
        item_status: row.item_status,
        item_is_deleted: row.item_is_deleted,
        approval_reason: row.approval_reason
      }
    } else if (row.work_status === 'PENDING') {
      const key = matterKey('WORK', row.work_id)
      if (seen.has(key)) continue
      seen.add(key)
      matter = {
        key,
        type: 'WORK',
        work_id: row.work_id,
        serial_no: row.serial_no,
        accession_no: row.accession_no,
        title: row.title,
        author: row.author,
        category: row.category,
        language: row.language,
        publisher: row.publisher,
        year: row.year,
        isbn: row.isbn,
        ddc: row.ddc,
        call_no: row.call_no,
        translation_compilation: row.translation_compilation,
        genre: row.genre,
        original_language: row.original_language,
        notes: row.notes,
        proposal_reason: row.proposal_reason,
        approval_reason: row.approval_reason,
        status: 'PENDING',
        item_status: row.item_status,
        item_is_deleted: row.item_is_deleted
      }
    } else if (row.item_status === 'PENDING') {
      const key = matterKey('ITEM', row.serial_no)
      if (seen.has(key)) continue
      seen.add(key)
      matter = {
        key,
        type: 'ITEM',
        work_id: row.work_id,
        serial_no: row.serial_no,
        accession_no: row.accession_no,
        title: row.title,
        author: row.author,
        category: row.category,
        language: row.language,
        status: 'PENDING',
        item_status: row.item_status,
        item_is_deleted: row.item_is_deleted,
        approval_reason: row.approval_reason
      }
    } else if (row.item_status === 'AVAILABLE' || row.work_status === 'APPROVED') {
      const key = row.serial_no
        ? matterKey('ITEM', row.serial_no)
        : matterKey('WORK', row.work_id)
      if (seen.has(key)) continue
      seen.add(key)
      matter = {
        key,
        type: row.serial_no ? 'ITEM' : 'WORK',
        work_id: row.work_id,
        serial_no: row.serial_no,
        accession_no: row.accession_no,
        title: row.title,
        author: row.author,
        category: row.category,
        language: row.language,
        status: row.serial_no ? 'AVAILABLE' : 'APPROVED',
        item_status: row.item_status,
        item_is_deleted: row.item_is_deleted
      }
    }

    if (matter) matter.since = matter.type === 'ITEM'
      ? (row.item_created_at || row.work_created_at)
      : (row.work_created_at || row.item_created_at)
    matters.push(matter)
  }

  return matters
}

const keeperMatters = computed(() => makeKeeperMatters(pendingWorks.value))

const chiefMatters = computed(() => [
  ...pendingWorks.value.map((work) => ({
    key: matterKey('WORK', work.work_id),
    type: 'WORK',
    work_id: work.work_id,
    serial_no: work.serial_no,
    accession_no: work.accession_no,
    title: work.title,
    author: work.author,
    category: work.category,
    language: work.language,
    publisher: work.publisher,
    year: work.year,
    isbn: work.isbn,
    ddc: work.ddc,
    call_no: work.call_no,
    proposal_reason: work.proposal_reason,
    approval_reason: work.approval_reason,
    since: work.waiting_since || work.created_at,
    status: 'PENDING'
  })),
  ...pendingItems.value.map((item) => ({
    key: matterKey('ITEM', item.serial_no),
    type: 'ITEM',
    work_id: item.work_id,
    serial_no: item.serial_no,
    accession_no: item.accession_no,
    title: item.title,
    author: item.author,
    category: item.category,
    language: item.language,
    since: item.waiting_since || item.created_at,
    status: 'PENDING'
  }))
])

const docketMatters = computed(() =>
  user_role.value === 'The Keeper' ? keeperMatters.value : chiefMatters.value
)

const attentionMatters = computed(() =>
  user_role.value === 'The Keeper'
    ? docketMatters.value.filter((matter) => matter.status === 'REJECTED')
    : docketMatters.value.filter((matter) => matter.status === 'PENDING')
)

const inProgressMatters = computed(() =>
  user_role.value === 'The Keeper'
    ? docketMatters.value.filter((matter) => matter.status === 'PENDING')
    : []
)

const resolvedMatters = computed(() =>
  user_role.value === 'The Keeper'
    ? docketMatters.value.filter(
        (matter) => matter.status === 'AVAILABLE' || matter.status === 'APPROVED'
      )
    : []
)

const visibleDocketMatters = computed(() => {
  let matters = docketMatters.value

  if (activeDocketFilter.value === 'ATTENTION') matters = attentionMatters.value
  if (activeDocketFilter.value === 'IN_PROGRESS') matters = inProgressMatters.value
  if (activeDocketFilter.value === 'RESOLVED') matters = resolvedMatters.value

  return [...matters].sort((a, b) => {
    if (docketSort.value === 'NEWEST') {
      return sinceTime(b.since) - sinceTime(a.since) || Number(b.work_id || 0) - Number(a.work_id || 0)
    }

    if (docketSort.value === 'OLDEST') {
      return sinceTime(a.since) - sinceTime(b.since) || Number(a.work_id || 0) - Number(b.work_id || 0)
    }

    if (docketSort.value === 'WORK') {
      return Number(a.work_id || 0) - Number(b.work_id || 0)
    }

    if (docketSort.value === 'ITEM') {
      return String(a.serial_no || '').localeCompare(
        String(b.serial_no || ''),
        undefined,
        { numeric: true, sensitivity: 'base' }
      )
    }

    return matterPriority(a.status) - matterPriority(b.status) ||
      Number(a.work_id || 0) - Number(b.work_id || 0) ||
      String(a.serial_no || '').localeCompare(
        String(b.serial_no || ''),
        undefined,
        { numeric: true, sensitivity: 'base' }
      )
  })
})

const docketTotalPages = computed(() =>
  Math.max(1, Math.ceil(visibleDocketMatters.value.length / docketPageSize))
)

const paginatedDocketMatters = computed(() => {
  const start = (docketPage.value - 1) * docketPageSize
  return visibleDocketMatters.value.slice(start, start + docketPageSize)
})

const docketPageStart = computed(() =>
  visibleDocketMatters.value.length
    ? (docketPage.value - 1) * docketPageSize + 1
    : 0
)

const docketPageEnd = computed(() =>
  Math.min(docketPage.value * docketPageSize, visibleDocketMatters.value.length)
)

const attentionCount = computed(() => attentionMatters.value.length)
const inProgressCount = computed(() => inProgressMatters.value.length)
const resolvedCount = computed(() => resolvedMatters.value.length)

function selectDocketFilter(filter) {
  activeDocketFilter.value = filter
  docketFilterWasSelected.value = true
  docketPage.value = 1
  expandedMatterKey.value = null
}

function changeDocketSort(sort) {
  docketSort.value = sort
  docketPage.value = 1
}

function changeDocketPage(page) {
  docketPage.value = Math.min(Math.max(1, page), docketTotalPages.value)
  expandedMatterKey.value = null
}

function toggleMatter(matter) {
  expandedMatterKey.value =
    expandedMatterKey.value === matter.key ? null : matter.key
}

function setDefaultDocketFilter() {
  if (docketFilterWasSelected.value) return

  if (user_role.value === 'The Keeper') {
    if (attentionCount.value > 0) activeDocketFilter.value = 'ATTENTION'
    else if (inProgressCount.value > 0) activeDocketFilter.value = 'IN_PROGRESS'
    else activeDocketFilter.value = 'RESOLVED'
  } else {
    activeDocketFilter.value =
      attentionCount.value > 0
        ? 'ATTENTION'
        : inProgressCount.value > 0
          ? 'IN_PROGRESS'
          : 'RESOLVED'
  }

  docketPage.value = 1
  expandedMatterKey.value = null
}

async function loadAll() {

  loading.value = true
  historyCache.value = {}

  error.value = ''



  try {

            if (user_role.value === 'The Keeper') {

          const response = await axios.get('/catalogue/my-submissions')



          pendingWorks.value =

            Array.isArray(response.data)

              ? response.data

              : []



          pendingItems.value = []

          setDefaultDocketFilter()

          return

        }



        if (user_role.value !== 'The Chief') {

          pendingWorks.value = []

          pendingItems.value = []

          return

        }



    const [

      worksRes,

      itemsRes

    ] = await Promise.all([

      axios.get('/catalogue/pending-works'),

      axios.get('/catalogue/pending-items')

    ])





    pendingWorks.value =

      Array.isArray(worksRes.data)

        ? worksRes.data

        : []





    pendingItems.value =

      Array.isArray(itemsRes.data)

        ? itemsRes.data

        : []

    setDefaultDocketFilter()



  } catch (err) {



    console.error(

      'Docket load failed:',

      err

    )



    error.value =

      err.response?.data?.detail ||

      'Unable to load the Docket.'



  } finally {



    loading.value = false



  }

}













/* ---------- Matter history (read from the audit ledger) ---------- */
const historyCache = ref({})
const historyLoading = ref({})
const historyFailed = ref({})
const historyOpen = ref({})

const FIELD_LABELS = {
  title: 'Title',
  author: 'Author',
  category: 'Category',
  language: 'Language',
  publisher: 'Publisher',
  year: 'Year',
  isbn: 'ISBN',
  ddc: 'DDC',
  call_no: 'Call no.',
  translation_compilation: 'Translation / compilation',
  genre: 'Genre',
  original_language: 'Original language',
  notes: 'Notes',
  proposal_reason: 'Proposal reason'
}

const EVENT_TITLES = {
  SUBMITTED: 'Submitted',
  APPROVED: 'Approved',
  REJECTED: 'Sent back',
  RESUBMITTED: 'Resubmitted',
  NOTE: 'Note'
}

const FLAG_LABELS = {
  work_id: 'Authorized Work ID',
  language_id: 'Copy language'
}

function historyUrl(matter) {
  return matter.type === 'WORK'
    ? `/catalogue/history/work/${matter.work_id}`
    : `/catalogue/history/item/${matter.serial_no}`
}

async function ensureHistory(matter) {
  const key = matter?.key
  if (!key || historyCache.value[key] || historyLoading.value[key]) return

  historyLoading.value = { ...historyLoading.value, [key]: true }

  try {
    const response = await axios.get(historyUrl(matter))
    historyCache.value = {
      ...historyCache.value,
      [key]: Array.isArray(response.data) ? response.data : []
    }
    historyFailed.value = { ...historyFailed.value, [key]: false }
  } catch (err) {
    console.error('History load failed:', err)
    historyCache.value = { ...historyCache.value, [key]: [] }
    historyFailed.value = { ...historyFailed.value, [key]: true }
  } finally {
    const next = { ...historyLoading.value }
    delete next[key]
    historyLoading.value = next
  }
}

function toggleHistory(matter) {
  const open = !historyOpen.value[matter.key]
  historyOpen.value = { ...historyOpen.value, [matter.key]: open }
  if (open) ensureHistory(matter)
}

function diffRows(changes) {
  return Object.entries(changes || {}).map(([field, value]) => ({
    field,
    label: FIELD_LABELS[field] || field,
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
    : date.toLocaleString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
}

/* ---------- Chief review desk ---------- */
const deskIndex = ref(0)
const decidedCount = ref(0)
const deciding = ref(null)
const decisionReason = ref('')
const reasonBox = ref(null)

// Decisions wait a few seconds before they are sent, so they can be undone.
const PENDING_SECONDS = 8
const hiddenKeys = ref([])
const pendingSend = ref(null)
let pendingTimer = null

const deskQueue = computed(() =>
  user_role.value === 'The Chief'
    ? attentionMatters.value
        .filter((matter) => !hiddenKeys.value.includes(matter.key))
        .sort(
          (a, b) =>
            sinceTime(b.since) - sinceTime(a.since) ||
            Number(b.work_id || 0) - Number(a.work_id || 0) ||
            String(b.serial_no || '').localeCompare(String(a.serial_no || ''), undefined, { numeric: true })
        )
    : []
)

const deskPos = computed(() =>
  Math.min(deskIndex.value, Math.max(0, deskQueue.value.length - 1))
)

const deskMatter = computed(() => deskQueue.value[deskPos.value] || null)

const deskFields = computed(() => {
  const m = deskMatter.value
  if (!m) return []
  return [
    ['Author', m.author],
    ['Category', m.category],
    ['Language', m.language],
    ['Publisher', m.publisher],
    ['Year', m.year],
    ['ISBN', m.isbn],
    ['DDC', m.ddc],
    ['Call no.', m.call_no],
    ['Work ID', m.work_id ? `#${m.work_id}` : ''],
    ['Item no.', m.serial_no ? `#${m.serial_no}` : ''],
    ['Accession no.', m.accession_no]
  ].filter(([, value]) => value)
})

// If the latest event is a resubmission, show what the Keeper changed.
const deskResubmission = computed(() => {
  const m = deskMatter.value
  const events = m ? historyCache.value[m.key] || [] : []
  const last = events[events.length - 1]
  if (!last || last.type !== 'RESUBMITTED') return null

  const rejection = [...events].reverse().find((event) => event.type === 'REJECTED') || null

  return {
    at: last.at,
    actor: last.actor,
    rows: diffRows(last.changes),
    recorded: last.changes !== null && last.changes !== undefined,
    isItem: m.type === 'ITEM',
    rejection
  }
})

watch(
  [() => deskMatter.value?.key, historyCache],
  () => {
    if (deskMatter.value) ensureHistory(deskMatter.value)
  },
  { immediate: true }
)

function deskGo(step) {
  if (!deskQueue.value.length) return
  cancelDecision()
  deskIndex.value = Math.min(Math.max(0, deskPos.value + step), deskQueue.value.length - 1)
}

function deskPick(index) {
  cancelDecision()
  deskIndex.value = index
}

function openItemReview(matter) {
  if (!matter) return
  if (matter.type === 'WORK') {
    router.push(`/review-work/${matter.work_id}`)
    return
  }
  if (matter.serial_no) router.push(`/review-item/${matter.serial_no}`)
}

function startDecision(action) {
  if (!deskMatter.value || busy.value) return
  if (deskMatter.value.type === 'ITEM') {
    openItemReview(deskMatter.value)
    return
  }
  deciding.value = action
  decisionReason.value = ''
  error.value = ''
  nextTick(() => reasonBox.value?.focus())
}

function cancelDecision() {
  deciding.value = null
  decisionReason.value = ''
}

function startPendingTimer() {
  clearInterval(pendingTimer)
  pendingTimer = setInterval(() => {
    if (!pendingSend.value) {
      clearInterval(pendingTimer)
      pendingTimer = null
      return
    }
    pendingSend.value.left -= 1
    if (pendingSend.value.left <= 0) commitPending()
  }, 1000)
}

async function confirmDecision() {
  const matter = deskMatter.value
  const action = deciding.value
  if (!matter || !action) return

  const reason = decisionReason.value.trim()
  if (!reason) {
    error.value = 'A decision reason is required.'
    return
  }

  // Only one decision can wait at a time: send the earlier one first.
  if (pendingSend.value) await commitPending()

  const isWork = matter.type === 'WORK'

  error.value = ''
  notice.value = ''

  hiddenKeys.value = [...hiddenKeys.value, matter.key]
  decidedCount.value += 1
  pendingSend.value = {
    matter,
    action,
    reason,
    isWork,
    name: isWork ? `Work “${matter.title || 'Untitled'}”` : `Item #${matter.serial_no}`,
    left: PENDING_SECONDS
  }

  cancelDecision()
  startPendingTimer()
}

async function commitPending() {
  const pending = pendingSend.value
  if (!pending) return

  clearInterval(pendingTimer)
  pendingTimer = null
  pendingSend.value = null
  busy.value = true

  try {
    await axios.post(
      pending.isWork
        ? `/catalogue/approve/${pending.matter.work_id}`
        : `/catalogue/approve-item/${pending.matter.serial_no}`,
      null,
      { params: { action: pending.action, reason: pending.reason } }
    )

    notice.value = `${pending.name} ${pending.action === 'APPROVE' ? 'approved' : 'rejected'}.`
    await loadAll()
  } catch (err) {
    decidedCount.value = Math.max(0, decidedCount.value - 1)
    error.value =
      err.response?.data?.detail ||
      (pending.isWork ? 'Unable to process the Work decision.' : 'Unable to process the Item decision.')
  } finally {
    hiddenKeys.value = hiddenKeys.value.filter((key) => key !== pending.matter.key)
    busy.value = false
  }
}

function undoPending() {
  const pending = pendingSend.value
  if (!pending) return

  clearInterval(pendingTimer)
  pendingTimer = null
  pendingSend.value = null

  hiddenKeys.value = hiddenKeys.value.filter((key) => key !== pending.matter.key)
  decidedCount.value = Math.max(0, decidedCount.value - 1)

  const index = deskQueue.value.findIndex((matter) => matter.key === pending.matter.key)
  if (index >= 0) deskIndex.value = index

  // Re-open the reason box with the same text so nothing has to be retyped.
  startDecision(pending.action)
  decisionReason.value = pending.reason
  notice.value = 'Decision cancelled. Nothing was sent.'
}

function onBeforeUnload(event) {
  if (pendingSend.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

function onDeskKey(event) {
  if (user_role.value !== 'The Chief') return

  const tag = event.target?.tagName
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
    if (event.key === 'Escape') cancelDecision()
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && deciding.value) confirmDecision()
    return
  }

  if (event.metaKey || event.ctrlKey || event.altKey) return

  const key = event.key.toLowerCase()
  if (key === 'j') deskGo(1)
  else if (key === 'k') deskGo(-1)
  else if (key === 'a') startDecision('APPROVE')
  else if (key === 'r') startDecision('REJECT')
  else if (key === 'u') undoPending()
}

/* ---------- Keeper tracker ---------- */
function trackerSteps(matter) {
  if (matter.status === 'REJECTED') {
    return [
      { label: 'Submitted', state: 'done' },
      { label: 'Reviewed', state: 'done' },
      { label: 'Sent back', state: 'bad' },
      { label: 'On the shelf', state: 'todo' }
    ]
  }
  if (matter.status === 'PENDING') {
    return [
      { label: 'Submitted', state: 'done' },
      { label: 'In review', state: 'now' },
      { label: 'Decision', state: 'todo' },
      { label: 'On the shelf', state: 'todo' }
    ]
  }
  return [
    { label: 'Submitted', state: 'done' },
    { label: 'Reviewed', state: 'done' },
    { label: 'Approved', state: 'done' },
    { label: 'On the shelf', state: 'done' }
  ]
}

// Matters that were sent back open their history automatically.
watch(paginatedDocketMatters, (matters) => {
  if (user_role.value !== 'The Keeper') return

  for (const matter of matters) {
    if (matter.status === 'REJECTED' && historyOpen.value[matter.key] === undefined) {
      historyOpen.value = { ...historyOpen.value, [matter.key]: true }
    }
    if (historyOpen.value[matter.key]) ensureHistory(matter)
  }
})

// Opens the matter named in the link (e.g. from a dashboard alert).
function applyFocusFromRoute() {
  const [type, id] = String(route.query.focus || '').split(':')
  const filter = String(route.query.filter || '').toUpperCase()

  if (user_role.value === 'The Keeper' && ['ATTENTION', 'IN_PROGRESS', 'RESOLVED'].includes(filter)) {
    docketFilterWasSelected.value = true
    activeDocketFilter.value = filter
    docketPage.value = 1
  }

  if (!type || !id) return
  const key = matterKey(type.toUpperCase(), id)

  if (user_role.value === 'The Chief') {
    const index = deskQueue.value.findIndex((matter) => matter.key === key)
    if (index >= 0) deskIndex.value = index
    return
  }

  const matter = docketMatters.value.find((entry) => entry.key === key)
  if (!matter) return
  docketFilterWasSelected.value = true
  activeDocketFilter.value =
    matter.status === 'REJECTED' ? 'ATTENTION' : matter.status === 'PENDING' ? 'IN_PROGRESS' : 'RESOLVED'
  docketPage.value = 1
  expandedMatterKey.value = key
}

onMounted(() => {
  loadAll().then(applyFocusFromRoute)
  window.addEventListener('keydown', onDeskKey)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onDeskKey)
  window.removeEventListener('beforeunload', onBeforeUnload)

  // Leaving the page must not drop a decision that is still counting down.
  if (pendingSend.value) commitPending()
})
</script>





<style scoped>
.dk{--ink:#1c2430;--mu:#667085;--ln:#dfe3ea;--bg:#f4f6f8;--sf:#fff;--ac:#1f5f5b;--acs:#e3f0ee;--at:#b4432f;--ats:#fbeae6;--pg:#9a6a00;--pgs:#fbf1d9;--dn:#2d7a52;--dns:#e4f3ea;
max-width:1000px;margin:0 auto;padding:32px 20px 48px;color:var(--ink);font-size:14px;line-height:1.5}
@media (prefers-color-scheme:dark){.dk{--ink:#e6e9ef;--mu:#9aa4b5;--ln:#2d3547;--bg:#131822;--sf:#1a2130;--ac:#7cc4bd;--acs:#1d3535;--at:#f0937f;--ats:#3a2420;--pg:#e5b94f;--pgs:#38301a;--dn:#78c79c;--dns:#1b3326}}
.dk h1{font:600 30px/1.1 Georgia,"Times New Roman",serif;margin:2px 0 6px}
.dk-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:24px}
.dk-org{margin:0;color:var(--ac);font-weight:600;font-size:13px}
.dk-sub{margin:0;color:var(--mu);max-width:48ch}
.dk-btn{min-height:38px;padding:0 14px;border:1px solid var(--ln);border-radius:8px;background:var(--sf);color:var(--ink);font:inherit;font-weight:500;cursor:pointer}
.dk-btn:hover:not(:disabled){border-color:var(--mu)}
.dk-btn:disabled{opacity:.55;cursor:wait}
.dk-btn-main{background:var(--ac);border-color:var(--ac);color:var(--sf)}
.dk-btn-danger{color:var(--at);border-color:var(--at)}
.dk-link{border:0;background:none;color:var(--mu);cursor:pointer;font:inherit}
.dk button:focus-visible,.dk input:focus-visible,.dk textarea:focus-visible,.dk select:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.dk-msg{display:flex;justify-content:space-between;gap:12px;padding:10px 14px;border-radius:8px;margin-bottom:12px;border:1px solid}
.dk-msg button{border:0;background:none;color:inherit;font-size:18px;cursor:pointer}
.dk-msg-error{background:var(--ats);border-color:var(--at);color:var(--at)}
.dk-msg-ok{background:var(--dns);border-color:var(--dn);color:var(--dn)}
.dk-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border-bottom:1px solid var(--ln);margin-bottom:16px}
.dk-tab{display:flex;align-items:baseline;gap:10px;padding:12px 4px;margin-bottom:-1px;border:0;border-bottom:3px solid transparent;background:none;color:var(--mu);font:inherit;cursor:pointer;text-align:left}
.dk-tab strong{font:600 26px/1 Georgia,serif;color:var(--ink)}
.dk-tab.on{color:var(--ink);font-weight:600}
.dk-tab.attn.on{border-bottom-color:var(--at)}.dk-tab.prog.on{border-bottom-color:var(--pg)}.dk-tab.done.on{border-bottom-color:var(--dn)}
.dk-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;color:var(--mu)}
.dk-sort{display:flex;align-items:center;gap:8px}
.dk-sort select{padding:6px 8px;border:1px solid var(--ln);border-radius:6px;background:var(--sf);color:var(--ink);font:inherit}
.dk-note{padding:10px 14px;border-radius:8px;background:var(--bg)}
.dk-note-reason{background:var(--ats)}
.dk-note h3,.dk-form-head h3{margin:0 0 2px;font-size:13px;font-weight:600}
.dk-note p{margin:0}
.dk-actions{display:flex;flex-wrap:wrap;gap:8px}
.dk-form{border:1px solid var(--ln);border-radius:8px;padding:14px;display:grid;gap:12px}
.dk-form-head{display:flex;justify-content:space-between;align-items:center}
.dk-grid{display:grid;grid-template-columns:1fr;gap:10px}
.dk-grid label{display:grid;gap:4px}
.dk-grid label span{color:var(--mu);font-size:12px}
.dk-grid .wide{grid-column:1/-1}
.dk-grid input,.dk-grid textarea{width:100%;padding:8px 10px;border:1px solid var(--ln);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit}
.dk-empty{display:grid;justify-items:center;gap:6px;padding:56px 16px;border:1px dashed var(--ln);border-radius:8px;text-align:center;color:var(--mu)}
.dk-empty strong{color:var(--ink);font-size:15px}
.dk-spin{width:22px;height:22px;border:2px solid var(--ln);border-top-color:var(--ac);border-radius:50%;animation:dk-spin .8s linear infinite}
@keyframes dk-spin{to{transform:rotate(360deg)}}
.dk-pager{display:flex;justify-content:center;align-items:center;gap:14px;margin-top:18px;color:var(--mu)}
@media (prefers-reduced-motion:reduce){.dk-spin{animation:none}.dk-chev{transition:none}}
kbd{display:inline-block;margin-left:6px;padding:0 6px;border:1px solid currentColor;border-radius:4px;font:600 11px/18px system-ui,sans-serif;opacity:.7}
/* Chief review desk */
.cd-progress{margin-bottom:16px}
.cd-progress p{margin:6px 0 0;color:var(--mu)}
.cd-progress strong{color:var(--ink)}
.cd-bar{height:6px;border-radius:99px;background:var(--ln);overflow:hidden}
.cd-bar span{display:block;height:100%;background:var(--ac);transition:width .3s}
.cd-grid{display:grid;grid-template-columns:240px minmax(0,1fr);gap:20px;align-items:start}
.cd-rail{list-style:none;margin:0;padding:0;display:grid;gap:6px;max-height:70vh;overflow:auto;position:sticky;top:16px}
.cd-chip{display:grid;gap:2px;width:100%;padding:10px 12px;border:1px solid var(--ln);border-radius:8px;background:var(--sf);color:var(--ink);font:inherit;text-align:left;cursor:pointer}
.cd-chip small{color:var(--mu);font-size:12px}
.cd-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cd-chip.on{background:var(--acs);border-color:var(--ac);box-shadow:inset 0 0 0 1px var(--ac)}
.cd-card{display:grid;gap:18px;padding:24px;background:var(--sf);border:1px solid var(--ln);border-radius:12px}
.cd-nav{display:flex;align-items:center;gap:12px}
.cd-kind{font-weight:600;color:var(--ac)}
.cd-pos{color:var(--mu);flex:1}
.cd-arrows{display:flex;gap:6px}
.cd-card h2{font:600 28px/1.2 Georgia,"Times New Roman",serif;margin:0}
.cd-fields{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px 20px;margin:0}
.cd-fields dt{color:var(--mu);font-size:12px}
.cd-fields dd{margin:0;font-weight:500;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.dk-note{padding:12px 16px;border-radius:8px;background:var(--bg)}
.dk-note h3{margin:0 0 2px;font-size:13px;font-weight:600}.dk-note p{margin:0}
.cd-decide{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cd-big{min-height:52px;font-size:16px;font-weight:600}
.cd-reason{display:grid;gap:10px;padding:14px;border-radius:10px;border:1px solid var(--ac);background:var(--acs)}
.cd-reason.rej{border-color:var(--at);background:var(--ats)}
.cd-reason label{font-weight:600}
.cd-reason textarea{width:100%;padding:10px 12px;border:1px solid var(--ln);border-radius:8px;background:var(--sf);color:var(--ink);font:inherit;resize:vertical}
.cd-keys{margin:0;color:var(--mu);font-size:13px}
.cd-keys kbd{margin:0 2px 0 0}
/* Keeper tracker */
.kt-list{list-style:none;margin:0;padding:0;display:grid;gap:12px}
.kt-card{display:grid;gap:16px;padding:18px 20px;background:var(--sf);border:1px solid var(--ln);border-radius:12px}
.kt-card.s-rejected{border-color:var(--at)}
.kt-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.kt-ref{color:var(--mu);font-size:13px}
.kt-card h2{font:600 19px/1.3 Georgia,serif;margin:2px 0 4px}
.kt-meta{display:flex;flex-wrap:wrap;gap:2px 14px;margin:0;color:var(--mu)}
.dk-pill{padding:2px 10px;border-radius:99px;font-size:12px;font-weight:600;background:var(--bg);color:var(--mu);white-space:nowrap}
.s-rejected .dk-pill{background:var(--ats);color:var(--at)}.s-pending .dk-pill{background:var(--pgs);color:var(--pg)}
.s-available .dk-pill,.s-approved .dk-pill{background:var(--dns);color:var(--dn)}
.kt-steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,1fr)}
.kt-steps li{position:relative;display:grid;justify-items:center;gap:6px;color:var(--mu);font-size:13px;text-align:center}
.kt-steps li::before{content:"";position:absolute;top:9px;left:-50%;width:100%;height:2px;background:var(--ln)}
.kt-steps li:first-child::before{display:none}
.kt-steps i{position:relative;z-index:1;width:20px;height:20px;border-radius:50%;border:2px solid var(--ln);background:var(--sf)}
.kt-steps .done i{background:var(--dn);border-color:var(--dn)}
.kt-steps .done::before,.kt-steps .now::before,.kt-steps .bad::before{background:var(--dn)}
.kt-steps .done{color:var(--ink)}
.kt-steps .now i{border-color:var(--pg);background:var(--pgs)}.kt-steps .now{color:var(--pg);font-weight:600}
.kt-steps .bad i{background:var(--at);border-color:var(--at)}.kt-steps .bad{color:var(--at);font-weight:600}
.kt-msg{padding:12px 16px;border-radius:8px;background:var(--bg);border-left:4px solid var(--mu)}
.kt-msg.bad{background:var(--ats);border-left-color:var(--at)}
.kt-msg h3{margin:0 0 2px;font-size:13px;font-weight:600}.kt-msg p{margin:0}
.dk-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:820px){.cd-grid{grid-template-columns:1fr}
.cd-rail{grid-auto-flow:column;grid-auto-columns:200px;overflow-x:auto;max-height:none;position:static;padding-bottom:4px}}
@media (max-width:640px){
.dk{padding:20px 12px 32px}.dk-head{flex-direction:column}
.dk-tab{flex-direction:column;gap:2px;align-items:flex-start}
.cd-card{padding:16px}.cd-decide{grid-template-columns:1fr}
.kt-steps span{font-size:11px}.dk-grid{grid-template-columns:1fr}.dk-grid .wide{grid-column:auto}}
@media (prefers-reduced-motion:reduce){.cd-bar span{transition:none}}
/* Field-level diff */
.dk-diff{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:4px}
.dk-diff li{display:grid;grid-template-columns:150px 1fr 1fr;gap:8px;align-items:baseline;font-size:13px}
.dk-diff-l{color:var(--mu)}
.dk-diff del{background:var(--ats);color:var(--at);padding:1px 6px;border-radius:4px;text-decoration:line-through;overflow-wrap:anywhere}
.dk-diff ins{background:var(--dns);color:var(--dn);padding:1px 6px;border-radius:4px;text-decoration:none;overflow-wrap:anywhere}
.cd-resub{padding:12px 16px;border-radius:8px;border:1px solid var(--pg);background:var(--pgs)}
.cd-resub h3{margin:0;font-size:13px;font-weight:600}
.cd-resub h3 small{font-weight:400;color:var(--mu);margin-left:8px}
.cd-was{margin:4px 0 0}
/* Keeper timeline */
.kt-history{display:grid;gap:8px;justify-items:start}
.kt-hint{margin:0;color:var(--mu)}
.tl{list-style:none;margin:0;padding:0;display:grid;gap:0;width:100%}
.tl li{position:relative;display:grid;grid-template-columns:20px 1fr;gap:12px;padding-bottom:14px}
.tl li::before{content:"";position:absolute;left:9px;top:18px;bottom:0;width:2px;background:var(--ln)}
.tl li:last-child{padding-bottom:0}.tl li:last-child::before{display:none}
.tl i{width:20px;height:20px;border-radius:50%;border:2px solid var(--mu);background:var(--sf);margin-top:1px}
.tl .approved i{background:var(--dn);border-color:var(--dn)}
.tl .rejected i{background:var(--at);border-color:var(--at)}
.tl .resubmitted i{background:var(--pg);border-color:var(--pg)}
.tl .submitted i{background:var(--ac);border-color:var(--ac)}
.tl-head{margin:0}
.tl-head time{margin-left:8px;color:var(--mu);font-size:13px}
.tl-chips{margin:6px 0 0;color:var(--mu)}
.tl-chip{display:inline-block;margin:0 4px 0 6px;padding:1px 8px;border-radius:99px;background:var(--ats);color:var(--at);font-size:12px;font-weight:600}
.tl .tl-note{border-left-color:var(--pg);background:var(--pgs)}
.tl-reason{margin:4px 0 0;padding:6px 12px;border-left:3px solid var(--ln);background:var(--bg);border-radius:0 6px 6px 0}
.tl .rejected .tl-reason{border-left-color:var(--at);background:var(--ats)}
/* Undo toast */
.dk-toast{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(20px + env(safe-area-inset-bottom,0px));z-index:60;display:flex;align-items:center;gap:16px;padding:12px 16px;min-width:min(440px,calc(100vw - 24px));background:var(--ink);color:var(--sf);border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.25);overflow:hidden}
.dk-toast-text{flex:1}
.dk-toast-bar{position:absolute;left:0;bottom:0;height:3px;background:var(--ac);transition:width 1s linear}
.dk-toast .dk-btn{background:transparent;border-color:currentColor;color:inherit}
@media (max-width:640px){.dk-diff li{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){.dk-toast-bar{transition:none}}
.cd-chip.age-a1,.kt-card.age-a1{border-left:5px solid #e3c63f}
.cd-chip.age-a2,.kt-card.age-a2{border-left:5px solid #f0a93a}
.cd-chip.age-a3,.kt-card.age-a3{border-left:5px solid #ee7d33}
.cd-chip.age-a4,.kt-card.age-a4{border-left:5px solid #dc4a3f}
.cd-age-txt{font-style:normal;font-size:11px;color:var(--mu)}
.cd-age{padding:2px 10px;border-radius:99px;font-size:12px;font-weight:600;color:#1c2430}
.cd-age.age-a1{background:#e3c63f}.cd-age.age-a2{background:#f0a93a}.cd-age.age-a3{background:#ee7d33}.cd-age.age-a4{background:#dc4a3f;color:#fff}
.cd-reason textarea{max-height:40vh;min-height:0}
</style>
