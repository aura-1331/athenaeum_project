<template>
  <div class="print-blueprint-sheet">
    <header class="blueprint-header">
      <div class="header-left">
        <span class="system-title">ATHENAEUM ORBIS // SPEC_LEAF_MANIFEST</span>
        <span class="classification-path">[ {{ book.category.toUpperCase() }} // {{ book.genre.toUpperCase() }} ]</span>
      </div>
      <div class="header-right text-mono">
        SYS_VERIFICATION: CLEAR // {{ generatedTimestamp }}
      </div>
    </header>

    <main class="blueprint-content-body">
      <section class="identity-section">
        <div class="index-marker">NODE_01</div>
        <div class="hero-block">
          <h1 class="manifest-title">{{ book.title }}</h1>
          <div class="author-line">
            <span class="lbl">DOCUMENT_CREATOR:</span>
            <span class="val">{{ book.author || 'UNKNOWN' }}</span>
          </div>
        </div>
      </section>

      <section class="blueprint-row identifiers-matrix">
        <div class="index-marker">NODE_02</div>
        <div class="matrix-grid text-mono">
          <div class="matrix-cell">
            <span class="cell-lbl">RECORD IDENTIFIER</span>
            <span class="cell-val text-emerald">{{ book.record_id }}</span>
          </div>
          <div class="matrix-cell border-left">
            <span class="cell-lbl">WORK INDEX ID</span>
            <span class="cell-val text-amber">#{{ book.work_id }}</span>
          </div>
          <div class="matrix-cell border-left">
            <span class="cell-lbl">ACCESSION SEQUENCE</span>
            <span class="cell-val text-blue">{{ book.accession_no }}</span>
          </div>
          <div class="matrix-cell border-left">
            <span class="cell-lbl">SERIAL INDEX</span>
            <span class="cell-val">#{{ book.serial_no }}</span>
          </div>
        </div>
      </section>

      <section class="blueprint-row coordinates-section">
        <div class="index-marker">NODE_03</div>
        <div class="coordinates-grid">
          <div class="coord-box">
            <span class="lbl">SHELF_LOCATION_VEC</span>
            <span class="val text-mono">{{ book.shelf || '---' }}</span>
          </div>
          <div class="coord-box border-left">
            <span class="lbl">CALL_SIGNATURE_SIG</span>
            <span class="val text-mono">{{ book.call_no || '---' }}</span>
          </div>
        </div>
      </section>

      <section class="blueprint-row technical-specs-section">
        <div class="index-marker">NODE_04</div>
        <div class="specs-linear-list">
          <div class="spec-line"><span>TEXT LANGUAGE</span><strong>{{ book.language }}</strong></div>
          <div class="spec-line"><span>SOURCE LANGUAGE</span><strong>{{ book.original_language || book.language }}</strong></div>
          <div class="spec-line"><span>CLASSIFICATION</span><strong>{{ book.work_nature || book.genre }}</strong></div>
          <div class="spec-line"><span>IMPRINT PUBLISHER</span><strong>{{ book.publisher }}</strong></div>
          <div class="spec-line"><span>TEMPORAL EPOCH</span><strong>{{ book.year }}</strong></div>
          <div class="spec-line"><span>ISBN IDENTIFIER</span><strong>{{ book.isbn || 'N/A' }}</strong></div>
          <div class="spec-line"><span>DDC INDEX EXTENSION</span><strong>{{ book.ddc || '---' }}</strong></div>
        </div>
      </section>

      <section class="blueprint-row annotations-section">
        <div class="index-marker">NODE_05</div>
        <div class="annotations-wrapper">
          <span class="lbl">CURATORIAL_NOTATIONS_LOG</span>
          <p class="notes-text">
            {{ book.notes || 'This asset ledger entry is currently verified clear of exceptional administrative annotations.' }}
          </p>
        </div>
      </section>
    </main>

    <footer class="blueprint-audit-footer text-mono">
      <div class="audit-col">STATION_ID // {{ authData.deviceID }}</div>
      <div class="audit-col">IP_V4 // {{ authData.ip }}</div>
      <div class="audit-col">ISSUING_OFFICER // {{ authData.userName }}</div>
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

.print-blueprint-sheet {
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

/* Header Architectural Strip */
.blueprint-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 2px solid #111111;
  padding-bottom: 16px;
  margin-bottom: 48px;
}

.system-title {
  font-weight: 700;
  font-size: 11px;
}

.classification-path {
  font-size: 10px;
  color: #666666;
  margin-left: 12px;
}

.header-right {
  font-size: 9px;
  color: #666666;
}

/* Layout Content Mapping Split Lines */
.blueprint-content-body {
  display: flex;
  flex-direction: column;
}

.blueprint-row, .identity-section {
  display: grid;
  grid-template-columns: 80px 1fr;
  border-bottom: 1px solid #e5e5e5;
  padding: 24px 0;
  page-break-inside: avoid;
}

.index-marker {
  font-size: 10px;
  font-weight: 700;
  color: #999999;
  letter-spacing: 0.5px;
  padding-top: 4px;
}

/* Core Title Data Blocks styling rules */
.identity-section {
  padding-top: 0;
}

.manifest-title {
  font-family: 'Cinzel', serif !important;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 12px 0;
  color: #000000 !important;
  text-transform: uppercase;
}

.author-line {
  font-size: 11px;
}

.author-line .lbl {
  color: #777777;
  margin-right: 6px;
}

.author-line .val {
  font-weight: bold;
}

/* Asymmetrical Row Configurations elements formatting */
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  width: 100%;
}

.matrix-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 16px;
}

.matrix-cell:first-child {
  padding-left: 0;
}

.matrix-cell.border-left {
  border-left: 1px solid #e5e5e5;
}

.cell-lbl {
  font-size: 9px;
  font-weight: 700;
  color: #666666;
}

.cell-val {
  font-size: 13px;
  font-weight: 700;
}

/* Separate highlight token ink shades on raw white paper background sheets */
.text-emerald { color: #15803d !important; }
.text-amber { color: #b45309 !important; }
.text-blue { color: #1d4ed8 !important; }

/* Coordinates Layout block nodes mapping */
.coordinates-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 100%;
}

.coord-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 16px;
}

.coord-box:first-child {
  padding-left: 0;
}

.coord-box.border-left {
  border-left: 1px solid #e5e5e5;
}

.coord-box .lbl {
  font-size: 9px;
  color: #666666;
  font-weight: 700;
}

.coord-box .val {
  font-size: 18px;
  font-weight: 700;
  color: #000000;
}

/* Full Width Multi Grid Specifications List structural mapping elements */
.specs-linear-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 48px;
  width: 100%;
}

.spec-line {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 11px;
  border-bottom: 1px dashed #eaeaea;
  padding-bottom: 6px;
}

.spec-line span {
  color: #666666;
  font-weight: 700;
}

.spec-line strong {
  color: #111111;
  font-weight: 600;
}

/* Annotations Text Mapping Frame container */
.annotations-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.annotations-wrapper .lbl {
  font-size: 9px;
  color: #666666;
  font-weight: 700;
}

.notes-text {
  font-size: 12px;
  line-height: 1.6;
  color: #333333;
  margin: 0;
}

/* Base Terminal Verification Footer layout mapping elements */
.blueprint-audit-footer {
  margin-top: 48px;
  border-top: 2px solid #111111;
  padding-top: 16px;
  font-size: 9px;
  color: #444444;
  display: flex;
  justify-content: space-between;
  page-break-inside: avoid;
}

.audit-col {
  font-weight: 700;
}

@media print {
  body, html {
    background-color: #ffffff !important;
    color: #111111 !important;
  }
}
</style>