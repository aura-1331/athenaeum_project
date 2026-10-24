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

      <!-- Saved Draft Banner -->
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
            <a href="#physical-copy" class="nav-item" @click.prevent="scrollToSection('physical-copy')">
              <span class="step-num">05</span>
              <div>
                <strong>Physical Holding</strong>
                <small>Dimensions & condition</small>
              </div>
            </a>
            <a href="#verification" class="nav-item" @click.prevent="scrollToSection('verification')">
              <span class="step-num">06</span>
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
                  <span class="card-tag">BIBLIOGRAPHIC & ARCHIVAL PEDIGREE</span>
                  <h2>Context, Translation & Rights</h2>
                  <p>Record translation lineages, role attributions, subject headings, and copyright status.</p>
                </div>
              </div>

              <!-- Translation Lineage -->
              <div class="form-grid" style="margin-bottom: 20px;">
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
                  <label>Original title</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.original_title" placeholder="Root title (e.g. O Alquimista)" /></div>
                </div>
                <div class="input-group">
                  <label>Original author</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.original_author" placeholder="Root creator name" /></div>
                </div>
                <div class="input-group">
                  <label>Translator</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.translator" placeholder="Credited translator" /></div>
                </div>
                <div class="input-group">
                  <label>Compiler / Editor</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.compiler_editor" placeholder="Compiler or editor" /></div>
                </div>
                <div class="input-group">
                  <label>Work nature</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.work_nature" placeholder="Nature or genre type" /></div>
                </div>
              </div>

              <!-- Edition, Series & Identifiers -->
              <div class="form-grid" style="margin-bottom: 20px; border-top: 1px solid #000; padding-top: 20px;">
                <div class="input-group">
                  <label>Edition statement</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.edition_statement" placeholder="e.g. 1st Edition, Revised" /></div>
                </div>
                <div class="input-group">
                  <label>Series title</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.series_title" placeholder="Academic series name" /></div>
                </div>
                <div class="input-group">
                  <label>Series volume / number</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.series_volume" placeholder="Series volume" /></div>
                </div>
                <div class="input-group">
                  <label>LCCN</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.lccn" placeholder="Library of Congress Control No." /></div>
                </div>
                <div class="input-group">
                  <label>OCLC No.</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.oclc_no" placeholder="OCLC control number" /></div>
                </div>
              </div>

              <!-- Subjects & Rights -->
              <div class="form-grid" style="border-top: 1px solid #000; padding-top: 20px;">
                <div class="input-group">
                  <label>Subject headings / Keywords</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.subject_headings" placeholder="Standardized tags / keywords" /></div>
                </div>
                <div class="input-group">
                  <label>Target audience / Era</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.target_audience_era" placeholder="e.g. 19th Century, Academic" /></div>
                </div>
                <div class="input-group">
                  <label>Copyright status</label>
                  <div class="input-wrapper"><input autocomplete="new-password" v-model="form.copyright_status" placeholder="e.g. Public Domain, In Copyright" /></div>
                </div>
                <div class="input-group full-width">
                  <label>Bibliographic notes</label>
                  <textarea autocomplete="off" v-model="form.notes" rows="4" placeholder="Anything the next reviewer should know about this record" class="textarea-field"></textarea>
                </div>
              </div>

            </div>
          </section>

          <!-- Section 05: Physical Holding -->
          <section id="physical-copy" class="form-section">
            <div class="section-badge">05</div>
            <div class="section-body">
              <div class="section-header-row">
                <div>
                  <span class="card-tag">PHYSICAL HOLDING</span>
                  <h2>Artifact & Provenance Details</h2>
                  <p>Record dimensions, condition, acquisition history, and digital availability for the initial copy.</p>
                </div>
              </div>

              <div class="form-grid">
                <div class="input-group">
                  <label>Extent / Page count</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.extent_page_count" placeholder="e.g. xiv, 342 p." />
                  </div>
                </div>

                <div class="input-group">
                  <label>Physical dimensions</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.physical_dimensions" placeholder="e.g. 24 cm" />
                  </div>
                </div>

                <div class="input-group">
                  <label>Date acquired</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" type="date" v-model="form.date_acquired" />
                  </div>
                </div>

                <div class="input-group">
                  <label>Collection / Fonds</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.collection_fonds" placeholder="Named special collection" />
                  </div>
                </div>

                <div class="input-group">
                  <label>Physical condition</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.physical_condition" placeholder="e.g. Fine, Good, Fragile" />
                  </div>
                </div>

                <div class="input-group">
                  <label>Binding type</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.binding_type" placeholder="e.g. Hardcover, Leather" />
                  </div>
                </div>

                <div class="input-group full-width">
                  <label>Provenance source / donor</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.provenance_source" placeholder="Source or vendor history" />
                  </div>
                </div>

                <div class="input-group full-width">
                  <label>Artifactual notes</label>
                  <textarea autocomplete="off" v-model="form.artifactual_notes" rows="2" class="textarea-field" placeholder="Bookplates, inscriptions, marginalia..."></textarea>
                </div>

                <div class="input-group">
                  <label>Access restrictions</label>
                  <div class="input-wrapper">
                    <input autocomplete="new-password" v-model="form.access_restrictions" placeholder="Restrictions or handling notes" />
                  </div>
                </div>

                <div class="input-group">
                  <label>Digital scan available</label>
                  <select v-model="form.digital_scan_available" class="select-field">
                    <option :value="false">No</option>
                    <option :value="true">Yes</option>
                  </select>
                </div>

                <div class="input-group">
                  <label>OCR status</label>
                  <select v-model="form.ocr_status" class="select-field">
                    <option value="Unindexed">Unindexed</option>
                    <option value="Indexed">Indexed</option>
                    <option value="Partial">Partial</option>
                  </select>
                </div>
              </div>
            </div>
          </section>
          
          <!-- Section 06: Verification -->
          <section id="verification" class="form-section">
            <div class="section-badge">06</div>
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
        <button type="button" aria-label="Dismiss" style="float:right;background:none;border:0;color:#000;font-size:18px;cursor:pointer" @click="result = null">&times;</button>
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
  background: #ffffff;
  color: #000000;
  font-family: monospace, system-ui, sans-serif;
  padding: 32px 24px;
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
  border-bottom: 2px solid #000000;
  margin-bottom: 32px;
}
.brand-group {
  display: flex;
  align-items: center;
  gap: 16px;
}
.brand-icon {
  width: 52px;
  height: 52px;
  background: #000000;
  color: #ffffff;
  border-radius: 0px;
  display: grid;
  place-items: center;
  font-weight: 900;
  font-size: 22px;
  border: 2px solid #000000;
}
.sub-eyebrow {
  font-size: 10px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #000000;
  font-weight: 900;
}
.catalog-header h1 {
  margin: 2px 0 0;
  font-size: 26px;
  font-weight: 900;
  color: #000000;
}
.status-indicator-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Saved draft banner styling */
.saved-draft-banner {
  margin-bottom: 24px;
  padding: 14px 18px;
  border: 2px solid #000000;
  border-left: 6px solid #000000;
  border-radius: 0px;
  background: #ffffff;
}
.saved-draft-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.saved-draft-copy {
  display: grid;
  gap: 2px;
}
.saved-draft-kicker {
  color: #000000;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.1em;
}
.saved-draft-summary-title {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
}
.saved-draft-actions {
  display: flex;
  gap: 8px;
}
.saved-draft-version-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 2px solid #000000;
  display: grid;
  gap: 8px;
}
.saved-draft-version-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #ffffff;
  border-radius: 0px;
  border: 2px solid #000000;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #000000;
  background: #ffffff;
  padding: 8px 14px;
  border-radius: 0px;
  border: 2px solid #000000;
  font-weight: 700;
}
.status-badge.has-changes {
  color: #000000;
  background: #ffffff;
  border: 2px dashed #000000;
}
.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 0px;
  background: #000000;
}
.progress-pill {
  display: flex;
  align-items: baseline;
  gap: 6px;
  background: #ffffff;
  border: 2px solid #000000;
  color: #000000;
  padding: 8px 16px;
  border-radius: 0px;
  font-size: 12px;
  font-weight: 700;
}
.progress-pill strong {
  font-size: 15px;
  font-weight: 900;
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
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sidebar-title {
  font-size: 10px;
  letter-spacing: 0.15em;
  color: #000000;
  font-weight: 900;
  padding-left: 4px;
}
.nav-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.nav-item {
  display: flex;
  gap: 14px;
  align-items: center;
  text-decoration: none;
  color: #000000;
  padding: 12px 16px;
  border-radius: 0px;
  background: #ffffff;
  border: 2px solid #000000;
  transition: none;
}
.nav-item:hover,
.nav-item.active {
  background: #000000;
  color: #ffffff;
  border-color: #000000;
}
.step-num {
  font-size: 11px;
  font-weight: 900;
  color: #000000;
}
.nav-item:hover .step-num,
.nav-item.active .step-num {
  color: #ffffff;
}
.nav-item strong {
  display: block;
  font-size: 13px;
  font-weight: 900;
}
.nav-item small {
  display: block;
  font-size: 11px;
  color: inherit;
  opacity: 0.8;
  margin-top: 1px;
}
.sidebar-card {
  background: #ffffff;
  border: 2px solid #000000;
  padding: 20px;
  border-radius: 0px;
}
.card-tag {
  font-size: 9px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #000000;
  font-weight: 900;
  display: block;
  margin-bottom: 6px;
}
.sidebar-card h4 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 900;
  color: #000000;
}
.sidebar-card p {
  margin: 0;
  font-size: 12px;
  color: #000000;
  line-height: 1.45;
}

.catalog-main-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.fast-capture-card {
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 24px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: center;
}
.capture-info h3 {
  margin: 4px 0 6px;
  font-size: 17px;
  font-weight: 900;
  color: #000000;
}
.capture-info p {
  margin: 0;
  font-size: 12px;
  color: #000000;
  line-height: 1.45;
}
.capture-action {
  display: flex;
  gap: 10px;
}
.capture-action input {
  flex: 1;
  height: 46px;
  border-radius: 0px;
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
  padding: 0 16px;
  font-size: 13px;
  outline: none;
}
.capture-action input:focus {
  outline: 2px solid #000000;
}
.capture-action button {
  background: #000000;
  color: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 0 20px;
  font-weight: 900;
  font-size: 12px;
  cursor: pointer;
}
.capture-action button:hover {
  background: #ffffff;
  color: #000000;
}

.form-section {
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 32px;
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: 20px;
}
.section-badge {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
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
  margin: 2px 0 4px;
  font-size: 18px;
  font-weight: 900;
  color: #000000;
}
.section-header-row p {
  margin: 0;
  font-size: 12px;
  color: #000000;
}
.check-counter {
  font-size: 11px;
  font-weight: 900;
  color: #000000;
  background: #ffffff;
  border: 2px solid #000000;
  padding: 6px 12px;
  border-radius: 0px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
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
  gap: 6px;
  position: relative;
}
.input-group label {
  font-size: 11px;
  font-weight: 900;
  color: #000000;
}
.required {
  color: #000000;
  font-weight: 900;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  min-height: 46px;
  padding: 0 14px;
}
.input-wrapper:focus-within {
  outline: 2px solid #000000;
}
.input-wrapper input, .textarea-field, .select-field {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: #000000;
}
.select-field {
  height: 46px;
  border-radius: 0px;
  border: 2px solid #000000;
  background: #ffffff;
  padding: 0 14px;
  outline: none;
  color: #000000;
  font-weight: 700;
}
.textarea-field {
  padding: 12px;
  resize: vertical;
  min-height: 90px;
  border: 2px solid #000000;
}
.clear-btn, .text-action-btn {
  background: none;
  border: none;
  font-size: 10px;
  font-weight: 900;
  color: #000000;
  cursor: pointer;
  text-transform: uppercase;
  text-decoration: underline;
}
.imported-note {
  font-size: 10px;
  color: #000000;
  font-weight: 900;
}
.valid-mark {
  color: #000000;
  font-weight: 900;
}

.title-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.title-label-row label { margin: 0; }
.title-lookup-note, .title-lookup-message {
  display: block;
  margin-top: 6px;
  color: #000000;
  font-size: 11px;
}
.title-candidate-list {
  margin-top: 8px;
  border: 2px solid #000000;
  border-radius: 0px;
  overflow: hidden;
  max-height: 280px;
  overflow-y: auto;
  background: #ffffff;
}
.title-candidate-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 2px solid #000000;
}
.title-candidate-row:last-child { border-bottom: 0; }
.title-candidate-copy { display: flex; flex-direction: column; gap: 2px; }
.title-candidate-copy strong { font-size: 12px; color: #000000; font-weight: 900; }
.title-candidate-copy small { color: #000000; font-size: 10px; }

/* Suggestions Dropdown */
.suggestions-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  box-shadow: 6px 6px 0px #000000;
  z-index: 200;
  max-height: 360px;
  overflow-y: auto;
}
.suggestions-header {
  padding: 8px 12px;
  font-size: 9px;
  letter-spacing: 0.1em;
  color: #ffffff;
  border-bottom: 2px solid #000000;
  background: #000000;
  font-weight: 900;
}
.suggestion-row {
  width: 100%;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: transparent;
  border: 0;
  border-bottom: 2px solid #000000;
  cursor: pointer;
  text-align: left;
  color: #000000;
  font-size: 12px;
  font-weight: 700;
}
.suggestion-row:hover {
  background: #000000;
  color: #ffffff;
}
.manual-isbn-note {
  display: block;
  margin-top: 6px;
  color: #000000;
  font-size: 11px;
}

.pub-grid {
  display: grid;
  grid-template-columns: minmax(240px, 1.2fr) minmax(0, 1fr);
  gap: 16px;
}
.pub-card, .system-metric-card, .verify-card, .conflicts-panel {
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 16px;
}
.system-metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.compact-system-metric-card span {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #000000;
  font-weight: 900;
  display: block;
}
.system-metric-card strong {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  font-weight: 900;
  color: #000000;
}
.system-metric-card small {
  font-size: 10px;
  color: #000000;
  margin-top: 2px;
  display: block;
}
.isbn-feedback {
  font-size: 11px;
  margin-top: 6px;
  color: #000000;
  font-weight: 700;
}
.isbn-feedback.success { color: #000000; text-decoration: underline; }
.isbn-feedback.error { color: #000000; font-weight: 900; }

.smart-suggestions-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 16px;
}
.smart-suggestions-box span {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: #000000;
  font-weight: 900;
  display: block;
}
.smart-suggestions-box strong {
  display: block;
  margin-top: 3px;
  font-size: 13px;
  font-weight: 900;
  color: #000000;
}

.genre-builder-box {
  margin-top: 20px;
  border-top: 2px solid #000000;
  padding-top: 20px;
}
.builder-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 12px;
}
.builder-title-row strong {
  display: block;
  font-size: 14px;
  font-weight: 900;
  color: #000000;
  margin-top: 2px;
}
.genre-select-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.custom-genre-input {
  width: 100%;
  height: 46px;
  border-radius: 0px;
  border: 2px solid #000000;
  background: #ffffff;
  padding: 0 14px;
  margin-top: 12px;
  outline: none;
  color: #000000;
}
.genre-chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}
.genre-chip {
  font-size: 11px;
  padding: 4px 10px;
  background: #000000;
  border: 2px solid #000000;
  color: #ffffff;
  border-radius: 0px;
  font-weight: 900;
}

.verification-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}
.card-inner-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.card-inner-title strong {
  font-size: 13px;
  font-weight: 900;
  color: #000000;
}
.alert-box {
  padding: 12px;
  border-radius: 0px;
  font-size: 12px;
  border: 2px solid #000000;
  font-weight: 700;
}
.success-alert {
  background: #ffffff;
  color: #000000;
}
.warning-alert {
  background: #000000;
  color: #ffffff;
}
.match-result-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: #ffffff;
  border: 2px solid #000000;
  padding: 8px 12px;
  border-radius: 0px;
  margin-top: 8px;
  cursor: pointer;
  color: #000000;
}
.match-result-btn span {
  font-weight: 900;
  display: block;
  font-size: 12px;
}
.checkbox-label {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
  font-size: 11px;
  color: #ffffff;
  font-weight: 700;
}
.percent-highlight {
  font-size: 18px;
  color: #000000;
  font-weight: 900;
}
.readiness-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.readiness-row {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 11px;
  color: #000000;
  font-weight: 700;
}
.check-box {
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 0px;
  border: 2px solid #000000;
  color: #000000;
  font-weight: 900;
}
.check-box.completed {
  background: #000000;
  border-color: #000000;
  color: #ffffff;
}
.conflicts-panel {
  margin-top: 16px;
}
.conflict-item {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  padding: 8px 0;
  border-top: 2px solid #000000;
  font-size: 11px;
  color: #000000;
  font-weight: 700;
}

.catalog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 24px;
  margin-top: 16px;
}
.footer-copy strong {
  font-size: 14px;
  font-weight: 900;
  color: #000000;
  display: block;
}
.footer-copy span {
  font-size: 11px;
  color: #000000;
  margin-top: 2px;
  display: block;
}
.footer-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}
.btn-secondary, .btn-primary {
  height: 46px;
  padding: 0 20px;
  border-radius: 0px;
  font-weight: 900;
  font-size: 12px;
  cursor: pointer;
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
}
.btn-secondary:hover {
  background: #000000;
  color: #ffffff;
}
.btn-primary {
  background: #000000;
  color: #ffffff;
  border-color: #000000;
}
.btn-primary:hover {
  background: #ffffff;
  color: #000000;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: grid;
  place-items: center;
  z-index: 100;
  padding: 20px;
}
.modal-card {
  width: min(460px, 100%);
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 28px;
  position: relative;
  box-shadow: 8px 8px 0px #000000;
}
.close-modal-btn {
  position: absolute;
  right: 20px;
  top: 20px;
  border: 2px solid #000000;
  background: #ffffff;
  width: 32px;
  height: 32px;
  font-weight: 900;
  font-size: 16px;
  color: #000000;
  cursor: pointer;
}
.modal-card h2 {
  margin: 10px 0 6px;
  font-size: 20px;
  font-weight: 900;
  color: #000000;
}
.modal-card p {
  font-size: 12px;
  color: #000000;
  font-weight: 700;
}
.modal-preview-box {
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 0px;
  padding: 14px;
  margin: 16px 0;
}
.modal-input {
  display: block;
  width: 100%;
  height: 46px;
  margin-top: 8px;
  border-radius: 0px;
  border: 2px solid #000000;
  background: #ffffff;
  padding: 0 14px;
  outline: none;
  color: #000000;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.toast-popup {
  position: fixed !important;
  top: 24px !important;
  right: 24px !important;
  width: min(360px, calc(100vw - 48px));
  background: #ffffff;
  border: 2px solid #000000;
  color: #000000;
  padding: 16px;
  border-radius: 0px;
  z-index: 2000;
  box-shadow: 6px 6px 0px #000000;
  font-weight: 700;
}
.toast-popup strong {
  color: #000000;
  font-weight: 900;
}
.toast-popup span {
  color: #000000;
}

@media (max-width: 900px) {
  .catalog-layout {
    grid-template-columns: 1fr;
  }
  .catalog-sidebar {
    position: static;
  }
  .pub-grid, .verification-grid, .form-grid {
    grid-template-columns: 1fr;
  }
  .span-two, .full-width {
    grid-column: span 1;
  }
}
</style>