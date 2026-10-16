<template>
  <div class="app-container">
    <!-- Header -->
    <header class="app-header">
      <div class="brand">
        <div class="brand-logo">AO</div>
        <div>
          <h1>Work Registration Dossier</h1>
          <p>Curatorial Review & Cataloging System</p>
        </div>
      </div>
      <div class="header-status">
        <span class="badge" :class="{ 'badge-warning': isFrozen }">
          {{ isFrozen ? 'Action Required: Match Found' : 'Ready for Registration' }}
        </span>
      </div>
    </header>

    <!-- Quick Intake Bar -->
    <section class="card intake-card">
      <div class="intake-label">
        <strong>Quick ISBN Lookup</strong>
        <span>Scan or paste barcode</span>
      </div>
      <div class="intake-input-group">
        <input
          id="parser-field-input"
          v-model="pasteInput"
          @input="normalizeParserIsbn"
          @paste="handleMetadataPaste"
          placeholder="Enter ISBN to auto-populate metadata..."
        />
        <button type="button" @click="handleMetadataPaste(null)" :disabled="isParsing || !isPasteIsbnReady">
          {{ isParsing ? 'Reading...' : 'Import Metadata' }}
        </button>
      </div>
    </section>

    <!-- Main Workspace Grid -->
    <main class="workspace">
      <!-- Left Column: Form Sections -->
      <div class="form-column">
        
        <!-- Section A: Identity -->
        <section class="card">
          <div class="card-header">
            <h2>A. Work Identity</h2>
          </div>
          <div class="card-body">
            <div class="field-group primary-title-group title-lookup-group" ref="titleLookupArea">
              <label for="title-input-field">Title</label>
              <div class="title-input-wrapper">
                <input
                  id="title-input-field"
                  v-model="form.title"
                  autocomplete="new-password"
                  autocapitalize="off"
                  spellcheck="false"
                  @input="clearTitleLookupResults()"
                  @blur="sanitizeField('title')"
                  maxlength="255"
                  placeholder="Enter work title..."
                />
                <button v-if="form.title" type="button" class="field-clear-btn" @mousedown.prevent @click="clearField('title'); clearTitleLookupResults(false)">Clear</button>
              </div>
              <small v-if="isFieldImported('title')">Imported from source · Please verify</small>
              <small class="lookup-help">Title candidates search automatically as you type. The title changes only after you select a candidate.</small>
              <p v-if="titleLookupMessage" class="lookup-message" role="status" aria-live="polite">{{ titleLookupMessage }}</p>
              <div v-if="titleLookupResults.length" class="title-candidate-list">
                <div v-for="(candidate, index) in titleLookupResults" :key="`${candidate.source}-${candidate.external_id || index}-${candidate.title}`" class="title-candidate-row">
                  <div class="title-candidate-copy">
                    <strong>{{ candidate.title }}</strong>
                    <small>{{ [candidate.author, candidate.year, candidate.source].filter(Boolean).join(' · ') }}</small>
                    <small v-if="Number.isFinite(Number(candidate.match_score))">Approximate spelling/title similarity: {{ candidate.match_score }}%</small>
                  </div>
                  <button type="button" class="title-use-btn" @mousedown.prevent @click="selectTitleCandidate(candidate)">Use title</button>
                </div>
              </div>
            </div>

            <div class="grid-2col">
              <div ref="authorLookupArea" class="field-group suggestion-container author-lookup-group">
                <label for="chief-author-input">Primary Authority (Author)</label>
                <div ref="authorInputAnchor" class="input-with-lock">
                  <input
                    id="chief-author-input"
                    ref="authorInput"
                    v-model="form.author"
                    autocomplete="new-password"
                    autocapitalize="off"
                    spellcheck="false"
                    aria-autocomplete="list"
                    aria-controls="chief-author-suggestions"
                    :aria-expanded="showAuthorSuggestions && form.author.trim().length >= 2"
                    @focus="openAuthorSuggestions"
                    @blur="handleAuthorBlur"
                    maxlength="150"
                    placeholder="Author name..."
                  />
                  <button v-if="form.author" type="button" class="field-clear-btn author-clear-btn" @mousedown.prevent @click="clearField('author')">Clear</button>
                  <span v-if="selectedAuthorityName" class="lock-badge">✓ Linked</span>
                </div>
                <Teleport to="body">
                  <div
                    v-if="showAuthorSuggestions && form.author.trim().length >= 2"
                    ref="authorDropdown"
                    id="chief-author-suggestions"
                    class="suggestions-dropdown author-suggestions-dropdown"
                    :style="authorDropdownStyle"
                    role="listbox"
                    aria-label="Author suggestions"
                    @pointerdown.stop
                  >
                    <div class="suggestion-header">LOCAL ATHENAEUM AUTHORITY RECORDS</div>
                    <button v-for="author in authorSuggestions" :key="author.authority_id" type="button" class="suggestion-row author-suggestion-button" @mousedown.prevent @click="selectAuthor(author)">
                      <span class="suggestion-main">{{ author.preferred_name }}</span>
                      <small class="suggestion-meta">{{ author.status }}</small>
                    </button>
                    <div v-if="!authorSuggestions.length" class="suggestion-empty">No matching local authority record.</div>
                    <template v-if="externalAuthorSuggestions.length">
                      <div class="suggestion-header external-suggestion-header">EXTERNAL CANDIDATES · OPEN LIBRARY</div>
                      <button v-for="author in externalAuthorSuggestions" :key="author.external_id || author.preferred_name" type="button" class="suggestion-row author-suggestion-button external-author-button" @mousedown.prevent @click="selectExternalAuthor(author)">
                        <span class="suggestion-main">{{ author.canonical_name || author.preferred_name }}</span>
                        <small class="suggestion-meta">{{ author.source || 'Open Library' }}<span v-if="author.correction_match"> · spelling correction candidate</span></small>
                        <small v-if="author.top_work" class="suggestion-detail">Top work: {{ author.top_work }}</small>
                        <small v-if="author.birth_date || author.death_date" class="suggestion-detail">Life dates: {{ [author.birth_date, author.death_date].filter(Boolean).join(' – ') }}</small>
                      </button>
                    </template>
                    <div v-if="externalAuthorSearchMessage" class="suggestion-empty" role="status" aria-live="polite">{{ externalAuthorSearchMessage }}</div>
                    <div v-if="externalAuthorSearchLoading" class="suggestion-empty" role="status">Searching Open Library…</div>
                  </div>
                </Teleport>
              </div>

              <div ref="publisherLookupArea" class="field-group suggestion-container">
                <label>Publisher</label>
                <input
                  v-model="form.publisher"
                  @focus="showPublisherSuggestions = true"
                  @blur="handleBlurAction('publisher')"
                  placeholder="Publisher name..."
                />
                <div v-if="showPublisherSuggestions && publisherSuggestions.length" class="suggestions-dropdown">
                  <div class="suggestion-header">Publisher Matches</div>
                  <div
                    v-for="pub in publisherSuggestions"
                    :key="pub"
                    @mousedown="selectPublisher(pub)"
                    class="suggestion-row"
                  >
                    <strong>{{ pub }}</strong>
                  </div>
                </div>
              </div>
            </div>

            <div class="grid-3col">
              <div class="field-group">
                <label>Language</label>
                <select v-model="form.language_id">
                  <option disabled value="">Select language</option>
                  <option value="Malayalam">Malayalam</option>
                  <option value="English">English</option>
                  <option value="Multi -Lingual">Multilingual</option>
                  <option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option>
                </select>
              </div>

              <div class="field-group">
                <label>Category</label>
                <select v-model="form.category">
                  <option value="">No category</option>
                  <option value="Fiction">Fiction</option>
                  <option value="Non-Fiction">Non-Fiction</option>
                  <option value="Reference">Reference</option>
                  <option value="Religious">Religious</option>
                  <option value="Poetry">Poetry</option>
                </select>
              </div>

              <div class="field-group">
                <label>Publication Year</label>
                <input v-model="form.year" maxlength="4" placeholder="YYYY" />
              </div>
            </div>
          </div>
        </section>

        <!-- Section B: Bibliography -->
        <section class="card">
          <div class="card-header">
            <h2>B. Bibliography & Identifiers</h2>
          </div>
          <div class="card-body">
            <div class="grid-3col">
              <div class="field-group">
                <label>ISBN</label>
                <input id="isbn-input-field" v-model="form.isbn" placeholder="ISBN-10 or ISBN-13" />
                <span class="helper-text">
                  {{ isbnLoading ? 'Looking up metadata...' : isIsbnReadyForCatalogue ? 'Valid identifier' : (isIsbnValid === true && isIsbnChecksumValid === false ? 'Checksum error' : 'Unverified identifier') }}
                </span>
              </div>
              <div class="stat-box">
                <span>Serial No.</span>
                <strong>{{ previewNumbers.serial_no || '—' }}</strong>
              </div>
              <div class="stat-box">
                <span>Accession No.</span>
                <strong>{{ previewNumbers.accession_no || '—' }}</strong>
              </div>
            </div>

            <div class="grid-2col" style="margin-top: 16px;">
              <div class="field-group">
                <label>Original Language</label>
                <select v-model="form.original_language">
                  <option value="" disabled>Select original language</option>
                  <option value="Malayalam">Malayalam</option>
                  <option value="English">English</option>
                  <option value="Multi -Lingual">Multilingual</option>
                  <option v-for="lang in extraLanguages" :key="lang" :value="lang">{{ lang }}</option>
                </select>
              </div>
              <div class="field-group">
                <label>Translation / Compilation</label>
                <input v-model="form.translation_compilation" placeholder="Translator or compiler context" />
              </div>
            </div>
          </div>
        </section>

        <!-- Section C: Classification -->
        <section class="card">
          <div class="card-header">
            <h2>C. Classification & Shelving</h2>
          </div>
          <div class="card-body">
            <div class="grid-3col">
              <div class="field-group">
                <label>DDC</label>
                <input id="ddc-input-field" v-model="form.ddc" placeholder="e.g. 823.9" />
              </div>
              <div class="field-group">
                <label>Call Number</label>
                <div class="inline-action-input">
                  <input v-model="form.call_no" placeholder="Library call number" />
                  <button type="button" @click="applyGeneratedCallNumber">Use</button>
                </div>
              </div>
              <div class="field-group">
                <label>Shelf Location</label>
                <input v-model="form.shelf" placeholder="Shelf" />
              </div>
            </div>

            <div class="preview-banner">
              <div><span>Suggested Call Number:</span> <strong>{{ callNumberPreview || '—' }}</strong></div>
              <div><span>Smart Shelf Suggestion:</span> <strong>{{ shelfSuggestion || '—' }}</strong></div>
            </div>

            <div class="genre-section">
              <div class="genre-header">
                <label>Genre Register</label>
                <span class="badge-sub">{{ liveCompiledGenreChips.length }} signals active</span>
              </div>
              <div class="grid-3col">
                <select v-model="selectedGroupAGenre" @change="syncGenreSelection">
                  <option value="">Creative</option>
                  <option v-for="g in genreGroupA" :key="g" :value="g">{{ g }}</option>
                </select>
                <select v-model="selectedGroupBGenre" @change="syncGenreSelection">
                  <option value="">Factual</option>
                  <option v-for="g in genreGroupB" :key="g" :value="g">{{ g }}</option>
                </select>
                <select v-model="selectedGroupCGenre" @change="syncGenreSelection">
                  <option value="">Community</option>
                  <option v-for="g in dynamicCommunityGenres" :key="g" :value="g">{{ g }}</option>
                  <option value="CUSTOM_MANUAL_OVERRIDE">Manual</option>
                </select>
              </div>
              <input
                v-if="showCustomManualGenreField"
                v-model="customManualGenreText"
                @input="syncManualGenreInput"
                class="custom-input"
                placeholder="Custom genres separated by /"
              />
              <div class="genre-chips-container">
                <span v-for="chip in liveCompiledGenreChips" :key="chip" class="chip">{{ chip }}</span>
                <span v-if="!liveCompiledGenreChips.length" class="empty-text">No genre signals entered yet.</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Section D: Relations & Notes -->
        <section class="card">
          <div class="card-header">
            <h2>D. Relations & Notes</h2>
          </div>
          <div class="card-body">
            <div class="grid-4col">
              <div class="field-group">
                <label>Series</label>
                <input v-model="seriesName" placeholder="Series name" />
              </div>
              <div class="field-group">
                <label>Series No.</label>
                <input v-model="seriesNumber" placeholder="e.g. 2" />
              </div>
              <div class="field-group">
                <label>Volume</label>
                <input v-model="volumeNumber" placeholder="e.g. 1" />
              </div>
              <div class="field-group">
                <label>Related Work ID</label>
                <input v-model="relatedWorkId" placeholder="Work ID" />
              </div>
            </div>

            <div class="field-group" style="margin-top: 16px;">
              <label>Bibliographic Notes</label>
              <textarea v-model="form.notes" rows="3" placeholder="Curatorial or contextual notes..."></textarea>
            </div>
          </div>
        </section>

      </div>

      <!-- Right Column: Verification & Decision Sidebar -->
      <div class="sidebar-column">
        
        <!-- Section E: Evidence & Duplicates -->
        <section class="card">
          <div class="card-header">
            <h2>E. Evidence & Readiness</h2>
          </div>
          <div class="card-body">
            <div class="evidence-box" :class="{ 'warning-box': duplicateResult.severity !== 'none' }">
              <div class="evidence-title">
                <span>Duplicate Check</span>
                <strong>{{ duplicateLoading ? 'Scanning...' : duplicateResult.severity === 'none' ? 'Clear' : duplicateResult.severity.toUpperCase() + ' Match' }}</strong>
              </div>
              <p v-if="!duplicateLoading && duplicateResult.severity === 'none'" class="success-text">Catalogue appears clear for this new work.</p>
              <div v-if="!duplicateLoading && duplicateResult.severity !== 'none'">
                <p class="warning-text">Potential conflict detected with existing work(s).</p>
                <div class="conflict-matches">
                  <button
                    v-for="m in duplicateResult.matches"
                    :key="m.work_id"
                    type="button"
                    @click="confirmPrefill(m)"
                    class="match-btn"
                  >
                    <strong>Work #{{ m.work_id }}: {{ m.title }}</strong>
                    <span>{{ m.author }} · {{ m.language }}</span>
                  </button>
                </div>
                <label v-if="duplicateResult.severity === 'strong'" class="checkbox-label">
                  <input type="checkbox" v-model="adminOverride" />
                  <span>Chief Override: Authorize despite strong match</span>
                </label>
              </div>
            </div>

            <!-- Readiness Checklist -->
            <div class="readiness-container">
              <div class="readiness-header">
                <span>Record Readiness</span>
                <strong>{{ readinessPercent }}%</strong>
              </div>
              <div class="progress-bar-wrap">
                <div class="progress-fill" :style="{ width: `${readinessPercent}%` }"></div>
              </div>
              <div v-for="item in readinessItems" :key="item.key" class="readiness-item">
                <span class="status-icon" :class="{ 'checked': item.value }">{{ item.value ? '✓' : '—' }}</span>
                <div>
                  <strong>{{ item.key.replace('_',' ') }}</strong>
                  <small>{{ item.value ? 'Complete' : 'Needs attention' }}</small>
                </div>
              </div>
            </div>

            <div v-if="metadataConflicts.length" class="conflicts-register">
              <h4>Import vs Manual Conflicts</h4>
              <div v-for="conflict in metadataConflicts" :key="conflict.field" class="conflict-row">
                <strong>{{ conflict.label }}</strong>
                <span>Current: {{ conflict.current }}</span>
                <span>Incoming: {{ conflict.incoming }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Section F: Decision & Authorization -->
        <section class="card action-card">
          <div class="card-header">
            <h2>F. Registration Gate</h2>
          </div>
          <div class="card-body">
            <div class="record-summary-preview">
              <h3>{{ form.title || 'Untitled work' }}</h3>
              <p>{{ form.author || 'Unknown author' }} · {{ form.language_id || 'No language' }}</p>
            </div>

            <div class="gate-status" :class="{ 'gate-held': isFrozen }">
              <span>Status</span>
              <strong>{{ isFrozen ? 'HOLD — Decision Required' : 'Open — Ready to Register' }}</strong>
            </div>

            <button
              type="button"
              class="btn-primary"
              @click="triggerCreationPrompt"
              :disabled="loading || isFrozen"
            >
              {{ loading ? 'Registering...' : isFrozen ? 'Resolve Match First' : 'Authorize & Register' }}
            </button>

            <div class="sub-actions">
              <button type="button" class="btn-secondary" @click="savePartialDraft()" :disabled="loading || !hasDraftContent">
                Save Draft
              </button>
              <button type="button" class="btn-danger" @click="clearPartialDrafts" v-if="draftVersions.length">
                Discard Drafts
              </button>
            </div>
          </div>
        </section>

      </div>
    </main>

    <!-- Authorization Modal -->
    <div class="modal-backdrop" v-if="showPromptModal">
      <div class="modal-card">
        <button type="button" class="modal-close" @click="showPromptModal = false">×</button>
        <h2>Authorize & Register Work</h2>
        <p>This work will be committed as an approved catalogue record.</p>
        <div class="modal-item-preview">
          <span>WORK RECORD</span>
          <strong>{{ form.title || 'Untitled work' }}</strong>
          <small>{{ form.author || 'Unknown author' }} · {{ form.language_id || 'No language' }}</small>
        </div>
        <div class="field-group" style="margin-top: 14px;">
          <label>Authorization Reason <span class="required-note">(required for direct registration)</span></label>
          <input v-model="creationReason" placeholder="New registration basis..." />
        </div>
        <div class="modal-footer">
          <button type="button" class="btn-secondary" @click="showPromptModal = false">Cancel</button>
          <button type="button" class="btn-primary" @click="executeConfirmedCreation" :disabled="loading || !creationReason.trim()">Confirm & Register →</button>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <div v-if="result" class="toast-notification">
      <strong>{{ result.draft_saved ? 'Working Draft Saved' : result.work_id ? 'Work Successfully Registered' : 'Action Failed' }}</strong>
      <span>{{ result.draft_saved ? result.message : result.work_id ? `Work #${result.work_id} · Accession: ${result.accession_no}` : (result.detail || result.error || 'Server rejected transaction.') }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, onUnmounted } from "vue"
import { useCreateWork } from "./useCreateWork.js"

const titleLookupArea = ref(null)
const authorLookupArea = ref(null)
const authorInputAnchor = ref(null)
const authorInput = ref(null)
const authorDropdown = ref(null)
const authorDropdownStyle = ref({ position: "fixed", visibility: "hidden" })
const publisherLookupArea = ref(null)

const {
  pasteInput, isParsing, showAuthorSuggestions, showPublisherSuggestions,
  showPromptModal, creationReason, form, previewNumbers, result, loading,
  duplicateLoading, isbnLoading, metadataConflicts, draftSavedAt, draftVersions,
  hasUnsavedChanges, callNumberPreview, shelfSuggestion, applyGeneratedCallNumber,
  duplicateResult, adminOverride, extraLanguages, genreGroupA, genreGroupB,
  dynamicCommunityGenres, selectedGroupAGenre, selectedGroupBGenre, selectedGroupCGenre,
  showCustomManualGenreField, customManualGenreText, isFrozen, isIsbnValid,
  isIsbnChecksumValid, isIsbnReadyForCatalogue, isPasteIsbnReady, readinessItems,
  readinessPercent, hasDraftContent, isFieldImported, authorSuggestions,
  externalAuthorSuggestions, externalAuthorSearchLoading, externalAuthorSearchMessage,
  selectedAuthorityName, publisherSuggestions,
  titleLookupLoading, titleLookupResults, titleLookupMessage, searchTitleCandidates,
  selectTitleCandidate, clearTitleLookupResults,
  liveCompiledGenreChips, seriesName, seriesNumber, volumeNumber, relatedWorkId,
  savePartialDraft, clearPartialDrafts, selectAuthor, selectExternalAuthor,
  selectPublisher, handleBlurAction, sanitizeField, handleMetadataPaste,
  clearField, confirmPrefill, triggerCreationPrompt, executeConfirmedCreation,
  normalizeParserIsbn
} = useCreateWork()

function updateAuthorDropdownPosition() {
  const anchor = authorInputAnchor.value
  if (!anchor || typeof window === "undefined") return
  const rect = anchor.getBoundingClientRect()
  const edge = 8
  const gap = 6
  const width = Math.max(180, Math.min(rect.width, window.innerWidth - edge * 2))
  const left = Math.max(edge, Math.min(rect.left, window.innerWidth - width - edge))
  const preferredHeight = Math.min(360, Math.floor(window.innerHeight * 0.48))
  const below = Math.max(0, window.innerHeight - rect.bottom - gap - edge)
  const above = Math.max(0, rect.top - gap - edge)
  const openAbove = below < Math.min(preferredHeight, 220) && above > below
  const space = openAbove ? above : below
  const maxHeight = Math.max(110, Math.min(preferredHeight, space || preferredHeight))
  const preferredTop = openAbove ? rect.top - maxHeight - gap : rect.bottom + gap
  const top = Math.max(edge, Math.min(preferredTop, window.innerHeight - maxHeight - edge))
  authorDropdownStyle.value = {
    position: "fixed", left: `${left}px`, top: `${top}px`, width: `${width}px`,
    maxWidth: `calc(100vw - ${edge * 2}px)`, maxHeight: `${maxHeight}px`,
    right: "auto", visibility: "visible", zIndex: 99999
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

function closeSuggestionsOnOutsidePointer(event) {
  const target = event.target
  if (titleLookupArea.value && !titleLookupArea.value.contains(target)) clearTitleLookupResults(false)
  const insideAuthor = authorLookupArea.value?.contains(target) || authorDropdown.value?.contains(target)
  if (!insideAuthor) showAuthorSuggestions.value = false
  if (publisherLookupArea.value && !publisherLookupArea.value.contains(target)) showPublisherSuggestions.value = false
}

watch([authorSuggestions, externalAuthorSuggestions, showAuthorSuggestions, externalAuthorSearchLoading], async () => {
  await nextTick()
  updateAuthorDropdownPosition()
}, { deep: true })

onMounted(() => {
  document.addEventListener("pointerdown", closeSuggestionsOnOutsidePointer)
  window.addEventListener("resize", updateAuthorDropdownPosition)
  window.addEventListener("scroll", updateAuthorDropdownPosition, true)
})
onUnmounted(() => {
  document.removeEventListener("pointerdown", closeSuggestionsOnOutsidePointer)
  window.removeEventListener("resize", updateAuthorDropdownPosition)
  window.removeEventListener("scroll", updateAuthorDropdownPosition, true)
})
</script>

<style scoped>
/* Modern, clean, professional cataloguing interface */
* { box-sizing: border-box; }
body { margin: 0; background: #f8fafc; font-family: Inter, system-ui, -apple-system, sans-serif; color: #0f172a; }

.app-container { max-width: 1400px; margin: 0 auto; padding: 24px; min-height: 100vh; background: #f8fafc; }

.app-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand-logo { width: 44px; height: 44px; background: #1ea253; color: #0d0e0e; border-radius: 10px; display: grid; place-items: center; font-weight: 700; font-size: 16px; }
.brand h1 { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
.brand p { margin: 2px 0 0; font-size: 12px; color: #64748b; }

.badge { padding: 6px 12px; background: #dcfce7; color: #166534; font-size: 12px; font-weight: 600; border-radius: 99px; }
.badge-warning { background: #fee2e2; color: #991b1b; }
.badge-sub { font-size: 11px; color: #64748b; font-weight: 500; }

.workspace { display: grid; grid-template-columns: 1fr 380px; gap: 24px; }
.form-column { display: flex; flex-direction: column; gap: 20px; }
.sidebar-column { display: flex; flex-direction: column; gap: 20px; }

.card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); overflow: hidden; }
.card-header { padding: 16px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
.card-header h2 { margin: 0; font-size: 14px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; }
.card-body { padding: 20px; }

.intake-card { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; margin-bottom: 24px; background: #ffffff; }
.intake-label strong { display: block; font-size: 13px; color: #0f172a; }
.intake-label span { font-size: 11px; color: #64748b; }
.intake-input-group { display: flex; gap: 10px; width: 60%; }
.intake-input-group input { flex: 1; height: 38px; border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 12px; font-size: 13px; outline: none; }
.intake-input-group button { height: 38px; background: #2563eb; color: #fff; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; font-size: 12px; cursor: pointer; }
.intake-input-group button:hover { background: #1d4ed8; }

.field-group { display: flex; flex-direction: column; gap: 6px; position: relative; }
.field-group label { font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; }
.field-group input, .field-group select, .field-group textarea { width: 100%; height: 38px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; padding: 0 12px; font-size: 13px; color: #0f172a; outline: none; }
.field-group input:focus, .field-group select:focus, .field-group textarea:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
.field-group textarea { height: auto; padding: 10px 12px; resize: vertical; }
.field-group small { font-size: 11px; color: #16a34a; }

.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid-4col { display: grid; grid-template-columns: 1.5fr 0.8fr 0.8fr 1fr; gap: 12px; }

.primary-title-group input { font-size: 18px; font-weight: 600; height: 44px; }

.suggestion-container { position: relative; }
.input-with-lock { position: relative; }
.lock-badge { position: absolute; right: 10px; top: 10px; font-size: 11px; color: #16a34a; font-weight: 600; }
.suggestions-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 4px; z-index: 50; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); max-height: 200px; overflow-y: auto; }
.suggestion-header { padding: 8px 12px; font-size: 10px; font-weight: 700; color: #64748b; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; }
.suggestion-row { padding: 10px 12px; display: flex; justify-content: space-between; cursor: pointer; border-bottom: 1px solid #f1f5f9; font-size: 12px; }
.suggestion-row:hover { background: #f8fafc; }
.suggestion-row .sub-text { color: #64748b; }

.stat-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; flex-direction: column; justify-content: center; }
.stat-box span { font-size: 10px; font-weight: 600; color: #64748b; text-transform: uppercase; }
.stat-box strong { font-size: 15px; color: #0f172a; margin-top: 4px; }

.inline-action-input { display: flex; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; height: 38px; }
.inline-action-input input { border: none; flex: 1; height: 100%; padding: 0 12px; outline: none; }
.inline-action-input button { border: none; background: #f1f5f9; border-left: 1px solid #cbd5e1; padding: 0 12px; font-size: 11px; font-weight: 700; color: #2563eb; cursor: pointer; }
.inline-action-input button:hover { background: #e2e8f0; }

.preview-banner { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-top: 16px; font-size: 12px; }
.preview-banner span { color: #64748b; }
.preview-banner strong { color: #0f172a; display: block; margin-top: 2px; }

.genre-section { margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 16px; }
.genre-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.custom-input { margin-top: 10px; }
.genre-chips-container { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.chip { padding: 4px 10px; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 99px; font-size: 11px; font-weight: 500; }
.empty-text { font-size: 12px; color: #94a3b8; }

.evidence-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 16px; }
.warning-box { background: #fff5f5; border-color: #fecaca; }
.evidence-title { display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-bottom: 8px; }
.evidence-title span { color: #64748b; font-weight: 600; }
.evidence-title strong { color: #16a34a; }
.warning-box .evidence-title strong { color: #dc2626; }
.success-text { font-size: 12px; color: #16a34a; margin: 0; }
.warning-text { font-size: 12px; color: #991b1b; margin: 0 0 8px 0; }
.conflict-matches { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.match-btn { display: flex; flex-direction: column; text-align: left; padding: 8px 10px; background: #fff; border: 1px solid #fecaca; border-radius: 6px; cursor: pointer; }
.match-btn:hover { background: #fff1f2; }
.match-btn strong { font-size: 12px; color: #991b1b; }
.match-btn span { font-size: 11px; color: #7f1d1d; }
.checkbox-label { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 11px; color: #7f1d1d; font-weight: 600; cursor: pointer; }

.readiness-container { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; }
.readiness-header { display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 8px; }
.progress-bar-wrap { height: 6px; background: #e2e8f0; border-radius: 99px; overflow: hidden; margin-bottom: 12px; }
.progress-fill { height: 100%; background: #16a34a; border-radius: 99px; }
.readiness-item { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid #e2e8f0; }
.readiness-item:last-child { border-bottom: none; }
.status-icon { width: 20px; height: 20px; border-radius: 4px; background: #e2e8f0; color: #64748b; display: grid; place-items: center; font-size: 11px; font-weight: 700; }
.status-icon.checked { background: #dcfce7; color: #166534; }
.readiness-item strong { display: block; font-size: 11px; text-transform: uppercase; color: #334155; }
.readiness-item small { display: block; font-size: 10px; color: #64748b; }

.conflicts-register { margin-top: 14px; border-top: 1px solid #e2e8f0; padding-top: 10px; }
.conflicts-register h4 { margin: 0 0 6px 0; font-size: 11px; color: #334155; text-transform: uppercase; }
.conflict-row { display: flex; flex-direction: column; gap: 2px; font-size: 11px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; }
.conflict-row strong { color: #0f172a; }
.conflict-row span { color: #64748b; }

.action-card .card-body { display: flex; flex-direction: column; gap: 14px; }
.record-summary-preview h3 { margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #0f172a; }
.record-summary-preview p { margin: 0; font-size: 12px; color: #64748b; }

.gate-status { padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
.gate-status span { display: block; font-size: 10px; font-weight: 600; color: #64748b; text-transform: uppercase; }
.gate-status strong { display: block; font-size: 12px; color: #166534; margin-top: 2px; }
.gate-held strong { color: #991b1b; }

.btn-primary { width: 100%; height: 42px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.sub-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.btn-secondary { height: 38px; background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }
.btn-secondary:hover { background: #e2e8f0; }
.btn-danger { height: 38px; background: #fff5f5; color: #dc2626; border: 1px solid #fecaca; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }
.btn-danger:hover { background: #fee2e2; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.6); display: grid; place-items: center; z-index: 100; padding: 20px; }
.modal-card { width: min(480px, 100%); background: #fff; border-radius: 12px; padding: 24px; position: relative; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-close { position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 20px; color: #64748b; cursor: pointer; }
.modal-card h2 { margin: 0 0 8px 0; font-size: 18px; color: #0f172a; }
.modal-card p { margin: 0 0 16px 0; font-size: 13px; color: #64748b; }
.modal-item-preview { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
.modal-item-preview span { display: block; font-size: 10px; font-weight: 600; color: #64748b; }
.modal-item-preview strong { display: block; font-size: 15px; color: #0f172a; margin-top: 2px; }
.modal-item-preview small { display: block; font-size: 11px; color: #64748b; margin-top: 2px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.toast-notification { position: fixed; right: 24px; bottom: 24px; width: min(360px, calc(100vw - 48px)); background: #0f172a; color: #fff; border-radius: 10px; padding: 16px; z-index: 110; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2); }
.toast-notification strong { display: block; font-size: 13px; color: #4ade80; }
.toast-notification span { display: block; font-size: 12px; color: #94a3b8; margin-top: 4px; }


/* Title candidates are inline so they cannot be clipped by card overflow. */
.title-input-wrapper { display: flex; align-items: stretch; width: 100%; min-width: 0; }
.title-input-wrapper input { flex: 1; min-width: 0; }
.field-clear-btn { flex: 0 0 auto; border: 1px solid #cbd5e1; border-left: 0; border-radius: 0 8px 8px 0; padding: 0 10px; background: #f8fafc; color: #475569; font-size: 11px; cursor: pointer; }
.title-input-wrapper input:has(+ .field-clear-btn) { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.input-with-lock input { padding-right: 112px; }
.author-clear-btn { position: absolute; right: 48px; top: 6px; min-height: 26px; border: 0; border-radius: 5px; margin: 0; padding: 0 6px; }
.lookup-help { display: block; color: #64748b; font-size: 11px; line-height: 1.4; }
.lookup-message { margin: 2px 0 0; padding: 8px 10px; border: 1px solid #dbeafe; border-radius: 7px; background: #eff6ff; color: #1e40af; font-size: 11px; line-height: 1.4; }
.title-candidate-list { display: grid; gap: 7px; margin-top: 8px; }
.title-candidate-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border: 1px solid #dbe4ee; border-radius: 8px; background: #fbfdff; }
.title-candidate-copy { display: grid; gap: 3px; min-width: 0; }
.title-candidate-copy strong { color: #0f172a; font-size: 13px; overflow-wrap: anywhere; }
.title-candidate-copy small { color: #64748b; font-size: 11px; line-height: 1.35; }
.title-use-btn { flex: 0 0 auto; min-height: 32px; border: 1px solid #bbf7d0; border-radius: 7px; padding: 0 11px; background: #f0fdf4; color: #166534; font-size: 11px; font-weight: 700; cursor: pointer; }
.author-suggestions-dropdown { box-sizing: border-box; overflow-y: auto; overscroll-behavior: contain; padding: 0; background: #fff; border: 1px solid #cbd5e1; border-radius: 10px; box-shadow: 0 14px 32px rgba(15, 23, 42, .22); color: #0f172a; }
.author-suggestions-dropdown .suggestion-header { position: sticky; top: 0; z-index: 1; padding: 9px 12px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; color: #475569; font-size: 10px; font-weight: 800; letter-spacing: .05em; }
.author-suggestions-dropdown .external-suggestion-header { top: 0; background: #ecfdf5; color: #166534; }
.author-suggestion-button { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; width: 100%; padding: 10px 12px; border: 0; border-bottom: 1px solid #eef2f7; background: #fff; text-align: left; cursor: pointer; white-space: normal; }
.author-suggestion-button:hover, .author-suggestion-button:focus-visible { background: #f8fafc; outline: 2px solid #93c5fd; outline-offset: -2px; }
.suggestion-main { display: block; max-width: 100%; color: #0f172a; font-size: 13px; font-weight: 700; overflow-wrap: anywhere; }
.suggestion-meta, .suggestion-detail { display: block; color: #64748b; font-size: 11px; line-height: 1.35; overflow-wrap: anywhere; }
.external-author-button .suggestion-main { color: #166534; }
.suggestion-empty { padding: 10px 12px; color: #64748b; background: #fff; font-size: 11px; line-height: 1.45; overflow-wrap: anywhere; }
@media (max-width: 640px) { .title-candidate-row { align-items: flex-start; flex-direction: column; } .title-use-btn { align-self: flex-start; } }

</style>
