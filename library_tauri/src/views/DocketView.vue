<template>
  <div class="docket-page docket-redesign">
    <header class="docket-header docket-redesign-header">
      <div>
        <div class="eyebrow">ATHENAEUM ORBIS</div>
        <div class="docket-title-row">
          <div>
            <h1>Docket</h1>
            <p>
              {{ user_role === 'The Keeper'
                ? 'Know what needs attention in your submissions.'
                : 'Review and resolve matters requiring your decision.' }}
            </p>
          </div>
          <span class="docket-total">
            {{ docketMatters.length }}
            {{ docketMatters.length === 1 ? 'matter' : 'matters' }}
          </span>
        </div>
      </div>

      <button
        type="button"
        class="docket-refresh"
        :disabled="loading"
        @click="loadAll"
      >
        <span aria-hidden="true">↻</span>
        {{ loading ? 'Syncing' : 'Refresh' }}
      </button>
    </header>

    <div v-if="error" class="docket-message docket-message-error">
      <span>{{ error }}</span>
      <button type="button" @click="error = ''">×</button>
    </div>

    <div v-if="notice" class="docket-message docket-message-success">
      <span>{{ notice }}</span>
      <button type="button" @click="notice = ''">×</button>
    </div>

    <section class="docket-situations" aria-label="Docket situation filters">
      <button
        type="button"
        class="situation-card situation-attention"
        :class="{ selected: activeDocketFilter === 'ATTENTION' }"
        @click="selectDocketFilter('ATTENTION')"
      >
        <span class="situation-label">ATTENTION</span>
        <strong>{{ attentionCount }}</strong>
        <span class="situation-note">
          {{ user_role === 'The Keeper' ? 'Rejected matters' : 'Awaiting decision' }}
        </span>
      </button>

      <button
        type="button"
        class="situation-card situation-progress"
        :class="{ selected: activeDocketFilter === 'IN_PROGRESS' }"
        @click="selectDocketFilter('IN_PROGRESS')"
      >
        <span class="situation-label">IN PROGRESS</span>
        <strong>{{ inProgressCount }}</strong>
        <span class="situation-note">
          {{ user_role === 'The Keeper'
            ? 'Currently moving through the docket'
            : 'Active processing' }}
        </span>
      </button>

      <button
        type="button"
        class="situation-card situation-resolved"
        :class="{ selected: activeDocketFilter === 'RESOLVED' }"
        @click="selectDocketFilter('RESOLVED')"
      >
        <span class="situation-label">RESOLVED</span>
        <strong>{{ resolvedCount }}</strong>
        <span class="situation-note">
          {{ user_role === 'The Keeper'
            ? 'Completed submissions'
            : 'Decision history' }}
        </span>
      </button>
    </section>

    <section class="docket-workspace">
      <div class="docket-toolbar">
        <div>
          <span class="docket-toolbar-kicker">MATTERS</span>
          <strong>
            {{ activeDocketFilter === 'ATTENTION'
              ? 'Needs attention'
              : activeDocketFilter === 'IN_PROGRESS'
                ? 'In progress'
                : 'Resolved' }}
          </strong>
          <span class="docket-range" v-if="visibleDocketMatters.length">
            Showing {{ docketPageStart }}–{{ docketPageEnd }}
            of {{ visibleDocketMatters.length }}
          </span>
          <span class="docket-range" v-else>No matters in this view</span>
        </div>

        <label class="docket-sort">
          <span>Sort</span>
          <select :value="docketSort" @change="changeDocketSort($event.target.value)">
            <option value="PRIORITY">Priority</option>
            <option value="WORK">Work ID</option>
            <option value="ITEM">Item No.</option>
          </select>
        </label>
      </div>

      <div v-if="loading && !docketMatters.length" class="docket-empty docket-loading">
        <div class="docket-loader"></div>
        <strong>Retrieving matters…</strong>
        <span>Synchronising the Docket.</span>
      </div>

      <div v-else-if="!paginatedDocketMatters.length" class="docket-empty">
        <div class="docket-empty-mark">✓</div>
        <strong>
          {{ activeDocketFilter === 'ATTENTION'
            ? 'Nothing needs attention'
            : activeDocketFilter === 'IN_PROGRESS'
              ? 'Nothing is in progress'
              : 'No resolved matters to show' }}
        </strong>
        <span>
          {{ user_role === 'The Keeper'
            ? 'Your submitted matters will appear here as their status changes.'
            : 'New matters awaiting your decision will appear in Attention.' }}
        </span>
      </div>

      <div v-else class="docket-matter-grid">
        <article
          v-for="matter in paginatedDocketMatters"
          :key="matter.key"
          class="docket-matter"
          :class="[
            `matter-${String(matter.status || '').toLowerCase()}`,
            { expanded: expandedMatterKey === matter.key }
          ]"
        >
          <button
            type="button"
            class="matter-summary"
            @click="toggleMatter(matter)"
          >
            <div class="matter-topline">
              <span class="matter-kind">
                {{ matter.type === 'WORK' ? 'WORK' : 'ITEM' }}
              </span>
              <span class="matter-number">
                {{ matter.type === 'WORK'
                  ? `#${matter.work_id}`
                  : `#${matter.serial_no}` }}
              </span>
              <span class="matter-status">
                {{ matter.status }}
              </span>
            </div>

            <h2>{{ matter.title || 'Untitled' }}</h2>

            <div class="matter-details">
              <span v-if="matter.author">{{ matter.author }}</span>
              <span v-if="matter.language">{{ matter.language }}</span>
              <span v-if="matter.category">{{ matter.category }}</span>
            </div>

            <div class="matter-reference">
              <span>WORK ID</span>
              <strong>#{{ matter.work_id }}</strong>
              <span v-if="matter.serial_no">ITEM NO.</span>
              <strong v-if="matter.serial_no">#{{ matter.serial_no }}</strong>
              <span v-if="matter.accession_no">ACCESSION NO.</span>
              <strong v-if="matter.accession_no">{{ matter.accession_no }}</strong>
            </div>

            <span class="matter-expand">
              {{ expandedMatterKey === matter.key ? 'Close' : 'Details' }}
            </span>
          </button>

          <div v-if="expandedMatterKey === matter.key" class="matter-expanded">
            <div v-if="matter.approval_reason" class="matter-reason">
              <span>Reason</span>
              <p>{{ matter.approval_reason }}</p>
            </div>

            <div v-if="matter.proposal_reason" class="matter-reason">
              <span>Proposal</span>
              <p>{{ matter.proposal_reason }}</p>
            </div>

            <div v-if="matter.type === 'WORK' && matter.status === 'REJECTED' && user_role === 'The Keeper'" class="matter-action-block">
              <div v-if="correctionWorkId !== matter.work_id">
                <button
                  type="button"
                  class="matter-action matter-action-primary"
                  @click="startCorrection(matter)"
                >
                  Correct submission
                </button>
              </div>

              <div v-else class="correction-panel">
                <div class="correction-heading">
                  <strong>Correct Work #{{ matter.work_id }}</strong>
                  <button type="button" @click="cancelCorrection">Close</button>
                </div>

                <div class="correction-grid">
                  <label><span>Title *</span><input v-model="correctionForm.title" type="text"></label>
                  <label><span>Author</span><input v-model="correctionForm.author" type="text"></label>
                  <label><span>Category</span><input v-model="correctionForm.category" type="text"></label>
                  <label><span>Language *</span><input v-model="correctionForm.language" type="text"></label>
                  <label><span>Publisher</span><input v-model="correctionForm.publisher" type="text"></label>
                  <label><span>Year</span><input v-model="correctionForm.year" type="number"></label>
                  <label><span>ISBN</span><input v-model="correctionForm.isbn" type="text"></label>
                  <label><span>DDC</span><input v-model="correctionForm.ddc" type="text"></label>
                  <label><span>Call no.</span><input v-model="correctionForm.call_no" type="text"></label>
                  <label><span>Translation / compilation</span><input v-model="correctionForm.translation_compilation" type="text"></label>
                  <label><span>Genre</span><input v-model="correctionForm.genre" type="text"></label>
                  <label><span>Original language</span><input v-model="correctionForm.original_language" type="text"></label>
                  <label class="correction-wide"><span>Notes</span><textarea v-model="correctionForm.notes" rows="3"></textarea></label>
                  <label class="correction-wide"><span>Proposal reason</span><textarea v-model="correctionForm.proposal_reason" rows="3"></textarea></label>
                </div>

                <div class="correction-actions">
                  <button type="button" class="matter-action" @click="cancelCorrection">Cancel</button>
                  <button type="button" class="matter-action matter-action-primary" :disabled="busy" @click="resubmitWork">
                    {{ busy ? 'Resubmitting…' : 'Resubmit for review' }}
                  </button>
                </div>
              </div>
            </div>

            <div v-if="user_role === 'The Chief' && matter.type === 'WORK' && matter.status === 'PENDING'" class="matter-actions">
              <button type="button" class="matter-action matter-action-approve" :disabled="busy" @click="decideWork(matter, 'APPROVE')">
                Approve Work
              </button>
              <button type="button" class="matter-action matter-action-reject" :disabled="busy" @click="decideWork(matter, 'REJECT')">
                Reject Work
              </button>
            </div>

            <div v-if="user_role === 'The Chief' && matter.type === 'ITEM' && matter.status === 'PENDING'" class="matter-actions">
              <button type="button" class="matter-action matter-action-approve" :disabled="busy" @click="decideItem(matter, 'APPROVE')">
                Approve Item
              </button>
              <button type="button" class="matter-action matter-action-reject" :disabled="busy" @click="decideItem(matter, 'REJECT')">
                Reject Item
              </button>
            </div>
          </div>
        </article>
      </div>

      <div v-if="docketTotalPages > 1" class="docket-pagination">
        <button
          type="button"
          :disabled="docketPage <= 1"
          @click="changeDocketPage(docketPage - 1)"
        >
          Previous
        </button>

        <span>Page {{ docketPage }} of {{ docketTotalPages }}</span>

        <button
          type="button"
          :disabled="docketPage >= docketTotalPages"
          @click="changeDocketPage(docketPage + 1)"
        >
          Next
        </button>
      </div>
    </section>
  </div>
</template>





<script setup>

import {

  computed,

  onMounted,

  ref

} from 'vue'



import axios from 'axios'

import { storeToRefs } from 'pinia'

import { useAuthStore } from '@/stores/auth'



const authStore = useAuthStore()

const { userRole: user_role } = storeToRefs(authStore)





const pendingWorks = ref([])

const pendingItems = ref([])



const loading = ref(false)

const busy = ref(false)



const error = ref('')

const notice = ref('')



const correctionWorkId = ref(null)

const correctionForm = ref({

  title: '',

  author: '',

  category: '',

  language: '',

  publisher: '',

  year: '',

  isbn: '',

  ddc: '',

  call_no: '',

  translation_compilation: '',

  genre: '',

  original_language: '',

  notes: '',

  proposal_reason: ''

})





const totalMatters = computed(

  () =>

    pendingWorks.value.length +

    pendingItems.value.length

)



  const activeDocketFilter = ref('ATTENTION')
const docketSort = ref('PRIORITY')
const docketPage = ref(1)
const docketPageSize = 12
const expandedMatterKey = ref(null)
const docketFilterWasSelected = ref(false)

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

    if (matter) matters.push(matter)
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





function startCorrection(submission) {

  correctionWorkId.value = submission.work_id

  correctionForm.value = {

    title: submission.title || '',

    author: submission.author || '',

    category: submission.category || '',

    language: submission.language || '',

    publisher: submission.publisher || '',

    year: submission.year || '',

    isbn: submission.isbn || '',

    ddc: submission.ddc || '',

    call_no: submission.call_no || '',

    translation_compilation: submission.translation_compilation || '',

    genre: submission.genre || '',

    original_language: submission.original_language || '',

    notes: submission.notes || '',

    proposal_reason: submission.proposal_reason || ''

  }

  error.value = ''

  notice.value = ''

}



function cancelCorrection() {

  correctionWorkId.value = null

}



async function resubmitWork() {

  if (!correctionWorkId.value) return



  if (!String(correctionForm.value.title || '').trim()) {

    error.value = 'Title is required.'

    return

  }



  if (!String(correctionForm.value.language || '').trim()) {

    error.value = 'Language is required.'

    return

  }



  busy.value = true

  error.value = ''

  notice.value = ''



  try {

    await axios.post(

      `/catalogue/resubmit/${correctionWorkId.value}`,

      correctionForm.value

    )



    correctionWorkId.value = null

    notice.value = 'Submission corrected and sent for review.'

    await loadAll()

  } catch (err) {

    console.error('Work resubmission failed:', err)

    error.value =

      err.response?.data?.detail ||

      'Unable to resubmit the corrected Work.'

  } finally {

    busy.value = false

  }

}





async function decideWork(

  work,

  action

) {



  const reason = window.prompt(

    `${

      action === 'APPROVE'

        ? 'Approval'

        : 'Rejection'

    } reason for “${work.title || 'Untitled'}”:`,

    ''

  )





  if (reason === null) {

    return

  }





  if (!reason.trim()) {



    error.value =

      'A decision reason is required.'



    return

  }





  busy.value = true

  error.value = ''

  notice.value = ''





  try {



    await axios.post(

      `/catalogue/approve/${work.work_id}`,

      null,

      {

        params: {

          action,

          reason: reason.trim()

        }

      }

    )





    notice.value =

      `Work “${work.title || 'Untitled'}” ${

        action === 'APPROVE'

          ? 'approved'

          : 'rejected'

      }.`





    await loadAll()



  } catch (err) {



    error.value =

      err.response?.data?.detail ||

      'Unable to process the Work decision.'



  } finally {



    busy.value = false



  }

}





async function decideItem(

  item,

  action

) {



  const reason = window.prompt(

    `${

      action === 'APPROVE'

        ? 'Approval'

        : 'Rejection'

    } reason for Item #${item.serial_no}:`,

    ''

  )





  if (reason === null) {

    return

  }





  if (!reason.trim()) {



    error.value =

      'A decision reason is required.'



    return

  }





  busy.value = true

  error.value = ''

  notice.value = ''





  try {



    await axios.post(

      `/catalogue/approve-item/${item.serial_no}`,

      null,

      {

        params: {

          action,

          reason: reason.trim()

        }

      }

    )





    notice.value =

      `Item #${item.serial_no} ${

        action === 'APPROVE'

          ? 'approved'

          : 'rejected'

      }.`





    await loadAll()



  } catch (err) {



    error.value =

      err.response?.data?.detail ||

      'Unable to process the Item decision.'



  } finally {



    busy.value = false



  }

}





onMounted(loadAll)

</script>





<style scoped>
.docket-redesign {
  --docket-ink: #20252b;
  --docket-muted: #6d737b;
  --docket-line: #d9dde2;
  --docket-paper: #fbfaf7;
  --docket-panel: #ffffff;
  --docket-attention: #b74b43;
  --docket-progress: #a87522;
  --docket-resolved: #3f725a;
  width: 100%;
  max-width: 1500px;
  margin: 0 auto;
  padding: 28px clamp(16px, 3vw, 42px) 48px;
  color: var(--docket-ink);
}

.docket-redesign-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--docket-line);
}

.docket-redesign .eyebrow {
  margin-bottom: 7px;
  color: var(--docket-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .18em;
}

.docket-title-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.docket-title-row h1 {
  margin: 0;
  font-size: clamp(30px, 4vw, 44px);
  line-height: 1;
  letter-spacing: -.04em;
}

.docket-title-row p {
  margin: 9px 0 0;
  color: var(--docket-muted);
  font-size: 14px;
}

.docket-total {
  display: inline-flex;
  align-items: center;
  min-height: 27px;
  padding: 0 10px;
  border: 1px solid var(--docket-line);
  border-radius: 999px;
  background: var(--docket-panel);
  color: var(--docket-muted);
  font-size: 11px;
  font-weight: 800;
}

.docket-refresh {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid var(--docket-line);
  border-radius: 8px;
  background: var(--docket-panel);
  color: var(--docket-ink);
  font-weight: 700;
  cursor: pointer;
}

.docket-refresh:hover:not(:disabled) {
  border-color: #aeb5bc;
}

.docket-refresh:disabled {
  opacity: .55;
  cursor: wait;
}

.docket-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: 16px 0 0;
  padding: 11px 13px;
  border: 1px solid var(--docket-line);
  border-radius: 8px;
  font-size: 13px;
}

.docket-message-error {
  border-color: #e2b9b5;
  background: #fff7f6;
}

.docket-message-success {
  border-color: #b9d2c5;
  background: #f5faf7;
}

.docket-message button {
  border: 0;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
}

.docket-situations {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 22px 0 20px;
}

.situation-card {
  position: relative;
  min-height: 132px;
  padding: 18px 20px;
  border: 1px solid var(--docket-line);
  border-radius: 10px;
  background: var(--docket-panel);
  text-align: left;
  color: var(--docket-ink);
  cursor: pointer;
  transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
}

.situation-card:hover {
  transform: translateY(-1px);
  border-color: #aeb5bc;
}

.situation-card.selected {
  box-shadow: 0 0 0 2px currentColor inset;
}

.situation-attention {
  color: var(--docket-attention);
}

.situation-progress {
  color: var(--docket-progress);
}

.situation-resolved {
  color: var(--docket-resolved);
}

.situation-label {
  display: block;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .15em;
}

.situation-card strong {
  display: block;
  margin-top: 8px;
  color: var(--docket-ink);
  font-size: 36px;
  line-height: 1;
  letter-spacing: -.04em;
}

.situation-note {
  display: block;
  margin-top: 9px;
  color: var(--docket-muted);
  font-size: 11px;
}

.docket-workspace {
  min-width: 0;
}

.docket-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 13px;
  padding: 0 2px;
}

.docket-toolbar > div {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.docket-toolbar-kicker {
  color: var(--docket-muted);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .15em;
}

.docket-toolbar strong {
  font-size: 14px;
}

.docket-range {
  color: var(--docket-muted);
  font-size: 11px;
}

.docket-sort {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--docket-muted);
  font-size: 11px;
  font-weight: 700;
}

.docket-sort select {
  min-height: 34px;
  padding: 0 28px 0 10px;
  border: 1px solid var(--docket-line);
  border-radius: 7px;
  background: var(--docket-panel);
  color: var(--docket-ink);
  font-size: 12px;
}

.docket-matter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.docket-matter {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--docket-line);
  border-radius: 9px;
  background: var(--docket-panel);
  box-shadow: 0 2px 8px rgba(32, 37, 43, .035);
}

.docket-matter:hover,
.docket-matter.expanded {
  border-color: #b8bec5;
}

.docket-matter.matter-rejected {
  border-top: 3px solid var(--docket-attention);
}

.docket-matter.matter-pending {
  border-top: 3px solid var(--docket-progress);
}

.docket-matter.matter-available,
.docket-matter.matter-approved {
  border-top: 3px solid var(--docket-resolved);
}

.matter-summary {
  display: block;
  width: 100%;
  min-height: 188px;
  padding: 14px;
  border: 0;
  background: transparent;
  color: var(--docket-ink);
  text-align: left;
  cursor: pointer;
}

.matter-topline {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.matter-kind {
  color: var(--docket-muted);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .13em;
}

.matter-number {
  color: var(--docket-ink);
  font-size: 12px;
  font-weight: 900;
}

.matter-status {
  margin-left: auto;
  padding: 4px 7px;
  border-radius: 999px;
  background: #f0f1f2;
  color: var(--docket-muted);
  font-size: 8px;
  font-weight: 900;
  letter-spacing: .08em;
}

.matter-rejected .matter-status {
  background: #f8e8e6;
  color: var(--docket-attention);
}

.matter-pending .matter-status {
  background: #f8efdf;
  color: var(--docket-progress);
}

.matter-available .matter-status,
.matter-approved .matter-status {
  background: #e8f1ec;
  color: var(--docket-resolved);
}

.matter-summary h2 {
  display: -webkit-box;
  margin: 17px 0 7px;
  overflow: hidden;
  font-size: 16px;
  line-height: 1.25;
  letter-spacing: -.015em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.matter-details {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 9px;
  min-height: 30px;
  color: var(--docket-muted);
  font-size: 11px;
}

.matter-details span + span::before {
  content: "·";
  margin-right: 9px;
}

.matter-reference {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid #eceef0;
  color: var(--docket-muted);
  font-size: 8px;
  font-weight: 800;
  letter-spacing: .1em;
}

.matter-reference strong {
  margin-right: 5px;
  color: var(--docket-ink);
  font-size: 11px;
  letter-spacing: 0;
}

.matter-expand {
  display: block;
  margin-top: 9px;
  color: var(--docket-muted);
  font-size: 9px;
  font-weight: 800;
}

.matter-expanded {
  padding: 0 14px 14px;
  border-top: 1px solid #eceef0;
}

.matter-reason {
  padding: 11px 0;
}

.matter-reason + .matter-reason {
  border-top: 1px solid #eceef0;
}

.matter-reason span {
  display: block;
  margin-bottom: 4px;
  color: var(--docket-muted);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.matter-reason p {
  margin: 0;
  color: var(--docket-ink);
  font-size: 12px;
  line-height: 1.45;
}

.matter-actions,
.correction-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}

.matter-action {
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid var(--docket-line);
  border-radius: 6px;
  background: var(--docket-panel);
  color: var(--docket-ink);
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.matter-action:hover:not(:disabled) {
  border-color: #9ea6ae;
}

.matter-action:disabled {
  opacity: .5;
  cursor: wait;
}

.matter-action-primary,
.matter-action-approve {
  border-color: #9bbbab;
  background: #edf6f0;
  color: #35654d;
}

.matter-action-reject {
  border-color: #d9aaa5;
  background: #fff2f0;
  color: #9f4039;
}

.correction-panel {
  margin-top: 10px;
  padding-top: 11px;
}

.correction-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 11px;
}

.correction-heading strong {
  font-size: 12px;
}

.correction-heading button {
  border: 0;
  background: transparent;
  color: var(--docket-muted);
  font-size: 10px;
  cursor: pointer;
}

.correction-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.correction-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.correction-grid label span {
  color: var(--docket-muted);
  font-size: 9px;
  font-weight: 800;
}

.correction-grid input,
.correction-grid textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--docket-line);
  border-radius: 5px;
  background: #fff;
  color: var(--docket-ink);
  font: inherit;
  font-size: 11px;
  padding: 7px 8px;
}

.correction-grid textarea {
  resize: vertical;
}

.correction-wide {
  grid-column: 1 / -1;
}

.docket-empty {
  display: flex;
  min-height: 250px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 7px;
  border: 1px dashed var(--docket-line);
  border-radius: 10px;
  background: rgba(255,255,255,.5);
  text-align: center;
}

.docket-empty strong {
  font-size: 14px;
}

.docket-empty span {
  max-width: 430px;
  color: var(--docket-muted);
  font-size: 11px;
}

.docket-empty-mark {
  display: grid;
  width: 35px;
  height: 35px;
  place-items: center;
  margin-bottom: 4px;
  border: 1px solid #b9d2c5;
  border-radius: 50%;
  color: var(--docket-resolved);
  font-weight: 900;
}

.docket-loader {
  width: 22px;
  height: 22px;
  margin-bottom: 5px;
  border: 2px solid #d9dde2;
  border-top-color: #69717a;
  border-radius: 50%;
  animation: docket-spin .8s linear infinite;
}

.docket-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 13px;
  margin-top: 18px;
  color: var(--docket-muted);
  font-size: 11px;
  font-weight: 700;
}

.docket-pagination button {
  min-height: 32px;
  padding: 0 11px;
  border: 1px solid var(--docket-line);
  border-radius: 6px;
  background: var(--docket-panel);
  color: var(--docket-ink);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.docket-pagination button:disabled {
  opacity: .4;
  cursor: default;
}

@keyframes docket-spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1150px) {
  .docket-matter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 800px) {
  .docket-situations {
    grid-template-columns: 1fr;
  }

  .docket-matter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .docket-redesign-header {
    align-items: flex-start;
  }
}

@media (max-width: 560px) {
  .docket-redesign {
    padding: 20px 12px 32px;
  }

  .docket-redesign-header {
    flex-direction: column;
  }

  .docket-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .docket-refresh {
    width: 100%;
    justify-content: center;
  }

  .docket-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .docket-sort {
    width: 100%;
    justify-content: space-between;
  }

  .docket-sort select {
    flex: 1;
  }

  .docket-matter-grid {
    grid-template-columns: 1fr;
  }

  .correction-grid {
    grid-template-columns: 1fr;
  }

  .correction-wide {
    grid-column: auto;
  }
}
</style>