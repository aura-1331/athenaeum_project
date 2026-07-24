<template>
  <div class="athenaeum-vault">
    <div v-if="loading" class="vault-loader">
      <div class="minimal-spinner"></div>
      <span class="loading-label">SYNCING_NODE_REGISTRY</span>
    </div>

    <div v-else-if="error" class="error-fallback-terminal">
      <div class="terminal-card-alert">
        <div class="alert-status-badge">ERROR // DATABASE_ACCESS_REJECTED</div>
        <h2 class="alert-title">RECORD_NOT_FOUND</h2>
        <p class="alert-summary">
          The requested system node sequence ID (#{{ $route.params.id }}) could not be mapped to an active asset matrix ledger footprint.
        </p>
        <button class="fallback-return-btn" @click="returnToAuthorsRegistry">
          ← RETURN_TO_CLASSIFICATION_REGISTRY
        </button>
      </div>
    </div>

    <div v-else-if="book" class="editorial-scroll-frame">
      <header class="master-header">
        <div class="breadcrumb-trail" @click="returnToCatalogue">
          CENTRAL_INDEX <span class="divider">/</span> {{ book.category }} <span class="divider">/</span> 
          <span class="inline-badge-stack">
            <span v-for="tag in splitGenres" :key="tag" class="breadcrumb-genre-badge">
              {{ tag }}
            </span>
          </span>
        </div>
        <div class="action-buttons-group">
          <button class="action-trigger text-link" @click="returnToCatalogue">← BACK_TO_INDEX</button>
          <button class="action-trigger outline" @click="editRecord">EDIT_FILE</button>
          
          <button class="action-trigger filled" @click="triggerPrint('public_leaf')">PRINT_LEAF</button>
          <button class="action-trigger filled" @click="triggerPrint('standard_card')">PRINT_CARD</button>
          
          <button 
            v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
            class="action-trigger filled" 
            @click="triggerPrint('location_slip')"
          >
            PRINT_SLIP
          </button>
          <button 
            v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
            class="action-trigger filled" 
            @click="triggerPrint('tech_manifest')"
          >
            PRINT_MANIFEST
          </button>
        </div>
      </header>

      <main class="asymmetric-cards-grid">
        <section class="grid-card dynamic-hero-card">
          <div class="system-tag">01 // CORE_ASSET_PROFILE</div>
          <h1 class="book-title">{{ book.title }}</h1>
          <div class="creator-stamp">
            <span class="prefix">CREATOR_ORIGIN:</span>
            <span class="value">{{ book.author || 'UNKNOWN AUTHOR' }}</span>
          </div>
          <div class="nav-arrows-strip">
            <button class="nav-arrow" @click="goToRecord('prev')">← PREV_NODE</button>
            <span class="divider">|</span>
            <button class="nav-arrow" @click="goToRecord('next')">NEXT_NODE →</button>
          </div>
        </section>

        <section 
          v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
          class="grid-card identifier-spec-card"
        >
          <div class="system-tag">02 // REGISTRY_SIGNATURE_SIGN</div>
          <div class="badge-row label-emerald">
            <span class="lbl">RECORD IDENTIFIER</span>
            <span class="val font-mono">{{ book.record_id }}</span>
          </div>
          <div class="badge-row label-amber">
            <span class="lbl">WORK INDEX ID</span>
            <span class="val font-mono">#{{ book.work_id }}</span>
          </div>
          <div class="badge-row label-blue">
            <span class="lbl">ACCESSION SEQUENCE</span>
            <span class="val font-mono">{{ book.accession_no }}</span>
          </div>
          <div class="badge-row label-magenta">
            <span class="lbl">SERIAL SEQUENCE</span>
            <span class="val font-mono">#{{ book.serial_no }}</span>
          </div>
        </section>

        <section 
          v-if="auditData.userRole === 'The Chief' || auditData.userRole === 'The Keeper'" 
          class="grid-card coordinates-telemetry-card"
        >
          <div class="system-tag">03 // LOCATION_VECTORS_AND_METADATA</div>
          <div class="vectors-sub-grid">
            <div class="vector-box">
              <span class="box-lbl">SHELF_LOCATION</span>
              <span class="box-val">{{ book.shelf || '---' }}</span>
            </div>
            <div class="vector-box">
              <span class="box-lbl">CALL_SIGNATURE</span>
              <span class="box-val">{{ book.call_no || '---' }}</span>
            </div>
          </div>
          <div class="telemetry-rows-stack">
            <div class="telemetry-node"><span>TEXT LANGUAGE</span><strong>{{ book.language }}</strong></div>
            <div class="telemetry-node"><span>SOURCE LANGUAGE</span><strong>{{ book.original_language || book.language }}</strong></div>
            <div class="telemetry-node">
              <span>CLASSIFICATION</span>
              <div class="inline-badge-stack justify-end">
                <span v-for="tag in splitGenres" :key="tag" class="metadata-genre-badge">
                  {{ tag }}
                </span>
              </div>
            </div>
            <div class="telemetry-node"><span>IMPRINT PUBLISHER</span><strong>{{ book.publisher }}</strong></div>
            <div class="telemetry-node"><span>TEMPORAL EPOCH</span><strong>{{ book.year }}</strong></div>
            <div class="telemetry-node"><span>ISBN IDENTIFIER</span><strong>{{ book.isbn || 'N/A' }}</strong></div>
            <div class="telemetry-node"><span>DDC EXTENSION</span><strong>{{ book.ddc || '---' }}</strong></div>
          </div>
        </section>

        <section class="grid-card full-width-notes-card">
          <div class="system-tag">04 // CURATORIAL_NOTATIONS_LOG</div>
          <div class="log-text-area">
            {{ book.notes || 'This asset ledger entry is currently verified clear of exceptional administrative annotations.' }}
          </div>
        </section>
      </main>
    </div>
  </div>

  <div v-if="isPrinting" class="print-mount-point">
    <PrintPublicLeaf 
      v-if="selectedPrintLayout === 'public_leaf'" 
      :book="book" 
      :authData="auditData" 
      @printed="finishPrinting" 
    />
    <PrintStandardCard 
      v-if="selectedPrintLayout === 'standard_card'" 
      :book="book" 
      :authData="auditData" 
      @printed="finishPrinting" 
    />
    <PrintLocationSlip 
      v-if="selectedPrintLayout === 'location_slip'" 
      :book="book" 
      :authData="auditData" 
      @printed="finishPrinting" 
    />
    <PrintTechnicalManifest 
      v-if="selectedPrintLayout === 'tech_manifest'" 
      :book="book" 
      :authData="auditData" 
      @printed="finishPrinting" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"

import PrintPublicLeaf from "@/components/print/PrintPublicLeaf.vue"
import PrintStandardCard from "@/components/print/PrintStandardCard.vue"
import PrintLocationSlip from "@/components/print/PrintLocationSlip.vue"
import PrintTechnicalManifest from "@/components/print/PrintTechnicalManifest.vue"

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref(false)
const book = ref<any>(null)

const isPrinting = ref(false)
const selectedPrintLayout = ref<string>("") 

const auditData = ref({
  deviceID: "EDITORIAL-CARDS-STATION-01",
  ip: "192.168.1.105", 
  userName: "System Archivist",
  userRole: "The Chief"
})

const splitGenres = computed(() => {
  const raw = book.value?.genre || book.value?.work_nature
  if (!raw) return ['GENERAL']
  return raw.split('/').map((g: string) => g.trim().toUpperCase()).filter((g: string) => g.length > 0)
})

function triggerPrint(layoutName: string) {
  selectedPrintLayout.value = layoutName
  isPrinting.value = true
}

function finishPrinting() {
  isPrinting.value = false
  selectedPrintLayout.value = ""
}

function generateRecordId(serialNo: number) {
  const currentYear = new Date().getFullYear()
  return `AO-REC-${currentYear}-${String(serialNo).padStart(6, '0')}`
}

async function fetchBookDetails() {
  loading.value = true
  error.value = false
  const id = route.params.id
  try {
    const response = await axios.get(`/catalogue/${id}`)
    const data = response.data
    
    if (data && data.serial_no && !data.record_id) {
      data.record_id = generateRecordId(data.serial_no)
    }
    
    book.value = data
  } catch (err) {
    console.error("Pipeline breakdown:", err)
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, () => {
  fetchBookDetails()
})

function goToRecord(direction: 'next' | 'prev') {
  const currentId = parseInt(route.params.id as string)
  const newId = direction === 'next' ? currentId + 1 : currentId - 1
  if (newId > 0) {
    router.push(`/details/${newId}`)
  }
}

function editRecord() {
  if (book.value?.serial_no) {
    router.push({ 
      name: 'edit-item', 
      params: { id: book.value.serial_no } 
    })
  }
}

function returnToCatalogue() {
  router.push("/catalogue")
}

function returnToAuthorsRegistry() {
  router.push("/classification/authors")
}

onMounted(() => fetchBookDetails())
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800&family=JetBrains+Mono:wght@400;700&display=swap');

.athenaeum-vault {
  background-color: #111216;
  color: #e2e4e9;
  height: 100vh;
  width: 100vw;
  display: flex;
  overflow: hidden !important;
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
}

.error-fallback-terminal {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #111216;
  padding: 32px;
  box-sizing: border-box;
}

.terminal-card-alert {
  background-color: #16181f;
  border: 1px solid #ef4444;
  padding: 48px;
  border-radius: 12px;
  max-width: 600px;
  width: 100%;
  box-shadow: 0 4px 32px rgba(239, 68, 68, 0.05);
  text-align: left;
}

.alert-status-badge {
  font-size: 10px;
  font-weight: bold;
  color: #f87171;
  letter-spacing: 1.5px;
  margin-bottom: 24px;
}

.alert-title {
  font-size: 28px;
  font-weight: 800;
  color: #ffffff;
  margin: 0 0 16px 0;
  letter-spacing: -0.5px;
}

.alert-summary {
  font-size: 13px;
  line-height: 1.6;
  color: #a3a8b4;
  margin: 0 0 32px 0;
}

.fallback-return-btn {
  background: rgba(245, 158, 11, 0.04);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #f59e0b;
  font-family: inherit;
  font-size: 11px;
  font-weight: bold;
  letter-spacing: 0.5px;
  padding: 12px 24px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.fallback-return-btn:hover {
  background-color: #f59e0b;
  color: #ffffff;
  border-color: #f59e0b;
}

.editorial-scroll-frame {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.editorial-scroll-frame::-webkit-scrollbar {
  display: none !important;
}

.master-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 40px 64px 24px 64px;
  background-color: #111216;
}

.breadcrumb-trail {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #626a7a;
  text-transform: uppercase;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.breadcrumb-trail .divider {
  color: #e2e4e9;
  margin: 0 4px;
}

.inline-badge-stack {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.justify-end {
  justify-content: flex-end;
}

.breadcrumb-genre-badge {
  font-size: 10px;
  font-weight: bold;
  background-color: #16181f;
  border: 1px solid #22252e;
  color: #ffffff;
  padding: 2px 8px;
  border-radius: 4px;
}

.metadata-genre-badge {
  font-size: 10px;
  font-weight: bold;
  background-color: rgba(236, 72, 153, 0.08);
  border: 1px solid rgba(236, 72, 153, 0.2);
  color: #ec4899;
  padding: 2px 8px;
  border-radius: 4px;
}

.action-buttons-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.action-trigger {
  background: none;
  border: none;
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 10px 20px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.text-link {
  color: #626a7a;
  padding-left: 0;
}

.text-link:hover {
  color: #ffffff;
}

.outline {
  border: 1px solid #2e333d;
  color: #e2e4e9;
}

.outline:hover {
  background-color: #e2e4e9;
  color: #111216;
  border-color: #e2e4e9;
}

.filled {
  background-color: #e2e4e9;
  color: #111216;
}

.filled:hover {
  background-color: #cdd1da;
}

.asymmetric-cards-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 24px;
  padding: 0 64px 64px 64px;
  max-width: 1400px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
}

.grid-card {
  background-color: #16181f;
  border: 1px solid #22252e;
  padding: 32px;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
}

.system-tag {
  font-size: 10px;
  font-weight: bold;
  color: #525966;
  letter-spacing: 1px;
  margin-bottom: 24px;
}

.dynamic-hero-card {
  grid-column: span 7;
  min-height: 320px;
}

.identifier-spec-card {
  grid-column: span 5;
}

.coordinates-telemetry-card {
  grid-column: span 8;
}

.full-width-notes-card {
  grid-column: span 4;
}

.book-title {
  font-family: 'Cinzel', serif;
  font-size: 36px;
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.5px;
  margin: 0 0 24px 0;
  color: #ffffff;
}

.creator-stamp {
  font-size: 12px;
  margin-bottom: auto;
}

.creator-stamp .prefix {
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
  margin-right: 8px;
}

.creator-stamp .value {
  font-weight: bold;
  color: #e2e4e9;
}

.nav-arrows-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  font-weight: 700;
  margin-top: 32px;
}

.nav-arrow {
  background: none;
  border: none;
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  color: #626a7a;
  cursor: pointer;
  padding: 0;
}

.nav-arrow:hover {
  color: #ffffff;
}

.badge-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #1c1f26;
  border-radius: 4px;
}

.badge-row:nth-child(even) {
  background-color: #12141a;
}

.badge-row:last-child {
  border-bottom: none;
}

.badge-row .lbl {
  font-size: 11px;
  font-weight: 700;
  color: #626a7a;
}

.badge-row .val {
  font-size: 13px;
  font-weight: 700;
}

.label-emerald .val { color: #10b981; }
.label-amber .val { color: #f59e0b; }
.label-blue .val { color: #3b82f6; }
.label-magenta .val { color: #ec4899; }

.vectors-sub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 32px;
}

.vector-box {
  background-color: #12141a;
  border: 1px solid #1c1f26;
  padding: 16px;
  border-radius: 6px;
}

.box-lbl {
  font-size: 9px;
  font-weight: 700;
  color: #626a7a;
  display: block;
  margin-bottom: 4px;
}

.box-val {
  font-size: 15px;
  font-weight: bold;
  color: #ffffff;
}

.telemetry-rows-stack {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 32px;
}

.telemetry-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  border-bottom: 1px solid #1c1f26;
  padding: 10px 12px;
  border-radius: 4px;
}

.telemetry-rows-stack .telemetry-node:nth-child(4n+1),
.telemetry-rows-stack .telemetry-node:nth-child(4n+2) {
  background-color: #12141a;
}

.telemetry-rows-stack .telemetry-node:nth-child(4n+3),
.telemetry-rows-stack .telemetry-node:nth-child(4n) {
  background-color: transparent;
}

.telemetry-node span {
  font-size: 10px;
  font-weight: 700;
  color: #626a7a;
}

.log-text-area {
  font-size: 13px;
  line-height: 1.6;
  color: #a3a8b4;
}

.vault-loader {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background-color: #111216;
}

.minimal-spinner {
  width: 16px;
  height: 16px;
  border: 1px solid rgba(226, 228, 233, 0.1);
  border-top-color: #e2e4e9;
  border-radius: 50%;
  animation: spin 0.7s infinite linear;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #626a7a;
}

.print-mount-point {
  display: none;
}

/* =====================================================
   📱 MOBILE RESPONSIVENESS FIXES
===================================================== */
@media (max-width: 768px) {
  .master-header {
    padding: 20px 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }

  .action-buttons-group {
    flex-wrap: wrap;
    width: 100%;
    justify-content: flex-start;
    gap: 10px;
  }

  .action-trigger {
    padding: 8px 12px;
    font-size: 10px;
  }

  .asymmetric-cards-grid {
    display: flex; /* Stacks the cards vertically instead of using the complex 12-column grid */
    flex-direction: column;
    padding: 0 16px 32px 16px;
    gap: 16px;
  }

  .grid-card {
    padding: 24px;
    width: 100%;
  }

  .book-title {
    font-size: 26px; /* Scales down the massive title font */
  }

  .telemetry-rows-stack {
    grid-template-columns: 1fr; /* Stacks the telemetry nodes vertically */
    gap: 12px;
  }

  .vectors-sub-grid {
    grid-template-columns: 1fr; /* Stacks the shelf location and call sign vertically */
  }
}

@media print {
  .athenaeum-vault,
  .editorial-scroll-frame,
  .master-header,
  .asymmetric-cards-grid,
  .grid-card {
    display: none !important;
  }
  .print-mount-point {
    display: block !important;
    background-color: #ffffff !important;
    width: 100% !important;
    height: auto !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }
}
</style>