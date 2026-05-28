<template>
  <div class="print-label-sheet">
    <header class="label-top-strip text-mono">
      <span>SYSTEM REFERENCE SHEET</span>
      <span>AO // MANIFEST_{{ book.serial_no }}</span>
    </header>

    <div class="label-main-frame">
      <div class="label-column-title">
        <div class="meta-tag">{{ book.category.toUpperCase() }} / {{ book.genre.toUpperCase() }}</div>
        <h1 class="manifest-title">{{ book.title }}</h1>
        <div class="creator-stamp">
          <span class="lbl">COMPILER //</span>
          <span class="val">{{ book.author || 'UNKNOWN AUTHOR' }}</span>
        </div>
      </div>

      <div class="label-column-identifiers text-mono">
        <div class="id-row text-emerald">
          <span class="lbl">RECORD_ID</span>
          <span class="val">{{ book.record_id }}</span>
        </div>
        <div class="id-row text-amber">
          <span class="lbl">WORK_ID</span>
          <span class="val">#{{ book.work_id }}</span>
        </div>
        <div class="id-row text-blue">
          <span class="lbl">ACCESS_NO</span>
          <span class="val">{{ book.accession_no }}</span>
        </div>
      </div>
    </div>

    <div class="label-vectors-strip text-mono">
      <div class="vector-box">
        <span class="lbl">SHELF_LOCATION_VEC</span>
        <span class="val">{{ book.shelf || '---' }}</span>
      </div>
      <div class="vector-box border-left-dashed">
        <span class="lbl">CALL_SIGNATURE_SIG</span>
        <span class="val">{{ book.call_no || '---' }}</span>
      </div>
    </div>

    <div class="label-telemetry-matrix">
      <div class="matrix-node"><span>TEXT_LANGUAGE</span><strong>{{ book.language }}</strong></div>
      <div class="matrix-node"><span>SOURCE_ORIGIN</span><strong>{{ book.original_language || book.language }}</strong></div>
      <div class="matrix-node"><span>CLASSIFICATION</span><strong>{{ book.work_nature || book.genre }}</strong></div>
      <div class="matrix-node"><span>IMPRINT_PUBLISHER</span><strong>{{ book.publisher }}</strong></div>
      <div class="matrix-node"><span>TEMPORAL_EPOCH</span><strong>{{ book.year }}</strong></div>
      <div class="matrix-node"><span>ISBN_IDENTIFIER</span><strong>{{ book.isbn || 'N/A' }}</strong></div>
      <div class="matrix-node full-width-node"><span>DDC_INDEX_EXTENSION</span><strong>{{ book.ddc || '---' }}</strong></div>
    </div>

    <div class="label-annotations-block">
      <span class="block-lbl text-mono">ARCHIVAL_CURATOR_NOTATIONS</span>
      <p class="notes-paragraph">
        {{ book.notes || 'This record index is cleared for public circulation without admin exceptions.' }}
      </p>
    </div>

    <footer class="label-audit-footer text-mono">
      <div class="audit-row">
        <span>STATION_ID: {{ authData.deviceID }}</span>
        <span>DEVICE_IP: {{ authData.ip }}</span>
      </div>
      <div class="audit-row border-top-line">
        <span>COMPILING_OFFICER: {{ authData.userName }}</span>
        <span>VERIFIED: {{ generatedTimestamp }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'

const props = defineProps<{
  book: any
  authData: {
    deviceID: string
    ip: string
    userName: string
  }
}>()

const emit = defineEmits(['printed'])

const generatedTimestamp = computed(() => {
  return new Date().toLocaleString('en-GB', { hour12: false }).toUpperCase()
})

onMounted(() => {
  setTimeout(() => {
    window.print()
    emit('printed')
  }, 500)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=JetBrains+Mono:wght@400;700&display=swap');

.print-label-sheet {
  background-color: #ffffff !important;
  color: #111111 !important;
  font-family: 'JetBrains Mono', monospace !important;
  padding: 48px !important;
  box-sizing: border-box !important;
  width: 100% !important;
  max-width: 8.5in !important;
  margin: 0 auto !important;
  -webkit-font-smoothing: grayscale;
}

.text-mono {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Label Top Strip layout styling rules */
.label-top-strip {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid #111111;
  padding-bottom: 12px;
  font-size: 10px;
  font-weight: bold;
  color: #666666;
}

/* Dual Column Main Framing Layout properties */
.label-main-frame {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 40px;
  padding: 32px 0;
  border-bottom: 1px solid #111111;
  page-break-inside: avoid;
}

.label-column-title {
  display: flex;
  flex-direction: column;
}

.meta-tag {
  font-size: 10px;
  color: #777777;
  font-weight: bold;
  margin-bottom: 12px;
}

.manifest-title {
  font-family: 'Cinzel', serif !important;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.25;
  margin: 0 0 16px 0;
  color: #000000 !important;
  text-transform: uppercase;
}

.creator-stamp {
  font-size: 11px;
}

.creator-stamp .lbl {
  color: #777777;
  font-weight: bold;
}

.creator-stamp .val {
  font-weight: bold;
}

/* Right Identification Token List Rows styling rules */
.label-column-identifiers {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  border-left: 1px solid #e5e5e5;
  padding-left: 32px;
}

.id-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.id-row .lbl {
  color: #777777;
  font-weight: bold;
}

.id-row .val {
  font-weight: bold;
}

.text-emerald .val { color: #16803d !important; }
.text-amber .val { color: #b45309 !important; }
.text-blue .val { color: #1d4ed8 !important; }

/* Vector Spatials display segment boxes alignment configuration */
.label-vectors-strip {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 20px 0;
  border-bottom: 1px solid #111111;
  page-break-inside: avoid;
}

.vector-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vector-box:last-child {
  padding-left: 40px;
}

.border-left-dashed {
  border-left: 1px dashed #cccccc;
}

.vector-box .lbl {
  font-size: 9px;
  color: #777777;
  font-weight: bold;
}

.vector-box .val {
  font-size: 15px;
  font-weight: bold;
  color: #000000;
}

/* Flat Telemetry Data grid nodes block layout */
.label-telemetry-matrix {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 40px;
  padding: 24px 0;
  border-bottom: 1px dashed #cccccc;
  page-break-inside: avoid;
}

.matrix-node {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 11px;
}

.matrix-node span {
  color: #777777;
  font-weight: bold;
  font-size: 10px;
}

.matrix-node strong {
  color: #111111;
  font-weight: 600;
}

.full-width-node {
  grid-column: span 2;
}

/* Archival Annotations Context mapping frame text box area properties */
.label-annotations-block {
  padding: 24px 0;
  border-bottom: 1px solid #111111;
  page-break-inside: avoid;
}

.block-lbl {
  font-size: 9px;
  color: #777777;
  font-weight: bold;
  display: block;
  margin-bottom: 8px;
}

.notes-paragraph {
  font-size: 12px;
  line-height: 1.6;
  color: #333333;
  margin: 0;
}

/* System Verification Running Terminal Audit footer layer layout rules */
.label-audit-footer {
  padding-top: 24px;
  font-size: 9px;
  color: #555555;
  display: flex;
  flex-direction: column;
  gap: 8px;
  page-break-inside: avoid;
}

.audit-row {
  display: flex;
  justify-content: space-between;
}

.border-top-line {
  border-top: 1px solid #e5e5e5;
  padding-top: 8px;
}

@media print {
  body, html {
    background-color: #ffffff !important;
    color: #111111 !important;
  }
}
</style>