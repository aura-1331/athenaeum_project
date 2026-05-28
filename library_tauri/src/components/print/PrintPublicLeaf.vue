<template>
  <div class="print-folio-sheet">
    <header class="folio-header-bar">
      <div class="header-left">ATHENAEUM ORBIS // SERIES CERTIFICATION</div>
      <div class="header-right text-mono">MANIFEST_ID: {{ book.serial_no }}</div>
    </header>

    <main class="folio-main-content">
      <section class="folio-hero-block">
        <div class="category-stamp">{{ book.category.toUpperCase() }} / {{ book.genre.toUpperCase() }}</div>
        <h1 class="manifest-title">{{ book.title }}</h1>
        <p class="author-subtext">Compedited under the registry classification of <strong>{{ book.author || 'Unknown Author' }}</strong></p>
      </section>

      <section class="folio-block block-break">
        <h3 class="section-heading">I // SYSTEM VERIFICATION KEY</h3>
        <div class="sig-grid">
          <div class="sig-node row-emerald">
            <span class="label">RECORD IDENTIFIER</span>
            <span class="value text-mono">{{ book.record_id }}</span>
          </div>
          <div class="sig-node row-amber">
            <span class="label">WORK REGISTER ID</span>
            <span class="value text-mono">#{{ book.work_id }}</span>
          </div>
          <div class="sig-node row-blue">
            <span class="label">ACCESSION NO</span>
            <span class="value text-mono">{{ book.accession_no }}</span>
          </div>
        </div>
      </section>

      <section class="folio-block block-break">
        <h3 class="section-heading">II // BIBLIOGRAPHIC PROFILE VECTORS</h3>
        <div class="vectors-grid">
          <div class="vector-cell">
            <span class="cell-lbl">SHELF_LOCATION</span>
            <span class="cell-val text-mono">{{ book.shelf || '---' }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">CALL_SIGNATURE</span>
            <span class="cell-val text-mono">{{ book.call_no || '---' }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">TEXT LANGUAGE</span>
            <span class="cell-val">{{ book.language }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">SOURCE LANGUAGE</span>
            <span class="cell-val">{{ book.original_language || book.language }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">CLASSIFICATION</span>
            <span class="cell-val">{{ book.work_nature || book.genre }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">IMPRINT PUBLISHER</span>
            <span class="cell-val">{{ book.publisher }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">TEMPORAL EPOCH</span>
            <span class="cell-val text-mono">{{ book.year }}</span>
          </div>
          <div class="vector-cell">
            <span class="cell-lbl">ISBN IDENTIFIER</span>
            <span class="cell-val text-mono">{{ book.isbn || 'N/A' }}</span>
          </div>
        </div>
        <div class="vector-cell-full">
          <span class="cell-lbl">DDC INDEX EXTENSION</span>
          <span class="cell-val text-mono">{{ book.ddc || '---' }}</span>
        </div>
      </section>

      <section class="folio-block block-break">
        <h3 class="section-heading">III // CURATORIAL MANAGEMENT SUMMARY</h3>
        <div class="notes-canvas-frame">
          {{ book.notes || 'This asset entry profile has been verified as clean and completely clear of administrative annotations.' }}
        </div>
      </section>
    </main>

    <footer class="folio-audit-footer text-mono">
      <div class="audit-strip-top">
        <span>STATION_ID: {{ authData.deviceID }}</span>
        <span>IP_ADDRESS: {{ authData.ip }}</span>
      </div>
      <div class="audit-strip-bottom">
        <span>PRINTED BY AUTHORIZED USER: {{ authData.userName }}</span>
        <span class="timestamp-string">TIMESTAMP: {{ generatedTimestamp }}</span>
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
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=JetBrains+Mono:wght@400;700&display=swap');

.print-folio-sheet {
  background-color: #ffffff !important;
  color: #1a1a1a !important;
  font-family: 'Inter', -apple-system, sans-serif !important;
  padding: 60px !important;
  box-sizing: border-box !important;
  width: 100% !important;
  max-width: 8.5in !important;
  margin: 0 auto !important;
  -webkit-font-smoothing: grayscale;
}

.text-mono {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Folio Context Ribbon Header */
.folio-header-bar {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #e5e5e0;
  padding-bottom: 14px;
  margin-bottom: 56px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #8c8c85;
}

/* Title Profile Section Block */
.folio-hero-block {
  margin-bottom: 56px;
}

.category-stamp {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #8c8c85;
  margin-bottom: 16px;
  letter-spacing: 0.5px;
}

.manifest-title {
  font-family: 'Cinzel', serif !important;
  font-size: 34px;
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 16px 0;
  color: #000000 !important;
  text-transform: uppercase;
  letter-spacing: -0.5px;
}

.author-subtext {
  font-size: 13px;
  color: #4a4a45;
  margin: 0;
}

.author-subtext strong {
  color: #000000;
}

/* Master Segment Structural Partitions */
.folio-block {
  margin-bottom: 44px;
}

.block-break {
  page-break-inside: avoid;
}

.section-heading {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #000000;
  margin: 0 0 20px 0;
  text-transform: uppercase;
}

/* Identification Fields Blocks */
.sig-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.sig-node {
  background-color: #fafaf9 !important;
  border-left: 2px solid #1a1a1a;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  -webkit-print-color-adjust: exact;
  color-adjust: exact;
}

.sig-node .label {
  font-size: 9px;
  font-weight: 700;
  color: #8c8c85;
  letter-spacing: 0.5px;
}

.sig-node .value {
  font-size: 14px;
  font-weight: 700;
  color: #000000;
}

.row-emerald { border-left-color: #10b981 !important; }
.row-amber { border-left-color: #f59e0b !important; }
.row-blue { border-left-color: #3b82f6 !important; }

/* Dynamic Specifications Matrix Sheet Grid */
.vectors-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px 20px;
  border-top: 1px solid #f0f0ed;
  padding-top: 24px;
}

.vector-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vector-cell-full {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 20px;
  border-top: 1px dashed #e5e5e0;
  padding-top: 16px;
  width: 100%;
}

.cell-lbl {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-weight: 700;
  color: #8c8c85;
}

.cell-val {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
}

/* Notes Text Display Container */
.notes-canvas-frame {
  font-size: 13px;
  line-height: 1.65;
  color: #333330;
  background-color: #fafaf9 !important;
  padding: 24px;
  border: 1px solid #e5e5e0;
  -webkit-print-color-adjust: exact;
  color-adjust: exact;
}

/* Archival Running Audit Footer Base block */
.folio-audit-footer {
  margin-top: 64px;
  border-top: 1px solid #000000;
  padding-top: 16px;
  font-size: 9px;
  color: #8c8c85;
  display: flex;
  flex-direction: column;
  gap: 8px;
  page-break-inside: avoid;
}

.audit-strip-top, .audit-strip-bottom {
  display: flex;
  justify-content: space-between;
}

.audit-strip-bottom {
  font-weight: 700;
  color: #1a1a1a;
}

@media print {
  body, html {
    background-color: #ffffff !important;
    color: #1a1a1a !important;
  }
}
</style>