<template>
  <div class="register-print-sheet">
    <!-- Master Header -->
    <header class="sheet-header">
      <div class="brand-block">
        <h1>ATHENAEUM ORBIS</h1>
        <p class="subtitle">CENTRAL ACCESSION REGISTER & HOLDINGS LEDGER</p>
      </div>
      <div class="meta-block">
        <div><strong>GENERATED:</strong> {{ generatedAt }}</div>
        <div><strong>FILTER APPLIED:</strong> {{ filterSummary }}</div>
        <div><strong>RECORD COUNT:</strong> {{ books.length }} VOLUMES</div>
      </div>
    </header>

    <!-- Ledger Table -->
    <table class="ledger-table">
      <thead>
        <tr>
          <th style="width: 10%;">ACC NO</th>
          <th style="width: 34%;">TITLE</th>
          <th style="width: 22%;">AUTHOR</th>
          <th style="width: 13%;">CATEGORY</th>
          <th style="width: 13%;">GENRE</th>
          <th style="width: 8%;">LANG</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in books" :key="item.serial_no || item.accession_no">
          <td class="mono">{{ item.accession_no || '—' }}</td>
          <td class="title-cell">{{ item.title }}</td>
          <td>{{ item.author || 'UNKNOWN' }}</td>
          <td>{{ item.category || '—' }}</td>
          <td>{{ item.genre || '—' }}</td>
          <td>{{ item.language || '—' }}</td>
        </tr>
        <tr v-if="books.length === 0">
          <td colspan="6" class="empty-notice">No holdings match the specified filter criteria.</td>
        </tr>
      </tbody>
    </table>

    <!-- Ledger Sign-Off (Appears directly after data) -->
    <div class="ledger-seal-block">
      <div class="seal-line"></div>
      <div class="seal-content">
        <span>ATHENAEUM VAULT // OFFICIAL LEDGER EXTRACT</span>
        <span>END OF REGISTER</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

defineProps<{
  books: any[]
  filterSummary: string
}>()

const emit = defineEmits(['printed'])

function getIndianFormattedDate(): string {
  const now = new Date()
  const day = String(now.getDate()).padStart(2, '0')
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const year = now.getFullYear()
  const weekday = now.toLocaleDateString('en-IN', { weekday: 'long' })
  const time = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })

  return `${day}/${month}/${year} ${weekday}, ${time}`
}

const generatedAt = ref(getIndianFormattedDate())

onMounted(() => {
  document.body.classList.add('batch-print-active')

  setTimeout(() => {
    window.print()
    document.body.classList.remove('batch-print-active')
    emit('printed')
  }, 200)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&display=swap');

@media screen {
  .register-print-sheet {
    display: none !important;
  }
}

@media print {
  @page {
    size: A4 portrait;
    margin: 14mm 14mm 16mm 14mm;
  }

  :global(html),
  :global(body),
  :global(#app),
  :global(.app) {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }

  .register-print-sheet {
    display: block !important;
    width: 100% !important;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }

  .sheet-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2pt solid #000000;
    padding-bottom: 6px;
    margin-bottom: 12px;
  }

  .brand-block h1 {
    font-size: 16pt;
    margin: 0;
    letter-spacing: 0.5px;
    font-weight: 800;
  }

  .subtitle {
    font-size: 7.5pt;
    letter-spacing: 1px;
    margin-top: 3px;
    color: #333333;
    font-family: monospace;
  }

  .meta-block {
    text-align: right;
    font-size: 8pt;
    line-height: 1.5;
  }

  /* Standard tabular print flow */
  .ledger-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    background: transparent !important;
  }

  /* Thead repeats automatically at the top of every new page */
  .ledger-table thead {
    display: table-header-group;
  }

  .ledger-table th {
    border-top: 1.5pt solid #000000;
    border-bottom: 1.5pt solid #000000;
    padding: 6px 4px;
    text-align: left;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    background: #ffffff !important;
  }

  .ledger-table td {
    border-bottom: 0.5pt solid #d1d5db;
    padding: 6px 4px;
    vertical-align: top;
    background: transparent !important;
  }

  /* Guarantees no row ever slices in half across pages */
  .ledger-table tr {
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }

  .title-cell {
    font-weight: 600;
    font-style: italic;
  }

  .mono {
    font-family: monospace;
    font-size: 8pt;
    font-weight: 600;
  }

  .empty-notice {
    text-align: center;
    padding: 24px 0 !important;
    font-style: italic;
    color: #555555;
  }

  .ledger-seal-block {
    margin-top: 18px;
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .seal-line {
    border-top: 0.5pt solid #999999;
    margin-bottom: 6px;
  }

  .seal-content {
    display: flex;
    justify-content: space-between;
    font-size: 7pt;
    font-style: italic;
    color: #444444;
  }
}
</style>