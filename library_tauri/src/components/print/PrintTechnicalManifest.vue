<template>
  <div class="print-split-sheet">
    <header class="split-header-row">
      <div class="header-tag">ATHENAEUM ORBIS // DATA ARCHIVE SHEET</div>
      <div class="header-timestamp text-mono">GEN_TIME: {{ generatedTimestamp }}</div>
    </header>

    <main class="split-framework-body">
      <section class="split-layout-section">
        <div class="index-margin-column text-mono">[01]</div>
        <div class="content-data-column">
          <div class="path-routing-tag">{{ book.category.toUpperCase() }} <span class="divider-slash">/</span> {{ book.genre.toUpperCase() }}</div>
          <h1 class="manifest-title">{{ book.title }}</h1>
          <p class="author-attribution">DOCUMENT CREATOR: <span class="name-underline">{{ book.author || 'UNKNOWN AUTHOR' }}</span></p>
        </div>
      </section>

      <section class="split-layout-section">
        <div class="index-margin-column text-mono">[02]</div>
        <div class="content-data-column">
          <div class="token-linear-strip text-mono">
            <div class="token-cell color-emerald">
              <span class="label">RECORD IDENTIFIER</span>
              <span class="value">{{ book.record_id }}</span>
            </div>
            <div class="token-cell color-amber">
              <span class="label">WORK REGISTER KEY</span>
              <span class="value">#{{ book.work_id }}</span>
            </div>
            <div class="token-cell color-blue">
              <span class="label">ACCESSION SEQUENCE</span>
              <span class="value">{{ book.accession_no }}</span>
            </div>
            <div class="token-cell">
              <span class="label">SERIAL METRIC ID</span>
              <span class="value">#{{ book.serial_no }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="split-layout-section">
        <div class="index-margin-column text-mono">[03]</div>
        <div class="content-data-column">
          <div class="coordinates-split-row">
            <div class="vector-block">
              <span class="lbl-tag">SHELF_LOCATION_VEC</span>
              <span class="val-tag text-mono">{{ book.shelf || '---' }}</span>
            </div>
            <div class="vector-block">
              <span class="lbl-tag">CALL_SIGNATURE_SIG</span>
              <span class="val-tag text-mono">{{ book.call_no || '---' }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="split-layout-section">
        <div class="index-margin-column text-mono">[04]</div>
        <div class="content-data-column">
          <div class="telemetry-linear-table">
            <div class="table-node"><span>TEXT LANGUAGE</span><strong>{{ book.language }}</strong></div>
            <div class="table-node"><span>SOURCE ORIGIN</span><strong>{{ book.original_language || book.language }}</strong></div>
            <div class="table-node"><span>WORK STRUCTURE</span><strong>{{ book.work_nature || book.genre }}</strong></div>
            <div class="table-node"><span>IMPRINT / PUB</span><strong>{{ book.publisher }}</strong></div>
            <div class="table-node"><span>TEMPORAL TIMESTAMP</span><strong>{{ book.year }}</strong></div>
            <div class="table-node"><span>ISBN IDENTIFIER</span><strong>{{ book.isbn || 'N/A' }}</strong></div>
            <div class="table-node full-width"><span>DDC INDEX EXTENSION</span><strong>{{ book.ddc || '---' }}</strong></div>
          </div>
        </div>
      </section>

      <section class="split-layout-section">
        <div class="index-margin-column text-mono">[05]</div>
        <div class="content-data-column">
          <div class="annotations-canvas">
            <span class="canvas-lbl-tag text-mono">CURATORIAL_NOTATIONS_LOG</span>
            <p class="notes-text">
              {{ book.notes || 'This record index data profile has been verified clear of public circulation exceptions.' }}
            </p>
          </div>
        </div>
      </section>
    </main>

    <footer class="split-audit-footer text-mono">
      <div class="audit-cell">STATION_ID // {{ authData.deviceID }}</div>
      <div class="audit-cell">NETWORK_IP // {{ authData.ip }}</div>
      <div class="audit-cell">COMPILING_OFFICER // {{ authData.userName }}</div>
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

.print-split-sheet {
  background-color: #ffffff !important;
  color: #111111 !important;
  font-family: 'JetBrains Mono', monospace !important;
  padding: 50px !important;
  box-sizing: border-box !important;
  width: 100% !important;
  max-width: 8.5in !important;
  margin: 0 auto !important;
  -webkit-font-smoothing: grayscale;
}

.text-mono {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Header Runner Styling elements */
.split-header-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 2px solid #111111;
  padding-bottom: 14px;
  margin-bottom: 40px;
}

.header-tag {
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.5px;
}

.header-timestamp {
  font-size: 9px;
  color: #666666;
}

/* Central Split Architecture Layout Columns Grid configuration rules */
.split-framework-body {
  display: flex;
  flex-direction: column;
}

.split-layout-section {
  display: grid;
  grid-template-columns: 80px 1fr;
  padding: 24px 0;
  border-bottom: 1px solid #e5e5e5;
  page-break-inside: avoid;
}

.index-margin-column {
  font-size: 11px;
  font-weight: bold;
  color: #cccccc;
  padding-top: 2px;
}

.content-data-column {
  display: flex;
  flex-direction: column;
}

/* Column 1 Data Elements Profiles elements formatting */
.path-routing-tag {
  font-size: 10px;
  font-weight: 700;
  color: #777777;
  margin-bottom: 12px;
  text-transform: uppercase;
}

.divider-slash {
  color: #111111;
}

.manifest-title {
  font-family: 'Cinzel', serif !important;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 14px 0;
  color: #000000 !important;
  text-transform: uppercase;
}

.author-attribution {
  font-size: 11px;
  color: #555555;
  margin: 0;
}

.author-attribution .name-underline {
  color: #111111;
  font-weight: bold;
  border-bottom: 1px solid #111111;
}

/* Linear Stripe Nodes block properties for Token section */
.token-linear-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  width: 100%;
}

.token-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.token-cell .label {
  font-size: 9px;
  font-weight: 700;
  color: #777777;
}

.token-cell .value {
  font-size: 13px;
  font-weight: 700;
}

.color-emerald .value { color: #16803d !important; }
.color-amber .value { color: #b45309 !important; }
.color-blue .value { color: #1d4ed8 !important; }

/* Horizontal Split Vectors rows alignment blocks */
.coordinates-split-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 100%;
}

.vector-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lbl-tag {
  font-size: 9px;
  color: #777777;
  font-weight: 700;
}

.val-tag {
  font-size: 16px;
  font-weight: bold;
  color: #000000;
}

/* Structured Telemetry Data rows stack table mapping elements */
.telemetry-linear-table {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 48px;
  width: 100%;
}

.table-node {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 11px;
  border-bottom: 1px dashed #e5e5e5;
  padding-bottom: 6px;
}

.table-node span {
  color: #777777;
  font-weight: 700;
}

.table-node strong {
  color: #111111;
  font-weight: 600;
}

.table-node.full-width {
  grid-column: span 2;
}

/* Context Annotations Canvas styling properties container */
.annotations-canvas {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.canvas-lbl-tag {
  font-size: 9px;
  color: #777777;
  font-weight: 700;
}

.notes-text {
  font-size: 12px;
  line-height: 1.6;
  color: #333333;
  margin: 0;
}

/* Base System Audit Verification footer ribbon text container */
.split-audit-footer {
  margin-top: 48px;
  border-top: 2px solid #111111;
  padding-top: 16px;
  font-size: 9px;
  color: #555555;
  display: flex;
  justify-content: space-between;
  page-break-inside: avoid;
}

.audit-cell {
  font-weight: 700;
}

@media print {
  body, html {
    background-color: #ffffff !important;
    color: #111111 !important;
  }
}
</style>