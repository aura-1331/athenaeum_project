<template>
  <div class="print-manifest-sheet">
    <header class="manifest-header">
      <div class="security-clearance">ATHENAEUM ORBIS // SYSTEM MANIFEST RECORD</div>
      <div class="timestamp-stamp">EXTRACTED: {{ generatedTimestamp }}</div>
    </header>

    <section class="manifest-hero-block">
      <h1 class="manifest-title">{{ book.title }}</h1>
      <div class="manifest-author">
        <span class="lbl">DOCUMENT_CREATOR //</span>
        <span class="val">{{ book.author || 'UNKNOWN AUTHOR' }}</span>
      </div>
    </section>

    <section class="manifest-data-block">
      <h3 class="manifest-section-title">01 // CORE SYSTEM IDENTIFIERS</h3>
      <div class="matrix-table text-mono">
        <div class="matrix-row row-emerald">
          <span class="lbl">RECORD IDENTIFIER</span>
          <span class="val">{{ book.record_id }}</span>
        </div>
        <div class="matrix-row row-amber">
          <span class="lbl">WORK INDEX ID</span>
          <span class="val">#{{ book.work_id }}</span>
        </div>
        <div class="matrix-row row-blue">
          <span class="lbl">ACCESSION SEQUENCE</span>
          <span class="val">{{ book.accession_no }}</span>
        </div>
        <div class="matrix-row">
          <span class="lbl">SERIAL SEQUENCE</span>
          <span class="val">#{{ book.serial_no }}</span>
        </div>
      </div>
    </section>

    <section class="manifest-data-block">
      <h3 class="manifest-section-title">02 // GEOGRAPHIC VECTORS & PARAMETERS</h3>
      <div class="dual-telemetry-grid">
        <div class="telemetry-node"><span class="lbl">SHELF_LOCATION</span><strong class="val text-mono">{{ book.shelf || '---' }}</strong></div>
        <div class="telemetry-node"><span class="lbl">CALL_SIGNATURE</span><strong class="val text-mono">{{ book.call_no || '---' }}</strong></div>
        <div class="telemetry-node"><span class="lbl">TEXT LANGUAGE</span><strong class="val">{{ book.language }}</strong></div>
        <div class="telemetry-node"><span class="lbl">SOURCE LANGUAGE</span><strong class="val">{{ book.original_language || book.language }}</strong></div>
        <div class="telemetry-node"><span class="lbl">CLASSIFICATION</span><strong class="val">{{ book.work_nature || book.genre }}</strong></div>
        <div class="telemetry-node"><span class="lbl">IMPRINT PUBLISHER</span><strong class="val">{{ book.publisher }}</strong></div>
        <div class="telemetry-node"><span class="lbl">TEMPORAL EPOCH</span><strong class="val text-mono">{{ book.year }}</strong></div>
        <div class="telemetry-node"><span class="lbl">ISBN IDENTIFIER</span><strong class="val text-mono">{{ book.isbn || 'N/A' }}</strong></div>
        <div class="telemetry-node full-width"><span class="lbl">DDC INDEX EXTENSION</span><strong class="val text-mono">{{ book.ddc || '---' }}</strong></div>
      </div>
    </section>

    <section class="manifest-data-block">
      <h3 class="manifest-section-title">03 // CURATORIAL NOTATIONS LOG</h3>
      <div class="manifest-notes-canvas">
        {{ book.notes || 'This asset ledger entry is currently verified clear of exceptional administrative annotations.' }}
      </div>
    </section>

    <footer class="manifest-footer-audit text-mono">
      <div class="audit-row">
        <span>STATION_ID: {{ authData.deviceID }}</span>
        <span>IP_V4: {{ authData.ip }}</span>
      </div>
      <div class="audit-row security-border">
        <span>ISSUING_OFFICER: {{ authData.userName }}</span>
        <span class="verified-token">STATUS // SYSTEM_VERIFIED</span>
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
  // Wait minor tick buffer to allow system text styling engines to parse fonts completely
  setTimeout(() => {
    window.print()
    emit('printed')
  }, 500)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=JetBrains+Mono:wght@400;700&display=swap');

/* Hard Reset Overriding Base Screen Styling Properties */
.print-manifest-sheet {
  background-color: #ffffff !important;
  color: #111111 !important;
  font-family: 'JetBrains Mono', monospace !important;
  padding: 40px !important;
  box-sizing: border-box !important;
  width: 100% !important;
  max-width: 8.5in !important; /* Forces layout tracking constraints exactly onto real A4/Letter dimensions */
  margin: 0 auto !important;
  -webkit-font-smoothing: grayscale;
}

.text-mono {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Document Authority Ribbon styling properties */
.manifest-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid #111111;
  padding-bottom: 12px;
  margin-bottom: 40px;
  font-size: 10px;
  font-weight: 700;
  color: #555555;
}

/* Master Title Typography Profiles configuration block */
.manifest-hero-block {
  margin-bottom: 40px;
}

.manifest-title {
  font-family: 'Cinzel', serif !important;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 16px 0;
  color: #000000 !important;
  text-transform: uppercase;
}

.manifest-author {
  font-size: 11px;
}

.manifest-author .lbl {
  color: #777777;
  font-weight: bold;
  margin-right: 6px;
}

.manifest-author .val {
  font-weight: bold;
  color: #111111;
}

/* Data Structure Content Group Rows layout rules */
.manifest-data-block {
  margin-bottom: 36px;
  page-break-inside: avoid; /* Completely safeguards data sheets from cracking right down the center across print bounds */
}

.manifest-section-title {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #555555;
  margin: 0 0 16px 0;
  border-bottom: 1px dashed #cccccc;
  padding-bottom: 6px;
}

/* High Contrast Core Matrix Identifier Block table elements */
.matrix-table {
  border: 1px solid #111111;
  border-radius: 6px;
  overflow: hidden;
}

.matrix-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  font-size: 12px;
  border-bottom: 1px solid #e5e5e5;
}

.matrix-row:last-child {
  border-bottom: none;
}

.matrix-row:nth-child(even) {
  background-color: #f8f9fa !important;
  -webkit-print-color-adjust: exact; /* Instructs browsers to physically force render rows configuration on paper sheets */
  color-adjust: exact;
}

.matrix-row .lbl {
  font-weight: 700;
  color: #555555;
}

.matrix-row .val {
  font-weight: 700;
  color: #111111;
}

/* Alternating Grid System Columns configuration elements */
.dual-telemetry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  overflow: hidden;
}

.telemetry-node {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 11px;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e5e5;
}

.telemetry-node:nth-child(4n+1),
.telemetry-node:nth-child(4n+2) {
  background-color: #f8f9fa !important;
  -webkit-print-color-adjust: exact;
  color-adjust: exact;
}

/* Handle uneven vertical row borders cleanly across the dual split layout */
.telemetry-node:nth-child(odd) {
  border-right: 1px solid #e5e5e5;
}

.telemetry-node.full-width {
  grid-column: span 2;
  border-right: none;
}

.telemetry-node .lbl {
  color: #666666;
  font-weight: 700;
}

.telemetry-node .val {
  color: #111111;
  font-weight: 600;
  text-align: right;
}

/* Curatorial Notation canvas spacing values configuration elements */
.manifest-notes-canvas {
  font-size: 12px;
  line-height: 1.6;
  color: #333333;
  background-color: #f8f9fa !important;
  padding: 20px;
  border-radius: 6px;
  border-left: 3px solid #111111;
  -webkit-print-color-adjust: exact;
  color-adjust: exact;
}

/* System Verification Footer Base Layer properties */
.manifest-footer-audit {
  margin-top: 60px;
  border-top: 1px dashed #111111;
  padding-top: 16px;
  font-size: 9px;
  color: #666666;
  display: flex;
  flex-direction: column;
  gap: 8px;
  page-break-inside: avoid;
}

.audit-row {
  display: flex;
  justify-content: space-between;
}

.security-border {
  border-top: 1px solid #e5e5e5;
  padding-top: 8px;
}

.verified-token {
  font-weight: bold;
  color: #000000 !important;
}

/* Pure Media Query Print Rules Overrides */
@media print {
  body, html {
    background-color: #ffffff !important;
    color: #111111 !important;
  }
}
</style>