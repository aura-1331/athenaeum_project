<template>
  <div
    class="item-page"
    :class="themeMode === 'light' ? 'theme-light' : 'theme-dark'"
  >
    <div class="item-header">
      <div>
        <div class="eyebrow">CATALOGUE // PHYSICAL COPY REGISTRY</div>
        <h1>Accession New Copy</h1>
        <p class="page-intro">
          Register a physical copy against an approved bibliographic Work and
          assign its permanent accession record.
        </p>
      </div>

      <div class="authority-badge" :class="isChief ? 'chief' : 'keeper'">
        <span class="badge-dot"></span>
        <div>
          <strong>{{ isChief ? "THE CHIEF" : "THE KEEPER" }}</strong>
          <small>{{ isChief ? "DIRECT COPY REGISTRATION" : "VERIFICATION REQUIRED" }}</small>
        </div>
      </div>
    </div>

    <div class="authority-note" :class="isChief ? 'chief-note' : 'keeper-note'">
      <strong>
        {{ isChief ? "Direct catalogue registration" : "Submit for verification" }}
      </strong>
      <p>
        {{
          isChief
            ? "This physical copy will become an available catalogue item immediately."
            : "This physical copy will remain pending until The Chief reviews and approves it."
        }}
      </p>
    </div>

    <!-- Section 01: Work Authority -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">01</div>
        <div>
          <h2>Work Authority</h2>
          <p>Select the approved bibliographic Work that this physical copy belongs to.</p>
        </div>
      </div>

      <div class="section-body">
        <div class="field full">
          <label>AUTHORIZED WORK ID</label>
          <input
            v-model="form.work_id"
            type="number"
            min="1"
            placeholder="e.g. 12"
          />
        </div>

        <div v-if="authorityLoading" class="authority-banner loading full">
          Consulting authority archive records...
        </div>

        <div
          v-if="authority && !authority.error"
          class="authority-banner full"
        >
          <div class="authority-title">{{ authority.title }}</div>
          <div class="authority-meta">
            <span>By {{ authority.author || "Unknown" }}</span>
            <span>Language: {{ authority.language }}</span>
            <span>Classification: {{ authority.category || "Unclassified" }}</span>
          </div>
        </div>

        <div
          v-if="authority && authority.error"
          class="authority-banner error full"
        >
          {{ authority.error }}
        </div>
      </div>
    </section>

    <!-- Section 02: Language Profile -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">02</div>
        <div>
          <h2>Copy Registration</h2>
          <p>Record the language profile of this physical copy.</p>
        </div>
      </div>

      <div class="section-body">
        <div class="field">
          <label>VOLUME COPY LANGUAGE</label>
          <select v-model="form.language_id">
            <option disabled value="">Select Language Profile</option>
            <option value="Malayalam">Malayalam</option>
            <option value="English">English</option>
            <option value="Sanskrit">Sanskrit</option>
            <option value="Tamil">Tamil</option>
            <option value="Hindi">Hindi</option>
            <option value="Multi -Lingual">Multilingual</option>
            <option value="German">German</option>
            <option value="French">French</option>
          </select>
        </div>

        <div class="registry-note">
          <span class="note-label">REGISTRY RULE</span>
          <strong>One physical copy → one Item record</strong>
          <p>
            The system assigns the serial and accession number automatically;
            this copy remains attached to the selected Work.
          </p>
        </div>
      </div>
    </section>

    <!-- Section 03: Preservation & Physical Copy Artifact -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">03</div>
        <div>
          <h2>Physical Artifact & Preservation</h2>
          <p>Record physical dimensions, condition, acquisition history, and digital status.</p>
        </div>
      </div>

      <div class="section-body">
        <!-- Strictly Numeric Extent/Pages -->
        <div class="field">
          <label>EXTENT / PAGE COUNT (NUMBERS ONLY)</label>
          <div class="input-with-unit">
            <input 
              v-model="form.extent_page_count" 
              inputmode="numeric" 
              placeholder="e.g. 420" 
              @input="enforceNumbersOnly($event, 'extent_page_count')"
            />
            <span class="unit-tag">pages</span>
          </div>
        </div>

        <!-- Height × Width Dimensions -->
        <div class="field">
          <label>PHYSICAL DIMENSIONS (HEIGHT × WIDTH)</label>
          <div class="dimension-input-group">
            <input 
              v-model="dimHeight" 
              class="dim-box" 
              inputmode="numeric" 
              placeholder="Height" 
              @input="syncDimensions" 
            />
            <span class="dim-separator">×</span>
            <input 
              v-model="dimWidth" 
              class="dim-box" 
              inputmode="numeric" 
              placeholder="Width" 
              @input="syncDimensions" 
            />
            <select v-model="dimUnit" class="dim-unit-select" @change="syncDimensions">
              <option value="cm">cm</option>
              <option value="mm">mm</option>
              <option value="in">inches</option>
            </select>
          </div>
        </div>

        <!-- Strict Date Acquired -->
        <div class="field">
          <label>DATE ACQUIRED</label>
          <input v-model="form.date_acquired" type="date" :max="todayDateString" />
        </div>

        <!-- Collection / Fonds -->
        <div class="field">
          <label>COLLECTION / ARCHIVAL FONDS</label>
          <input v-model="form.collection_fonds" placeholder="e.g. Rare Palm-Leaf Archival Fonds, Donor Collection" />
        </div>

        <!-- Condition Combobox -->
        <div class="field">
          <label>PHYSICAL CONDITION</label>
          <select v-model="conditionSelectValue" @change="handleConditionSelectChange">
            <option value="">Select Condition</option>
            <option v-for="cond in conditionOptions" :key="cond" :value="cond">{{ cond }}</option>
            <option value="__CUSTOM__">Other (Enter Manually)…</option>
          </select>
          <input 
            v-if="conditionSelectValue === '__CUSTOM__'" 
            v-model="form.physical_condition" 
            class="custom-subfield" 
            placeholder="Specify physical condition…" 
          />
        </div>

        <!-- Binding Type Combobox -->
        <div class="field">
          <label>BINDING TYPE</label>
          <select v-model="bindingSelectValue" @change="handleBindingSelectChange">
            <option value="">Select Binding</option>
            <option v-for="b in bindingOptions" :key="b" :value="b">{{ b }}</option>
            <option value="__CUSTOM__">Other (Enter Manually)…</option>
          </select>
          <input 
            v-if="bindingSelectValue === '__CUSTOM__'" 
            v-model="form.binding_type" 
            class="custom-subfield" 
            placeholder="Specify binding style…" 
          />
        </div>

        <!-- Provenance Source Combobox -->
        <div class="field full">
          <label>PROVENANCE SOURCE / DONOR</label>
          <select v-model="provenanceSelectValue" @change="handleProvenanceSelectChange">
            <option value="">Select Provenance Source</option>
            <option v-for="p in provenanceOptions" :key="p" :value="p">{{ p }}</option>
            <option value="__CUSTOM__">Other (Specify Source/Donor)…</option>
          </select>
          <input 
            v-if="provenanceSelectValue === '__CUSTOM__'" 
            v-model="form.provenance_source" 
            class="custom-subfield" 
            placeholder="Enter donor name, vendor, or transfer authority…" 
          />
        </div>

        <!-- Access Restrictions Combobox -->
        <div class="field full">
          <label>ACCESS RESTRICTIONS</label>
          <select v-model="restrictionsSelectValue" @change="handleRestrictionsSelectChange">
            <option value="">Select Circulation Policy</option>
            <option v-for="r in restrictionOptions" :key="r" :value="r">{{ r }}</option>
            <option value="__CUSTOM__">Other (Specify Restriction Policy)…</option>
          </select>
          <input 
            v-if="restrictionsSelectValue === '__CUSTOM__'" 
            v-model="form.access_restrictions" 
            class="custom-subfield" 
            placeholder="Specify restriction or reading room rule…" 
          />
        </div>

        <div class="field full">
          <label>ARTIFACTUAL NOTES (INSCRIPTIONS, SEALS, MARGINALIA)</label>
          <textarea v-model="form.artifactual_notes" placeholder="Bookplates, signatures, stamps, notations..." rows="2"></textarea>
        </div>

        <div class="field">
          <label>DIGITAL SCAN AVAILABLE</label>
          <select v-model="form.digital_scan_available">
            <option :value="false">No (Unscanned)</option>
            <option :value="true">Yes (Archived Scan Available)</option>
          </select>
        </div>

        <div class="field">
          <label>OCR STATUS</label>
          <select v-model="form.ocr_status">
            <option value="NOT_APPLICABLE">NOT_APPLICABLE</option>
            <option value="PENDING">PENDING</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </div>
      </div>
    </section>

    <!-- Action Section -->
    <section class="action-card">
      <div>
        <span class="footer-label">
          {{ isChief ? "CHIEF AUTHORITY" : "KEEPER SUBMISSION" }}
        </span>
        <strong>
          {{ isChief ? "Register directly in catalogue" : "Submit copy for Chief verification" }}
        </strong>
        <p>
          {{
            isChief
              ? "The Item becomes an available physical copy immediately."
              : "The Item enters the verification queue and is not available until approved."
          }}
        </p>
      </div>

      <button
        class="submit-btn"
        @click="triggerCreationPrompt"
        :disabled="loading"
      >
        <span v-if="loading">
          {{ isChief ? "Registering..." : "Submitting..." }}
        </span>
        <span v-else>
          {{ isChief ? "REGISTER COPY" : "SUBMIT FOR VERIFICATION" }}
        </span>
      </button>
    </section>

    <!-- Results Display -->
    <div v-if="result && !result.error" class="result-card success">
      <div class="result-label">
        {{ isChief ? "ACCESSION NUMBER ALLOCATED" : "COPY SUBMITTED FOR VERIFICATION" }}
      </div>

      <div class="result-work-title">{{ result.title || "Untitled Work" }}</div>

      <div class="result-details">
        <div class="result-detail">
          <span>Work ID</span>
          <strong>#{{ result.work_id }}</strong>
        </div>
        <div class="result-detail">
          <span>Item ID</span>
          <strong>#{{ result.item_id }}</strong>
        </div>
        <div class="result-detail">
          <span>Serial No.</span>
          <strong>#{{ result.serial_no }}</strong>
        </div>
        <div class="result-detail">
          <span>Accession No.</span>
          <strong>{{ result.accession_no }}</strong>
        </div>
      </div>

      <p>
        {{
          isChief
            ? "The physical copy is now registered as an available catalogue Item."
            : "The physical copy is pending The Chief's approval."
        }}
      </p>
    </div>

    <div v-if="result && result.error" class="result-card error">
      <div class="result-label">COPY REGISTRATION FAILED</div>
      <p>{{ result.error }}</p>
    </div>

    <!-- Confirm Modal -->
    <div
      v-if="showPromptModal"
      class="modal-backdrop"
      @click.self="showPromptModal = false"
    >
      <section class="confirm-modal">
        <div class="modal-eyebrow">
          {{ isChief ? "DIRECT REGISTRATION" : "VERIFICATION SUBMISSION" }}
        </div>

        <h2>
          {{ isChief ? "Register this physical copy?" : "Submit this copy for verification?" }}
        </h2>

        <p>
          {{
            isChief
              ? "This Item will be registered directly as an available catalogue copy."
              : "This Item will be submitted to The Chief and remain pending until a decision is made."
          }}
        </p>

        <label>
          <span>Reason for this catalogue action</span>
          <input
            v-model="creationReason"
            placeholder="e.g. New acquisition / Additional physical copy"
            @keyup.enter="executeConfirmedCreation"
          />
        </label>

        <div class="modal-actions">
          <button class="cancel-btn" @click="showPromptModal = false">
            CANCEL
          </button>
          <button
            class="confirm-btn"
            @click="executeConfirmedCreation"
            :disabled="!creationReason.trim() || loading"
          >
            {{ isChief ? "REGISTER COPY" : "SUBMIT FOR VERIFICATION" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from "vue"
import { useRoute } from "vue-router"
import axios from "axios"
import { dispatchAuditTrail } from "../utils/audit"
import { storeToRefs } from "pinia"
import { useAuthStore } from "@/stores/auth"

const route = useRoute()
const authStore = useAuthStore()
const { userRole: user_role } = storeToRefs(authStore)

const isChief = computed(() => user_role.value === "The Chief")
const todayDateString = computed(() => new Date().toISOString().split('T')[0])

const themeMode = ref(
  document.documentElement.getAttribute("data-theme") ||
  localStorage.getItem("ui-theme") ||
  "dark"
)
let themeObserver = null

const showPromptModal = ref(false)
const creationReason = ref("")

// Dropdown options
const conditionOptions = [
  "Pristine / New",
  "Good",
  "Fair",
  "Fragile / Brittle",
  "Damaged / Requires Conservation",
  "Restricted Handling"
]
const conditionSelectValue = ref("")

const bindingOptions = [
  "Hardcover",
  "Paperback / Softcover",
  "Leatherbound",
  "Cloth / Buckram",
  "Palm-Leaf Bundle",
  "Spiral / Comb",
  "Loose Sheets / Portfolio"
]
const bindingSelectValue = ref("")

const provenanceOptions = [
  "Purchase / Vendor",
  "Gift / Personal Donation",
  "Institutional Transfer",
  "Bequest / Estate",
  "Found in Collection"
]
const provenanceSelectValue = ref("")

const restrictionOptions = [
  "Open Access / General Circulation",
  "Reference Room Only",
  "Supervised Reading Room Only",
  "Restricted / Rare Archive",
  "Digitized Copy Only"
]
const restrictionsSelectValue = ref("")

// Dimensions split
const dimHeight = ref("")
const dimWidth = ref("")
const dimUnit = ref("cm")

function syncDimensions() {
  if (!dimHeight.value && !dimWidth.value) {
    form.value.physical_dimensions = ""
    return
  }
  form.value.physical_dimensions = `${dimHeight.value.trim()} × ${dimWidth.value.trim()} ${dimUnit.value}`
}

function enforceNumbersOnly(event, fieldKey) {
  const input = event.target
  const digits = input.value.replace(/\D/g, "")
  form.value[fieldKey] = digits
  input.value = digits
}

function handleConditionSelectChange() {
  if (conditionSelectValue.value !== '__CUSTOM__') {
    form.value.physical_condition = conditionSelectValue.value
  }
}

function handleBindingSelectChange() {
  if (bindingSelectValue.value !== '__CUSTOM__') {
    form.value.binding_type = bindingSelectValue.value
  }
}

function handleProvenanceSelectChange() {
  if (provenanceSelectValue.value !== '__CUSTOM__') {
    form.value.provenance_source = provenanceSelectValue.value
  }
}

function handleRestrictionsSelectChange() {
  if (restrictionsSelectValue.value !== '__CUSTOM__') {
    form.value.access_restrictions = restrictionsSelectValue.value
  }
}

const form = ref({
  work_id: "",
  language_id: "",
  extent_page_count: "",
  physical_dimensions: "",
  date_acquired: "",
  collection_fonds: "",
  physical_condition: "",
  binding_type: "",
  provenance_source: "",
  artifactual_notes: "",
  access_restrictions: "",
  digital_scan_available: false,
  ocr_status: "NOT_APPLICABLE"
})

const result = ref(null)
const loading = ref(false)

const authority = ref(null)
const authorityLoading = ref(false)

watch(
  () => form.value.work_id,
  async (newVal) => {
    authority.value = null
    if (!newVal) return
    authorityLoading.value = true

    try {
      const res = await axios.get(`/catalogue/work/${newVal}`)
      authority.value = res.data
    } catch (err) {
      authority.value = {
        error:
          err.response?.data?.detail ||
          "Authorized catalogued work not found in registry"
      }
    } finally {
      authorityLoading.value = false
    }
  }
)

function triggerCreationPrompt() {
  if (!form.value.work_id || !form.value.language_id) {
    alert("Provide Work ID and Language Profile")
    return
  }

  if (authority.value?.error) {
    alert("Select an authorized catalogued Work before registering the copy.")
    return
  }

  creationReason.value = ""
  showPromptModal.value = true
}

async function executeConfirmedCreation() {
  const reason = creationReason.value.trim()
  if (!reason) {
    alert("Reason for this catalogue action is required.")
    return
  }

  loading.value = true
  result.value = null
  showPromptModal.value = false

  try {
    const res = await axios.post(
      "/catalogue/create-item",
      {
        work_id: Number(form.value.work_id),
        language_id: form.value.language_id,
        extent_page_count: form.value.extent_page_count || null,
        physical_dimensions: form.value.physical_dimensions || null,
        date_acquired: form.value.date_acquired || null,
        collection_fonds: form.value.collection_fonds || null,
        physical_condition: form.value.physical_condition || null,
        binding_type: form.value.binding_type || null,
        provenance_source: form.value.provenance_source || null,
        artifactual_notes: form.value.artifactual_notes || null,
        access_restrictions: form.value.access_restrictions || null,
        digital_scan_available: !!form.value.digital_scan_available,
        ocr_status: form.value.ocr_status || null
      },
      {
        headers: {
          "X-Change-Reason": reason,
          "X-Registration-Mode": isChief.value ? "DIRECT_CHIEF" : "KEEPER_SUBMISSION"
        }
      }
    )

    result.value = res.data

    await dispatchAuditTrail(
      "CREATE",
      "CATALOGUE",
      res.data.accession_no,
      `Allocated physical copy for Work ID: #${form.value.work_id}`,
      reason
    )

    alert(
      isChief.value
        ? `Volume Copy Registered Successfully • ${res.data.accession_no}`
        : `Volume Copy Submitted for Verification • ${res.data.accession_no}`
    )

    // Reset Form
    form.value.work_id = ""
    form.value.language_id = ""
    form.value.extent_page_count = ""
    form.value.physical_dimensions = ""
    form.value.date_acquired = ""
    form.value.collection_fonds = ""
    form.value.physical_condition = ""
    form.value.binding_type = ""
    form.value.provenance_source = ""
    form.value.artifactual_notes = ""
    form.value.access_restrictions = ""
    form.value.digital_scan_available = false
    form.value.ocr_status = "NOT_APPLICABLE"
    
    dimHeight.value = ""
    dimWidth.value = ""
    conditionSelectValue.value = ""
    bindingSelectValue.value = ""
    provenanceSelectValue.value = ""
    restrictionsSelectValue.value = ""

    authority.value = null
    creationReason.value = ""
  } catch (err) {
    result.value = {
      error: err.response?.data?.detail || "Failed to catalog copy"
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const queryWorkId = Array.isArray(route.query.work_id) ? route.query.work_id[0] : route.query.work_id
  const queryLanguageId = Array.isArray(route.query.language_id) ? route.query.language_id[0] : route.query.language_id
  if (queryWorkId && /^\d+$/.test(String(queryWorkId))) form.value.work_id = String(queryWorkId)
  if (queryLanguageId) form.value.language_id = String(queryLanguageId)

  themeObserver = new MutationObserver(() => {
    themeMode.value =
      document.documentElement.getAttribute("data-theme") || "dark"
  })

  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"]
  })
})

onUnmounted(() => {
  if (themeObserver) themeObserver.disconnect()
})
</script>

<style scoped>
.item-page {
  min-height: 100%;
  padding: 34px 30px 60px;
  transition: background .2s ease, color .2s ease;
}

.item-page.theme-dark {
  --page: #030712;
  --card: #0f172a;
  --card-alt: #111827;
  --input: #181817;
  --border: #1e293b;
  --border-soft: #252b38;
  --text: #f9fafb;
  --muted: #9ca3af;
  --accent: #2dd4bf;
  --warm: #b5a27d;
  background: #030712;
  color: #f9fafb;
}

.item-page.theme-light {
  --page: #edf3f2;
  --card: #d9eceb;
  --card-header: #c9e4e2;
  --card-alt: #f5f9f9;
  --input: #eef7f6;
  --border: #a8c9c8;
  --border-soft: #bdd5d4;
  --text: #173138;
  --muted: #506970;
  --accent: #0d9488;
  --warm: #806f4f;
  background: #edf3f2;
  color: #173138;
}

.item-header,
.authority-note,
.form-card,
.action-card,
.result-card {
  width: min(1120px, 100%);
  margin-left: auto;
  margin-right: auto;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 28px;
  margin-bottom: 22px;
}

.eyebrow,
.footer-label,
.modal-eyebrow,
.note-label {
  font-size: 11px;
  letter-spacing: 1.8px;
  font-weight: 700;
  color: var(--accent);
}

.eyebrow {
  margin-bottom: 10px;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  font-family: "Playfair Display", serif;
  font-size: 36px;
  line-height: 1.1;
  font-weight: 500;
  margin-bottom: 9px;
  color: var(--text);
}

.page-intro {
  max-width: 650px;
  color: var(--muted);
  line-height: 1.6;
  font-size: 14px;
}

.authority-badge {
  min-width: 210px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 17px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.authority-badge.chief {
  background: #eadfc7;
  border-color: #c4ad7d;
  color: #332b1d;
}

.authority-badge.keeper {
  background: #dcecef;
  border-color: #b4ced1;
  color: #18353b;
}

.badge-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: 0 0 auto;
  background: var(--warm);
}

.authority-badge.keeper .badge-dot {
  background: #4f8b91;
}

.authority-badge strong,
.authority-badge small {
  display: block;
}

.authority-badge strong {
  font-size: 12px;
  letter-spacing: 1.1px;
}

.authority-badge small {
  margin-top: 4px;
  font-size: 9px;
  letter-spacing: 1.2px;
  opacity: .72;
}

.authority-note {
  padding: 17px 20px;
  margin-bottom: 18px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 7px;
  background: var(--card-alt);
}

.theme-light .authority-note.chief-note {
  border-left-color: #a98e58;
}

.authority-note strong {
  color: var(--text);
  font-size: 14px;
}

.authority-note p {
  color: var(--muted);
  font-size: 13px;
  margin: 6px 0 0;
}

.form-card,
.action-card,
.result-card {
  border: 1px solid var(--border);
  border-radius: 9px;
  overflow: hidden;
  margin-bottom: 18px;
  box-shadow: 0 7px 18px rgba(18, 45, 50, .05);
}

.theme-dark .form-card,
.theme-dark .action-card {
  background: var(--card);
}

.theme-light .form-card {
  background: var(--card);
  border-color: #a8c9c8;
}

.section-heading {
  display: flex;
  gap: 14px;
  padding: 20px 23px;
  background: var(--card-header, #111827);
  border-bottom: 1px solid var(--border);
}

.section-number {
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  padding-top: 3px;
}

.section-heading h2 {
  color: var(--text);
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 4px;
}

.section-heading p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 0;
}

.section-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  padding: 24px;
}

.field {
  display: flex;
  flex-direction: column;
}

.field.full,
.authority-banner.full {
  grid-column: 1 / -1;
}

.field label {
  margin-bottom: 9px;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 1.2px;
  font-weight: 700;
}

.field input,
.field select,
.field textarea {
  height: 50px;
  width: 100%;
  box-sizing: border-box;
  padding: 0 15px;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--input);
  color: var(--text);
  font-size: 14px;
  outline: none;
  transition: .18s ease;
}

.field textarea {
  height: auto;
  padding: 10px 14px;
  line-height: 1.5;
}

.field input::placeholder,
.field textarea::placeholder {
  color: var(--muted);
  opacity: .82;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: var(--accent);
  background: var(--card-alt);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, .11);
}

.custom-subfield {
  margin-top: 8px;
  border-style: dashed !important;
}

/* Dimensions Input Controls */
.dimension-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dim-box {
  width: 90px !important;
  text-align: center;
}

.dim-separator {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
}

.dim-unit-select {
  width: 90px !important;
}

.input-with-unit {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-unit input {
  padding-right: 65px;
}

.unit-tag {
  position: absolute;
  right: 14px;
  color: var(--muted);
  font-size: 12px;
  pointer-events: none;
}

.theme-dark .field input,
.theme-dark .field select,
.theme-dark .field textarea {
  background: #181817;
}

.field select {
  cursor: pointer;
}

.theme-dark .field select option {
  background: #141414;
  color: #e0e0e0;
}

.theme-light .field select option {
  background: #ffffff;
  color: #173138;
}

.authority-banner {
  padding: 19px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--card-alt);
}

.theme-dark .authority-banner {
  background: #181715;
  border-color: #2a251e;
}

.authority-banner.loading {
  color: var(--muted);
  font-style: italic;
}

.authority-banner.error {
  background: #fff2f0;
  border-color: #edc2bb;
  color: #9f3f38;
}

.theme-dark .authority-banner.error {
  background: #250906;
  border-color: #4a120b;
  color: #f87171;
}

.authority-title {
  font-family: "Playfair Display", serif;
  font-size: 20px;
  color: var(--text);
  margin-bottom: 12px;
}

.authority-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.authority-meta span {
  padding: 5px 10px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,.38);
  color: var(--muted);
  font-size: 11px;
}

.theme-dark .authority-meta span {
  background: #221f1a;
  border-color: #2a251e;
  color: #cfb997;
}

.registry-note {
  align-self: end;
  padding: 16px 18px;
  border-left: 3px solid var(--accent);
  border-radius: 5px;
  background: var(--card-alt);
  border-top: 1px solid var(--border-soft);
  border-right: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.registry-note .note-label {
  display: block;
  margin-bottom: 7px;
  font-size: 9px;
}

.registry-note strong {
  display: block;
  color: var(--text);
  font-size: 13px;
  margin-bottom: 5px;
}

.registry-note p {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
  margin: 0;
}

.action-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 25px;
  padding: 21px 24px;
  background: var(--card-alt);
}

.theme-light .action-card {
  background: #f5f9f9;
}

.action-card > div {
  display: flex;
  flex-direction: column;
}

.action-card strong {
  color: var(--text);
  font-size: 15px;
  margin: 5px 0 4px;
}

.action-card p {
  color: var(--muted);
  font-size: 12px;
  margin: 0;
}

.submit-btn,
.confirm-btn,
.cancel-btn {
  height: 48px;
  padding: 0 25px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: .18s ease;
}

.submit-btn,
.confirm-btn {
  border: 1px solid var(--accent);
  background: var(--accent);
  color: white;
}

.submit-btn:hover:not(:disabled),
.confirm-btn:hover:not(:disabled) {
  filter: brightness(.94);
}

.submit-btn:disabled,
.confirm-btn:disabled {
  opacity: .55;
  cursor: not-allowed;
}

.result-card {
  padding: 22px 24px;
}

.result-card.success {
  background: #edf9f2;
  border-color: #b9dfc7;
  color: #246b40;
}

.result-card.error {
  background: #fff4f2;
  border-color: #edc2bb;
  color: #9f3f38;
}

.result-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  font-weight: 700;
  margin-bottom: 8px;
}

.result-work-title {
  margin-top: 2px;
  font-family: "Playfair Display", serif;
  font-size: 23px;
  line-height: 1.25;
  font-weight: 600;
  color: inherit;
}

.result-details {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 24px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(36, 107, 64, .18);
}

.result-detail {
  min-width: 130px;
}

.result-detail span {
  display: block;
  margin-bottom: 3px;
  font-size: 9px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  opacity: .72;
}

.result-detail strong {
  font-family: monospace;
  font-size: 14px;
  font-weight: 700;
}

.result-card p {
  margin: 7px 0 0;
  font-size: 12px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(3, 7, 18, .58);
}

.confirm-modal {
  width: min(510px, 100%);
  padding: 28px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  box-shadow: 0 25px 70px rgba(0,0,0,.28);
}

.modal-eyebrow {
  margin-bottom: 10px;
}

.confirm-modal h2 {
  font-family: "Playfair Display", serif;
  color: var(--text);
  font-size: 25px;
  font-weight: 500;
  margin-bottom: 10px;
}

.confirm-modal > p {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 22px;
}

.confirm-modal label span {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .7px;
}

.confirm-modal input {
  width: 100%;
  height: 46px;
  box-sizing: border-box;
  padding: 0 13px;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--input);
  color: var(--text);
  outline: none;
}

.confirm-modal input:focus {
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}

.cancel-btn {
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
}

.cancel-btn:hover {
  background: rgba(127,127,127,.08);
}

@media (max-width: 760px) {
  .item-page {
    padding: 24px 16px 45px;
  }

  .item-header,
  .action-card {
    flex-direction: column;
  }

  .authority-badge {
    width: 100%;
    box-sizing: border-box;
  }

  .section-body {
    grid-template-columns: 1fr;
  }

  .field.full,
  .authority-banner.full {
    grid-column: auto;
  }

  .submit-btn {
    width: 100%;
  }
}
</style>