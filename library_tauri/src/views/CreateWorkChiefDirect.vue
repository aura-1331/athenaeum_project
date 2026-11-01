<template>
  <div class="chief-work-page" :class="themeMode === 'light' ? 'theme-light' : 'theme-dark'">
    <!-- Topbar Header -->
    <header class="page-header">
      <div class="header-left">
        <button class="btn btn-back" type="button" @click="handleBackToCatalogue" title="Back to Catalogue (Esc)">
          <span class="btn-glyph">←</span>
          <span>Catalogue</span>
          <kbd class="kbd-pill">Esc</kbd>
        </button>
        <div>
          <div class="eyebrow">CATALOGUE // DIRECT CHIEF REGISTRY</div>
          <h1>Work Registration Dossier</h1>
          <p class="page-intro">Direct bibliographic intake into the primary Athenaeum holding ledger.</p>
        </div>
      </div>

      <div class="header-right">
        <div class="authority-badge chief">
          <span class="badge-dot"></span>
          <div>
            <strong>THE CHIEF</strong>
            <small>DIRECT INTAKE</small>
          </div>
        </div>
        <div class="readiness-badge">
          <strong>{{ readinessPercent }}%</strong>
          <span>Ready</span>
        </div>
      </div>
    </header>

    <!-- Quick ISBN Lookup Intake Bar -->
    <section class="form-card intake-strip">
      <div class="intake-info">
        <span class="badge-tag">FAST INTAKE</span>
        <h3>Quick ISBN & Barcode Scanner</h3>
        <p>Scan barcode or paste ISBN to retrieve verified authority metadata instantly.</p>
      </div>
      <div class="intake-actions">
        <input
          id="parser-field-input"
          v-model="pasteInput"
          @input="normalizeParserIsbn"
          @paste="handleMetadataPaste"
          placeholder="Enter 10 or 13-digit ISBN…"
        />
        <button type="button" class="btn btn-primary" @click="handleMetadataPaste(null)" :disabled="isParsing || !isPasteIsbnReady">
          {{ isParsing ? 'Reading…' : 'Import Metadata' }}
        </button>
      </div>
    </section>

    <!-- Section 01: Work Identity -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">01</div>
        <div>
          <h2>Work Identity</h2>
          <p>Establish foundational bibliographic identity and creator attribution.</p>
        </div>
      </div>

      <div class="section-body">
        <!-- Work Title with Candidate Dropdown -->
        <div class="field full" ref="titleLookupArea">
          <div class="label-row">
            <label for="chief-title-input">WORK TITLE <span class="required">*</span></label>
            <span v-if="isFieldImported('title')" class="tag-imported">Imported</span>
          </div>
          <div class="input-clearable">
            <input
              id="chief-title-input"
              v-model="form.title"
              autocomplete="off"
              placeholder="Enter full formal work title…"
              @input="clearTitleLookupResults"
              @blur="sanitizeField('title')"
            />
            <button v-if="form.title" type="button" class="clear-btn" @click="clearField('title'); clearTitleLookupResults()">Clear</button>
          </div>
          <div v-if="titleLookupResults.length" class="lookup-candidate-dropdown">
            <div v-for="c in titleLookupResults" :key="c.title" class="candidate-row" @click="selectTitleCandidate(c)">
              <strong>{{ c.title }}</strong>
              <small>{{ [c.author, c.year, c.source].filter(Boolean).join(' · ') }}</small>
            </div>
          </div>
        </div>

        <!-- Author / Creator with Authority linkage -->
        <div class="field" ref="authorLookupArea">
          <div class="label-row">
            <label for="chief-author-input">PRIMARY AUTHORITY (AUTHOR)</label>
            <span v-if="selectedAuthorityName" class="tag-linked">✓ Linked</span>
          </div>
          <div ref="authorInputAnchor" class="input-clearable">
            <input
              id="chief-author-input"
              ref="authorInput"
              v-model="form.author"
              autocomplete="off"
              placeholder="Search authority or enter author name…"
              @focus="openAuthorSuggestions"
              @blur="handleAuthorBlur"
            />
            <button v-if="form.author" type="button" class="clear-btn" @click="clearField('author')">Clear</button>
          </div>
          <Teleport to="body">
            <div
              v-if="showAuthorSuggestions && form.author && form.author.trim().length >= 2"
              ref="authorDropdown"
              class="popover-dropdown"
              :style="authorDropdownStyle"
              @pointerdown.stop
            >
              <div class="popover-head">LOCAL AUTHORITY RECORDS</div>
              <button v-for="a in authorSuggestions" :key="a.authority_id" type="button" class="popover-item" @mousedown.prevent @click="selectAuthor(a)">
                <strong>{{ a.preferred_name }}</strong>
                <small>{{ a.status }} · {{ a.authority_code }}</small>
              </button>
              <div v-if="!authorSuggestions.length" class="popover-empty">No matching local authority record.</div>

              <template v-if="externalAuthorSuggestions.length">
                <div class="popover-head ext">OPEN LIBRARY CANDIDATES</div>
                <button v-for="ext in externalAuthorSuggestions" :key="ext.preferred_name" type="button" class="popover-item" @mousedown.prevent @click="selectExternalAuthor(ext)">
                  <strong>{{ ext.canonical_name || ext.preferred_name }}</strong>
                  <small>{{ ext.source || 'Open Library' }}</small>
                </button>
              </template>
            </div>
          </Teleport>
        </div>

        <!-- Publisher -->
        <div class="field" ref="publisherLookupArea">
          <label for="chief-publisher-input">PUBLISHER / IMPRINT</label>
          <div class="input-clearable">
            <input
              id="chief-publisher-input"
              v-model="form.publisher"
              placeholder="Publisher name…"
              @focus="showPublisherSuggestions = true"
              @blur="handleBlurAction('publisher')"
            />
            <button v-if="form.publisher" type="button" class="clear-btn" @click="clearField('publisher')">Clear</button>
            <div v-if="showPublisherSuggestions && publisherSuggestions.length" class="popover-dropdown inline">
              <button v-for="pub in publisherSuggestions" :key="pub" type="button" class="popover-item" @mousedown="selectPublisher(pub)">
                <strong>{{ pub }}</strong>
              </button>
            </div>
          </div>
        </div>

        <!-- Deduplicated Language Dropdown -->
        <div class="field">
          <label for="chief-lang-select">LANGUAGE <span class="required">*</span></label>
          <select id="chief-lang-select" v-model="form.language_id">
            <option disabled value="">Select Language</option>
            <option v-for="lang in availableLanguages" :key="lang" :value="lang">
              {{ lang }}
            </option>
          </select>
        </div>

        <!-- Category -->
        <div class="field">
          <label for="chief-category-select">CATEGORY</label>
          <select id="chief-category-select" v-model="form.category">
            <option value="">No Category</option>
            <option value="Fiction">Fiction</option>
            <option value="Non-Fiction">Non-Fiction</option>
            <option value="Reference">Reference</option>
            <option value="Religious">Religious</option>
            <option value="Poetry">Poetry</option>
            <option value="Manuscript / Rare">Manuscript / Rare</option>
            <option value="Periodical">Periodical</option>
          </select>
        </div>

        <!-- Numeric Year -->
        <div class="field full">
          <label for="chief-year-input">PUBLICATION YEAR (DIGITS ONLY)</label>
          <input
            id="chief-year-input"
            v-model="form.year"
            inputmode="numeric"
            maxlength="4"
            placeholder="YYYY"
            @input="enforceNumbersOnly($event, 'year', 4)"
          />
        </div>
      </div>
    </section>

    <!-- Section 02: Publication & Standards -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">02</div>
        <div>
          <h2>Publication & Standards</h2>
          <p>ISBN, system accession counters, and translation notes.</p>
        </div>
      </div>

      <div class="section-body">
        <div class="field">
          <div class="label-row">
            <label for="chief-isbn-input">ISBN (10 OR 13 DIGITS)</label>
            <span v-if="!isIsbnValid && form.isbn" class="val-error">Invalid Checksum</span>
          </div>
          <input
            id="chief-isbn-input"
            v-model="form.isbn"
            placeholder="e.g. 978-81-264-1234-5"
            @blur="formatIsbnOnBlur"
          />
        </div>

        <div class="stat-card">
          <span>SERIAL NO.</span>
          <strong>{{ previewNumbers.serial_no || 'Auto-assigned' }}</strong>
        </div>

        <div class="stat-card">
          <span>ACCESSION NO.</span>
          <strong class="accent">{{ previewNumbers.accession_no || 'Select Language First' }}</strong>
        </div>

        <div class="field">
          <label for="chief-orig-lang">ORIGINAL LANGUAGE</label>
          <select id="chief-orig-lang" v-model="form.original_language">
            <option value="">Select Original Language</option>
            <option v-for="lang in availableLanguages" :key="'orig-' + lang" :value="lang">
              {{ lang }}
            </option>
          </select>
        </div>

        <div class="field">
          <label for="chief-trans-comp">TRANSLATION / COMPILATION</label>
          <input id="chief-trans-comp" v-model="form.translation_compilation" placeholder="Translator context or notes…" />
        </div>
      </div>
    </section>

    <!-- Section 03: Classification & Shelving -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">03</div>
        <div>
          <h2>Classification & Shelving</h2>
          <p>Dewey Decimal Classification, stack call numbers, and genre tags.</p>
        </div>
      </div>

      <div class="section-body">
        <!-- Strict DDC with validation message -->
        <div class="field">
          <div class="label-row">
            <label for="chief-ddc-input">DDC (DEWEY DECIMAL)</label>
            <span v-if="!isDdcValid" class="val-error">3 digits [.decimals]</span>
          </div>
          <input
            id="chief-ddc-input"
            v-model="form.ddc"
            placeholder="e.g. 894.812"
            maxlength="14"
            :class="{ 'field-error': !isDdcValid }"
          />
        </div>

        <div class="field">
          <label for="chief-callno-input">CALL NUMBER</label>
          <div class="input-clearable">
            <input id="chief-callno-input" v-model="form.call_no" placeholder="e.g. ML-FIC-26.0" />
            <button type="button" class="inline-btn" @click="applyGeneratedCallNumber">Use Suggestion</button>
          </div>
        </div>

        <div class="field">
          <label for="chief-shelf-input">SHELF LOCATION</label>
          <input id="chief-shelf-input" v-model="form.shelf" placeholder="e.g. S-800-ML" />
        </div>

        <!-- Suggestion Banner -->
        <div class="suggestion-banner full">
          <div>
            <span>Suggested Call Number:</span>
            <strong>{{ callNumberPreview || '—' }}</strong>
          </div>
          <div>
            <span>Smart Shelf Placement:</span>
            <strong>{{ shelfSuggestion || '—' }}</strong>
          </div>
        </div>

        <!-- Multi-Tag Genre Combobox -->
        <div class="field full">
          <div class="label-row">
            <label>GENRE TAGS (MULTI-SELECT COMBOBOX)</label>
            <span class="badge-sub">{{ liveCompiledGenreChips.length }} active</span>
          </div>

          <div class="genre-tag-container">
            <div class="chips-row">
              <span v-for="tag in liveCompiledGenreChips" :key="tag" class="genre-chip">
                {{ tag }}
                <button type="button" @click="removeGenreChip(tag)">×</button>
              </span>
              <span v-if="!liveCompiledGenreChips.length" class="empty-text">No genre tags added yet.</span>
            </div>

            <div class="tag-input-group">
              <input
                v-model="newGenreInput"
                placeholder="Type genre and press Enter or comma…"
                @keydown.enter.prevent="submitGenre"
                @keydown.,.prevent="submitGenre"
              />
              <button type="button" class="btn btn-secondary btn-sm" @click="submitGenre">Add Tag</button>
              <button v-if="liveCompiledGenreChips.length" type="button" class="clear-link" @click="clearAllGenres">Clear all</button>
            </div>

            <div class="quick-pills-row">
              <small>Quick Pick:</small>
              <button
                v-for="p in popularIndianGenres"
                :key="p"
                type="button"
                class="quick-pill"
                :class="{ active: liveCompiledGenreChips.includes(p) }"
                @click="toggleGenrePill(p)"
              >
                + {{ p }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 04: Context, Series & Rights -->
    <section class="form-card">
      <div class="section-heading">
        <div class="section-number">04</div>
        <div>
          <h2>Context, Series & Rights</h2>
          <p>Relational series grouping, academic imprint series, and copyright status.</p>
        </div>
      </div>

      <div class="section-body">
        <div class="field">
          <label for="chief-orig-title">ORIGINAL TITLE</label>
          <input id="chief-orig-title" v-model="form.original_title" placeholder="Root title in source tongue" />
        </div>

        <div class="field">
          <label for="chief-orig-author">ORIGINAL AUTHOR</label>
          <input id="chief-orig-author" v-model="form.original_author" placeholder="Root creator" />
        </div>

        <div class="field">
          <label for="chief-translator">TRANSLATOR</label>
          <input id="chief-translator" v-model="form.translator" placeholder="Credited translator" />
        </div>

        <div class="field">
          <label for="chief-editor">COMPILER / EDITOR</label>
          <input id="chief-editor" v-model="form.compiler_editor" placeholder="Compiler or editor" />
        </div>

        <div class="field">
          <label for="chief-work-nature">WORK NATURE</label>
          <input id="chief-work-nature" v-model="form.work_nature" placeholder="e.g. Novel, Monograph, Play, Anthology" />
        </div>

        <div class="field">
          <label for="chief-edition">EDITION STATEMENT</label>
          <input id="chief-edition" v-model="form.edition_statement" placeholder="e.g. 1st Edition, Revised" />
        </div>

        <!-- Series Grouping with Digits Only -->
        <div class="field">
          <label for="chief-series-group">SERIES GROUP NAME</label>
          <input id="chief-series-group" v-model="seriesName" placeholder="Group name for discoverability" />
        </div>

        <div class="field">
          <label for="chief-series-num">SERIES NUMBER (DIGITS ONLY)</label>
          <input id="chief-series-num" v-model="seriesNumber" inputmode="numeric" placeholder="e.g. 2" @input="enforceNumbersOnly($event, 'seriesNumber')" />
        </div>

        <div class="field">
          <label for="chief-vol-num">VOLUME NUMBER (DIGITS ONLY)</label>
          <input id="chief-vol-num" v-model="volumeNumber" inputmode="numeric" placeholder="e.g. 1" @input="enforceNumbersOnly($event, 'volumeNumber')" />
        </div>

        <div class="field">
          <label for="chief-rel-work">RELATED WORK ID (DIGITS ONLY)</label>
          <input id="chief-rel-work" v-model="relatedWorkId" inputmode="numeric" placeholder="Existing Work ID" @input="enforceNumbersOnly($event, 'relatedWorkId')" />
        </div>

        <div class="field full">
          <label for="chief-subjects">SUBJECT HEADINGS (COMMA-SEPARATED)</label>
          <input id="chief-subjects" v-model="form.subject_headings" placeholder="e.g. Kerala History, Folklore, Detective" />
        </div>

        <!-- Copyright Combobox -->
        <div class="field">
          <label for="chief-copyright-select">COPYRIGHT STATUS</label>
          <select id="chief-copyright-select" v-model="copyrightSelectValue" @change="handleCopyrightSelectChange">
            <option value="">Select Status</option>
            <option v-for="c in copyrightOptions" :key="c" :value="c">{{ c }}</option>
            <option value="__CUSTOM__">Other (Specify)…</option>
          </select>
          <input
            v-if="copyrightSelectValue === '__CUSTOM__'"
            v-model="form.copyright_status"
            class="custom-subfield"
            placeholder="Enter custom copyright terms…"
          />
        </div>

        <div class="field">
          <label for="chief-target-era">TARGET AUDIENCE / ERA</label>
          <input id="chief-target-era" v-model="form.target_audience_era" placeholder="e.g. 19th Century, Academic" />
        </div>

        <!-- Expandable Drawer for LCCN / OCLC -->
        <div class="field full">
          <details class="advanced-drawer">
            <summary>External Identifiers (LCCN / OCLC WorldCat)</summary>
            <div class="drawer-grid">
              <div class="field">
                <label for="chief-lccn-input">LCCN</label>
                <input id="chief-lccn-input" v-model="form.lccn" placeholder="Library of Congress Control No." />
              </div>
              <div class="field">
                <label for="chief-oclc-input">OCLC NO. (DIGITS ONLY)</label>
                <input id="chief-oclc-input" v-model="form.oclc_no" inputmode="numeric" placeholder="OCLC control number" @input="enforceNumbersOnly($event, 'oclc_no')" />
              </div>
            </div>
          </details>
        </div>

        <div class="field full">
          <label for="chief-notes-input">BIBLIOGRAPHIC NOTES</label>
          <textarea id="chief-notes-input" v-model="form.notes" rows="3" placeholder="Curatorial or contextual notes…"></textarea>
        </div>
      </div>
    </section>

    <!-- Section 05: Verification & Registration Gate -->
    <section class="form-card gate-section">
      <div class="section-heading">
        <div class="section-number">05</div>
        <div>
          <h2>Registration Gate</h2>
          <p>Duplicate checks, record readiness, and direct authorization.</p>
        </div>
      </div>

      <div class="section-body">
        <!-- Conflict Box -->
        <div class="gate-card" :class="{ 'warning-box': duplicateResult.severity !== 'none' }">
          <div class="gate-card-title">
            <span>Duplicate Check</span>
            <strong>{{ duplicateLoading ? 'Scanning…' : duplicateResult.severity === 'none' ? 'Clear' : duplicateResult.severity.toUpperCase() + ' MATCH' }}</strong>
          </div>
          <p v-if="!duplicateLoading && duplicateResult.severity === 'none'" class="success-text">Catalogue clear. No conflicts detected.</p>
          <div v-if="!duplicateLoading && duplicateResult.severity !== 'none'">
            <p class="warning-text">Potential match identified in catalogue records:</p>
            <button
              v-for="m in duplicateResult.matches"
              :key="m.work_id"
              type="button"
              class="match-record-btn"
              @click="confirmPrefill(m)"
            >
              <strong>#{{ m.work_id }}: {{ m.title }}</strong>
              <small>{{ m.author }} · {{ m.language }}</small>
            </button>
            <label v-if="duplicateResult.severity === 'strong'" class="checkbox-override">
              <input type="checkbox" v-model="adminOverride" />
              <span>Chief Override: Authorize despite strong duplicate match</span>
            </label>
          </div>
        </div>

        <!-- Readiness Score Card -->
        <div class="gate-card">
          <div class="gate-card-title">
            <span>Record Readiness</span>
            <strong class="accent">{{ readinessPercent }}%</strong>
          </div>
          <div class="progress-bar-wrap">
            <div class="progress-fill" :style="{ width: `${readinessPercent}%` }"></div>
          </div>
          <div class="readiness-grid">
            <div v-for="item in readinessItems" :key="item.key" class="readiness-item">
              <span class="status-sym" :class="{ checked: item.value }">{{ item.value ? '✓' : '○' }}</span>
              <small>{{ item.key.toUpperCase() }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Card Bar -->
      <div class="action-footer">
        <div>
          <span class="footer-label">CHIEF AUTHORITY</span>
          <strong>Direct catalogue intake</strong>
          <p>Committed records immediately become primary holding references.</p>
        </div>

        <div class="footer-btns">
          <button type="button" class="btn btn-secondary" @click="savePartialDraft()" :disabled="loading || !hasDraftContent">
            Save Draft
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="loading || isFrozen"
            @click="triggerCreationPrompt"
          >
            {{ loading ? 'Registering…' : isFrozen ? 'Resolve Match First' : 'AUTHORIZE & REGISTER WORK' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Confirm Modal -->
    <div v-if="showPromptModal" class="modal-backdrop" @click.self="showPromptModal = false">
      <section class="confirm-modal">
        <div class="modal-eyebrow">CHIEF DIRECT COMMIT</div>
        <h2>Authorize New Work Record?</h2>
        <p>This work will be directly added to the active registry dossier.</p>

        <div class="modal-item-preview">
          <strong>{{ form.title || 'Untitled Work' }}</strong>
          <span>{{ form.author || 'Unknown' }} · {{ form.language_id || 'No Language' }}</span>
        </div>

        <label>
          <span>Operational Reason (Required)</span>
          <input
            v-model="creationReason"
            placeholder="e.g. New accession / First edition acquisition"
            @keyup.enter="executeConfirmedCreation"
          />
        </label>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="showPromptModal = false">CANCEL</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="loading || !creationReason.trim()"
            @click="executeConfirmedCreation"
          >
            CONFIRM & REGISTER →
          </button>
        </div>
      </section>
    </div>

    <!-- Toast Notification -->
    <div v-if="result" class="toast-popup" :class="{ 'toast-err': result.error }">
      <strong>{{ result.draft_saved ? 'Working Draft Saved' : result.work_id ? 'Work Successfully Registered' : 'Transaction Failed' }}</strong>
      <span>{{ result.draft_saved ? result.message : result.work_id ? `Work #${result.work_id} · Accession: ${result.accession_no}` : (result.detail || result.error) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import { useCreateWork } from "./useCreateWork.js"

const router = useRouter()

const themeMode = ref(
  document.documentElement.getAttribute("data-theme") ||
  localStorage.getItem("ui-theme") ||
  "dark"
)
let themeObserver = null

const titleLookupArea = ref(null)
const authorLookupArea = ref(null)
const authorInputAnchor = ref(null)
const authorInput = ref(null)
const authorDropdown = ref(null)
const authorDropdownStyle = ref({ position: "fixed", visibility: "hidden" })
const publisherLookupArea = ref(null)

const newGenreInput = ref("")
const copyrightSelectValue = ref("")
const copyrightOptions = [
  "Public Domain",
  "In Copyright (All Rights Reserved)",
  "In Copyright - Orphan Work",
  "Creative Commons (CC BY / CC BY-SA)",
  "Creative Commons Zero (CC0)",
  "Copyright Not Evaluated / Unknown"
]

const {
  pasteInput, isParsing, showAuthorSuggestions, showPublisherSuggestions,
  showPromptModal, creationReason, form, previewNumbers, result, loading,
  duplicateLoading, isbnLoading, draftVersions, hasDraftContent, isFrozen,
  isIsbnValid, isDdcValid, isPasteIsbnReady, readinessItems, readinessPercent,
  isFieldImported, authorSuggestions, externalAuthorSuggestions,
  selectedAuthorityName, publisherSuggestions, titleLookupResults,
  selectTitleCandidate, clearTitleLookupResults, liveCompiledGenreChips,
  popularIndianGenres, addGenreTag, toggleGenrePill, removeGenreChip, clearAllGenres,
  seriesName, seriesNumber, volumeNumber, relatedWorkId, availableLanguages,
  savePartialDraft, clearPartialDrafts, selectAuthor, selectExternalAuthor,
  selectPublisher, handleBlurAction, sanitizeField, handleMetadataPaste,
  clearField, confirmPrefill, triggerCreationPrompt, executeConfirmedCreation,
  normalizeParserIsbn, enforceNumbersOnly, formatIsbnOnBlur,
  duplicateResult, adminOverride, applyGeneratedCallNumber, callNumberPreview, shelfSuggestion
} = useCreateWork()

function submitGenre() {
  if (!newGenreInput.value.trim()) return
  addGenreTag(newGenreInput.value)
  newGenreInput.value = ""
}

function handleCopyrightSelectChange() {
  if (copyrightSelectValue.value !== '__CUSTOM__') {
    form.value.copyright_status = copyrightSelectValue.value
  }
}

function handleBackToCatalogue() {
  router.push('/catalogue')
}

function handleKeyboard(e) {
  if (e.key === 'Escape') {
    if (showPromptModal.value) {
      showPromptModal.value = false
    } else {
      handleBackToCatalogue()
    }
  }
}

function updateAuthorDropdownPosition() {
  const anchor = authorInputAnchor.value
  if (!anchor || typeof window === "undefined") return
  const rect = anchor.getBoundingClientRect()
  const edge = 8
  const width = Math.max(180, Math.min(rect.width, window.innerWidth - edge * 2))
  const left = Math.max(edge, Math.min(rect.left, window.innerWidth - width - edge))
  const preferredHeight = Math.min(360, Math.floor(window.innerHeight * 0.48))
  const below = Math.max(0, window.innerHeight - rect.bottom - 6 - edge)
  const above = Math.max(0, rect.top - 6 - edge)
  const openAbove = below < Math.min(preferredHeight, 220) && above > below
  const maxHeight = Math.max(110, Math.min(preferredHeight, openAbove ? above : below))
  const top = openAbove ? rect.top - maxHeight - 6 : rect.bottom + 6

  authorDropdownStyle.value = {
    position: "fixed",
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    maxHeight: `${maxHeight}px`,
    visibility: "visible",
    zIndex: 99999
  }
}

function openAuthorSuggestions() {
  showAuthorSuggestions.value = true
  requestAnimationFrame(updateAuthorDropdownPosition)
}

function handleAuthorBlur() {
  sanitizeField("author")
  window.setTimeout(() => {
    const active = document.activeElement
    if (!authorInputAnchor.value?.contains(active) && !authorDropdown.value?.contains(active)) {
      showAuthorSuggestions.value = false
    }
  }, 220)
}

function closePopoversOnClickOutside(e) {
  if (titleLookupArea.value && !titleLookupArea.value.contains(e.target)) clearTitleLookupResults()
  const inAuthor = authorLookupArea.value?.contains(e.target) || authorDropdown.value?.contains(e.target)
  if (!inAuthor) showAuthorSuggestions.value = false
  if (publisherLookupArea.value && !publisherLookupArea.value.contains(e.target)) showPublisherSuggestions.value = false
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyboard)
  document.addEventListener('pointerdown', closePopoversOnClickOutside)
  window.addEventListener('resize', updateAuthorDropdownPosition)
  window.addEventListener('scroll', updateAuthorDropdownPosition, true)

  themeObserver = new MutationObserver(() => {
    themeMode.value = document.documentElement.getAttribute("data-theme") || "dark"
  })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"]
  })
})

onUnmounted(() => {
  if (themeObserver) themeObserver.disconnect()
  window.removeEventListener('keydown', handleKeyboard)
  document.removeEventListener('pointerdown', closePopoversOnClickOutside)
  window.removeEventListener('resize', updateAuthorDropdownPosition)
  window.removeEventListener('scroll', updateAuthorDropdownPosition, true)
})
</script>

<style scoped>
/* Inherit shell CSS variables cleanly from CreateItemView */
.chief-work-page {
  min-height: 100%;
  padding: 34px 30px 60px;
  box-sizing: border-box;
  transition: background .2s ease, color .2s ease;
}

.chief-work-page.theme-dark {
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

.chief-work-page.theme-light {
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

.page-header,
.form-card {
  width: min(1120px, 100%);
  margin-left: auto;
  margin-right: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 28px;
  margin-bottom: 22px;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 1.8px;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 8px;
}

h1 {
  font-family: "Playfair Display", serif;
  font-size: 34px;
  line-height: 1.1;
  font-weight: 500;
  margin: 0 0 8px;
  color: var(--text);
}

.page-intro {
  margin: 0;
  max-width: 600px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.authority-badge {
  min-width: 170px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.authority-badge.chief {
  background: #eadfc7;
  border-color: #c4ad7d;
  color: #332b1d;
}

.theme-dark .authority-badge.chief {
  background: #231b10;
  border-color: #5c431d;
  color: #fbbf24;
}

.badge-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #b45309;
}

.authority-badge strong {
  display: block;
  font-size: 12px;
  letter-spacing: 1.1px;
}

.authority-badge small {
  display: block;
  font-size: 9px;
  letter-spacing: 1.2px;
  opacity: .75;
}

.readiness-badge {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 10px 16px;
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  color: var(--muted);
}

.readiness-badge strong {
  font-size: 16px;
  color: var(--accent);
}

/* Form Cards */
.form-card {
  border: 1px solid var(--border);
  border-radius: 9px;
  overflow: hidden;
  margin-bottom: 18px;
  box-shadow: 0 7px 18px rgba(18, 45, 50, .05);
  background: var(--card);
}

.intake-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
}

.intake-info h3 {
  margin: 2px 0 4px;
  font-size: 15px;
  color: var(--text);
}

.intake-info p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.badge-tag {
  font-size: 10px;
  letter-spacing: 1.5px;
  font-weight: 700;
  color: var(--accent);
}

.intake-actions {
  display: flex;
  gap: 10px;
  width: 48%;
}

.intake-actions input {
  flex: 1;
  height: 44px;
  padding: 0 14px;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--input);
  color: var(--text);
  outline: none;
}

.section-heading {
  display: flex;
  gap: 14px;
  padding: 18px 24px;
  background: var(--card-header, #111827);
  border-bottom: 1px solid var(--border);
}

.section-number {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  padding-top: 2px;
}

.section-heading h2 {
  color: var(--text);
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 3px;
}

.section-heading p {
  color: var(--muted);
  font-size: 12px;
  margin: 0;
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

.field.full {
  grid-column: 1 / -1;
}

.field label {
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 1.1px;
  font-weight: 700;
}

.field input,
.field select,
.field textarea {
  height: 48px;
  width: 100%;
  box-sizing: border-box;
  padding: 0 14px;
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
  padding: 12px 14px;
  line-height: 1.5;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, .11);
}

.field-error {
  border-color: #ef4444 !important;
}

.label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.label-row label {
  margin-bottom: 0;
}

.val-error {
  font-size: 11px;
  color: #ef4444;
  font-weight: 700;
}

.required {
  color: #ef4444;
}

.input-clearable {
  position: relative;
  display: flex;
  align-items: center;
}

.clear-btn {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.inline-btn {
  position: absolute;
  right: 8px;
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  cursor: pointer;
}

.custom-subfield {
  margin-top: 8px;
  border-style: dashed !important;
}

.stat-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 12px 16px;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--input);
}

.stat-card span {
  font-size: 10px;
  color: var(--muted);
  font-weight: 700;
  letter-spacing: 1px;
}

.stat-card strong {
  margin-top: 4px;
  font-size: 15px;
  font-family: monospace;
}

.stat-card strong.accent {
  color: var(--accent);
}

.suggestion-banner {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 14px 18px;
  border-left: 3px solid var(--accent);
  border-radius: 5px;
  background: var(--card-alt);
  border-top: 1px solid var(--border-soft);
  border-right: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.suggestion-banner span {
  display: block;
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 1px;
}

.suggestion-banner strong {
  display: block;
  margin-top: 3px;
  color: var(--text);
  font-size: 13px;
}

/* Multi-Tag Genre Combobox */
.genre-tag-container {
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px;
}

.chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
  min-height: 28px;
}

.genre-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--input);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
}

.genre-chip button {
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  line-height: 1;
}

.tag-input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tag-input-group input {
  flex: 1;
  height: 42px;
}

.clear-link {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
  text-decoration: underline;
}

.quick-pills-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 10px;
}

.quick-pills-row small {
  font-size: 11px;
  color: var(--muted);
  margin-right: 4px;
}

.quick-pill {
  padding: 4px 10px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text);
  cursor: pointer;
}

.quick-pill:hover, .quick-pill.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.advanced-drawer {
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 16px;
}

.advanced-drawer summary {
  cursor: pointer;
  font-size: 11px;
  letter-spacing: 1px;
  font-weight: 700;
  color: var(--accent);
}

.drawer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 14px;
}

/* Verification Gate Section */
.gate-section .section-body {
  grid-template-columns: 1fr 1fr;
}

.gate-card {
  padding: 16px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--card-alt);
}

.gate-card-title {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 700;
}

.gate-card.warning-box {
  background: #fff4f2;
  border-color: #edc2bb;
  color: #9f3f38;
}

.theme-dark .gate-card.warning-box {
  background: #250906;
  border-color: #4a120b;
  color: #f87171;
}

.success-text {
  font-size: 12px;
  color: #16a34a;
  margin: 0;
}

.warning-text {
  font-size: 12px;
  margin: 0 0 8px;
}

.match-record-btn {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--card);
  margin-top: 6px;
  cursor: pointer;
}

.match-record-btn strong {
  display: block;
  font-size: 12px;
  color: var(--text);
}

.match-record-btn small {
  color: var(--muted);
  font-size: 11px;
}

.checkbox-override {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.progress-bar-wrap {
  height: 6px;
  background: var(--border);
  border-radius: 99px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: #16a34a;
}

.readiness-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.readiness-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.status-sym {
  color: var(--muted);
}

.status-sym.checked {
  color: #16a34a;
  font-weight: 700;
}

.action-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 24px;
  background: var(--card-alt);
  border-top: 1px solid var(--border);
}

.action-footer strong {
  display: block;
  font-size: 15px;
  color: var(--text);
}

.action-footer p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.footer-btns {
  display: flex;
  gap: 10px;
}

/* Global Buttons */
.btn {
  height: 44px;
  padding: 0 20px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .8px;
  cursor: pointer;
  transition: .18s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-primary {
  border: 1px solid var(--accent);
  background: var(--accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  filter: brightness(.94);
}

.btn-primary:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.btn-secondary {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
}

.btn-back {
  height: 38px;
  padding: 0 14px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
}

.btn-sm {
  height: 36px;
  padding: 0 14px;
}

.kbd-pill {
  background: var(--input);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  color: var(--accent);
}

/* Modal */
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
  font-size: 11px;
  letter-spacing: 1.5px;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 8px;
}

.confirm-modal h2 {
  font-family: "Playfair Display", serif;
  font-size: 24px;
  font-weight: 500;
  margin: 0 0 10px;
}

.confirm-modal p {
  color: var(--muted);
  font-size: 13px;
  margin: 0 0 16px;
}

.modal-item-preview {
  background: var(--card-alt);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 16px;
}

.modal-item-preview strong {
  display: block;
  font-size: 14px;
  color: var(--text);
}

.modal-item-preview span {
  font-size: 12px;
  color: var(--muted);
}

.confirm-modal label span {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  margin-bottom: 6px;
}

.confirm-modal input {
  width: 100%;
  height: 44px;
  box-sizing: border-box;
  padding: 0 14px;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--input);
  color: var(--text);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

/* Popover suggestions */
.popover-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 10px 25px rgba(0,0,0,.25);
  z-index: 1000;
  max-height: 250px;
  overflow-y: auto;
}

.popover-head {
  padding: 8px 12px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  background: var(--card-alt);
  color: var(--accent);
}

.popover-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  text-align: left;
  cursor: pointer;
  color: var(--text);
}

.popover-item:hover {
  background: var(--card-alt);
}

.lookup-candidate-dropdown {
  margin-top: 6px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--card-alt);
  overflow: hidden;
}

.candidate-row {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}

.candidate-row:hover {
  background: var(--input);
}

.candidate-row strong {
  display: block;
  font-size: 13px;
  color: var(--text);
}

.candidate-row small {
  color: var(--muted);
  font-size: 11px;
}

.toast-popup {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 4px solid #16a34a;
  padding: 14px 18px;
  border-radius: 6px;
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
  z-index: 2000;
  color: var(--text);
}

.toast-popup.toast-err {
  border-left-color: #ef4444;
}

.toast-popup strong {
  display: block;
  font-size: 13px;
}

.toast-popup span {
  font-size: 11px;
  color: var(--muted);
}

@media (max-width: 800px) {
  .section-body {
    grid-template-columns: 1fr;
  }
  .page-header {
    flex-direction: column;
  }
  .intake-strip {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }
  .intake-actions {
    width: 100%;
  }
}
</style>