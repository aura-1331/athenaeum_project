<script setup lang="ts">
import { ref, onMounted } from 'vue'
import QRCode from 'qrcode'

const props = defineProps<{ 
  book: any, 
  authData: { deviceID: string, ip: string, userName: string } 
}>()

const emit = defineEmits(['printed'])
const qrCodeUrl = ref<string>('')

onMounted(async () => {
  try {
    qrCodeUrl.value = await QRCode.toDataURL(`https://archives.ao/v/${props.book.serial_no}`, {
      margin: 0,
      width: 200,
      color: { dark: '#000000', light: '#ffffff' }
    })
    setTimeout(() => {
      window.print()
      emit('printed')
    }, 800)
  } catch (e) {
    window.print()
    emit('printed')
  }
})
</script>

<template>
  <div class="archival-manifest-folio">
    <div class="security-void-mark">ATHENAEUM ORBIS - OFFICIAL ARCHIVE</div>

    <div class="master-frame">
      <header class="manifest-header">
        <div class="header-cell seal-box">
          <img src="@/assets/logo.png" class="archival-seal" />
        </div>
        <div class="header-cell title-box">
          <h1 class="inst-bold">ATHENAEUM ORBIS</h1>
          <p class="inst-sub">OFFICIAL CATALOGUE UNIT | VAULT RECORD MANIFEST</p>
        </div>
        <div class="header-cell tracking-box">
          <div class="track-item"><span>SERIAL NO</span><strong>{{ book.serial_no }}</strong></div>
          <div class="track-item"><span>ACCESSION</span><strong>{{ book.accession_no }}</strong></div>
        </div>
      </header>

      <div class="data-manifest-grid">
        <div class="grid-row full">
          <label>DOCUMENT TITLE</label>
          <div class="val-title">{{ book.title }}</div>
        </div>
        
        <div class="grid-row">
          <label>CATEGORY / GENRE</label>
          <div class="val">{{ book.category }} / {{ book.genre }}</div>
        </div>
        <div class="grid-row">
          <label>LANGUAGE</label>
          <div class="val">{{ book.language }}</div>
        </div>

        <div class="grid-row">
          <label>ORIGINAL LANGUAGE</label>
          <div class="val">{{ book.original_language || book.language }}</div>
        </div>
        <div class="grid-row">
          <label>PUBLISHER</label>
          <div class="val">{{ book.publisher }} ({{ book.year }})</div>
        </div>

        <div class="grid-row">
          <label>ISBN IDENTIFIER</label>
          <div class="val">{{ book.isbn || '973-Xx' }}</div>
        </div>
        <div class="grid-row">
          <label>DDC INDEX</label>
          <div class="val">{{ book.ddc || '891.489' }}</div>
        </div>

        <div class="grid-row full">
          <label>STORAGE COORDINATES</label>
          <div class="val">SHELF {{ book.shelf }} | CALL {{ book.call_no }}</div>
        </div>
      </div>

      <section class="annotation-zone">
        <label class="section-label">ADMINISTRATIVE NOTATIONS & CURATORIAL REMARKS</label>
        <div class="notes-content typewriter">{{ book.notes }}</div>
      </section>

      <footer class="manifest-footer">
        <div class="audit-metadata">
          <p><strong>PRINTED ON:</strong> {{ new Date().toLocaleString() }}</p>
          <p><strong>STATION:</strong> {{ authData.deviceID }}</p>
          <p><strong>AUTHORIZED BY:</strong> {{ authData.userName }}</p>
          <p class="warning-text">© OFFICIAL ARCHIVE RECORDS - ATHENAEUM ORBIS</p>
        </div>
        <div class="qr-cell">
          <img v-if="qrCodeUrl" :src="qrCodeUrl" />
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.archival-manifest-folio {
  width: 210mm; height: 297mm; padding: 15mm;
  background: white !important; color: black !important;
  font-family: 'Courier New', Courier, monospace;
  position: relative; box-sizing: border-box;
}

.security-void-mark {
  position: absolute; top: 45%; left: 50%; transform: translate(-50%, -50%) rotate(-35deg);
  font-size: 50pt; font-weight: 900; color: rgba(0,0,0,0.02) !important; z-index: 0; pointer-events: none;
}

.master-frame {
  height: 100%; border: 2pt solid black;
  display: flex; flex-direction: column; position: relative; z-index: 1;
}

/* HEADER */
.manifest-header { display: grid; grid-template-columns: 40mm 1fr 50mm; height: 35mm; border-bottom: 2pt solid black; }
.seal-box { border-right: 2pt solid black; display: flex; align-items: center; justify-content: center; padding: 5px; }
.archival-seal { width: 90%; filter: grayscale(1); }
.title-box { padding-left: 15px; display: flex; flex-direction: column; justify-content: center; }
.inst-bold { font-family: 'Times New Roman', serif; font-size: 22pt; font-weight: 900; margin: 0; }
.inst-sub { font-size: 8pt; font-weight: bold; margin-top: 2px; }
.tracking-box { border-left: 2pt solid black; background: #eee; padding: 10px; font-size: 8.5pt; }
.track-item span { display: block; border-bottom: 1px solid black; margin-bottom: 2px; font-weight: bold; }

/* GRID */
.data-manifest-grid { border-bottom: 2pt solid black; display: grid; grid-template-columns: 1fr 1fr; }
.grid-row { border-bottom: 1.5pt solid black; border-right: 1.5pt solid black; padding: 8px; }
.grid-row.full { grid-column: span 2; border-right: none; }
.grid-row:nth-child(even):not(.full) { border-right: none; }
.grid-row label { display: block; font-size: 7.5pt; font-weight: 900; margin-bottom: 4px; border-bottom: 0.5pt solid black; width: fit-content; }
.val-title { font-size: 18pt; font-family: 'Times New Roman', serif; font-weight: 900; text-transform: uppercase; }
.val { font-size: 10.5pt; font-weight: bold; text-transform: uppercase; }

/* NOTES */
.annotation-zone { flex-grow: 1; padding: 15px; }
.section-label { display: block; font-size: 8.5pt; font-weight: 900; border-bottom: 1.5pt solid black; padding-bottom: 4px; margin-bottom: 10px; }
.notes-content { font-size: 11pt; line-height: 1.4; word-break: break-all; white-space: pre-wrap; font-style: italic; }

/* FOOTER */
.manifest-footer { border-top: 2pt solid black; display: grid; grid-template-columns: 1fr 45mm; height: 40mm; margin-top: auto; }
.audit-metadata { padding: 10px; font-size: 8.5pt; line-height: 1.4; }
.warning-text { font-weight: 900; border-top: 1pt solid black; margin-top: 8px; padding-top: 4px; font-size: 7.5pt; }
.qr-cell { border-left: 2pt solid black; display: flex; align-items: center; justify-content: center; }
.qr-cell img { width: 35mm; height: 35mm; }

@media print {
  @page { margin: 0; size: A4; }
  .archival-manifest-folio { padding: 15mm; }
}
</style>