<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"
import phoenixLogo from "@/assets/logo.png"
import PrintLayout from "@/components/print/PrintLayout.vue";

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const book = ref<any>(null)
const folioContent = ref<HTMLElement | null>(null)
const isPrinting = ref(false)

// Mock Audit Data - In a real app, pull these from your Auth/System state
const auditData = ref({
  deviceID: "VAULT-MAIN-STATION-01",
  ip: "192.168.1.105", 
  userName: "Authorized Architect" 
})

function triggerPrint() {
  isPrinting.value = true
  // The PrintLayout component will handle its own window.print() on mount
}

function finishPrinting() {
  // This is called when the print dialog closes
  isPrinting.value = false
}
async function fetchBookDetails() {
  loading.value = true
  const id = route.params.id
  try {
    const response = await axios.get(`/catalogue/${id}`)
    book.value = response.data
    
    // Reset scroll to top when new data loads
    await nextTick()
    if (folioContent.value) {
      folioContent.value.scrollTop = 0
    }
  } catch (err) {
    console.error("Connection severed:", err)
  } finally {
    loading.value = false
  }
}

// Ensure the page refreshes when the ID in the URL changes via Nav buttons
watch(() => route.params.id, () => {
  fetchBookDetails()
})

const titleParts = computed(() => {
  if (!book.value?.title) return { first: '', rest: '' };
  try {
    const segmenter = new Intl.Segmenter('ml', { granularity: 'grapheme' });
    const segments = Array.from(segmenter.segment(book.value.title));
    return {
      first: segments[0]?.segment || '',
      rest: segments.slice(1).map(s => s.segment).join('').trim()
    };
  } catch (e) {
    return { first: book.value.title.charAt(0), rest: book.value.title.substring(1) };
  }
});

function goToRecord(direction: 'next' | 'prev') {
  const currentId = parseInt(route.params.id as string)
  const newId = direction === 'next' ? currentId + 1 : currentId - 1
  if (newId > 0) {
    router.push(`/details/${newId}`)
  }
}

function handlePrint() {
  window.print()
}
function closeWindow() {
  window.close()
}
function editRecord() {
  if (book.value?.serial_no) {
    router.push({ 
      name: 'edit-item', 
      params: { id: book.value.serial_no } 
    })
  }
}


onMounted(() => fetchBookDetails())
</script>

<template>
  <div class="athenaeum-vault">
    <div v-if="loading" class="vault-loader">Consulting the Orbis...</div>

    <div v-else-if="book" class="vault-container">
      <aside class="mahogany-spine">
        <div class="spine-top">
          <img :src="phoenixLogo" alt="Seal" class="phoenix-seal" />
          <h2 class="inst-name">Athenaeum<br>Orbis</h2>
        </div>
        <div class="spine-data">
          <div class="spine-group"><label>SL No</label><div class="val">{{ book.serial_no || '---' }}</div></div>
          <div class="spine-group"><label>Accession No</label><div class="val">{{ book.accession_no || '---' }}</div></div>
        </div>
        <div class="spine-motto">NON OMNIA SCRIBUNTUR, SED OMNIA SERVANTUR</div>
      </aside>

      <main class="folio-parchment">
        <header class="folio-header">
          <div class="cat-path">{{ book.category }} <span class="sep">/</span> {{ book.genre }}</div>
          <div class="title-container">
            <span class="drop-cap">{{ titleParts.first }}</span>
            <h1 class="book-title">{{ titleParts.rest }}</h1>
          </div>
          <p class="book-author">By the hand of <strong>{{ book.author || 'Unknown' }}</strong></p>
        </header>

        <div class="folio-content" ref="folioContent">
          <section class="ledger-section">
            <h3 class="section-title">I. Retrieval Coordinates</h3>
            <div class="coord-stack">
              <div class="coord-box"><label>Shelf Location</label><div class="val">{{ book.shelf }}</div></div>
              <div class="coord-box"><label>Call Number</label><div class="val">{{ book.call_no }}</div></div>
            </div>
          </section>

          <section class="ledger-section">
            <h3 class="section-title">II. Bibliographic & Linguistic Ledger</h3>
            <div class="master-ledger">
              <div class="ledger-row"><span>Language</span><strong>{{ book.language }}</strong></div>
              <div class="ledger-row"><span>Original Language</span><strong>{{ book.original_language || book.language }}</strong></div>
              <div class="ledger-row"><span>Work Nature</span><strong>{{ book.work_nature || book.genre }}</strong></div>
              <div class="ledger-row"><span>Publisher</span><strong>{{ book.publisher }}</strong></div>
              <div class="ledger-row"><span>Year of Release</span><strong>{{ book.year }}</strong></div>
              <div class="ledger-row"><span>ISBN Identifier</span><strong>{{ book.isbn || 'N/A' }}</strong></div>
              <div class="ledger-row"><span>DDC Index</span><strong>{{ book.ddc || '---' }}</strong></div>
            </div>
          </section>

          <section class="ledger-section">
            <h3 class="section-title">III. Curatorial Annotations</h3>
            <div class="notes-box">
              {{ book.notes || 'This record is currently free of administrative notations.' }}
            </div>
          </section>
        </div>

        <footer class="folio-footer">
  <div class="nav-group">
    <button class="btn-nav" @click="closeWindow">← Return to Ledger</button>
    <button class="btn-nav" @click="goToRecord('prev')">← Previous</button>
    <button class="btn-nav" @click="goToRecord('next')">Next →</button>
  </div>
  <div class="action-group">
    <button class="btn-action edit" @click="editRecord">Edit Record</button>
    <button class="btn-action print" @click="triggerPrint">Print Folio</button>
  </div>
</footer>
              </main>
    </div>
  </div>
  <div v-if="isPrinting" class="print-mount-point">
    <PrintLayout 
      :book="book" 
      :authData="auditData" 
      @printed="finishPrinting" 
    />
  </div>
</template>

<style scoped>
/* 1. ROOT & SCROLLBAR SUPPRESSION */
.athenaeum-vault {
  --mahogany: #250906; --gold: #d4af37; --parchment: #f2e8cf; --ink: #111; --blood: #8b0000;
  background: #000; 
  height: 100vh; 
  width: 100vw; 
  display: flex; 
  overflow: hidden !important; /* Kill edge bars */
}

.vault-container { 
  display: flex; 
  width: 100%; 
  height: 100%; 
  overflow: hidden !important;
}

/* 2. SIDEBAR & LOGO ALIGNMENT */
.mahogany-spine {
  width: 320px; 
  min-width: 320px; 
  background: var(--mahogany); 
  color: var(--gold);
  padding: 40px; 
  border-right: 4px solid #1a0504; 
  display: flex; 
  flex-direction: column; 
  position: relative;
}

.spine-top {
  display: flex;
  flex-direction: column;
  align-items: center; 
  text-align: center;
  margin-bottom: 30px;
  width: 100%;
}

.phoenix-seal {
  width: 160px;
  height: auto;
  margin: 0 auto 15px; 
  display: block;
  mix-blend-mode: multiply; 
}

.inst-name {
  font-family: 'Playfair Display', serif;
  font-size: 22px;
  text-transform: uppercase;
  line-height: 1.2;
  color: var(--gold);
  letter-spacing: 2px;
}

.spine-data { flex-grow: 1; margin-top: 30px; }
.spine-group { margin-bottom: 25px; border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding-bottom: 8px; }
.spine-group label { display: block; font-size: 10px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; opacity: 0.8; }
.spine-group .val { font-size: 26px; font-weight: 900; color: #fff; margin-top: 5px; }
.spine-motto { position: absolute; bottom: 30px; right: 10px; writing-mode: vertical-rl; transform: rotate(180deg); font-size: 10px; letter-spacing: 4px; opacity: 0.15; }

/* 3. FOLIO PARCHMENT */
.folio-parchment {
  flex-grow: 1;
  background: var(--parchment);
  display: flex;
  flex-direction: column;
  overflow: hidden !important;
}

.folio-header { padding: 25px 60px 10px; border-bottom: 1px solid rgba(0,0,0,0.08); }
.cat-path { font-size: 14px; font-weight: 800; color: var(--mahogany); text-transform: uppercase; letter-spacing: 1.5px; }
.cat-path .sep { color: var(--blood); padding: 0 5px; }
.title-container { display: flex; align-items: flex-start; gap: 15px; margin: 5px 0; }
.drop-cap { background: var(--blood); color: #fff; font-size: 38px; padding: 6px 16px; border-radius: 3px; line-height: 1; font-weight: 900; box-shadow: 2px 2px 0px rgba(0,0,0,0.1); }
.book-title { font-family: 'Playfair Display', serif; font-size: 34px; color: var(--ink); margin: 0; font-weight: 900; line-height: 1.1; }
.book-author { font-size: 16px; color: #3d2b1f; margin-top: 5px; }

/* 4. CONTENT & SCROLLBAR REMOVAL */
.folio-content { 
  flex-grow: 1; 
  overflow-y: scroll; /* Allow vertical scroll function */
  overflow-x: hidden; /* Kill horizontal wiggle */
  padding: 20px 60px; 
  scrollbar-width: none !important; /* Firefox */
  -ms-overflow-style: none !important; /* IE/Edge */
}

/* Hide scrollbars Chrome/Safari/Brave */
.folio-content::-webkit-scrollbar,
.notes-box::-webkit-scrollbar,
.vault-container::-webkit-scrollbar,
.athenaeum-vault::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}

.ledger-section { margin-bottom: 15px; }
.section-title { font-size: 11px; font-weight: 900; text-transform: uppercase; color: var(--blood); border-bottom: 2px solid var(--blood); margin-bottom: 12px; padding-bottom: 4px; }

.coord-stack { display: flex; gap: 40px; margin-bottom: 15px; }
.coord-box { flex: 0 1 auto; border-left: 3px solid var(--mahogany); padding-left: 12px; }
.coord-box label { display: block; font-size: 10px; font-weight: 900; color: var(--blood); text-transform: uppercase; }
.coord-box .val { font-size: 18px; font-weight: 900; color: var(--ink); line-height: 1; }

.ledger-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid rgba(0,0,0,0.04); align-items: center; }
.ledger-row span { font-weight: 900; font-size: 11px; text-transform: uppercase; color: #3d2b1f; }
.ledger-row strong { font-size: 14px; color: var(--ink); }

.notes-box {
  font-size: 16px; line-height: 1.6; color: var(--ink); background: rgba(0,0,0,0.03); padding: 20px; border-radius: 4px; border-left: 6px solid var(--gold); font-style: italic;
  max-height: 180px; overflow-y: auto; scrollbar-width: none !important;
}

/* 5. FOOTER & LOADER */
.folio-footer {
  padding: 15px 60px; background: rgba(0, 0, 0, 0.05); border-top: 1px solid rgba(0, 0, 0, 0.1);
  display: flex; justify-content: space-between; align-items: center;
}
.btn-nav, .btn-action {
  font-weight: 900; text-transform: uppercase; letter-spacing: 1px; cursor: pointer;
  border: 1px solid var(--mahogany); padding: 8px 16px; font-size: 11px;
}
.btn-nav { background: transparent; color: var(--mahogany); margin-right: 8px; }
.btn-nav:hover { background: var(--mahogany); color: #fff; }
.btn-action { background: var(--blood); color: #fff; border: none; margin-left: 8px; }
.btn-action.print { background: var(--mahogany); }

.vault-loader { background: #000; color: var(--gold); width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.athenaeum-vault {
  /* ... existing variables ... */
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden !important;
}

/* This is the most common reason scrollbars "stay" */
html, body {
  overflow: hidden !important;
  height: 100vh !important;
  width: 100vw !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Hide scrollbars globally for the entire app window */
::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
}

.notes-box {
  font-size: 16px; 
  line-height: 1.6; 
  color: var(--ink); 
  background: rgba(0,0,0,0.03); 
  padding: 20px; 
  border-radius: 4px; 
  border-left: 6px solid var(--gold); 
  font-style: italic;
  max-height: 180px; 
  overflow-y: auto; 
  
  /* --- ADD THESE TWO LINES --- */
  word-wrap: break-word;       /* Allows breaking of long words */
  overflow-wrap: break-word;   /* Standard modern equivalent */
  white-space: pre-wrap;       /* Preserves line breaks but wraps text */
  /* --------------------------- */

  scrollbar-width: none !important;
}

.book-title, .cat-path {
  overflow-wrap: break-word;
  word-break: normal;
}
/* --- BOTTOM OF THE FILE --- */

@media screen {
  .print-mount-point { 
    position: absolute; 
    top: -9999px; 
    visibility: hidden; 
  }
}

@media print {
  /* Hide the entire Screen UI */
  .athenaeum-vault { 
    display: none !important; 
  }

  /* Force the Print Mount Point to show */
  .print-mount-point { 
    display: block !important; 
    position: static !important;
    visibility: visible !important;
    width: 100% !important;
    background: white !important;
  }

  /* Reset the paper environment */
  body, html { 
    background: white !important; 
    color: black !important;
    overflow: visible !important;
  }
}
</style>