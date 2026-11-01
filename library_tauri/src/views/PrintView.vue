<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"
// @ts-ignore
import bwipjs from "bwip-js"
import { storeToRefs } from "pinia"
import { useAuthStore } from "@/stores/auth"
import { gatherHardwareTelemetry, type ForensicHardwareInfo } from "@/services/sysAuditBridge"

interface HoldingRecord {
  item_id?: number | string
  serial_no?: number | string
  work_id?: number | string
  accession_no?: string
  shelf?: string
  shelf_location?: string
  extent_page_count?: string | number
  physical_dimensions?: string
  date_acquired?: string
  collection_fonds?: string
  physical_condition?: string
  binding_type?: string
  provenance_source?: string
  artifactual_notes?: string
  access_restrictions?: string
  digital_scan_available?: boolean | string
  ocr_status?: string
  availability_status?: string
  circulation_status?: string
  title?: string
  author?: string
  language?: string
  publisher?: string
  year?: string | number
  publication_year?: string | number
  isbn?: string
  ddc?: string
  call_no?: string
  original_language?: string
  original_title?: string
  original_author?: string
  translator?: string
  compiler_editor?: string
  work_nature?: string | string[]
  edition_statement?: string
  edition?: string
  series_title?: string
  series_volume?: string
  lccn?: string
  oclc_no?: string
  subject_headings?: string | string[]
  target_audience_era?: string
  copyright_status?: string
  notes?: string
  description?: string
  category?: string
  genre?: string | string[]
  categories?: string | string[]
  translation_compilation?: string
  series_name?: string
  series_number?: string | number
  volume_number?: string | number
  related_work_id?: number | string
  record_id?: string
  [key: string]: any
}

const route = useRoute()
const router = useRouter()
const holdingId = computed(() => (route.params.id as string) || "")

const authStore = useAuthStore()
const { userRole, userName, userId } = storeToRefs(authStore)

const loading = ref(true)
const showAllFields = ref(false)
const isPrinting = ref(false)
const printMode = ref<"compact" | "detailed">("compact")
const printStatus = ref("Ready")
const pageFitWarning = ref("")
const printHistory = ref<any[]>([])
const showPrintHistory = ref(false)
const sheetRef = ref<HTMLElement | null>(null)
const book = ref<HoldingRecord>({})
const buttonFeedback = ref("")

const headerQrCanvas = ref<HTMLCanvasElement | null>(null)
const pdf417Canvas = ref<HTMLCanvasElement | null>(null)
const pocketQrCanvas = ref<HTMLCanvasElement | null>(null)

const hardware = ref<ForensicHardwareInfo>({
  machineUuid: "WS-INIT",
  biosUuid: "—",
  macAddress: "—",
  osUsername: "—",
  platform: "—",
  printerName: "Default Spooler",
  printerDriver: "WinSpool",
  spoolerJobId: "—",
  dpiResolution: "600 DPI",
  mediaSize: "A4"
})

const audit = ref({
  operatorName: "Archive Officer",
  operatorRole: "The Keeper",
  operatorId: "UID-00",
  stationIp: "127.0.0.1",
  stationGeo: "08.5241° N, 76.9366° E · Thiruvananthapuram Central",
  timestamp: "",
  checksum: "",
  printRun: "#1",
  dossierType: "OFFICIAL MASTER REGISTER",
  protocolTag: "ISAD(G) / ISO 15489-1"
})

function flashMessage(msg: string) {
  buttonFeedback.value = msg
  setTimeout(() => {
    buttonFeedback.value = ""
  }, 3000)
}

async function handleClose() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window")
    await getCurrentWindow().close()
    return
  } catch {
    // Non-Tauri fallback
  }

  try {
    if (window.opener) {
      window.close()
      return
    }
  } catch {
    // Ignore close error
  }

  if (window.history.length > 1) {
    router.back()
  } else {
    router.push("/catalogue")
  }
}

async function getLocalStationIP(): Promise<string> {
  return new Promise((resolve) => {
    try {
      const pc = new RTCPeerConnection({ iceServers: [] })
      pc.createDataChannel("")
      pc.createOffer()
        .then((offer) => pc.setLocalDescription(offer))
        .catch(() => resolve("127.0.0.1 (Station)"))

      pc.onicecandidate = (ice) => {
        if (!ice || !ice.candidate || !ice.candidate.candidate) {
          resolve("127.0.0.1 (Station)")
          return
        }
        const match = ice.candidate.candidate.match(/([0-9]{1,3}(\.[0-9]{1,3}){3})/)
        if (match) {
          resolve(match[1])
          pc.close()
        }
      }
      setTimeout(() => resolve("127.0.0.1 (Station)"), 600)
    } catch {
      resolve("127.0.0.1 (Station)")
    }
  })
}

function canonicalRecordPayload(record: HoldingRecord): string {
  const excluded = new Set(["updated_at", "created_at", "last_modified"])
  const stable: Record<string, unknown> = {}
  Object.keys(record).sort().forEach((key) => {
    if (!excluded.has(key)) stable[key] = record[key]
  })
  return JSON.stringify(stable)
}

async function generateChecksum(payload: string): Promise<string> {
  try {
    const encoder = new TextEncoder()
    const data = encoder.encode(payload)
    const hash = await crypto.subtle.digest("SHA-256", data)
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .toUpperCase()
  } catch {
    return "UNAVAILABLE"
  }
}

async function recordServerAudit(status: "SUCCESS" | "CANCELLED" | "VOIDED" | "INITIATED", reason?: string) {
  flashMessage(`Recording ${status}...`)
  try {
    const activeSession =
      (authStore as any).sessionId ||
      (authStore as any).session_id ||
      localStorage.getItem("active_session_id") ||
      localStorage.getItem("session_id") ||
      sessionStorage.getItem("active_session_id") ||
      null

    const payload = {
      serial_no: Number(book.value.serial_no || holdingId.value || 0),
      item_id: book.value.item_id ? Number(book.value.item_id) : null,
      accession_no: book.value.accession_no || "UNASSIGNED",
      client_checksum: audit.value.checksum || "MANUAL_ENTRY",
      dossier_type: audit.value.dossierType,
      machine_uuid: hardware.value.machineUuid,
      hardware_bios_uuid: hardware.value.biosUuid,
      mac_address: hardware.value.macAddress,
      os_username: hardware.value.osUsername,
      platform: hardware.value.platform,
      printer_name: hardware.value.printerName,
      printer_driver: hardware.value.printerDriver,
      spooler_job_id: hardware.value.spoolerJobId,
      media_size: hardware.value.mediaSize,
      dpi_resolution: hardware.value.dpiResolution,
      station_ip: audit.value.stationIp,
      geo_station: audit.value.stationGeo,
      parent_session_id: activeSession,
      print_status: status,
      cancellation_reason: reason || (status === "SUCCESS" ? "Normal completion" : "Operator action")
    }

    const res = await axios.post("/status_audit/log-print", payload)

    if (res.data) {
      flashMessage(`Recorded: ${status}`)
      printStatus.value = status === "INITIATED"
        ? "Print dialog closed"
        : `${status} · audit record saved`
      if (status === "SUCCESS") {
        audit.value.printRun = res.data.print_run || audit.value.printRun
        audit.value.dossierType = res.data.dossier_type || audit.value.dossierType
      }
      await loadPrintHistory()
    }
  } catch (err: any) {
    flashMessage(`Audit failed: ${err.response?.status || err.message}`)
    printStatus.value = `Server audit rejected: ${err.message}`
  }
}

async function loadPrintHistory() {
  try {
    const serial = Number(book.value.serial_no || holdingId.value || 0)
    if (!serial) return
    const res = await axios.get("/status_audit/print-history", { params: { serial_no: serial } })
    printHistory.value = Array.isArray(res.data?.items) ? res.data.items : []
  } catch (err) {
    console.warn("Print history unavailable:", err)
  }
}

async function checkPageFit() {
  await nextTick()
  if (!sheetRef.value) return
  const maxPx = 1060
  pageFitWarning.value = sheetRef.value.scrollHeight > maxPx
    ? "Exceeds standard 1-page fit. Switch to compact mode."
    : ""
}

async function triggerPrint() {
  await checkPageFit()
  isPrinting.value = true
  printStatus.value = "Print dialog opened"
  let handled = false
  window.onafterprint = async () => {
    if (handled) return
    handled = true
    await recordServerAudit("INITIATED", "Browser print dialog closed")
    isPrinting.value = false
  }
  await nextTick()
  window.print()
}

function hasVal(val: any): boolean {
  if (val === null || val === undefined) return false
  if (typeof val === "string" && val.trim() === "") return false
  if (Array.isArray(val) && val.length === 0) return false
  if (typeof val === "boolean" && val === false) return false
  return true
}

function shouldShow(val: any): boolean {
  return showAllFields.value || hasVal(val)
}

function formatVal(val: any): string {
  if (!hasVal(val)) return "—"
  if (Array.isArray(val)) return val.join(", ")
  if (typeof val === "boolean") return val ? "Yes" : "—"
  return String(val)
}

const missingFields = computed(() => {
  const missing: string[] = []
  if (!hasVal(book.value.accession_no)) missing.push("Accession number")
  if (!hasVal(book.value.call_no)) missing.push("Call number")
  if (!hasVal(book.value.shelf_location || book.value.shelf)) missing.push("Shelf location")
  if (!hasVal(book.value.item_id)) missing.push("Item ID")
  return missing
})

const hasBlockA = computed(() => showAllFields.value || hasVal(book.value.call_no) || hasVal(book.value.shelf_location || book.value.shelf) || hasVal(book.value.ddc) || hasVal(book.value.isbn) || hasVal(book.value.lccn) || hasVal(book.value.oclc_no) || hasVal(book.value.publisher) || hasVal(book.value.edition_statement || book.value.edition))
const hasBlockB = computed(() => showAllFields.value || hasVal(book.value.genre || book.value.categories) || hasVal(book.value.work_nature) || hasVal(book.value.original_title) || hasVal(book.value.original_author) || hasVal(book.value.original_language) || hasVal(book.value.translator) || hasVal(book.value.compiler_editor) || hasVal(book.value.translation_compilation) || hasVal(book.value.target_audience_era) || hasVal(book.value.copyright_status) || hasVal(book.value.series_name || book.value.series_title) || hasVal(book.value.subject_headings))
const hasBlockC = computed(() => showAllFields.value || hasVal(book.value.extent_page_count) || hasVal(book.value.physical_dimensions) || hasVal(book.value.binding_type) || hasVal(book.value.physical_condition) || hasVal(book.value.date_acquired) || hasVal(book.value.collection_fonds) || hasVal(book.value.provenance_source) || hasVal(book.value.access_restrictions) || hasVal(book.value.digital_scan_available) || hasVal(book.value.ocr_status) || hasVal(book.value.notes || book.value.description) || hasVal(book.value.artifactual_notes))

function renderBarcodes() {
  const targetId = String(book.value.serial_no || book.value.item_id || holdingId.value || "")
  const recId = book.value.record_id || targetId
  const accNo = book.value.accession_no || targetId
  const callNo = book.value.call_no || ""
  const author = book.value.author || ""

  const qrPayload = accNo ? `${accNo} © ATHENAEUM` : `ID:${targetId} © ATHENAEUM`
  const pdf417Payload = [recId, accNo, callNo, author].filter(Boolean).join("|")

  if (headerQrCanvas.value && qrPayload) {
    try {
      bwipjs.toCanvas(headerQrCanvas.value, {
        bcid: "qrcode",
        text: qrPayload,
        scale: 3,
        eclevel: "M",
        includetext: false
      } as any)
    } catch (err) {
      console.error(err)
    }
  }

  if (pocketQrCanvas.value && qrPayload) {
    try {
      bwipjs.toCanvas(pocketQrCanvas.value, {
        bcid: "qrcode",
        text: qrPayload,
        scale: 2.5,
        eclevel: "M",
        includetext: false
      } as any)
    } catch (err) {
      console.error(err)
    }
  }

  if (pdf417Canvas.value && pdf417Payload) {
    try {
      bwipjs.toCanvas(pdf417Canvas.value, {
        bcid: "pdf417",
        text: pdf417Payload,
        scale: 2.5,
        height: 7,
        columns: 5,
        includetext: false
      } as any)
    } catch (err) {
      console.error(err)
    }
  }
}

async function loadRecord() {
  loading.value = true

  audit.value.operatorRole = (userRole.value as string) || "The Keeper"
  audit.value.operatorName = (userName.value as string) || "Archive Officer"
  audit.value.operatorId = `UID #${userId.value || "1"}`

  const [hw, ip] = await Promise.all([
    gatherHardwareTelemetry(),
    getLocalStationIP()
  ])
  hardware.value = hw
  audit.value.stationIp = ip

  const now = new Date()
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  audit.value.timestamp = `${now.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  })} (${tz})`

  if (holdingId.value) {
    try {
      const res = await axios.get(`/catalogue/holding/${holdingId.value}`)
      if (res.data) {
        book.value = res.data
        if (!book.value.shelf_location && book.value.shelf) {
          book.value.shelf_location = book.value.shelf
        }
        if (!book.value.circulation_status && book.value.availability_status) {
          book.value.circulation_status = book.value.availability_status
        }
      }
    } catch (err) {
      console.error("Could not fetch holding record:", err)
    }
  }

  audit.value.checksum = await generateChecksum(canonicalRecordPayload(book.value))

  loading.value = false
  await nextTick()
  renderBarcodes()
  await checkPageFit()
  await loadPrintHistory()
}

onMounted(() => {
  loadRecord()
})
</script>

<template>
  <div class="print-page-wrapper">
    <!-- Screen Control Toolbar -->
    <header class="no-print screen-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-brand">Athenaeum Archival Dossier</span>
        <span class="toolbar-badge">A4 Monospace Bold</span>
        <span v-if="buttonFeedback" class="feedback-badge">{{ buttonFeedback }}</span>
      </div>
      <div class="toolbar-actions">
        <label class="mode-control">
          <span>Layout</span>
          <select v-model="printMode" @change="showAllFields = printMode === 'detailed'; checkPageFit()">
            <option value="compact">Compact (1 Page)</option>
            <option value="detailed">Detailed (Full Schema)</option>
          </select>
        </label>
        <button type="button" class="btn btn-secondary" @click="showPrintHistory = !showPrintHistory">
          {{ showPrintHistory ? 'Hide History' : 'Print History' }}
        </button>
        <label class="toggle-control">
          <input type="checkbox" v-model="showAllFields" @change="checkPageFit()" />
          <span class="toggle-slider"></span>
          <span class="toggle-label">Full Schema</span>
        </label>
        <button type="button" class="btn btn-primary" @click="triggerPrint">⎙ Print Sheet</button>
        <button type="button" class="btn btn-secondary" @click="recordServerAudit('CANCELLED', 'Operator recorded a cancellation')">Record Cancel</button>
        <button type="button" class="btn btn-secondary" @click="recordServerAudit('VOIDED', 'Manual void by operator')">⚠ Spoilage</button>
        <button type="button" class="btn btn-secondary" @click="handleClose">✕ Close</button>
      </div>
    </header>

    <section class="no-print status-panel" aria-live="polite">
      <strong>Status:</strong> {{ printStatus }}
      <span v-if="pageFitWarning"> · <span class="warning-text">{{ pageFitWarning }}</span></span>
      <div v-if="missingFields.length" class="warning-text">Missing catalogue details: {{ missingFields.join(", ") }}</div>
      <div v-if="showPrintHistory" class="history-list">
        <strong>Previous Print Records:</strong>
        <p v-if="!printHistory.length">No print history returned by backend.</p>
        <ul v-else><li v-for="entry in printHistory" :key="entry.id">{{ entry.timestamp }} — {{ entry.outcome }} — {{ entry.summary }}</li></ul>
      </div>
    </section>

    <!-- Master A4 Sheet Container -->
    <main ref="sheetRef" class="sheet-container" :class="{ 'detailed-layout': printMode === 'detailed' }">
      <div class="sheet-main-content">
        <!-- 1. Forensic Archival Security Ribbon -->
        <section class="security-ribbon">
          <div class="ribbon-row primary-line">
            <div class="ribbon-brand">
              <span class="inst-name">THE ATHENAEUM ARCHIVE &amp; REPOSITORY</span>
              <span class="sep-slash">//</span>
              <span class="dossier-tag">{{ audit.dossierType }}</span>
            </div>
            <div class="ribbon-seal">
              <span>COMPLIANCE: {{ audit.protocolTag }}</span>
            </div>
          </div>

          <div class="ribbon-audit-grid">
            <div><span class="audit-k">OPERATOR:</span> {{ audit.operatorName }} ({{ audit.operatorRole }} &bull; {{ audit.operatorId }})</div>
            <div><span class="audit-k">WORKSTATION:</span> {{ hardware.platform || 'Client reported' }}</div>
            <div><span class="audit-k">HARDWARE ID:</span> {{ hardware.machineUuid || 'Reported' }}</div>
            <div><span class="audit-k">NETWORK:</span> {{ audit.stationIp || '127.0.0.1' }}</div>
            <div><span class="audit-k">PRINT DEVICE:</span> {{ hardware.printerName || 'Spooler' }}</div>
            <div><span class="audit-k">RECORD SHA-256:</span> <span class="seal-digest">{{ audit.checksum }}</span></div>
          </div>
        </section>

        <!-- 2. Primary Title & Cleanly Margined Header QR Block -->
        <section class="identity-header">
          <div class="header-details">
            <div class="record-meta">
              <span class="status-badge">{{ book.circulation_status || book.availability_status || 'AVAILABLE' }}</span>
              <span class="category-tag" v-if="hasVal(book.category)">{{ book.category }}</span>
              <span class="lang-tag" v-if="hasVal(book.language)">{{ book.language }}</span>
            </div>
            <h1 class="item-title">{{ book.title || 'Untitled Holding' }}</h1>
            <p class="item-author">
              <strong>{{ book.author || 'Author Unspecified' }}</strong>
              <span v-if="book.publication_year || book.year"> &bull; {{ book.publication_year || book.year }}</span>
            </p>
          </div>
          <div class="header-qr-block">
            <canvas ref="headerQrCanvas" width="76" height="76" class="qr-canvas"></canvas>
            <span class="qr-caption">ACCESSION: {{ book.accession_no || '—' }}</span>
          </div>
        </section>

        <!-- 3. Master Identifiers Ribbon -->
        <section class="master-id-bar">
          <div class="id-card">
            <span class="id-label">ITEM ID</span>
            <strong class="id-val accent-val">{{ formatVal(book.item_id) }}</strong>
          </div>
          <div class="id-card">
            <span class="id-label">RECORD ID</span>
            <strong class="id-val">{{ formatVal(book.record_id) }}</strong>
          </div>
          <div class="id-card">
            <span class="id-label">SERIAL NO</span>
            <strong class="id-val">{{ formatVal(book.serial_no) }}</strong>
          </div>
          <div class="id-card">
            <span class="id-label">ACCESSION NO</span>
            <strong class="id-val">{{ formatVal(book.accession_no) }}</strong>
          </div>
          <div class="id-card">
            <span class="id-label">WORK ID</span>
            <strong class="id-val">{{ hasVal(book.work_id) ? '#' + book.work_id : '—' }}</strong>
          </div>
        </section>

        <!-- 4. Dense PDF417 Audit Strip -->
        <section class="barcode-strip-section">
          <div class="strip-label">INVENTORY AUDIT MANIFEST (PDF417)</div>
          <div class="strip-canvas-wrapper">
            <canvas ref="pdf417Canvas" class="pdf417-canvas"></canvas>
          </div>
        </section>

        <!-- 5. Archival Description Dossier Sections -->
        <section class="dossier-tables-section">
          <!-- Block A: Cataloguing & Placement -->
          <div class="table-block" v-if="hasBlockA">
            <div class="block-title">A. Cataloguing, Placement &amp; Identifiers</div>
            <div class="field-grid">
              <div class="field-cell" v-if="shouldShow(book.call_no)">
                <span class="cell-label">Call Number</span>
                <span class="cell-value font-bold">{{ formatVal(book.call_no) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.shelf_location || book.shelf)">
                <span class="cell-label">Shelf Location</span>
                <span class="cell-value font-bold">{{ formatVal(book.shelf_location || book.shelf) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.ddc)">
                <span class="cell-label">DDC</span>
                <span class="cell-value">{{ formatVal(book.ddc) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.isbn)">
                <span class="cell-label">ISBN</span>
                <span class="cell-value">{{ formatVal(book.isbn) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.lccn)">
                <span class="cell-label">LCCN</span>
                <span class="cell-value">{{ formatVal(book.lccn) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.oclc_no)">
                <span class="cell-label">OCLC No.</span>
                <span class="cell-value">{{ formatVal(book.oclc_no) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.publisher)">
                <span class="cell-label">Publisher</span>
                <span class="cell-value">{{ formatVal(book.publisher) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.edition_statement || book.edition)">
                <span class="cell-label">Edition</span>
                <span class="cell-value">{{ formatVal(book.edition_statement || book.edition) }}</span>
              </div>
            </div>
          </div>

          <!-- Block B: Textual Lineage & Classification -->
          <div class="table-block" v-if="hasBlockB">
            <div class="block-title">B. Textual Lineage, Classification &amp; Series</div>
            <div class="field-grid">
              <div class="field-cell" v-if="shouldShow(book.genre || book.categories)">
                <span class="cell-label">Genre Signals</span>
                <span class="cell-value">{{ formatVal(book.genre || book.categories) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.work_nature)">
                <span class="cell-label">Work Nature</span>
                <span class="cell-value">{{ formatVal(book.work_nature) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.original_title)">
                <span class="cell-label">Original Title</span>
                <span class="cell-value">{{ formatVal(book.original_title) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.original_author)">
                <span class="cell-label">Original Creator</span>
                <span class="cell-value">{{ formatVal(book.original_author) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.original_language)">
                <span class="cell-label">Original Language</span>
                <span class="cell-value">{{ formatVal(book.original_language) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.translator)">
                <span class="cell-label">Translator</span>
                <span class="cell-value">{{ formatVal(book.translator) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.compiler_editor)">
                <span class="cell-label">Editor / Compiler</span>
                <span class="cell-value">{{ formatVal(book.compiler_editor) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.translation_compilation)">
                <span class="cell-label">Compilation</span>
                <span class="cell-value">{{ formatVal(book.translation_compilation) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.target_audience_era)">
                <span class="cell-label">Audience / Era</span>
                <span class="cell-value">{{ formatVal(book.target_audience_era) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.copyright_status)">
                <span class="cell-label">Copyright</span>
                <span class="cell-value">{{ formatVal(book.copyright_status) }}</span>
              </div>
              <div class="field-cell full-span" v-if="shouldShow(book.series_name || book.series_title)">
                <span class="cell-label">Series Group</span>
                <span class="cell-value">
                  {{ formatVal(book.series_name || book.series_title) }}
                  <span v-if="hasVal(book.volume_number)">&bull; Vol. {{ book.volume_number }}</span>
                  <span v-if="hasVal(book.series_number)">&bull; No. {{ book.series_number }}</span>
                </span>
              </div>
              <div class="field-cell full-span" v-if="shouldShow(book.subject_headings)">
                <span class="cell-label">Subject Headings</span>
                <span class="cell-value">{{ formatVal(book.subject_headings) }}</span>
              </div>
            </div>
          </div>

          <!-- Block C: Physical Holding & Preservation -->
          <div class="table-block" v-if="hasBlockC">
            <div class="block-title">C. Physical Holding &amp; Preservation Details</div>
            <div class="field-grid">
              <div class="field-cell" v-if="shouldShow(book.extent_page_count)">
                <span class="cell-label">Pages / Extent</span>
                <span class="cell-value">{{ formatVal(book.extent_page_count) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.physical_dimensions)">
                <span class="cell-label">Dimensions</span>
                <span class="cell-value">{{ formatVal(book.physical_dimensions) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.binding_type)">
                <span class="cell-label">Binding Style</span>
                <span class="cell-value">{{ formatVal(book.binding_type) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.physical_condition)">
                <span class="cell-label">Physical Condition</span>
                <span class="cell-value font-bold">{{ formatVal(book.physical_condition) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.date_acquired)">
                <span class="cell-label">Acquisition Date</span>
                <span class="cell-value">{{ formatVal(book.date_acquired) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.collection_fonds)">
                <span class="cell-label">Fonds / Collection</span>
                <span class="cell-value">{{ formatVal(book.collection_fonds) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.provenance_source)">
                <span class="cell-label">Provenance</span>
                <span class="cell-value">{{ formatVal(book.provenance_source) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.access_restrictions)">
                <span class="cell-label">Access Policy</span>
                <span class="cell-value">{{ formatVal(book.access_restrictions) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.digital_scan_available)">
                <span class="cell-label">Digital Scan</span>
                <span class="cell-value">{{ formatVal(book.digital_scan_available) }}</span>
              </div>
              <div class="field-cell" v-if="shouldShow(book.ocr_status)">
                <span class="cell-label">OCR Status</span>
                <span class="cell-value">{{ formatVal(book.ocr_status) }}</span>
              </div>
              <div class="field-cell full-span" v-if="shouldShow(book.notes || book.description)">
                <span class="cell-label">Bibliographic Notes</span>
                <span class="cell-value">{{ formatVal(book.notes || book.description) }}</span>
              </div>
              <div class="field-cell full-span" v-if="shouldShow(book.artifactual_notes)">
                <span class="cell-label">Artifactual Notes</span>
                <span class="cell-value">{{ formatVal(book.artifactual_notes) }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Attestation Line -->
        <section class="signature-section">
          <div><strong class="attest-title">OPERATOR ATTESTATION</strong></div>
          <div><span class="audit-k">Prepared by:</span> {{ audit.operatorName }} · {{ audit.operatorId }}</div>
          <div><span class="audit-k">Prepared:</span> {{ audit.timestamp }}</div>
          <div class="signature-line"><span class="audit-k">Officer signature / approval:</span> ______________________________</div>
          <small>This section identifies the logged-in operator; it is not a cryptographic digital signature.</small>
        </section>
      </div>

      <!-- 6. Tear-off Insert Slip (Sticky Bottom) -->
      <footer class="sheet-bottom-section">
        <div class="tear-off-divider">
          <span class="cut-indicator">✂ TEAR-OFF BOOK POCKET INSERT</span>
        </div>
        <div class="pocket-insert-slip">
          <div class="insert-text-col">
            <div class="insert-header">
              <span class="insert-title">{{ book.title || 'Untitled Holding' }}</span>
              <span class="insert-copyright">© ATHENAEUM ARCHIVES</span>
            </div>
            <div class="insert-meta">
              {{ book.author || 'Author Unspecified' }}
              <span v-if="book.publication_year || book.year">&bull; {{ book.publication_year || book.year }}</span>
            </div>
            <div class="insert-grid">
              <div><strong class="slip-k">ITEM ID:</strong> <span class="slip-v">{{ formatVal(book.item_id) }}</span></div>
              <div><strong class="slip-k">SERIAL:</strong> <span class="slip-v">{{ formatVal(book.serial_no) }}</span></div>
              <div><strong class="slip-k">ACCESSION:</strong> <span class="slip-v">{{ formatVal(book.accession_no) }}</span></div>
              <div><strong class="slip-k">WORK ID:</strong> <span class="slip-v">{{ hasVal(book.work_id) ? '#' + book.work_id : '—' }}</span></div>
              <div><strong class="slip-k">CALL NO:</strong> <span class="slip-v">{{ formatVal(book.call_no) }}</span></div>
              <div><strong class="slip-k">SHELF:</strong> <span class="slip-v">{{ formatVal(book.shelf_location || book.shelf) }}</span></div>
              <div><strong class="slip-k">CONDITION:</strong> <span class="slip-v">{{ formatVal(book.physical_condition) }}</span></div>
              <div><strong class="slip-k">STATUS:</strong> <span class="slip-v">{{ book.circulation_status || book.availability_status || 'AVAILABLE' }}</span></div>
            </div>
          </div>
          <div class="insert-barcode-col">
            <canvas ref="pocketQrCanvas" width="60" height="60" class="pocket-qr-canvas"></canvas>
            <span class="pocket-qr-text">{{ book.accession_no || '' }}</span>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<style scoped>
/* Classical Bold Monospace Typewriter Font Stack */
.print-page-wrapper {
  background-color: #e5e7eb;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: "Courier Prime", "Courier New", Courier, monospace;
  font-weight: 700;
  color: #000000;
  -webkit-font-smoothing: antialiased;
}

.screen-toolbar {
  width: 96%;
  max-width: 1200px;
  background: #ffffff;
  border-bottom: 2px solid #000000;
  padding: 8px 16px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-weight: 600;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.toolbar-brand {
  font-weight: 800;
  font-size: 13px;
}

.toolbar-badge {
  font-size: 11px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
}

.feedback-badge {
  font-size: 11px;
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 700;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.mode-control {
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #111827;
}

.mode-control select {
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background-color: #fff;
  height: 32px;
}

.toggle-control {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  height: 32px;
}

.toggle-control input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}

.toggle-slider {
  position: relative;
  width: 30px;
  height: 16px;
  background-color: #d1d5db;
  border-radius: 20px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 10px;
  width: 10px;
  left: 3px;
  bottom: 3px;
  background-color: #ffffff;
  border-radius: 50%;
  transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-control input:checked + .toggle-slider {
  background-color: #2563eb;
}

.toggle-control input:checked + .toggle-slider:before {
  transform: translateX(14px);
}

.toggle-label {
  font-size: 12px;
  font-weight: 700;
  color: #111827;
}

.btn {
  font-size: 12px;
  font-weight: 700;
  padding: 0 10px;
  height: 32px;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background: #000000;
  color: #ffffff;
  border: 1.5px solid #000000;
}

.btn-secondary {
  background: #ffffff;
  border: 1.5px solid #d1d5db;
  color: #111827;
}

.status-panel {
  width: 96%;
  max-width: 1200px;
  box-sizing: border-box;
  margin: 6px auto 0;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #cbd5e1;
  font-size: 12px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.warning-text {
  color: #9a3412;
  margin-top: 4px;
  font-weight: 700;
}

.history-list {
  margin-top: 6px;
  border-top: 1px solid #ddd;
  padding-top: 4px;
}

.history-list ul {
  margin: 4px 0;
  padding-left: 18px;
}

/* Master A4 Sheet Container */
.sheet-container {
  width: 210mm;
  min-height: 297mm;
  box-sizing: border-box;
  background: #ffffff;
  padding: 8mm 12mm;
  margin: 12px auto;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  display: flex;
  flex-direction: column;
}

.sheet-main-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

/* Forensic Security Ribbon (Bold Contrast) */
.security-ribbon {
  border: 2px solid #000000;
  padding: 5px 8px;
  font-size: 8.5px;
  line-height: 1.4;
  background: #fafafa;
  font-weight: 700;
}

.primary-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 900;
  border-bottom: 1.5px solid #000000;
  padding-bottom: 2px;
  margin-bottom: 3px;
}

.ribbon-brand {
  display: flex;
  align-items: center;
  gap: 6px;
}

.inst-name {
  font-weight: 900;
}

.sep-slash {
  color: #000000;
  font-weight: 900;
}

.dossier-tag {
  letter-spacing: 0.05em;
  font-weight: 900;
}

.ribbon-seal {
  font-size: 8.5px;
  letter-spacing: 0.04em;
  font-weight: 900;
}

.ribbon-audit-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 2px 10px;
  color: #000000;
  font-weight: 700;
}

.audit-k {
  font-weight: 900;
}

.seal-digest {
  font-weight: 900;
  letter-spacing: 0.03em;
  color: #000000;
}

/* Identity Header with Clean QR Margin */
.identity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2.5px solid #000000;
  padding: 4px 0 6px 0;
  margin-top: 4px;
}

.header-details {
  flex: 1;
  padding-right: 20px;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.status-badge {
  font-size: 10.5px;
  font-weight: 900;
  border: 2px solid #000000;
  padding: 1px 6px;
}

.category-tag, .lang-tag {
  font-size: 10.5px;
  border: 1.5px solid #000000;
  padding: 1px 6px;
  background: #f3f4f6;
  font-weight: 900;
}

.item-title {
  font-size: 22px;
  font-weight: 900;
  margin: 3px 0;
  line-height: 1.2;
}

.item-author {
  font-size: 13.5px;
  color: #000000;
  font-weight: 800;
  margin: 0;
}

/* Header QR Block: Dedicated Padded Enclosure */
.header-qr-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  margin-left: 16px;
  border-left: 2px solid #000000;
  background-color: #fafafa;
  flex-shrink: 0;
}

.qr-canvas {
  width: 76px;
  height: 76px;
  display: block;
  image-rendering: pixelated;
  margin: 0 auto;
}

.qr-caption {
  font-size: 8.5px;
  font-weight: 900;
  margin-top: 3px;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* Master Identifiers Bar */
.master-id-bar {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  border: 2.5px solid #000000;
  background: #f8fafc;
}

.id-card {
  padding: 4px 6px;
  border-right: 2px solid #000000;
  display: flex;
  flex-direction: column;
}

.id-card:last-child {
  border-right: none;
}

.id-label {
  font-size: 8.5px;
  font-weight: 900;
  letter-spacing: 0.05em;
  color: #000000;
}

.id-val {
  font-size: 13.5px;
  font-weight: 900;
  margin-top: 1px;
  word-break: break-all;
  color: #000000;
}

/* PDF417 Strip */
.barcode-strip-section {
  padding: 2px 4px;
  border: 1.5px solid #000000;
  text-align: center;
}

.strip-label {
  font-size: 8px;
  font-weight: 900;
  letter-spacing: 0.04em;
}

.strip-canvas-wrapper {
  display: flex;
  justify-content: center;
}

.pdf417-canvas {
  max-width: 100%;
  height: 20px;
  image-rendering: pixelated;
}

/* Dossier Tables */
.dossier-tables-section {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 5px;
}

.table-block {
  display: flex;
  flex-direction: column;
  width: 100%;
  border: 2px solid #000000;
  box-sizing: border-box;
}

.block-title {
  font-size: 9.5px;
  font-weight: 900;
  text-transform: uppercase;
  background: #000000;
  color: #ffffff;
  padding: 3px 8px;
  letter-spacing: 0.05em;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  background: #000000;
  gap: 1.5px;
  width: 100%;
  box-sizing: border-box;
}

.field-cell {
  background: #ffffff;
  display: flex;
  padding: 3.5px 8px;
  gap: 8px;
  font-size: 10.5px;
  align-items: baseline;
  font-weight: 700;
}

.full-span {
  grid-column: 1 / -1;
}

.cell-label {
  width: 32%;
  min-width: 95px;
  font-weight: 900;
  color: #000000;
  background: #f3f4f6;
  padding: 1px 4px;
  font-size: 9.5px;
}

.cell-value {
  flex: 1;
  color: #000000;
  font-size: 11px;
  font-weight: 800;
}

.font-bold {
  font-weight: 900;
}

/* Attestation */
.signature-section {
  border: 2px solid #000000;
  padding: 5px 8px;
  margin-top: 3px;
  font-size: 8.5px;
  line-height: 1.4;
  font-weight: 700;
}

.attest-title {
  font-weight: 900;
}

.signature-line {
  margin-top: 3px;
  font-weight: 800;
}

.signature-section small {
  display: block;
  color: #000000;
  font-size: 7.5px;
  font-weight: 700;
}

/* Tear-off Slip (Pinned to Bottom) */
.sheet-bottom-section {
  margin-top: auto;
  width: 100%;
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

.tear-off-divider {
  border-top: 2px dashed #000000;
  position: relative;
  margin-bottom: 6px;
  text-align: center;
}

.cut-indicator {
  display: inline-block;
  position: relative;
  top: -8px;
  background: #ffffff;
  padding: 0 8px;
  font-size: 8.5px;
  color: #000000;
  letter-spacing: 0.05em;
  font-weight: 900;
}

.pocket-insert-slip {
  border: 2px dashed #000000;
  padding: 6px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fafafa;
  box-sizing: border-box;
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

.insert-text-col {
  flex: 1;
  padding-right: 14px;
}

.insert-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1.5px solid #000000;
  padding-bottom: 2px;
  margin-bottom: 4px;
}

.insert-title {
  font-size: 13px;
  font-weight: 900;
}

.insert-copyright {
  font-size: 8.5px;
  font-weight: 900;
}

.insert-meta {
  font-size: 10px;
  color: #000000;
  font-weight: 800;
  margin-bottom: 4px;
}

.insert-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 2px 8px;
  font-size: 9px;
}

.slip-k {
  font-weight: 900;
  color: #000000;
}

.slip-v {
  font-weight: 800;
  color: #000000;
}

.insert-barcode-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.pocket-qr-canvas {
  width: 48px;
  height: 48px;
  image-rendering: pixelated;
}

.pocket-qr-text {
  font-size: 8px;
  font-weight: 900;
  margin-top: 2px;
}

.detailed-layout .sheet-main-content {
  gap: 8px;
}

.detailed-layout .field-cell {
  padding: 4px 6px;
  font-size: 11px;
}

/* Print Directives Clamped to Exact Single-Page A4 */
@media print {
  @page {
    size: A4 portrait;
    margin: 0;
  }

  .no-print {
    display: none !important;
  }

  body, html {
    margin: 0 !important;
    padding: 0 !important;
    background: #ffffff !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    width: 210mm !important;
    height: 297mm !important;
    overflow: hidden !important;
    font-weight: 700 !important;
  }

  .print-page-wrapper {
    background: #ffffff !important;
    padding: 0 !important;
    margin: 0 !important;
    min-height: auto !important;
    height: 297mm !important;
    overflow: hidden !important;
    font-weight: 700 !important;
  }

  .sheet-container {
    width: 210mm !important;
    max-width: 210mm !important;
    height: 295mm !important;
    max-height: 295mm !important;
    margin: 0 !important;
    padding: 6mm 10mm 5mm 10mm !important;
    box-shadow: none !important;
    page-break-after: avoid !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
    font-weight: 700 !important;
  }

  .sheet-bottom-section {
    margin-top: auto !important;
  }

  .table-block,
  .identity-header,
  .master-id-bar,
  .barcode-strip-section,
  .signature-section,
  .sheet-bottom-section,
  .pocket-insert-slip {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }
}
</style>