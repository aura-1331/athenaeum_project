import { reactive } from "vue"

export const liveWorkflow = reactive({
  selectedAccession: null,
  selectedBook: null,
  loading: false,
  actionLock: false,
  lastAuditTick: 0,
  keyboardIndex: -1,

  /* ⭐ LEVEL 4 */
  lastStatusChange: null,   // used to live-update catalogue rows
  focusLock: true           // scanner-ready mode
})

export function setSelectedBook(book, index = -1) {
  liveWorkflow.selectedAccession = book.accession_no
  liveWorkflow.selectedBook = book
  liveWorkflow.keyboardIndex = index
}

export function triggerAuditRefresh() {
  liveWorkflow.lastAuditTick++
}

export function pushStatusUpdate(accession, status) {
  liveWorkflow.lastStatusChange = {
    accession,
    status,
    tick: Date.now()
  }
}