<template>
  <div class="modern-catalog-container">
    <div class="catalog-shell">
      
      <!-- Header Toolbar -->
      <header class="catalog-header">
        <div class="brand-group">
          <div class="brand-icon">AO</div>
          <div>
            <span class="sub-eyebrow">ATHENAEUM CATALOGUE</span>
            <h1>New Work Record</h1>
          </div>
        </div>

        <div class="status-indicator-group">
          <div class="status-badge" :class="{ 'has-changes': hasUnsavedChanges }">
            <span class="pulse-dot"></span>
            {{ hasUnsavedChanges ? 'Unsaved changes' : (draftSavedAt ? 'Draft saved' : 'Ready to catalogue') }}
          </div>
          <div class="progress-pill">
            <strong>{{ readinessPercent }}%</strong>
            <span>complete</span>
          </div>
        </div>
      </header>

      <!-- Compact notice: shown only when at least one meaningful draft exists. -->
      <section v-if="draftOfferVisible && draftVersions.length" class="saved-draft-banner" role="status" aria-live="polite">
        <div class="saved-draft-main">
          <div class="saved-draft-copy">
            <span class="saved-draft-kicker">SAVED DRAFTS · {{ draftVersions.length }}</span>
            <strong class="saved-draft-summary-title">A saved work is available</strong>
            <small v-if="draftVersions[0]?.saved_at">
              Latest: {{ formatDraftSavedAt(draftVersions[0].saved_at) }}
              <span v-if="draftVersions[0]?.mode"> · {{ draftVersions[0].mode === 'auto' ? 'Auto-saved' : 'Manual save' }}</span>
            </small>
          </div>
          <div class="saved-draft-actions">
            <button type="button" class="btn-primary saved-draft-open-btn" @click="restoreDraftVersion(draftVersions[0])">Restore latest</button>
            <button
              v-if="draftVersions.length > 1"
              type="button"
              class="btn-secondary saved-draft-history-btn"
              @click="showSavedDraftVersions = !showSavedDraftVersions"
            >{{ showSavedDraftVersions ? 'Hide older versions' : `Older versions (${draftVersions.length - 1})` }}</button>
            <button type="button" class="btn-secondary saved-draft-remove-btn" @click="clearPartialDrafts">Remove saved</button>
          </div>
        </div>
        <div v-if="showSavedDraftVersions && draftVersions.length > 1" class="saved-draft-version-list">
          <div v-for="(draft, index) in draftVersions.slice(1)" :key="draft.saved_at || index" class="saved-draft-version-row">
            <div class="saved-draft-version-copy">
              <strong>Saved version {{ index + 2 }}</strong>
              <small>{{ formatDraftSavedAt(draft.saved_at) }}<span v-if="draft.mode"> · {{ draft.mode === 'auto' ? 'Auto-saved' : 'Manual save' }}</span></small>
            </div>
            <button type="button" class="btn-secondary saved-draft-open-btn" @click="restoreDraftVersion(draft)">Restore this version</button>
          </div>
        </div>
      </section>

      <!-- Main Layout -->
      <div class="catalog-layout">
        
        <!-- Sidebar Navigation -->
        <aside class="catalog-sidebar">
          <div class="sidebar-title">WORKFLOW STEPS</div>
          <nav class="nav-steps">
            <a href="#identity" class="nav-item active" @click.prevent="scrollToSection('identity')">
              <span class="step-num">01</span>
              <div>
                <strong>Identity</strong>
                <small>Title, author, publisher</small>
              </div>
            </a>
            <a href="#publication" class="nav-item" @click.prevent="scrollToSection('publication')">
              <span class="step-num">02</span>
              <div>
                <strong>Publication</strong>
                <small>Language, year, ISBN</small>
              </div>
            </a>
            <a href="#classification" class="nav-item" @click.prevent="scrollToSection('classification')">
              <span class="step-num">03</span>
              <div>
                <strong>Classification</strong>
                <small>DDC, call no., shelf</small>
              </div>
            </a>
            <a href="#context" class="nav-item" @click.prevent="scrollToSection('context')">
              <span class="step-num">04</span>
              <div>
                <strong>Context</strong>
                <small>Series & description</small>
              </div>
            </a>
            <a href="#verification" class="nav-item" @click.prevent="scrollToSection('verification')">
              <span class="step-num">05</span>
              <div>
                <strong>Verification</strong>
                <small>Duplicate & readiness</small>
              </div>
            </a>
          </nav>

          <div class="sidebar-card">
            <span class="card-tag">KEEPER MODE</span>
            <h4>Careful cataloging</h4>
            <p>Manual entries are preserved while lookup metadata assists your workflow.</p>
          </div>
        </aside>

        <!-- Main Form Area -->
        <main class="catalog-main-content">
          
          <!-- Fast Capture Strip -->
          <section class="fast-capture-card">
            <div class="capture-info">
              <span class="card-tag">FAST CAPTURE</span>
              <h3>Optional ISBN lookup</h3>
              <p>Click LOOK UP &amp; IMPORT only when you want to fetch metadata. Typing in the form below never runs an ISBN lookup.</p>
            </div>
            <div class="capture-action">
              <input autocomplete="new-password" 
                id="parser-field-input" 
                v-model="pasteInput" 
                @input="normalizeParserIsbn" 
                placeholder="ISBN-10 / ISBN-13 / barcode" 
              />
              <button type="button" @click="handleMetadataPaste(null)" :disabled="isParsing || !isPasteIsbnReady">
                {{ isParsing ? 'LOOKING UP…' : 'LOOK UP & IMPORT' }}
              </button>
            </div>
          </section>

          <!-- Section 01: Identity -->
          <section id="identity" class="form-section">
            <div class="section-badge">01</div>
            <div class="section-body">
              <div class="section-header-row">
                <div>
                  <span class="card-tag">START HERE</span>
                  <h2>Work identity</h2>
                  <p>Establish the foundational bibliographic identity before cataloging details.</p>
                </div>
                <div class="check-counter">{{ readinessCount }}/{{ readinessTotal }} key checks</div>
              </div>

              <div class="form-grid">
                <div class="input-group full-width title-lookup-group" ref="titleLookupArea">
                  <div class="title-label-row">
                    <label for="title-input-field">Title <span class="required">*</span></label>
                    <span class="title-lookup-status" aria-live="polite">{{ titleLookupLoading ? 'SEARCHING…' : '' }}</span>
                  </div>
                  <div class="input-wrapper" :class="{ 'is-imported': isFieldImported('title') }">
                    <input id="title-input-field" v-model="form.title" autocomplete="new-password" autocapitalize="off" spellcheck="false" @input="clearTitleLookupResults" @blur="sanitizeField('title')" maxlength="255" placeholder="Enter formal title" />
                    <button v-if="form.title" type="button" @mousedown.prevent @click="clearField('title'); clearTitleLookupResults()" class="clear-btn">Clear</button>
                  </div>
                  <small v-if="isFieldImported('title')" class="imported-note">Imported from ISBN lookup</small>
                  <small class="title-lookup-note">Suggestions search automatically as you type. The title changes only after you choose a candidate.</small>
                  <p v-if="titleLookupMessage" class="title-lookup-message" aria-live="polite">{{ titleLookupMessage }}</p>
                  <div v-if="titleLookupResults.length" class="title-candidate-list">
                    <div v-for="(candidate, index) in titleLookupResults" :key="`${candidate.source}-${candidate.external_id || index}-${candidate.title}`" class="title-candidate-row">
                      <div class="title-candidate-copy">
                        <strong>{{ candidate.title }}</strong>
                        <small>{{ [candidate.author, candidate.year, candidate.source].filter(Boolean).join(' · ') }}</small>
                        <small v-if="Number.isFinite(Number(candidate.match_score))">Approximate title match: {{ candidate.match_score }}%</small>
                      </div>
                      <button type="button" class="btn-secondary title-candidate-use" @click="selectTitleCandidate(candidate)">Use title</button>
                    </div>
                  </div>
                </div>

                <div
                  ref="authorLookupArea"
                  class="input-group span-two author-lookup-group"
                  :class="{ 'has-open-suggestions': showAuthorSuggestions && (authorSuggestions.length || externalAuthorSuggestions.length || form.author.trim().length >= 2) }"
                >
                  <label>Primary author / authority</label>
                  <div ref="authorInputAnchor" class="input-wrapper author-input-wrapper" :class="{ 'is-imported': isFieldImported('author') }">
                    <input
                      v-model="form.author"
                      ref="authorInput"
                      autocomplete="new-password"
                      autocapitalize="off"
                      spellcheck="false"
                      aria-label="Primary author or authority"
                      aria-autocomplete="list"
                      aria-controls="author-suggestion-list"
                      :aria-expanded="showAuthorSuggestions && (authorSuggestions.length || externalAuthorSuggestions.length || form.author.trim().length >= 2)"
                      @focus="openAuthorSuggestions"
                      @blur="handleAuthorBlur"
                      maxlength="150"
                      placeholder="Search or enter author"
                    />
                    <button v-if="form.author" type="button" @mousedown.prevent @click="clearField('author')" class="clear-btn">Clear</button>
                  </div>

                  <!-- Teleport the menu to body so parent grid/card stacking and overflow cannot clip it. -->
                  <Teleport to="body">
                    <div
                      v-if="showAuthorSuggestions && (authorSuggestions.length || externalAuthorSuggestions.length || form.author.trim().length >= 2)"
                      ref="authorDropdown"
                      id="author-suggestion-list"
                      class="suggestions-dropdown author-suggestions-dropdown"
                      :style="authorDropdownStyle"
                      role="listbox"
                      aria-label="Author suggestions"
                      @pointerdown.stop
                    >
                      <div class="suggestions-header">LOCAL ATHENAEUM AUTHORITY RECORDS</div>
                      <button
                        v-for="author in authorSuggestions"
                        :key="author.authority_id"
                        type="button"
                        class="suggestion-row local-author-suggestion"
                        @mousedown.prevent
                        @click="selectAuthor(author)"
                      >
                        <span class="suggestion-primary-name">{{ author.preferred_name }}</span>
                        <small class="suggestion-status">{{ author.status }}</small>
                      </button>
                      <div v-if="!authorSuggestions.length" class="suggestion-empty local-empty">No matching local authority record. Open Library candidates, if available, appear in the separate section below.</div>

                      <template v-if="externalAuthorSuggestions.length">
                        <div class="suggestions-header external-results-header">EXTERNAL CANDIDATES · OPEN LIBRARY</div>
                        <button
                          v-for="author in externalAuthorSuggestions"
                          :key="author.external_id || author.preferred_name"
                          type="button"
                          class="suggestion-row external-author-suggestion"
                          @mousedown.prevent
                          @click="selectExternalAuthor(author)"
                        >
                          <span class="external-author-main-line">
                            <span class="suggestion-primary-name">{{ author.canonical_name || author.preferred_name }}</span>
                            <small class="suggestion-status">{{ author.source || 'Open Library' }}<span v-if="author.correction_match"> · spelling correction candidate</span></small>
                          </span>
                          <small v-if="author.top_work" class="suggestion-detail">Top work: {{ author.top_work }}</small>
                          <small v-if="author.birth_date || author.death_date" class="suggestion-detail">Life dates: {{ [author.birth_date, author.death_date].filter(Boolean).join(' – ') }}</small>
                        </button>
                      </template>

                      <div v-if="externalAuthorSearchMessage" class="suggestion-empty" role="status" aria-live="polite">{{ externalAuthorSearchMessage }}</div>
                      <div v-if="externalAuthorSearchLoading" class="suggestion-empty" role="status">Searching Open Library after local authority search…</div>
                    </div>
                  </Teleport>
                </div>

                <div class="input-group" ref="publisherLookupArea">
                  <label>Publisher</label>
                  <div class="input-wrapper" :class="{ 'is-imported': isFieldImported('publisher') }">
                    <input autocomplete="new-password" v-model="form.publisher" @focus="showPublisherSuggestions = true" @blur="handleBlurAction('publisher')" placeholder="Publisher / imprint" />
                    <button v-if="form.publisher" type="button" @click="clearField('publisher')" class="clear-btn">Clear</button>
                    
                    <div v-if="showPublisherSuggestions && publisherSuggestions.length" class="suggestions-dropdown">
                      <div class="suggestions-header">PUBLISHER SUGGESTIONS</div>
                      <div v-for="pub in publisherSuggestions" :key="pub" @mousedown="selectPublisher(pub)" class="suggestion-row">
                        <span>{{ pub }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="input-group">
                  <label>Language <span class="required">*</span></label>
                  <select :value="isOtherChoice('language_id', form.language_id, [...BASE_LANGS, ...extraLanguages]) ? '__other__' : form.language_id" @change="onPick('language_id', $event.target.value); form.language_id = $event.target.value === '__other__' ? '' : $event.target.value" class="select-field">
                    <option disabled value="">Select language</option>
                    <option v-for="lang in [...BASE_LANGS, ...extraLanguages]" :key="lang" :value="lang">{{ lang === 'Multi -Lingual' ? 'Multilingual' : lang }}</option>
                    <option value="__other__">Other (type new)...</option>
                  </select>
                  <input v-if="isOtherChoice('language_id', form.language_id, [...BASE_LANGS, ...extraLanguages])" v-model="form.language_id" @blur="form.language_id = matchLang(form.language_id, [...BASE_LANGS, ...extraLanguages])" autocomplete="off" placeholder="Type language" class="select-field" style="margin-top:8px" />
                  <small v-if="isOtherChoice('language_id', form.language_id, [...BASE_LANGS, ...extraLanguages]) && form.language_id && ![...BASE_LANGS, ...extraLanguages].includes(matchLang(form.language_id, [...BASE_LANGS, ...extraLanguages]))">New language will be added to the registry.</small>
                </div>

                <div class="input-group">
                  <label>Category</label>
                  <select v-model="form.category" class="select-field">
                    <option value="">No category</option>
                    <option value="Fiction">Fiction</option>
                    <option value="Non-Fiction">Non-Fiction</option>
                    <option value="Reference">Reference</option>
                    <option value="Religious">Religious</option>
                    <option value="Poetry">Poetry</option>
                  </select>
                </div>

                <div class="input-group">
                  <label>Publication year</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" id="year-input-field" v-model="form.year" placeholder="YYYY" maxlength="4" />
                    <span v-if="isYearValid === true" class="valid-mark">✓</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- Section 02: Publication -->
          <section id="publication" class="form-section">
            <div class="section-badge">02</div>
            <div class="section-body">
              <div class="section-header-row">
                <div>
                  <span class="card-tag">IDENTIFIERS</span>
                  <h2>Publication details</h2>
                  <p>Capture publication numbers and track record provenance.</p>
                </div>
              </div>

              <div class="pub-grid">
                <div class="pub-card">
                  <label>ISBN</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" id="isbn-input-field" v-model="form.isbn" placeholder="ISBN-10 or ISBN-13" />
                    <button v-if="form.isbn" type="button" @click="clearField('isbn')" class="clear-btn">Clear</button>
                  </div>
                  <div class="isbn-feedback" :class="{ 'success': isIsbnReadyForCatalogue, 'error': isIsbnValid === true && isIsbnChecksumValid === false }">
                    <span>{{ isbnLoading ? 'Checking metadata…' : isIsbnReadyForCatalogue ? 'Checksum valid · no lookup run from this field' : (isIsbnValid === true ? 'Checksum needs attention' : 'Format checked as you type') }}</span>
                  </div>
                  <small class="manual-isbn-note">Manual entry only. To fetch metadata, use the optional ISBN lookup above.</small>
                </div>

                <div class="system-metrics-grid" aria-label="System-generated identifiers">
                  <div class="system-metric-card compact-system-metric-card">
                    <span>Serial no.</span>
                    <strong>{{ previewNumbers.serial_no === '[Auto-Generated by System]' ? 'Auto-generated' : previewNumbers.serial_no }}</strong>
                    <small>Assigned on save.</small>
                  </div>
                  <div class="system-metric-card compact-system-metric-card">
                    <span>Accession no.</span>
                    <strong>{{ previewNumbers.accession_no === '[Select Language First]' ? 'Select language' : previewNumbers.accession_no }}</strong>
                    <small>Preview after language selection.</small>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- Section 03: Classification -->
          <section id="classification" class="form-section">
            <div class="section-badge">03</div>
            <div class="section-body">
              <div class="section-header-row">
                <div>
                  <span class="card-tag">DISCOVERY & LOCATION</span>
                  <h2>Classification</h2>
                  <p>Ensure works are findable and physically locatable on shelves.</p>
                </div>
              </div>

              <div class="form-grid">
                <div class="input-group">
                  <label>DDC <i>{{ fieldHints.ddc }}</i></label>
                  <div class="input-wrapper"><input autocomplete="new-password" id="ddc-input-field" v-model="form.ddc" placeholder="823.9" /></div>
                </div>
                <div class="input-group">
                  <label>Call number <i>{{ fieldHints.call_no }}</i></label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.call_no" placeholder="Library call number" />
                    <button type="button" @click="applyGeneratedCallNumber" class="text-action-btn">Use suggestion</button>
                  </div>
                </div>
                <div class="input-group">
                  <label>Shelf <i>{{ fieldHints.shelf }}</i></label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.shelf" placeholder="Shelf location" /></div>
                </div>
              </div>

              <div class="smart-suggestions-box">
                <div>
                  <span>SUGGESTED CALL NUMBER</span>
                  <strong>{{ callNumberPreview || 'Complete language / author / year' }}</strong>
                </div>
                <div>
                  <span>SHELF SMART-SUGGEST</span>
                  <strong>{{ shelfSuggestion || 'Enter DDC or category' }}</strong>
                </div>
              </div>

              <div class="genre-builder-box">
                <div class="builder-title-row">
                  <div><span class="card-tag">GENRE</span><strong>Build catalogue genre signals</strong></div>
                  <small>{{ liveCompiledGenreChips.length }} selected</small>
                </div>
                <div class="genre-select-grid">
                  <select v-model="selectedGroupAGenre" @change="syncGenreSelection" class="select-field">
                    <option value="">Creative genre</option>
                    <option v-for="g in genreGroupA" :key="g" :value="g">{{ g }}</option>
                  </select>
                  <select v-model="selectedGroupBGenre" @change="syncGenreSelection" class="select-field">
                    <option value="">Factual genre</option>
                    <option v-for="g in genreGroupB" :key="g" :value="g">{{ g }}</option>
                  </select>
                  <select v-model="selectedGroupCGenre" @change="syncGenreSelection" class="select-field">
                    <option value="">Community genre</option>
                    <option v-for="g in dynamicCommunityGenres" :key="g" :value="g">{{ g }}</option>
                    <option value="CUSTOM_MANUAL_OVERRIDE">Other (type new)...</option>
                  </select>
                </div>
                <input autocomplete="new-password" v-if="showCustomManualGenreField" v-model="customManualGenreText" @input="syncManualGenreInput" placeholder="Custom genres separated by /" class="custom-genre-input" />
                <div class="genre-chips-container">
                  <span v-for="chip in liveCompiledGenreChips" :key="chip" class="genre-chip">{{ chip }}</span>
                  <small v-if="!liveCompiledGenreChips.length">No genre signals yet.</small>
                </div>
              </div>
            </div>
          </section>

          <!-- Section 04: Context -->
          <section id="context" class="form-section">
            <div class="section-badge">04</div>
            <div class="section-body">
              <div class="section-header-row">
                <div>
                  <span class="card-tag">BIBLIOGRAPHIC CONTEXT</span>
                  <h2>Series & description</h2>
                  <p>Record translation context, series relationships, and reviewer notes.</p>
                </div>
              </div>

              <div class="form-grid">
                <div class="input-group">
                  <label>Original language</label>
                  <select :value="isOtherChoice('original_language', form.original_language, [...BASE_LANGS, ...extraLanguages]) ? '__other__' : form.original_language" @change="onPick('original_language', $event.target.value); form.original_language = $event.target.value === '__other__' ? '' : $event.target.value" class="select-field">
                    <option value="" disabled>Select original language</option>
                    <option v-for="lang in [...BASE_LANGS, ...extraLanguages]" :key="lang" :value="lang">{{ lang === 'Multi -Lingual' ? 'Multilingual' : lang }}</option>
                    <option value="__other__">Other (type new)...</option>
                  </select>
                  <input v-if="isOtherChoice('original_language', form.original_language, [...BASE_LANGS, ...extraLanguages])" v-model="form.original_language" @blur="form.original_language = matchLang(form.original_language, [...BASE_LANGS, ...extraLanguages])" autocomplete="off" placeholder="Type original language" class="select-field" style="margin-top:8px" />
                </div>
                <div class="input-group">
                  <label>Translation / compilation</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.translation_compilation" placeholder="Translator or compiler" /></div>
                </div>
                <div class="input-group">
                  <label>Series name</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="seriesName" placeholder="Series / collection name" /></div>
                </div>
                <div class="input-group">
                  <label>Series number</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="seriesNumber" placeholder="e.g. 2" /></div>
                </div>
                <div class="input-group">
                  <label>Volume number</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="volumeNumber" inputmode="numeric" placeholder="e.g. 2" /></div>
                </div>
                <div class="input-group">
                  <label>Related Work ID</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="relatedWorkId" inputmode="numeric" placeholder="Optional existing Work ID" /></div>
                </div>
                <div class="input-group full-width">
                  <label>Bibliographic notes</label>
                  <textarea autocomplete="off" v-model="form.notes" rows="4" placeholder="Anything the next reviewer should know about this record" class="textarea-field"></textarea>
                </div>
              </div>
            </div>
          </section>

          <!-- Section 05: Verification -->
          <section id="verification" class="form-section">
            <div class="section-badge">05</div>
            <div class="section-body">
              <div class="section-header-row">
                <div>
                  <span class="card-tag">BEFORE SUBMISSION</span>
                  <h2>Verification desk</h2>
                  <p>Resolve duplicate matches and make the record ready for review.</p>
                </div>
              </div>

              <div class="verification-grid">
                <div class="verify-card">
                  <div class="card-inner-title">
                    <div><span class="card-tag">CATALOGUE MATCH</span><strong>Duplicate check</strong></div>
                    <span v-if="duplicateLoading" class="sub-status">Checking…</span>
                  </div>

                  <div v-if="!duplicateLoading && duplicateResult.severity === 'none'" class="alert-box success-alert">
                    <strong>No matching work found</strong>
                    <span>The current title, author, language, and ISBN combination is clear.</span>
                  </div>

                  <div v-if="!duplicateLoading && duplicateResult.severity !== 'none'" class="alert-box warning-alert">
                    <strong>{{ duplicateResult.severity === 'strong' ? 'Strong catalogue match' : 'Possible match' }}</strong>
                    <span>Open a match before you submit a new Work.</span>
                    <button v-for="m in duplicateResult.matches" :key="m.work_id" type="button" class="match-result-btn" @click="confirmPrefill(m)">
                      <span>{{ m.title }}</span><small>Work #{{ m.work_id }} · {{ m.author }} · {{ m.language }}</small>
                    </button>
                    <label v-if="duplicateResult.severity === 'strong'" class="checkbox-label">
                      <input autocomplete="new-password" type="checkbox" v-model="adminOverride" />
                      <span>Override warning and continue with a new Work.</span>
                    </label>
                  </div>
                </div>

                <div class="verify-card">
                  <div class="card-inner-title">
                    <div><span class="card-tag">RECORD READINESS</span><strong>Key fields</strong></div>
                    <strong class="percent-highlight">{{ readinessPercent }}%</strong>
                  </div>
                  <div class="readiness-grid">
                    <div v-for="item in readinessItems" :key="item.key" class="readiness-row">
                      <span class="check-box" :class="{ 'completed': item.value }">{{ item.value ? '✓' : '○' }}</span>
                      <small>{{ item.key.replace('_',' ').replace(/^\w/, m => m.toUpperCase()) }}</small>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="metadataConflicts.length" class="conflicts-panel">
                <div class="card-inner-title"><div><span class="card-tag">METADATA CONFLICTS</span><strong>Manual values need attention</strong></div></div>
                <div v-for="conflict in metadataConflicts" :key="conflict.field" class="conflict-item">
                  <strong>{{ conflict.label }}</strong>
                  <span>Current: {{ conflict.current }}</span>
                  <span>Incoming: {{ conflict.incoming }}</span>
                </div>
              </div>
            </div>
          </section>

          <!-- Footer Actions -->
          <footer class="catalog-footer">
            <div class="footer-copy">
              <strong>{{ hasUnsavedChanges ? 'Unsaved changes' : 'Record state saved' }}</strong>
              <span>New Keeper Works are submitted as pending records for Chief review.</span>
            </div>
            <div class="footer-buttons">
              <button type="button" class="btn-secondary" @click="savePartialDraft()" :disabled="loading || !hasDraftContent">Save draft</button>
              <button type="button" class="btn-primary" @click="triggerCreationPrompt" :disabled="loading || isFrozen">
                {{ loading ? 'Creating…' : 'Submit for Chief review' }} <span>→</span>
              </button>
            </div>
          </footer>

        </main>
      </div>

      <!-- Submission Modal -->
      <div class="modal-backdrop" v-if="showPromptModal">
        <div class="modal-card">
          <span class="card-tag">KEEPER SUBMISSION</span>
          <button type="button" class="close-modal-btn" @click="showPromptModal = false">×</button>
          <h2>Submit this work for Chief review?</h2>
          <p>The new Work will be created as pending and will await formal verification.</p>
          <div class="modal-preview-box">
            <strong>{{ form.title || 'Untitled work' }}</strong>
            <span>{{ form.author || 'Unknown author' }} · {{ form.language_id || 'No language' }}</span>
          </div>
          <label class="modal-label">Reason for action
            <input autocomplete="new-password" v-model="creationReason" placeholder="New registration / source note" class="modal-input" />
          </label>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showPromptModal = false">Cancel</button>
            <button type="button" class="btn-primary" @click="executeConfirmedCreation">Submit for review →</button>
          </div>
        </div>
      </div>

      <!-- Toast Popup -->
      <div v-if="result" class="toast-popup" :class="{ 'toast-error': !result.draft_saved && !result.work_id }" role="status" aria-live="polite">
        <button type="button" aria-label="Dismiss" style="float:right;background:none;border:0;color:#94a3b8;font-size:18px;cursor:pointer" @click="result = null">&times;</button>
        <strong>{{ result.title ? result.title : result.draft_saved ? 'Draft saved' : result.work_id ? 'Work submitted' : 'Action failed' }}</strong>
        <span>{{ result.draft_saved ? result.message : result.work_id ? `Work #${result.work_id} · ${result.accession_no}` : (result.detail || result.error || 'The server rejected the transaction.') }}</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue"
import { useCreateWork } from "./useCreateWork.js"

const showSavedDraftVersions = ref(false)
const BASE_LANGS = ['Malayalam', 'English', 'Multi -Lingual']
const otherChoice = ref({})
function onPick(key, val) { otherChoice.value = { ...otherChoice.value, [key]: val === '__other__' } }
function isOtherChoice(key, current, list) { return !!otherChoice.value[key] || (!!current && !list.includes(current)) }
function matchLang(text, list) {
  const norm = (x) => String(x || '').toLowerCase().replace(/[\s-]/g, '')
  const clean = String(text || '').trim().replace(/\s+/g, ' ')
  return list.find((x) => norm(x) === norm(clean)) || clean
}
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
  duplicateLoading, isbnLoading, metadataConflicts, draftSavedAt, draftVersions, draftOfferVisible,
  hasUnsavedChanges, fieldHints, callNumberPreview, shelfSuggestion,
  applyGeneratedCallNumber, duplicateResult, adminOverride, extraLanguages,
  genreGroupA, genreGroupB, dynamicCommunityGenres, selectedGroupAGenre,
  selectedGroupBGenre, selectedGroupCGenre, showCustomManualGenreField,
  customManualGenreText, isFrozen, isIsbnValid, isIsbnChecksumValid,
  isPasteIsbnReady, isIsbnReadyForCatalogue, readinessItems, readinessCount, readinessTotal,
  readinessPercent, hasDraftContent, isFieldImported, isYearValid,
  authorSuggestions, externalAuthorSuggestions, externalAuthorSearchLoading, externalAuthorSearchMessage, searchExternalAuthors, publisherSuggestions,
  titleLookupLoading, titleLookupResults, titleLookupMessage, searchTitleCandidates, selectTitleCandidate, clearTitleLookupResults,
  liveCompiledGenreChips, seriesName, seriesNumber, volumeNumber, relatedWorkId,
  savePartialDraft, clearPartialDrafts, restoreDraftVersion, selectAuthor, selectExternalAuthor,
  selectPublisher, handleBlurAction, sanitizeField, handleMetadataPaste,
  clearField, confirmPrefill, triggerCreationPrompt, executeConfirmedCreation,
  normalizeParserIsbn, syncGenreSelection, syncManualGenreInput
} = useCreateWork()

function scrollToSection(sectionId) {
  document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" })
}

function updateAuthorDropdownPosition() {
  const anchor = authorInputAnchor.value
  if (!anchor || typeof window === "undefined") return

  const rect = anchor.getBoundingClientRect()
  const edge = 8
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const width = Math.max(180, Math.min(rect.width, viewportWidth - edge * 2))
  const left = Math.max(edge, Math.min(rect.left, viewportWidth - width - edge))
  const gap = 6
  const preferredHeight = Math.min(380, Math.floor(viewportHeight * 0.48))
  const spaceBelow = Math.max(0, viewportHeight - rect.bottom - gap - edge)
  const spaceAbove = Math.max(0, rect.top - gap - edge)
  const openAbove = spaceBelow < Math.min(preferredHeight, 220) && spaceAbove > spaceBelow
  const availableSpace = openAbove ? spaceAbove : spaceBelow
  const maxHeight = Math.max(100, Math.min(preferredHeight, availableSpace || preferredHeight))
  const preferredTop = openAbove ? rect.top - maxHeight - gap : rect.bottom + gap
  const top = Math.max(edge, Math.min(preferredTop, viewportHeight - edge - maxHeight))

  authorDropdownStyle.value = {
    position: "fixed",
    left: `${left}px`,
    top: `${Math.max(edge, top)}px`,
    width: `${width}px`,
    maxWidth: `calc(100vw - ${edge * 2}px)`,
    right: "auto",
    maxHeight: `${maxHeight}px`,
    visibility: "visible",
    zIndex: 99999,
  }
}

function openAuthorSuggestions() {
  showAuthorSuggestions.value = true
  requestAnimationFrame(updateAuthorDropdownPosition)
}

function handleAuthorBlur() {
  sanitizeField("author")
  // Allow keyboard users to move focus from the input into the teleported menu.
  window.setTimeout(() => {
    const activeElement = document.activeElement
    const focusStayedInside = authorInputAnchor.value?.contains(activeElement)
      || authorDropdown.value?.contains(activeElement)
    if (!focusStayedInside) showAuthorSuggestions.value = false
  }, 220)
}

function closeSuggestionsOnOutsidePointer(event) {
  const target = event.target
  if (titleLookupArea.value && !titleLookupArea.value.contains(target)) {
    clearTitleLookupResults(false)
  }
  const insideAuthorField = authorLookupArea.value && authorLookupArea.value.contains(target)
  const insideAuthorMenu = authorDropdown.value && authorDropdown.value.contains(target)
  if (!insideAuthorField && !insideAuthorMenu) {
    showAuthorSuggestions.value = false
  }
  if (publisherLookupArea.value && !publisherLookupArea.value.contains(target)) {
    showPublisherSuggestions.value = false
  }
}

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

function formatDraftSavedAt(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "time unavailable" : date.toLocaleString()
}
</script>

<style scoped>

.modern-catalog-container {
  min-height: 100vh;
  background: var(--content-bg);
  color: var(--text-primary);
  font-family: "Lilex", system-ui, -apple-system, sans-serif;
  padding: 24px;
}

.catalog-shell {
  max-width: 1400px;
  margin: 0 auto;
}
.catalog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-main);
  margin-bottom: 28px;
}
.brand-group {
  display: flex;
  align-items: center;
  gap: 16px;
}
.brand-icon {
  width: 54px;
  height: 54px;
  background: var(--accent);
  color: var(--text-primary);
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 24px;
  font-family: "Dekko", serif;
  box-shadow: 0 4px 12px var(--catalog-shadow, rgba(40, 70, 25, 0.16));
}
.sub-eyebrow {
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 700;
}
.catalog-header h1 {
  margin: 2px 0 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}
.status-indicator-group {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* Compact saved-draft strip; it exists only while valid saved versions are present. */
.saved-draft-banner {
  margin: -8px 0 16px;
  padding: 10px 12px;
  border: 1px solid var(--catalog-card-border-hover, var(--border-main));
  border-left: 4px solid var(--accent);
  border-radius: 12px;
  background: var(--surface-2);
  color: var(--text-primary);
  box-shadow: inset 0 1px 0 var(--catalog-card-highlight, transparent),
    0 2px 8px var(--catalog-shadow, rgba(40, 70, 25, 0.08));
}
.saved-draft-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.saved-draft-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.saved-draft-kicker {
  color: var(--accent);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
}
.saved-draft-summary-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}
.saved-draft-copy small {
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.35;
}
.saved-draft-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
}
.saved-draft-actions button {
  min-height: 34px;
  padding: 6px 11px;
  border-radius: 9px;
  font-size: 11px;
}
.saved-draft-open-btn {
  white-space: nowrap;
}
.saved-draft-history-btn,
.saved-draft-remove-btn {
  white-space: nowrap;
}
.saved-draft-version-list {
  display: grid;
  gap: 6px;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid var(--border-main);
}
.saved-draft-version-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 9px;
  border: 1px solid var(--border-main);
  border-radius: 9px;
  background: var(--surface);
}
.saved-draft-version-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.saved-draft-version-copy strong {
  color: var(--text-primary);
  font-size: 11px;
}
.saved-draft-version-copy small {
  color: var(--text-muted);
  font-size: 10px;
}
@media (max-width: 800px) {
  .saved-draft-main {
    align-items: flex-start;
    flex-direction: column;
  }
  .saved-draft-actions {
    justify-content: flex-start;
  }
  .saved-draft-version-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--surface-2);
  padding: 8px 14px;
  border-radius: 99px;
}
.status-badge.has-changes {
  color: var(--text-warning);
  background: var(--surface-warning);
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}
.has-changes .pulse-dot {
  background: var(--text-warning);
}
.progress-pill {
  display: flex;
  align-items: baseline;
  gap: 6px;
  background: var(--active-bg);
  color: var(--text-primary);
  padding: 8px 16px;
  border-radius: 99px;
  font-size: 13px;
}
.progress-pill strong {
  font-size: 16px;
}

.catalog-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 32px;
}
.catalog-sidebar {
  position: sticky;
  top: 24px;
  align-self: start;
}
.sidebar-title {
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-weight: 800;
  margin-bottom: 16px;
}
.nav-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nav-item {
  display: flex;
  gap: 14px;
  align-items: center;
  text-decoration: none;
  color:var(--text-primary);
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--surface);
  border: 1px solid var(--border-main);
  transition: all 0.2s ease;
}
.nav-item.active {
  background: var(--surface-2);
border-color: var(--border-main);
color: var(--text-primary);
}
.step-num {
  font-size: 12px;
  font-weight: 800;
  color: var(--text-muted);
}
.nav-item.active .step-num {
  color: var(--text-primary);
}
.nav-item strong {
  display: block;
  font-size: 14px;
  font-weight: 600;
}
.nav-item small {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
.sidebar-card {
  margin-top: 24px;
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border-main);
  padding: 20px;
  border-radius: 16px;
}
.card-tag {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-primary);
  font-weight: 800;
  display: block;
  margin-bottom: 6px;
}
.sidebar-card h4 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}
.sidebar-card p {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.catalog-main-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.fast-capture-card {
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 20px;
  padding: 24px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: center;
}
.capture-info h3 {
  margin: 4px 0 6px;
  font-size: 18px;
  color: var(--text-primary);
}
.capture-info p {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary)  ;
  line-height: 1.4;
}

.capture-action {
  display: flex;
  gap: 10px;
}
.capture-action input {
  flex: 1;
  height: 48px;
  border-radius: 12px;
  border: 1px solid var(--border-main);
  background: var(--surface-2);
  color: var(--text-primary);
  padding: 0 16px;
  font-size: 14px;
  outline: none;
}
.capture-action button {
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  padding: 0 24px;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
}

.form-section {
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border-main);
  border-radius: 20px;
  padding: 28px;
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 20px;
}
.section-badge {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-muted);
}
.section-body {
  min-width: 0;
}
.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.section-header-row h2 {
  margin: 2px 0 6px;
  font-size: 20px;
  font-weight: 700;
}
.section-header-row p {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}
.check-counter {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  background: var(--active-bg);
  padding: 6px 12px;
  border-radius: 99px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.full-width {
  grid-column: 1 / -1;
}
.span-two {
  grid-column: span 2;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}
.input-group label {
  font-size: 12px;
  font-weight: 700;
  color:  var(--text-muted);
}
.required {
  color: var(--text-danger);
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  min-height: 48px;
  padding: 0 14px;
  transition: all 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: var(--accent);
  background: var(--surface);
  box-shadow: 0 0 0 3px var(--catalog-accent-soft, var(--hover-bg));
}


.input-wrapper.is-imported {
  background: var(--surface-2);
  border-color: var(--catalog-card-border-hover);
}
/* Keep focus indication on the outer input wrapper; prevent a second inset rectangle inside every field. */
.input-wrapper input,
.input-wrapper input:focus,
.input-wrapper input:focus-visible,
.input-wrapper textarea,
.input-wrapper textarea:focus,
.input-wrapper select,
.input-wrapper select:focus {
  outline: none !important;
  box-shadow: none !important;
  border: 0 !important;
  background-image: none !important;
}
.input-wrapper input:-webkit-autofill,
.input-wrapper input:-webkit-autofill:hover,
.input-wrapper input:-webkit-autofill:focus {
  -webkit-text-fill-color: var(--text-primary);
  transition: background-color 999999s ease-out 0s;
  box-shadow: none !important;
}
.title-lookup-status { color: var(--text-muted); font-size: 11px; min-height: 1em; }

.input-wrapper input, .textarea-field, .select-field {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  color:  var(--text-primary);
}
.select-field {
  height: 48px;
  border-radius: 12px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  padding: 0 14px;
  outline: none;
}
.textarea-field {
  padding: 12px;
  resize: vertical;
  min-height: 100px;
}
.clear-btn, .text-action-btn {
  background: none;
  border: none;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  cursor: pointer;
  text-transform: uppercase;
}
.imported-note {
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
}
.valid-mark {
  color: var(--accent);
  font-weight: 800;
}

.title-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 7px;
}
.title-label-row label { margin: 0; }
.title-lookup-button, .title-candidate-use {
  min-height: 32px;
  padding: 7px 11px;
  font-size: 11px;
  white-space: nowrap;
}
.title-lookup-note, .title-lookup-message {
  display: block;
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
}
.title-candidate-list {
  margin-top: 8px;
  border: 1px solid var(--border-main);
  border-radius: 10px;
  overflow-x: hidden;
  overflow-y: auto;
  max-height: min(52vh, 360px);
  background: var(--surface-2);
}
.title-candidate-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-main);
}
.title-candidate-row:last-child { border-bottom: 0; }
.title-candidate-copy { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.title-candidate-copy strong { font-size: 12px; overflow-wrap: anywhere; }
.title-candidate-copy small { color: var(--text-muted); font-size: 10px; }
.title-lookup-button:disabled, .title-candidate-use:disabled { opacity: .6; cursor: not-allowed; }
@media (max-width: 640px) {
  .title-label-row, .title-candidate-row { align-items: stretch; flex-direction: column; }
  .title-lookup-button, .title-candidate-use { width: 100%; }
}

.author-lookup-group { min-width: 0; }
.author-lookup-group.has-open-suggestions { z-index: 120; }
.author-input-wrapper { position: relative; overflow: visible; }
.suggestions-dropdown {
  position: absolute;
  top: calc(100% + 7px);
  left: 0;
  right: 0;
  width: 100%;
  box-sizing: border-box;
  margin-top: 0;
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  box-shadow: 0 14px 30px rgba(0,0,0,0.26);
  z-index: 200;
  max-height: min(58vh, 420px);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.suggestions-header {
  padding: 10px 14px;
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-main);
}
.suggestion-row {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  color: var(--text-primary);
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--border-main);
  border-radius: 0;
  white-space: normal;
  min-width: 0;
}
.suggestion-row:hover,
.suggestion-row:focus-visible {
  background: var(--hover-bg);
  outline: none;
}
.local-author-suggestion .suggestion-primary-name,
.external-author-suggestion .suggestion-primary-name {
  font-size: 13px;
  font-weight: 650;
  overflow-wrap: anywhere;
}
.suggestion-status {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
  line-height: 1.4;
  text-align: right;
  max-width: 55%;
  overflow-wrap: anywhere;
}
.external-author-suggestion {
  display: block;
  padding: 12px 14px;
}
.external-author-main-line {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.suggestion-detail {
  display: block;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.suggestion-empty {
  padding: 10px 14px;
  color: var(--text-muted);
  font-size: 12px;
}
.external-search-trigger {
  display: block;
  width: 100%;
  text-align: left;
  background: var(--surface-2);
  color: var(--text-primary);
  font: inherit;
  border-bottom: 0;
}
.external-search-trigger:disabled {
  cursor: wait;
  opacity: 0.7;
}
@media (max-width: 640px) {
  .external-author-main-line { flex-direction: column; gap: 4px; }
  .suggestion-status { max-width: 100%; text-align: left; }
  .suggestions-dropdown { max-height: 52vh; }
}
.manual-isbn-note {
  display: block;
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
}

.pub-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1.25fr) minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}
.pub-card, .system-metric-card {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  padding: 14px;
}
.system-metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
}
.compact-system-metric-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: 11px 12px;
}
.system-metric-card span {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 800;
  display: block;
}
.system-metric-card strong {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.25;
  font-weight: 700;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}
.system-metric-card small {
  font-size: 10px;
  line-height: 1.35;
  color: var(--text-muted);
  margin-top: 3px;
  display: block;
}
.isbn-feedback {
  font-size: 12px;
  margin-top: 8px;
  color: var(--text-muted);
}
.isbn-feedback.success { color: var(--text-success); }
.isbn-feedback.error { color: var(--text-error); }

.smart-suggestions-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
  background: var(--surface-2);
  border: 1px solid var(--border-main) ;
  border-radius: 16px;
  padding: 16px;
}
.smart-suggestions-box span {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-weight: 700;
  display: block;
}
.smart-suggestions-box strong {
  display: block;
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
}

.genre-builder-box {
  margin-top: 24px;
  border-top: 1px solid var(--border-main);
  padding-top: 24px;
}
.builder-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}
.builder-title-row strong {
  display: block;
  font-size: 16px;
  font-weight: 600;
  margin-top: 4px;
}
.genre-select-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.custom-genre-input {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  padding: 0 16px;
  margin-top: 14px;
  outline: none;
}
.genre-chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.genre-chip {
  font-size: 12px;
  padding: 6px 12px;
  background: var(--surface-2);
  color: var(--text-primary);
  border-radius: 8px;
  font-weight: 600;
}

.verification-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 20px;
}
.verify-card {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  border-radius: 16px;
  padding: 20px;
}
.card-inner-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.card-inner-title strong {
  font-size: 16px;
  font-weight: 600;
  display: block;
  margin-top: 2px;
}
.alert-box {
  padding: 16px;
  border-radius: 12px;
}
.success-alert {
  background: var(--surface-success);
  border: 1px solid var(--border-success);
  color: var(--text-success);
}
.warning-alert {
  background: var(--surface-warning);
  border: 1px solid var(--border-warning);
  color: var(--text-warning);
}
.match-result-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--border-main);
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 10px;
  cursor: pointer;
}
.match-result-btn span {
  font-weight: 700;
  display: block;
}
.checkbox-label {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
  font-size: 12px;
}
.percent-highlight {
  font-size: 20px;
  color: var(--accent);
}
.readiness-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.readiness-row {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
}
.check-box {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: 1px solid var(--border-main);
  color: var(--text-secondary);
}
.check-box.completed {
  background: var(--surface-success);
  border-color: var(--border-success);
  color: var(--text-success);
}
.conflicts-panel {
  margin-top: 20px;
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  border-radius: 16px;
  padding: 20px;
}
.conflict-item {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid var(--border-main);
  font-size: 12px;
}

.catalog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 20px;
  padding: 24px;
  margin-top: 12px;
}
.footer-copy strong {
  font-size: 16px;
  font-weight: 600;
  display: block;
}
.footer-copy span {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  display: block;
}
.footer-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}
.btn-secondary, .btn-danger, .btn-primary {
  height: 48px;
  padding: 0 20px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid var(--border-main);
  background: var(--surface);
  color: var(--text-primary);
}
.btn-danger {
  color: var(--text-danger);
  border-color: var(--border-danger);
  background: var(--surface-danger);
}
.btn-primary {
  background: var(--accent);
  color: var(--catalog-button-text, var(--button-text));
  border-color: var(--accent);
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(5, 20, 12, 0.62);
  display: grid;
  place-items: center;
  z-index: 100;
  padding: 20px;
}
.modal-card {
  width: min(480px, 100%);
  background:var(--surface);
  border-radius: 20px;
  padding: 28px;
  position: relative;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}
.close-modal-btn {
  position: absolute;
  right: 20px;
  top: 20px;
  border: none;
  background: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
}
.modal-card h2 {
  margin: 12px 0 6px;
  font-size: 22px;
}
.modal-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}
.modal-preview-box {
  background: var(--surface-2);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  padding: 16px;
  margin: 16px 0;
}
.modal-preview-box strong {
  display: block;
  font-size: 15px;
}
.modal-preview-box span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}
.modal-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}
.modal-input {
  display: block;
  width: 100%;
  height: 48px;
  margin-top: 8px;
  border-radius: 12px;
  border: 1px solid var(--border-main);
  background: var(--surface);
  padding: 0 16px;
  outline: none;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
.toast-popup {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: min(380px, calc(100vw - 48px));
  background: var(--surface);
  color: var(--text-primary);
  padding: 16px;
  border-radius: 16px;
  z-index: 110;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  border-left: 4px solid var(--accent);
}
.toast-popup strong {
  display: block;
  font-size: 14px;
}
.toast-popup span {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

/* Keep verification concise while preserving all checks and duplicate details. */
#verification.form-section {
  padding: 18px 20px;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 12px;
  border-radius: 16px;
}
#verification .section-header-row {
  margin-bottom: 12px;
}
#verification .section-header-row h2 {
  margin-bottom: 3px;
  font-size: 18px;
}
#verification .section-header-row p {
  font-size: 12px;
  line-height: 1.4;
}
#verification .verification-grid {
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 12px;
  align-items: start;
}
#verification .verify-card {
  min-width: 0;
  padding: 13px;
  border-radius: 12px;
}
#verification .card-inner-title {
  margin-bottom: 9px;
}
#verification .card-inner-title strong {
  font-size: 14px;
}
#verification .alert-box {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.4;
}
#verification .alert-box > strong,
#verification .alert-box > span {
  display: block;
  width: 100%;
}
#verification .alert-box > strong {
  line-height: 1.25;
}
#verification .readiness-grid {
  gap: 5px 8px;
}
#verification .readiness-row {
  min-height: 24px;
  gap: 6px;
  padding: 3px 5px;
  border-radius: 7px;
  font-size: 11px;
}
#verification .check-box {
  flex: 0 0 17px;
  width: 17px;
  height: 17px;
  border-radius: 5px;
}
#verification .percent-highlight {
  font-size: 17px;
}
@media (max-width: 900px) {
  .pub-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .verification-grid,
  #verification .verification-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* Theme-aware card depth: green accents only, no blue/indigo. */
.sidebar-card,
.fast-capture-card,
.form-section,
.pub-card,
.system-metric-card,
.smart-suggestions-box,
.verify-card,
.conflicts-panel,
.catalog-footer,
.modal-card,
.nav-item,
.match-result-btn,
.modal-preview-box,
.suggestions-dropdown,
.suggestion-row,
.genre-chips-container,
.readiness-row,
.conflict-item {
  border-color: var(--catalog-card-border, var(--border-main));
  box-shadow:
    inset 0 1px 0 var(--catalog-card-highlight, transparent),
    0 2px 7px var(--catalog-shadow, rgba(40, 70, 25, 0.10)),
    0 1px 0 rgba(0, 0, 0, 0.025);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

.sidebar-card,
.fast-capture-card,
.form-section,
.pub-card,
.system-metric-card,
.smart-suggestions-box,
.verify-card,
.conflicts-panel,
.catalog-footer,
.modal-card,
.nav-item {
  border-style: solid;
  border-width: 1px;
}

.sidebar-card:hover,
.fast-capture-card:hover,
.form-section:hover,
.pub-card:hover,
.system-metric-card:hover,
.smart-suggestions-box:hover,
.verify-card:hover,
.conflicts-panel:hover,
.catalog-footer:hover,
.nav-item:hover,
.match-result-btn:hover {
  border-color: var(--catalog-card-border-hover, var(--accent));
  box-shadow:
    inset 0 1px 0 var(--catalog-card-highlight, transparent),
    0 6px 16px var(--catalog-shadow, rgba(40, 70, 25, 0.14)),
    0 0 0 1px var(--catalog-accent-soft, var(--hover-bg));
  transform: translateY(-2px);
}

.form-section,
.fast-capture-card,
.sidebar-card,
.pub-card,
.verify-card,
.system-metric-card,
.smart-suggestions-box,
.conflicts-panel,
.catalog-footer,
.modal-card {
  position: relative;
}

/* Inner panels have a quieter, nested layer of depth. */
.verify-card,
.conflicts-panel,
.modal-preview-box,
.match-result-btn,
.suggestions-dropdown,
.genre-chips-container {
  box-shadow:
    inset 0 1px 0 var(--catalog-card-highlight, transparent),
    0 1px 4px var(--catalog-shadow, rgba(40, 70, 25, 0.08));
}

.input-wrapper:focus-within,
.select-field:focus-visible,
.textarea-field:focus-visible,
.modal-input:focus-visible {
  border-color: var(--catalog-card-border-hover, var(--accent));
  box-shadow: 0 0 0 3px var(--catalog-accent-soft, var(--hover-bg));
  outline: none;
}

.nav-item.active {
  border-color: var(--catalog-card-border-hover, var(--accent));
  box-shadow: inset 3px 0 0 var(--accent), 0 2px 8px var(--catalog-shadow, rgba(40, 70, 25, 0.08));
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-card,
  .fast-capture-card,
  .form-section,
  .pub-card,
  .system-metric-card,
  .smart-suggestions-box,
  .verify-card,
  .conflicts-panel,
  .catalog-footer,
  .modal-card,
  .nav-item,
  .match-result-btn {
    transition: none;
  }
}


/* Author menu is teleported to body and positioned against the input rect. */
.author-suggestions-dropdown {
  position: fixed !important;
  z-index: 99999 !important;
  margin: 0;
  padding: 0;
  border-radius: 12px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  background: var(--surface);
  color: var(--text-primary);
  box-shadow: 0 16px 42px rgba(0, 0, 0, 0.48);
  isolation: isolate;
}
.author-suggestions-dropdown .suggestion-row {
  box-shadow: none !important;
  transform: none !important;
  transition: background-color 120ms ease;
  border-color: var(--border-main);
  min-height: 46px;
}
.author-suggestions-dropdown .suggestion-row:last-child {
  border-bottom: 0;
}
.author-suggestions-dropdown .suggestion-row:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.author-suggestions-dropdown .suggestions-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--surface);
  font-size: 10px;
  line-height: 1.3;
  font-weight: 800;
}
.author-suggestions-dropdown .external-results-header {
  position: static;
  top: auto;
  border-top: 1px solid var(--border-main);
}
.author-suggestions-dropdown .local-author-suggestion {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}
.author-suggestions-dropdown .external-author-suggestion {
  display: block;
  padding: 12px 14px;
}
.author-suggestions-dropdown .external-author-main-line {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: 4px;
}
.author-suggestions-dropdown .suggestion-primary-name {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.4;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.author-suggestions-dropdown .suggestion-status {
  display: block;
  max-width: 100%;
  text-align: left;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.4;
  font-weight: 600;
  white-space: normal;
  overflow-wrap: anywhere;
}
.author-suggestions-dropdown .suggestion-detail {
  display: block;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.author-suggestions-dropdown .suggestion-empty {
  padding: 10px 14px;
  white-space: normal;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.author-suggestions-dropdown .external-search-trigger {
  position: sticky;
  bottom: 0;
  z-index: 2;
  border-top: 1px solid var(--border-main);
  background: var(--surface-2);
  color: var(--accent);
  font-size: 12px;
  font-weight: 750;
}
.author-suggestions-dropdown .external-search-trigger:hover:not(:disabled) {
  background: var(--hover-bg);
}
.title-lookup-group { min-width: 0; }
.title-lookup-group .title-candidate-row { min-width: 0; }

/* Green-dominant theme typography. */
.modern-catalog-container {
  font-family: "Lilex", system-ui, sans-serif;
}
.brand-group .sub-eyebrow,
.catalog-header h1 {
  font-family: "Dekko", cursive;
}
.catalog-header h1 {
  font-size: 30px;
  line-height: 1.1;
}
.section-header-row h2,
.capture-info h3,
.sidebar-card h4,
.fast-capture-card h3,
.smart-suggestions-box h3,
.verify-card h3 {
  font-family: "Hi Melody", cursive;
  font-weight: 600;
}
.sub-eyebrow,
.sidebar-title {
  color: var(--text-muted);
}
.status-badge {
  color: var(--text-secondary);
  background: var(--surface-2);
}
.status-badge.has-changes {
  color: var(--text-warning);
  background: var(--surface-warning);
}


/* Visible toast + button feedback */
.toast-popup { position: fixed !important; top: 76px !important; right: 24px !important; bottom: auto !important; left: auto !important; width: min(380px, calc(100vw - 48px)); padding: 14px 16px !important; border-radius: 10px !important; z-index: 2000 !important; color: #fff !important; background: #14532d !important; border-left: 6px solid #4ade80; box-shadow: 0 12px 32px rgba(0,0,0,.35) !important; animation: toast-in .25s ease-out; }
.toast-popup.toast-error { background: #7f1d1d !important; border-left-color: #fca5a5; }
.toast-popup strong { color: #fff !important; font-size: 14px; }
.toast-popup span { color: #e5e7eb !important; }
@keyframes toast-in { from { opacity: 0; transform: translateX(24px); } to { opacity: 1; transform: none; } }
button { transition: transform .15s ease, box-shadow .15s ease, filter .15s ease; }
button:not(:disabled):hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.18); filter: brightness(1.06); }
button:not(:disabled):active { transform: translateY(1px) scale(.97); box-shadow: none; filter: brightness(.95); }
button:focus-visible { outline: 2px solid #4ade80; outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { button, .toast-popup { transition: none; animation: none; } }</style>
