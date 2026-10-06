<template>
  <div class="control-panel-layout">
    <!-- LOADER -->
    <div v-if="loading" class="vault-loader">
      <div class="minimal-spinner"></div>
      <span class="loading-label">RETRIEVING_WRITE_AUTHORIZATION</span>
    </div>

    <!-- MAIN EDIT INTERFACE -->
    <div v-else-if="editableBook" class="panel-container">
      
      <!-- 1. LEFT ANCHOR SIDEBAR -->
      <aside class="identity-anchor-panel">
        <div class="panel-badge-strip">
          <span class="panel-badge">REVISION_STATION_01</span>
          <span class="rank-badge">{{ auditData.userRole }}</span>
        </div>
        
        <div class="hero-identity-block">
          <span class="meta-label">CURRENT RECORD</span>
          <h1 class="display-title" :title="editableBook.title">
            {{ editableBook.title || 'UNTITLED_RECORD' }}
          </h1>
          <p class="display-author">
            BY <strong>{{ editableBook.author || 'UNKNOWN AUTHOR' }}</strong>
          </p>

          <!-- System Identifiers Mini-Dock -->
          <div class="identity-tokens-dock">
            <div class="token-pill">
              <span class="t-key">SERIAL</span>
              <span class="t-val text-magenta">#{{ editableBook.serial_no }}</span>
            </div>
            <div class="token-pill">
              <span class="t-key">WORK ID</span>
              <span class="t-val text-amber">#{{ editableBook.work_id }}</span>
            </div>
            <div class="token-pill">
              <span class="t-key">ACCESSION</span>
              <span class="t-val text-blue">{{ editableBook.accession_no }}</span>
            </div>
          </div>
        </div>

        <!-- SECTION NAVIGATION TABS -->
        <nav class="sidebar-tab-nav" aria-label="Edit Sections">
          <button 
            type="button"
            class="tab-nav-btn"
            :class="{ active: activeTab === 'work' && !searchQuery }"
            @click="setTab('work')"
          >
            <span class="tab-indicator"></span>
            <span class="tab-num">01</span>
            <span class="tab-label">Core Work & Creator</span>
            <span v-if="tabChangesCount('work')" class="tab-change-dot">
              {{ tabChangesCount('work') }}
            </span>
          </button>

          <button 
            type="button"
            class="tab-nav-btn"
            :class="{ active: activeTab === 'taxonomy' && !searchQuery }"
            @click="setTab('taxonomy')"
          >
            <span class="tab-indicator"></span>
            <span class="tab-num">02</span>
            <span class="tab-label">Classification & Genre</span>
            <span v-if="tabChangesCount('taxonomy')" class="tab-change-dot">
              {{ tabChangesCount('taxonomy') }}
            </span>
          </button>

          <button 
            type="button"
            class="tab-nav-btn"
            :class="{ active: activeTab === 'languages' && !searchQuery }"
            @click="setTab('languages')"
          >
            <span class="tab-indicator"></span>
            <span class="tab-num">03</span>
            <span class="tab-label">Language Profiles</span>
            <span v-if="tabChangesCount('languages')" class="tab-change-dot">
              {{ tabChangesCount('languages') }}
            </span>
          </button>

          <button 
            type="button"
            class="tab-nav-btn"
            :class="{ active: activeTab === 'publication' && !searchQuery }"
            @click="setTab('publication')"
          >
            <span class="tab-indicator"></span>
            <span class="tab-num">04</span>
            <span class="tab-label">Imprint & Identifiers</span>
            <span v-if="tabChangesCount('publication')" class="tab-change-dot">
              {{ tabChangesCount('publication') }}
            </span>
          </button>

          <button 
            type="button"
            class="tab-nav-btn"
            :class="{ active: activeTab === 'location' && !searchQuery }"
            @click="setTab('location')"
          >
            <span class="tab-indicator"></span>
            <span class="tab-num">05</span>
            <span class="tab-label">Location & Registry Tokens</span>
            <span v-if="tabChangesCount('location')" class="tab-change-dot">
              {{ tabChangesCount('location') }}
            </span>
          </button>

          <button 
            type="button"
            class="tab-nav-btn"
            :class="{ active: activeTab === 'notes' && !searchQuery }"
            @click="setTab('notes')"
          >
            <span class="tab-indicator"></span>
            <span class="tab-num">06</span>
            <span class="tab-label">Curatorial Remarks</span>
            <span v-if="tabChangesCount('notes')" class="tab-change-dot">
              {{ tabChangesCount('notes') }}
            </span>
          </button>
        </nav>

        <!-- ACTION BUTTONS -->
        <div class="panel-actions-stack">
          <button type="button" class="btn btn-filled" @click="triggerActionConfirm('commit')">
            COMMIT CHANGES
            <span v-if="modifiedFieldsList.length" class="commit-count-pill">
              {{ modifiedFieldsList.length }}
            </span>
          </button>
          <button type="button" class="btn btn-outline" @click="triggerActionConfirm('abort')">
            ABORT TRANSACTION
          </button>
        </div>
      </aside>

      <!-- 2. CENTER FORM WORKSPACE -->
      <main class="form-feed-column">
        <!-- TOP UTILITY BAR (Quick Search & Mode Controls) -->
        <div class="workspace-top-bar">
          <div class="field-finder-wrap">
            <span class="finder-icon">🔍</span>
            <input 
              type="text" 
              v-model="searchQuery" 
              placeholder="Find any field instantly (e.g. 'title', 'shelf', 'isbn', 'language')..." 
              class="finder-input"
            />
            <button 
              v-if="searchQuery" 
              type="button" 
              class="finder-clear-btn" 
              @click="searchQuery = ''"
            >
              ✕
            </button>
          </div>

          <div class="workspace-view-controls">
            <span v-if="searchQuery" class="finder-matches-tag">
              ⚡ FILTER ACTIVE: SHOWING SEARCH MATCHES
            </span>
            <button 
              v-else 
              type="button"
              class="view-toggle-btn"
              @click="showAllSections = !showAllSections"
            >
              {{ showAllSections ? '📑 SWITCH TO TABBED VIEW' : '📜 EXPAND ALL SECTIONS' }}
            </button>
          </div>
        </div>

        <div class="form-scroll-wrapper">
          
          <!-- TAB 1 / SECTION 01: CORE WORK & CREATOR -->
          <section 
            v-show="isSectionVisible('work', ['title', 'author', 'creator'])"
            class="form-card-section"
          >
            <header class="section-header">
              <div class="header-badge-row">
                <span class="section-kicker">SECTION 01</span>
                <span class="section-category-tag">CORE BIBLIOGRAPHIC</span>
              </div>
              <h2 class="section-title">Core Work & Creator</h2>
              <p class="section-desc">Primary identification data for the intellectual work.</p>
            </header>

            <div class="form-grid">
              <!-- Book Title -->
              <div class="field-card col-full required-field" :class="{ 'is-edited': isFieldModified('title') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-title">Work Title</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('title')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-mandatory">REQUIRED</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-title"
                    type="text" 
                    v-model="editableBook.title" 
                    class="large-input font-bold" 
                    placeholder="Enter complete work title..."
                  />
                </div>
              </div>

              <!-- Author / Creator -->
              <div class="field-card col-full relative-position" :class="{ 'is-edited': isFieldModified('author') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-author">Author / Primary Creator</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('author')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">DEFAULT: 'Unknown'</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-author"
                    type="text" 
                    v-model="editableBook.author" 
                    @input="searchAuthorsDebounced"
                    @focus="showAuthorSuggestions = true"
                    @blur="hideSuggestionsWithDelay('author')"
                    class="large-input" 
                    placeholder="e.g. Leo Tolstoy, Homer, Anonymous..."
                  />
                </div>
                
                <!-- Autocomplete Tray -->
                <div 
                  v-if="showAuthorSuggestions && authorSuggestions.length > 0" 
                  class="typeahead-overlay-tray"
                >
                  <div 
                    v-for="suggestion in authorSuggestions" 
                    :key="suggestion"
                    @mousedown.prevent="selectSuggestion('author', suggestion)"
                    class="typeahead-node"
                  >
                    {{ suggestion }}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- TAB 2 / SECTION 02: TAXONOMY & CLASSIFICATION -->
          <section 
            v-show="isSectionVisible('taxonomy', ['category', 'genre', 'ddc', 'classification'])"
            class="form-card-section"
          >
            <header class="section-header">
              <div class="header-badge-row">
                <span class="section-kicker">SECTION 02</span>
                <span class="section-category-tag">TAXONOMY</span>
              </div>
              <h2 class="section-title">Classification & Genre Taxonomy</h2>
              <p class="section-desc">Curatorial classification, subject cataloguing, and thematic genre tags.</p>
            </header>

            <div class="form-grid">
              <!-- Category -->
              <div class="field-card col-half" :class="{ 'is-edited': isFieldModified('category') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-category">Collection Category</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('category')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <select 
                    id="field-category"
                    v-model="editableBook.category" 
                    class="large-select"
                  >
                    <option value="">-- None / Unassigned --</option>
                    <option value="Fiction">Fiction</option>
                    <option value="Non-Fiction">Non-Fiction</option>
                    <option value="Reference">Reference</option>
                    <option value="Religious">Religious</option>
                    <option value="Poetry">Poetry</option>
                  </select>
                </div>
              </div>

              <!-- DDC (Dewey Decimal) -->
              <div class="field-card col-half" :class="{ 'is-edited': isFieldModified('ddc') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-ddc">Dewey Decimal Code (DDC)</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('ddc')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-ddc"
                    type="text" 
                    v-model="editableBook.ddc" 
                    class="large-input font-mono" 
                    placeholder="e.g. 823.914, 294.5..."
                  />
                </div>
              </div>

              <!-- Genre Active Chips Assembly -->
              <div class="field-card col-full layout-dock" :class="{ 'is-edited': isFieldModified('genre') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-magenta"></span>
                    <label class="prominent-label">Active Genre Tags</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('genre')" class="edited-tag">MODIFIED</span>
                    <button 
                      v-if="liveCompiledGenreChips.length > 0" 
                      type="button" 
                      class="clear-inline-btn" 
                      @click="clearAllGenres"
                    >
                      RESET ALL GENRES
                    </button>
                  </div>
                </div>
                <div class="field-card-body">
                  <div class="chip-assembly-dock">
                    <span 
                      v-for="chip in liveCompiledGenreChips" 
                      :key="chip" 
                      class="active-badge-chip"
                    >
                      {{ chip }}
                      <button 
                        type="button" 
                        class="chip-remove" 
                        @click="removeGenreChip(chip)"
                        title="Remove genre"
                      >
                        ×
                      </button>
                    </span>
                    <span v-if="liveCompiledGenreChips.length === 0" class="dock-empty-text">
                      No genre facets currently assigned to this record.
                    </span>
                  </div>
                </div>
              </div>

              <!-- Genre Selectors -->
              <div class="field-card col-third">
                <div class="field-card-header">
                  <label class="prominent-label-sub">Creative Preset (Group A)</label>
                </div>
                <div class="field-card-body">
                  <select 
                    v-model="selectedGroupAGenre" 
                    @change="syncGenreSelection" 
                    class="large-select"
                  >
                    <option value="">-- Choose Creative --</option>
                    <option v-for="g in genreGroupA" :key="g" :value="g">{{ g }}</option>
                  </select>
                </div>
              </div>

              <div class="field-card col-third">
                <div class="field-card-header">
                  <label class="prominent-label-sub">Factual Preset (Group B)</label>
                </div>
                <div class="field-card-body">
                  <select 
                    v-model="selectedGroupBGenre" 
                    @change="syncGenreSelection" 
                    class="large-select"
                  >
                    <option value="">-- Choose Factual --</option>
                    <option v-for="g in genreGroupB" :key="g" :value="g">{{ g }}</option>
                  </select>
                </div>
              </div>

              <div class="field-card col-third">
                <div class="field-card-header">
                  <label class="prominent-label-sub">Community / Override (Group C)</label>
                </div>
                <div class="field-card-body">
                  <select 
                    v-model="selectedGroupCGenre" 
                    @change="syncGenreSelection" 
                    class="large-select"
                  >
                    <option value="">-- Choose or Override --</option>
                    <option v-for="g in dynamicCommunityGenres" :key="g" :value="g">{{ g }}</option>
                    <option disabled class="dropdown-divider-line">────────────────────</option>
                    <option value="CUSTOM_MANUAL_OVERRIDE">✍ Type Custom Manual Tag</option>
                  </select>
                </div>
              </div>

              <!-- Custom Manual Input -->
              <div v-if="showCustomManualGenreField" class="field-card col-full border-highlight-amber">
                <div class="field-card-header">
                  <label class="prominent-label text-amber">
                    Custom Manual Genre (Separate Multiples With '/')
                  </label>
                </div>
                <div class="field-card-body">
                  <input 
                    type="text" 
                    v-model="customManualGenreText" 
                    @input="syncManualGenreInput"
                    placeholder="e.g. PHILOSOPHY/HERMETICISM/ANCIENT" 
                    class="large-input font-mono" 
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- TAB 3 / SECTION 03: LANGUAGE PROFILES -->
          <section 
            v-show="isSectionVisible('languages', ['language', 'text language', 'original language', 'translation'])"
            class="form-card-section"
          >
            <header class="section-header">
              <div class="header-badge-row">
                <span class="section-kicker">SECTION 03</span>
                <span class="section-category-tag">LINGUISTICS</span>
              </div>
              <h2 class="section-title">Language Profiles</h2>
              <p class="section-desc">Script language of the holding and source language of original composition.</p>
            </header>

            <div class="form-grid">
              <!-- Text Language (Required) -->
              <div class="field-card col-half required-field" :class="{ 'is-edited': isFieldModified('language') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-text-lang">Text Language (Physical Copy)</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('language')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-mandatory">REQUIRED</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-text-lang"
                    type="text" 
                    v-model="editableBook.language" 
                    class="large-input font-bold" 
                    placeholder="e.g. English, Latin, Malayalam..."
                  />
                  <span class="field-note">
                    Mandatory archive attribute. Cannot be left blank.
                  </span>
                </div>
              </div>

              <!-- Original Language (Optional) -->
              <div class="field-card col-half" :class="{ 'is-edited': isFieldModified('original_language') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-orig-lang">Original Source Language</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('original_language')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-orig-lang"
                    type="text" 
                    v-model="editableBook.original_language" 
                    class="large-input" 
                    placeholder="Leave blank if not a translation..."
                  />
                  <span class="field-note">
                    Specify only for translations. Leave empty for native compositions.
                  </span>
                </div>
              </div>
            </div>
          </section>

          <!-- TAB 4 / SECTION 04: IMPRINT & IDENTIFIERS -->
          <section 
            v-show="isSectionVisible('publication', ['publisher', 'year', 'isbn'])"
            class="form-card-section"
          >
            <header class="section-header">
              <div class="header-badge-row">
                <span class="section-kicker">SECTION 04</span>
                <span class="section-category-tag">IMPRINT</span>
              </div>
              <h2 class="section-title">Imprint & Identifiers</h2>
              <p class="section-desc">Publisher provenance, release epoch, and standard ISBN serial identifiers.</p>
            </header>

            <div class="form-grid">
              <!-- Publisher -->
              <div class="field-card col-half relative-position" :class="{ 'is-edited': isFieldModified('publisher') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-publisher">Imprint Publisher</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('publisher')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-publisher"
                    type="text" 
                    v-model="editableBook.publisher" 
                    @input="searchPublishersDebounced"
                    @focus="showPublisherSuggestions = true"
                    @blur="hideSuggestionsWithDelay('publisher')"
                    class="large-input" 
                    placeholder="e.g. Oxford University Press, DC Books..."
                  />
                </div>
                
                <!-- Autocomplete Tray -->
                <div 
                  v-if="showPublisherSuggestions && publisherSuggestions.length > 0" 
                  class="typeahead-overlay-tray"
                >
                  <div 
                    v-for="suggestion in publisherSuggestions" 
                    :key="suggestion"
                    @mousedown.prevent="selectSuggestion('publisher', suggestion)"
                    class="typeahead-node"
                  >
                    {{ suggestion }}
                  </div>
                </div>
              </div>

              <!-- Year -->
              <div class="field-card col-quarter" :class="{ 'is-edited': isFieldModified('year') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-year">Publication Year</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('year')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-year"
                    type="text" 
                    v-model="editableBook.year" 
                    class="large-input font-mono" 
                    placeholder="e.g. 1984"
                  />
                </div>
              </div>

              <!-- ISBN -->
              <div class="field-card col-quarter" :class="{ 'is-edited': isFieldModified('isbn') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-isbn">ISBN Code</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('isbn')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-isbn"
                    type="text" 
                    v-model="editableBook.isbn" 
                    class="large-input font-mono" 
                    placeholder="e.g. 9780141036137"
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- TAB 5 / SECTION 05: LOCATION & REGISTRY TOKENS -->
          <section 
            v-show="isSectionVisible('location', ['shelf', 'call number', 'call_no', 'record id', 'serial', 'accession'])"
            class="form-card-section"
          >
            <header class="section-header">
              <div class="header-badge-row">
                <span class="section-kicker">SECTION 05</span>
                <span class="section-category-tag">STORAGE & LEDGER</span>
              </div>
              <h2 class="section-title">Physical Location & Registry Tokens</h2>
              <p class="section-desc">Physical shelf stack placement, call signature, and immutable registry ledger IDs.</p>
            </header>

            <div class="form-grid">
              <!-- Shelf -->
              <div class="field-card col-half contextual-highlight" :class="{ 'is-edited': isFieldModified('shelf') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-shelf">Shelf Location</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('shelf')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-highlight">EDITABLE</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-shelf"
                    type="text" 
                    v-model="editableBook.shelf" 
                    class="large-input font-mono font-bold" 
                    placeholder="e.g. FL-01-SH-04"
                  />
                </div>
              </div>

              <!-- Call Number -->
              <div class="field-card col-half contextual-highlight" :class="{ 'is-edited': isFieldModified('call_no') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-call-no">Call Signature Number</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('call_no')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-highlight">EDITABLE</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <input 
                    id="field-call-no"
                    type="text" 
                    v-model="editableBook.call_no" 
                    class="large-input font-mono font-bold" 
                    placeholder="e.g. EN-FIC-12.0"
                  />
                </div>
              </div>

              <!-- System Tokens (Read-Only) -->
              <div class="field-card col-quarter locked-field">
                <div class="field-card-header">
                  <label class="prominent-label-sub">System Record ID</label>
                </div>
                <div class="field-card-body">
                  <div class="static-value font-mono">{{ editableBook.record_id }}</div>
                </div>
              </div>

              <div class="field-card col-quarter locked-field">
                <div class="field-card-header">
                  <label class="prominent-label-sub">Work Matrix ID</label>
                </div>
                <div class="field-card-body">
                  <div class="static-value font-mono text-amber">#{{ editableBook.work_id }}</div>
                </div>
              </div>

              <div class="field-card col-quarter locked-field">
                <div class="field-card-header">
                  <label class="prominent-label-sub">Accession No</label>
                </div>
                <div class="field-card-body">
                  <div class="static-value font-mono text-blue">{{ editableBook.accession_no }}</div>
                </div>
              </div>

              <div class="field-card col-quarter locked-field">
                <div class="field-card-header">
                  <label class="prominent-label-sub">Serial No</label>
                </div>
                <div class="field-card-body">
                  <div class="static-value font-mono text-magenta">#{{ editableBook.serial_no }}</div>
                </div>
              </div>
            </div>
          </section>

          <!-- TAB 6 / SECTION 06: CURATORIAL REMARKS -->
          <section 
            v-show="isSectionVisible('notes', ['notes', 'remarks', 'curatorial'])"
            class="form-card-section"
          >
            <header class="section-header">
              <div class="header-badge-row">
                <span class="section-kicker">SECTION 06</span>
                <span class="section-category-tag">ARCHIVAL LOG</span>
              </div>
              <h2 class="section-title">Curatorial Remarks & Log</h2>
              <p class="section-desc">Preservation history, physical condition notes, and acquisition backstory.</p>
            </header>

            <div class="form-grid">
              <div class="field-card col-full" :class="{ 'is-edited': isFieldModified('notes') }">
                <div class="field-card-header">
                  <div class="heading-cluster">
                    <span class="heading-dot dot-amber"></span>
                    <label class="prominent-label" for="field-notes">Conservation Notes & Remarks</label>
                  </div>
                  <div class="badge-cluster">
                    <span v-if="isFieldModified('notes')" class="edited-tag">MODIFIED</span>
                    <span class="status-badge badge-neutral">OPTIONAL</span>
                  </div>
                </div>
                <div class="field-card-body">
                  <textarea 
                    id="field-notes"
                    v-model="editableBook.notes" 
                    class="large-textarea" 
                    rows="6"
                    placeholder="Record binding condition, preservation context, or curatorial restrictions..."
                  ></textarea>
                </div>
              </div>
            </div>
          </section>

        </div>
      </main>

      <!-- 3. RIGHT VIEW PANE: LIVE MODIFICATION INSPECTOR (TABBED MODE ONLY) -->
      <aside v-if="!showAllSections" class="modification-audit-pane">
        <header class="audit-pane-header">
          <div class="audit-pane-title-group">
            <span class="audit-kicker">CHANGE DETECTOR</span>
            <h3 class="audit-heading">Active Modifications</h3>
          </div>
          <span 
            class="audit-count-badge" 
            :class="modifiedFieldsList.length ? 'has-changes' : 'no-changes'"
          >
            {{ modifiedFieldsList.length }} {{ modifiedFieldsList.length === 1 ? 'FIELD' : 'FIELDS' }}
          </span>
        </header>

        <!-- No Changes Empty State -->
        <div v-if="modifiedFieldsList.length === 0" class="audit-empty-state">
          <div class="audit-pulse-icon">✓</div>
          <h4 class="empty-state-title">All Fields Pristine</h4>
          <p class="empty-state-copy">
            No uncommitted modifications detected. As you alter any field across the 6 sections, changes will be tracked here in real time.
          </p>
        </div>

        <!-- Live Changes List -->
        <div v-else class="audit-feed-scroll">
          <div class="audit-feed-summary-bar">
            <span>UNCOMMITTED SESSION DIFF</span>
            <button type="button" class="revert-all-btn" @click="revertAllModifications">
              REVERT ALL
            </button>
          </div>

          <div 
            v-for="item in modifiedFieldsList" 
            :key="item.key"
            class="diff-card"
            @click="jumpToField(item.tab, item.key)"
          >
            <div class="diff-card-top">
              <div class="diff-field-name">
                <span class="diff-bullet"></span>
                <strong>{{ item.label }}</strong>
              </div>
              <span class="diff-tab-tag">{{ item.tabLabel }}</span>
            </div>

            <div class="diff-values-matrix">
              <div class="diff-row diff-before">
                <span class="diff-label">PREV:</span>
                <span class="diff-content" :title="item.oldValue">
                  {{ item.oldValue || '[EMPTY / UNSET]' }}
                </span>
              </div>
              <div class="diff-row diff-after">
                <span class="diff-label">NEW:</span>
                <span class="diff-content" :title="item.newValue">
                  {{ item.newValue || '[CLEARED / EMPTY]' }}
                </span>
              </div>
            </div>

            <div class="diff-card-footer">
              <span class="diff-jump-hint">Click to inspect</span>
              <button 
                type="button" 
                class="diff-single-revert" 
                @click.stop="revertSingleField(item.key)"
                title="Revert this field to saved state"
              >
                Undo
              </button>
            </div>
          </div>
        </div>

        <footer class="audit-pane-footer">
          <button 
            type="button" 
            class="btn btn-filled commit-audit-btn" 
            :disabled="modifiedFieldsList.length === 0"
            @click="triggerActionConfirm('commit')"
          >
            COMMIT ({{ modifiedFieldsList.length }})
          </button>
        </footer>
      </aside>

    </div>

    <!-- TOAST NOTIFICATION -->
    <div v-if="toast" class="toast-banner-notification" :class="toast.type">
      <span class="toast-indicator"></span>
      <span class="toast-message-label">{{ toast.message }}</span>
    </div>

    <!-- CONFIRMATION / REASON MODAL -->
    <div v-if="activeModalType" class="modal-overlay-shroud">
      <div 
        class="modal-alert-box" 
        :class="activeModalType === 'commit' ? 'border-emerald' : 'border-crimson'"
      >
        <div class="modal-tag">SYSTEM_TRANSACTION_ALERT</div>
        
        <h3 class="modal-heading">
          {{ activeModalType === 'commit' ? 'CONFIRM WRITE OPERATION?' : 'ABORT CURRENT TRANSACTION?' }}
        </h3>
        
        <p class="modal-body-text">
          {{ activeModalType === 'commit' 
              ? 'You are committing new modifications to the centralized database matrix. This record will update across all client node networks.' 
              : 'You are abandoning all pending modifications. Uncommitted form changes will be completely deleted from temporary session memory.' 
          }}
        </p>

        <div v-if="activeModalType === 'commit'" class="modal-input-field-block">
          <label class="modal-input-label">SPECIFY OPERATIONAL CHANGE JUSTIFICATION</label>
          <input 
            type="text" 
            v-model="changeReason" 
            placeholder="e.g., Fixing spelling error / Updating shelf vectors..." 
            class="modal-reason-input"
          />
        </div>

        <div class="countdown-ticker-bar">
          AUTO-RESOLVING IN: <span class="ticker-value">{{ countdownTimerSeconds }}s</span>
        </div>

        <div class="modal-button-row">
          <button 
            type="button"
            class="m-btn m-btn-confirm" 
            :class="activeModalType === 'commit' ? 'bg-emerald' : 'bg-crimson'"
            @click="executeConfirmedAction"
          >
            EXECUTE
          </button>
          <button type="button" class="m-btn m-btn-dismiss" @click="closeModalPrompt">
            DISMISS
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"
import { dispatchAuditTrail } from '@/utils/audit'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const editableBook = ref<any>(null)
const pristineBook = ref<any>(null) // Baseline snapshot for delta comparison

// Navigation & UX Search
type TabKey = 'work' | 'taxonomy' | 'languages' | 'publication' | 'location' | 'notes'
const activeTab = ref<TabKey>('work')
const searchQuery = ref('')
const showAllSections = ref(false)

const activeModalType = ref<'commit' | 'abort' | null>(null)
const changeReason = ref<string>("")
const countdownTimerSeconds = ref<number>(0)
let nativeIntervalReference: any = null

interface ToastNotification {
  message: string
  type: 'success' | 'error'
}
const toast = ref<ToastNotification | null>(null)

// Taxonomy Presets
const genreGroupA = ref([
  "ADVENTURE", "BIOGRAPHY", "CLASSIC", "DETECTIVE", "FANTASY", 
  "FOLKLORE", "FOLKTALES", "HORROR", "MYSTERY", "NOVEL", 
  "POETRY", "SATIRE", "SHORT STORIES", "TEMPLE SONGS"
])

const genreGroupB = ref([
  "AETHISM", "ANIMAL HUSBANDRY", "AUTOBIOGRAPHY", "COLLECTION OF PROVERBS", 
  "COLLECTION OF WORKS", "EDUCATIONAL", "ENCYCLOPEDIA", "ENGINEERING", 
  "FORENSIC INVESTIGATIONS", "FUTURISM", "HISTORY", "HOBBY", "INVESTIGATION", 
  "MEDICINE (AYURVEDA)", "MEMOIR", "PHILATELY", "PHILOSOPHY", "POLITICS", 
  "PSYCHOLOGY", "SCIENCE", "SERVICE STORY", "STUDY", "VETERINARY"
])

const dynamicCommunityGenres = ref<string[]>([])

const selectedGroupAGenre = ref("")
const selectedGroupBGenre = ref("")
const selectedGroupCGenre = ref("")
const showCustomManualGenreField = ref(false)
const customManualGenreText = ref("")

// Typeahead suggestions
const authorSuggestions = ref<string[]>([])
const publisherSuggestions = ref<string[]>([])
const showAuthorSuggestions = ref(false)
const showPublisherSuggestions = ref(false)

let debounceAuthorTimeout: any = null
let debouncePublisherTimeout: any = null

const auditData = ref({
  deviceID: "EDITORIAL-CARDS-STATION-01",
  ip: "192.168.1.105", 
  userName: "System Archivist",
  userRole: "The Chief" 
})

// Active compiled chips from book genre string - explicitly typed string[]
const liveCompiledGenreChips = computed<string[]>(() => {
  if (!editableBook.value?.genre) return []
  return String(editableBook.value.genre)
    .split('/')
    .map((g: string) => g.trim().toUpperCase())
    .filter((g: string) => g.length > 0)
})

// Field definition schema for change detection
interface TrackedFieldConfig {
  key: string
  label: string
  tab: TabKey
  tabLabel: string
}

const trackedFieldsConfig: TrackedFieldConfig[] = [
  { key: 'title', label: 'Work Title', tab: 'work', tabLabel: '01 Core' },
  { key: 'author', label: 'Author / Creator', tab: 'work', tabLabel: '01 Core' },
  { key: 'category', label: 'Collection Category', tab: 'taxonomy', tabLabel: '02 Taxonomy' },
  { key: 'ddc', label: 'Dewey Decimal (DDC)', tab: 'taxonomy', tabLabel: '02 Taxonomy' },
  { key: 'genre', label: 'Genre Tags', tab: 'taxonomy', tabLabel: '02 Taxonomy' },
  { key: 'language', label: 'Text Language', tab: 'languages', tabLabel: '03 Lang' },
  { key: 'original_language', label: 'Original Source Language', tab: 'languages', tabLabel: '03 Lang' },
  { key: 'publisher', label: 'Imprint Publisher', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'year', label: 'Publication Year', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'isbn', label: 'ISBN Identifier', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'shelf', label: 'Shelf Location', tab: 'location', tabLabel: '05 Location' },
  { key: 'call_no', label: 'Call Signature Number', tab: 'location', tabLabel: '05 Location' },
  { key: 'notes', label: 'Conservation Notes', tab: 'notes', tabLabel: '06 Remarks' },
]

function normalizeValue(val: any): string {
  if (val === null || val === undefined) return ""
  return String(val).trim()
}

// Compute live modified fields comparing editableBook against pristineBook
const modifiedFieldsList = computed(() => {
  if (!editableBook.value || !pristineBook.value) return []

  const changes: Array<TrackedFieldConfig & { oldValue: string; newValue: string }> = []

  trackedFieldsConfig.forEach((cfg) => {
    const oldNorm = normalizeValue(pristineBook.value[cfg.key])
    const newNorm = normalizeValue(editableBook.value[cfg.key])

    if (oldNorm !== newNorm) {
      changes.push({
        ...cfg,
        oldValue: oldNorm,
        newValue: newNorm,
      })
    }
  })

  return changes
})

function isFieldModified(fieldKey: string): boolean {
  return modifiedFieldsList.value.some(item => item.key === fieldKey)
}

function tabChangesCount(tabKey: TabKey): number {
  return modifiedFieldsList.value.filter(item => item.tab === tabKey).length
}

function jumpToField(tabKey: TabKey, fieldKey: string) {
  setTab(tabKey)
  nextTick(() => {
    const el = document.getElementById(`field-${fieldKey}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.focus()
    }
  })
}

function revertSingleField(fieldKey: string) {
  if (!pristineBook.value || !editableBook.value) return
  editableBook.value[fieldKey] = pristineBook.value[fieldKey]

  if (fieldKey === 'genre') {
    parseCurrentGenresIntoDropdowns(editableBook.value.genre)
  }

  triggerToastNotification(`Field '${fieldKey}' restored to original value.`, 'success')
}

function revertAllModifications() {
  if (!pristineBook.value) return
  editableBook.value = JSON.parse(JSON.stringify(pristineBook.value))
  parseCurrentGenresIntoDropdowns(editableBook.value.genre)
  triggerToastNotification("All modifications reverted to original baseline.", "success")
}

function setTab(tabKey: TabKey) {
  activeTab.value = tabKey
  searchQuery.value = ''
}

// Determines if a section card should be shown given the current tab or active search
function isSectionVisible(sectionKey: string, fieldKeywords: string[]): boolean {
  if (searchQuery.value.trim() !== '') {
    const q = searchQuery.value.toLowerCase().trim()
    return fieldKeywords.some((keyword: string) => keyword.toLowerCase().includes(q))
  }
  if (showAllSections.value) return true
  return activeTab.value === sectionKey
}

function triggerToastNotification(message: string, type: 'success' | 'error') {
  toast.value = { message, type }
  setTimeout(() => {
    toast.value = null
  }, 4000)
}

function parseCurrentGenresIntoDropdowns(genreString: string) {
  if (!genreString) {
    selectedGroupAGenre.value = ""
    selectedGroupBGenre.value = ""
    selectedGroupCGenre.value = ""
    customManualGenreText.value = ""
    showCustomManualGenreField.value = false
    return
  }
  const currentTokens = genreString.split('/').map((g: string) => g.trim().toUpperCase())
  
  let matchedAny = false
  currentTokens.forEach((token: string) => {
    if (genreGroupA.value.includes(token)) {
      selectedGroupAGenre.value = token
      matchedAny = true
    } else if (genreGroupB.value.includes(token)) {
      selectedGroupBGenre.value = token
      matchedAny = true
    } else if (dynamicCommunityGenres.value.includes(token)) {
      selectedGroupCGenre.value = token
      matchedAny = true
    }
  })

  if (!matchedAny && genreString.trim() !== "") {
    showCustomManualGenreField.value = true
    selectedGroupCGenre.value = "CUSTOM_MANUAL_OVERRIDE"
    customManualGenreText.value = genreString
  }
}

function syncGenreSelection() {
  if (selectedGroupCGenre.value === "CUSTOM_MANUAL_OVERRIDE") {
    showCustomManualGenreField.value = true
    editableBook.value.genre = customManualGenreText.value.trim().toUpperCase() || null
    return
  }
  
  showCustomManualGenreField.value = false
  const activeSelectionArray: string[] = []
  
  if (selectedGroupAGenre.value) activeSelectionArray.push(selectedGroupAGenre.value)
  if (selectedGroupBGenre.value) activeSelectionArray.push(selectedGroupBGenre.value)
  if (selectedGroupCGenre.value && selectedGroupCGenre.value !== "CUSTOM_MANUAL_OVERRIDE") {
    activeSelectionArray.push(selectedGroupCGenre.value)
  }
  
  editableBook.value.genre = activeSelectionArray.join('/') || null
  customManualGenreText.value = editableBook.value.genre || ""
}

function syncManualGenreInput() {
  editableBook.value.genre = customManualGenreText.value.trim().toUpperCase() || null
}

function removeGenreChip(chipToRemove: string) {
  const remaining = liveCompiledGenreChips.value.filter((chip: string) => chip !== chipToRemove)
  editableBook.value.genre = remaining.join('/') || null
  if (selectedGroupAGenre.value === chipToRemove) selectedGroupAGenre.value = ""
  if (selectedGroupBGenre.value === chipToRemove) selectedGroupBGenre.value = ""
  if (selectedGroupCGenre.value === chipToRemove) selectedGroupCGenre.value = ""
}

function clearAllGenres() {
  editableBook.value.genre = null
  selectedGroupAGenre.value = ""
  selectedGroupBGenre.value = ""
  selectedGroupCGenre.value = ""
  customManualGenreText.value = ""
  showCustomManualGenreField.value = false
}

async function harvestSystemGenresMatrix() {
  try {
    const response = await axios.get('/catalogue?limit=1000')
    const items = response.data?.data || []
    const genresFound = new Set<string>()
    items.forEach((item: any) => {
      if (item.genre) {
        item.genre.split('/').forEach((g: string) => {
          const clean = g.trim().toUpperCase()
          if (clean && !genreGroupA.value.includes(clean) && !genreGroupB.value.includes(clean)) {
            genresFound.add(clean)
          }
        })
      }
    })
    dynamicCommunityGenres.value = Array.from(genresFound)
  } catch (err) {
    console.error("Failed to dynamically harvest taxonomy metrics:", err)
  }
}

function searchAuthorsDebounced() {
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  debounceAuthorTimeout = setTimeout(async () => {
    const query = editableBook.value.author?.trim() || ""
    if (query.length < 2) {
      authorSuggestions.value = []
      return
    }
    try {
      const response = await axios.get(`/catalogue/authors/search?q=${encodeURIComponent(query)}`)
      authorSuggestions.value = response.data || []
    } catch (err) {
      console.error("Author micro-lookup breakdown:", err)
    }
  }, 200)
}

function searchPublishersDebounced() {
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
  debouncePublisherTimeout = setTimeout(async () => {
    const query = editableBook.value.publisher?.trim() || ""
    if (query.length < 2) {
      publisherSuggestions.value = []
      return
    }
    try {
      const response = await axios.get(`/catalogue/publishers/search?q=${encodeURIComponent(query)}`)
      publisherSuggestions.value = response.data || []
    } catch (err) {
      console.error("Publisher micro-lookup breakdown:", err)
    }
  }, 200)
}

function selectSuggestion(type: 'author' | 'publisher', value: string) {
  if (type === 'author') {
    editableBook.value.author = value
    authorSuggestions.value = []
    showAuthorSuggestions.value = false
  } else {
    editableBook.value.publisher = value
    publisherSuggestions.value = []
    showPublisherSuggestions.value = false
  }
}

function hideSuggestionsWithDelay(type: 'author' | 'publisher') {
  setTimeout(() => {
    if (type === 'author') showAuthorSuggestions.value = false
    else showPublisherSuggestions.value = false
  }, 250)
}

async function fetchRecordData() {
  loading.value = true
  const id = route.params.id
  try {
    await harvestSystemGenresMatrix()
    const response = await axios.get(`/catalogue/${id}`)
    editableBook.value = { ...response.data }
    // Save pristine deep copy for change detection
    pristineBook.value = JSON.parse(JSON.stringify(response.data))
    
    if (editableBook.value) {
      parseCurrentGenresIntoDropdowns(editableBook.value.genre)
    }
  } catch (err) {
    console.error("Database loading exception:", err)
  } finally {
    loading.value = false
  }
}

function triggerActionConfirm(actionType: 'commit' | 'abort') {
  if (actionType === 'commit') {
    // Validate mandatory Text Language
    if (!editableBook.value?.language || !editableBook.value.language.trim()) {
      triggerToastNotification("Validation Error: Text Language is required.", "error")
      setTab('languages')
      return
    }

    // Validate mandatory Title
    if (!editableBook.value?.title || !editableBook.value.title.trim()) {
      triggerToastNotification("Validation Error: Book Title cannot be empty.", "error")
      setTab('work')
      return
    }
  }

  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  
  activeModalType.value = actionType
  changeReason.value = ""
  countdownTimerSeconds.value = 15
  
  nativeIntervalReference = setInterval(() => {
    countdownTimerSeconds.value--
    if (countdownTimerSeconds.value <= 0) {
      clearInterval(nativeIntervalReference)
      executeConfirmedAction()
    }
  }, 1000)
}

function executeConfirmedAction() {
  const targetAction = activeModalType.value
  
  if (targetAction === 'commit') {
    saveRecord()
  } else if (targetAction === 'abort') {
    cancelEdit()
  }
  closeModalPrompt()
}

function closeModalPrompt() {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  activeModalType.value = null
}

async function saveRecord() {
  const id = route.params.id || editableBook.value?.serial_no

  if (!editableBook.value?.language || !editableBook.value.language.trim()) {
    triggerToastNotification("Validation Error: Text Language is required.", "error")
    setTab('languages')
    return
  }

  if (!editableBook.value?.title || !editableBook.value.title.trim()) {
    triggerToastNotification("Validation Error: Book Title cannot be empty.", "error")
    setTab('work')
    return
  }

  try {
    const operationalReason = changeReason.value.trim() || "Routine operational adjustment"
    const token = authStore.accessToken || authStore.access_token
    
    // 1. Database update with Auth & Reason headers
    await axios.patch(`/catalogue/${id}`, editableBook.value, {
      headers: {
        'X-Change-Reason': operationalReason,
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    })
    
    // 2. Client audit telemetry (Fail-soft)
    try {
      await dispatchAuditTrail(
        'UPDATE',
        'CATALOGUE',
        id,
        `Updated record details for ${editableBook.value.title}`,
        operationalReason,
        null,
        editableBook.value
      )
    } catch (auditErr) {
      console.warn("Client audit telemetry skipped:", auditErr)
    }
    
    triggerToastNotification("Authority modifications saved successfully.", "success")
    
    setTimeout(() => {
      router.push(`/details/${id}`)
    }, 1200)
  } catch (err) {
    console.error("Transaction commit rejected:", err)
    triggerToastNotification("Write Failure: Transaction rejected by registry.", "error")
  }
}

function cancelEdit() {
  router.push(`/details/${route.params.id}`)
}

onBeforeUnmount(() => {
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
})

onMounted(() => fetchRecordData())
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* =========================================================
   BASE LAYOUT
========================================================= */
.control-panel-layout {
  background-color: #0b0c10;
  color: #f1f5f9;
  position: fixed !important;
  top: 0 !important; left: 0 !important;
  width: 100vw !important; height: 100vh !important;
  z-index: 9999 !important;
  display: flex; 
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  margin: 0 !important; 
  padding: 0 !important;
}

.panel-container {
  display: flex;
  width: 100% !important; 
  height: 100% !important;
  margin: 0 !important; 
  padding: 0 !important;
}

/* =========================================================
   1. LEFT IDENTITY & NAVIGATION SIDEBAR
========================================================= */
.identity-anchor-panel {
  width: 330px;
  background-color: #07080b !important;
  border-right: 1px solid #1e222b !important;
  padding: 28px 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow-y: auto;
}

.panel-badge-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.panel-badge {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 1.8px;
  font-family: 'JetBrains Mono', monospace;
}

.rank-badge {
  color: #34d399;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  background: rgba(16, 185, 129, 0.15);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.hero-identity-block {
  margin-bottom: 20px;
  border-bottom: 1px solid #1e222b;
  padding-bottom: 18px;
}

.meta-label {
  font-size: 10px;
  color: #94a3b8;
  letter-spacing: 1.2px;
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}

.display-title {
  font-family: 'Cinzel', serif;
  font-size: 20px;
  font-weight: 800;
  line-height: 1.3;
  color: #ffffff;
  margin: 0 0 8px 0;
  word-break: break-word;
}

.display-author {
  font-size: 12px;
  color: #94a3b8;
  margin: 0 0 14px 0;
}

.display-author strong {
  color: #f1f5f9;
}

.identity-tokens-dock {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.token-pill {
  background: #11131a;
  border: 1px solid #232834;
  padding: 6px 8px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.t-key {
  font-size: 8px;
  color: #64748b;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.t-val {
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'JetBrains Mono', monospace;
}

/* Tab Navigation Buttons */
.sidebar-tab-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: auto;
}

.tab-nav-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 10px 14px;
  color: #94a3b8;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  text-align: left;
  position: relative;
  transition: all 0.15s ease;
}

.tab-indicator {
  width: 4px;
  height: 0;
  border-radius: 99px;
  background-color: #38bdf8;
  position: absolute;
  left: 4px;
  transition: height 0.2s ease;
}

.tab-nav-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #ffffff;
}

.tab-nav-btn.active {
  background: #171b24;
  border-color: #2b3242;
  color: #ffffff;
  font-weight: 700;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.tab-nav-btn.active .tab-indicator {
  height: 18px;
}

.tab-num {
  font-size: 10px;
  color: #64748b;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.tab-nav-btn.active .tab-num {
  color: #38bdf8;
}

.tab-label {
  flex-grow: 1;
}

.tab-change-dot {
  background: #fbbf24;
  color: #0b0c10;
  font-size: 10px;
  font-weight: 800;
  border-radius: 99px;
  padding: 2px 6px;
  line-height: 1;
}

/* Actions */
.panel-actions-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 18px;
  border-top: 1px solid #1e222b;
}

.commit-count-pill {
  background: #0b0c10;
  color: #34d399;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 99px;
  margin-left: 6px;
}

.btn {
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-filled {
  background-color: #f1f5f9;
  color: #0b0c10;
}

.btn-filled:hover {
  background-color: #ffffff;
  box-shadow: 0 4px 14px rgba(255, 255, 255, 0.2);
}

.btn-outline {
  border: 1px solid #333a4a;
  color: #cbd5e1;
  background: transparent;
}

.btn-outline:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: #ffffff;
  border-color: #64748b;
}

/* =========================================================
   2. CENTER FORM WORKSPACE
========================================================= */
.form-feed-column {
  flex-grow: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #0d0f14;
  overflow: hidden;
}

/* TOP SEARCH / UTILITY BAR */
.workspace-top-bar {
  padding: 14px 32px;
  border-bottom: 1px solid #1e222b;
  background-color: #10121a;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.field-finder-wrap {
  position: relative;
  max-width: 440px;
  width: 100%;
  display: flex;
  align-items: center;
}

.finder-icon {
  position: absolute;
  left: 14px;
  font-size: 13px;
  opacity: 0.7;
}

.finder-input {
  width: 100%;
  background: #171a23;
  border: 1px solid #282e3c;
  border-radius: 6px;
  padding: 10px 38px;
  color: #ffffff;
  font-family: inherit;
  font-size: 13px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.finder-input:focus {
  outline: none;
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
}

.finder-clear-btn {
  position: absolute;
  right: 12px;
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 13px;
}

.finder-clear-btn:hover {
  color: #ffffff;
}

.workspace-view-controls {
  display: flex;
  align-items: center;
  gap: 14px;
}

.finder-matches-tag {
  font-size: 11px;
  font-weight: 700;
  color: #38bdf8;
  letter-spacing: 0.5px;
}

.view-toggle-btn {
  background: #171a23;
  border: 1px solid #282e3c;
  color: #cbd5e1;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: 0.5px;
  transition: all 0.15s ease;
}

.view-toggle-btn:hover {
  border-color: #475569;
  color: #ffffff;
  background-color: #1f2330;
}

/* SCROLL WRAPPER */
.form-scroll-wrapper {
  flex-grow: 1;
  overflow-y: auto;
  padding: 28px 32px 80px 32px;
  max-width: 900px;
  box-sizing: border-box;
}

.form-scroll-wrapper::-webkit-scrollbar {
  width: 6px;
}
.form-scroll-wrapper::-webkit-scrollbar-track {
  background: #0d0f14;
}
.form-scroll-wrapper::-webkit-scrollbar-thumb {
  background: #232834;
  border-radius: 3px;
}

/* =========================================================
   FORM SECTION CARDS
========================================================= */
.form-card-section {
  background-color: #13161f;
  border: 1px solid #232733;
  border-radius: 12px;
  padding: 24px 28px;
  margin-bottom: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}

.section-header {
  border-bottom: 1px solid #232733;
  padding-bottom: 14px;
  margin-bottom: 20px;
}

.header-badge-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.section-kicker {
  font-size: 10px;
  font-weight: 800;
  color: #34d399;
  letter-spacing: 1.8px;
  font-family: 'JetBrains Mono', monospace;
}

.section-category-tag {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 1px;
  background: #1a1e2a;
  padding: 3px 8px;
  border-radius: 4px;
}

.section-title {
  font-size: 19px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 6px 0;
  letter-spacing: -0.2px;
}

.section-desc {
  font-size: 12px;
  color: #94a3b8;
  margin: 0;
  line-height: 1.4;
}

/* FORM GRID */
.form-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 18px;
}

.col-full { grid-column: span 12; }
.col-half { grid-column: span 6; }
.col-third { grid-column: span 4; }
.col-quarter { grid-column: span 3; }

/* =========================================================
   TWO-TIER FIELD CARD (VIBRANT GOLD HEADINGS)
========================================================= */
.field-card {
  display: flex;
  flex-direction: column;
  background-color: #161a25;
  border: 1px solid #293042;
  border-radius: 8px;
  overflow: hidden;
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.field-card:focus-within {
  border-color: #fbbf24 !important;
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.2);
}

.field-card.required-field {
  border-left: 5px solid #fbbf24;
}

.field-card.contextual-highlight {
  border-left: 5px solid #38bdf8;
}

.field-card.is-edited {
  border-color: #fbbf24;
  box-shadow: 0 0 12px rgba(251, 191, 36, 0.15);
}

.field-card.locked-field {
  background-color: #10121a;
  border-color: #1e2330;
}

.border-highlight-amber {
  border-color: rgba(245, 158, 11, 0.5) !important;
}

/* HEADER STRIP */
.field-card-header {
  background-color: #181c28;
  border-bottom: 1px solid #283042;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.heading-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge-cluster {
  display: flex;
  align-items: center;
  gap: 6px;
}

.edited-tag {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.4);
  font-size: 9px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}

.heading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-amber {
  background-color: #fbbf24;
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.7);
}

.dot-magenta {
  background-color: #f472b6;
  box-shadow: 0 0 8px rgba(244, 114, 182, 0.7);
}

/* PROMINENT HEADING LABELS (15px BOLD ELECTRIC AMBER) */
.prominent-label {
  font-size: 15px;
  font-weight: 800;
  color: #fbbf24 !important;
  letter-spacing: 0.2px;
  cursor: pointer;
  line-height: 1.2;
}

.prominent-label-sub {
  font-size: 13px;
  font-weight: 800;
  color: #fbbf24 !important;
  letter-spacing: 0.2px;
}

/* STATUS BADGES */
.status-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 3px 7px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  font-family: 'JetBrains Mono', monospace;
}

.badge-mandatory {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.35);
}

.badge-neutral {
  background: #252c3c;
  color: #94a3b8;
  border: 1px solid #333c50;
}

.badge-highlight {
  background: rgba(56, 189, 248, 0.25);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.4);
}

/* INPUT BODY STRIP */
.field-card-body {
  background-color: #0f121a;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
}

.field-note {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
  line-height: 1.4;
}

/* INPUT CONTROLS */
.large-input {
  background: transparent;
  border: none;
  color: #ffffff;
  font-family: inherit;
  font-size: 15px;
  padding: 4px 0;
  width: 100%;
}

.large-input:focus {
  outline: none;
}

.large-select {
  background: transparent;
  border: none;
  color: #ffffff;
  font-family: inherit;
  font-size: 15px;
  width: 100%;
  padding: 4px 0;
  cursor: pointer;
}

.large-select:focus {
  outline: none;
}

.large-select option {
  background-color: #171b26;
  color: #ffffff;
}

.large-textarea {
  background: transparent;
  border: none;
  color: #f1f5f9;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  min-height: 120px;
  width: 100%;
  box-sizing: border-box;
  padding-top: 4px;
}

.large-textarea:focus {
  outline: none;
}

.static-value {
  font-size: 13px;
  font-weight: 700;
  padding: 4px 0;
}

/* GENRE CHIP ASSEMBLY DOCK */
.layout-dock {
  background-color: transparent;
}

.chip-assembly-dock {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 30px;
  align-items: center;
}

.active-badge-chip {
  font-size: 11px;
  font-weight: 700;
  background-color: rgba(236, 72, 153, 0.18);
  border: 1px solid rgba(236, 72, 153, 0.4);
  color: #f472b6;
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.chip-remove {
  background: transparent;
  border: none;
  color: #f472b6;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0;
}

.chip-remove:hover {
  color: #ffffff;
}

.clear-inline-btn {
  background: transparent;
  border: none;
  color: #f472b6;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}

.dock-empty-text {
  font-size: 12px;
  color: #64748b;
  font-style: italic;
}

/* TYPEAHEAD DROPDOWN */
.relative-position {
  position: relative;
}

.typeahead-overlay-tray {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  background-color: #131722;
  border: 1px solid #333a4d;
  border-radius: 6px;
  margin-top: 6px;
  max-height: 180px;
  overflow-y: auto;
  z-index: 99;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
}

.typeahead-node {
  padding: 10px 14px;
  font-size: 13px;
  color: #f1f5f9;
  cursor: pointer;
  transition: background 0.15s ease;
  text-align: left;
}

.typeahead-node:hover {
  background-color: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
}

/* =========================================================
   3. RIGHT VIEW PANE: MODIFICATION AUDITOR
========================================================= */
.modification-audit-pane {
  width: 320px;
  background-color: #08090d;
  border-left: 1px solid #1e222b;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100%;
  overflow: hidden;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
}

.audit-pane-header {
  padding: 20px 20px 16px 20px;
  border-bottom: 1px solid #1e222b;
  background: #0d0f15;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.audit-kicker {
  font-size: 9px;
  font-weight: 800;
  color: #fbbf24;
  letter-spacing: 1.5px;
  display: block;
  margin-bottom: 3px;
}

.audit-heading {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.2px;
}

.audit-count-badge {
  font-size: 10px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 99px;
  font-family: 'JetBrains Mono', monospace;
}

.audit-count-badge.has-changes {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.4);
}

.audit-count-badge.no-changes {
  background: rgba(100, 116, 139, 0.15);
  color: #64748b;
  border: 1px solid rgba(100, 116, 139, 0.25);
}

/* EMPTY STATE */
.audit-empty-state {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  text-align: center;
}

.audit-pulse-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 16px;
}

.empty-state-title {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.empty-state-copy {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  margin: 0;
}

/* FEED OF MODIFICATIONS */
.audit-feed-scroll {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.audit-feed-scroll::-webkit-scrollbar {
  width: 5px;
}
.audit-feed-scroll::-webkit-scrollbar-track {
  background: #08090d;
}
.audit-feed-scroll::-webkit-scrollbar-thumb {
  background: #232834;
  border-radius: 3px;
}

.audit-feed-summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.8px;
  padding-bottom: 4px;
}

.revert-all-btn {
  background: transparent;
  border: none;
  color: #f87171;
  font-size: 10px;
  font-weight: 800;
  cursor: pointer;
  letter-spacing: 0.5px;
}

.revert-all-btn:hover {
  text-decoration: underline;
  color: #ef4444;
}

/* INDIVIDUAL DIFF CARD */
.diff-card {
  background: #11141c;
  border: 1px solid #232836;
  border-radius: 8px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.diff-card:hover {
  border-color: #fbbf24;
  background: #151922;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  transform: translateY(-1px);
}

.diff-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.diff-field-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #f8fafc;
}

.diff-bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fbbf24;
  box-shadow: 0 0 6px rgba(251, 191, 36, 0.6);
}

.diff-tab-tag {
  font-size: 9px;
  font-weight: 700;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.diff-values-matrix {
  background: #090a0f;
  border: 1px solid #1c202a;
  border-radius: 6px;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.diff-row {
  display: flex;
  gap: 6px;
  font-size: 11px;
  line-height: 1.4;
  align-items: baseline;
}

.diff-label {
  font-size: 9px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  width: 38px;
  flex-shrink: 0;
}

.diff-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-grow: 1;
}

.diff-before {
  color: #94a3b8;
}

.diff-before .diff-label {
  color: #64748b;
}

.diff-before .diff-content {
  text-decoration: line-through;
  opacity: 0.8;
}

.diff-after {
  color: #fbbf24;
  font-weight: 600;
}

.diff-after .diff-label {
  color: #fbbf24;
}

.diff-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 2px;
}

.diff-jump-hint {
  font-size: 10px;
  color: #64748b;
  font-style: italic;
}

.diff-single-revert {
  background: transparent;
  border: 1px solid #283042;
  color: #94a3b8;
  border-radius: 4px;
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.diff-single-revert:hover {
  border-color: #f87171;
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.audit-pane-footer {
  padding: 16px 20px;
  border-top: 1px solid #1e222b;
  background: #0d0f15;
}

.commit-audit-btn {
  width: 100%;
}

.commit-audit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

/* =========================================================
   COLOR UTILITIES
========================================================= */
.text-amber { color: #fbbf24 !important; }
.text-blue { color: #38bdf8 !important; }
.text-magenta { color: #f472b6 !important; }
.font-mono { font-family: 'JetBrains Mono', monospace; }
.font-bold { font-weight: 700; }

/* =========================================================
   MODAL & TOAST
========================================================= */
.toast-banner-notification {
  position: fixed;
  top: 24px;
  right: 24px;
  padding: 14px 22px;
  border-radius: 6px;
  background-color: #171a23;
  border: 1px solid #282e3c;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 20000;
  font-size: 13px;
  font-weight: 600;
  animation: slideInToast 0.3s cubic-bezier(0.1, 0.8, 0.3, 1);
}

.toast-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.toast-banner-notification.success {
  border-left: 4px solid #34d399;
}
.toast-banner-notification.success .toast-indicator {
  background-color: #34d399;
}

.toast-banner-notification.error {
  border-left: 4px solid #ef4444;
}
.toast-banner-notification.error .toast-indicator {
  background-color: #ef4444;
}

.toast-message-label {
  color: #ffffff;
}

@keyframes slideInToast {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.modal-overlay-shroud {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background-color: rgba(7, 8, 11, 0.85);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-alert-box {
  background-color: #141722;
  border-top: 4px solid #282e3c;
  padding: 36px;
  border-radius: 8px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
}

.border-emerald { border-top-color: #34d399; }
.border-crimson { border-top-color: #ef4444; }

.modal-tag {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 2px;
  margin-bottom: 12px;
  font-family: 'JetBrains Mono', monospace;
}

.modal-heading {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 14px 0;
}

.modal-body-text {
  font-size: 13px;
  line-height: 1.6;
  color: #94a3b8;
  margin: 0 0 20px 0;
}

.modal-input-field-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.modal-input-label {
  font-size: 11px;
  font-weight: 700;
  color: #f59e0b;
  letter-spacing: 1px;
}

.modal-reason-input {
  background-color: #0d0f15;
  border: 1px solid #282e3c;
  border-radius: 4px;
  padding: 11px 14px;
  font-family: inherit;
  font-size: 14px;
  color: #ffffff;
  width: 100%;
  box-sizing: border-box;
}

.modal-reason-input:focus {
  outline: none;
  border-color: #f59e0b;
}

.countdown-ticker-bar {
  background-color: #0d0f15;
  border: 1px solid #1e2330;
  padding: 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-align: center;
  margin-bottom: 24px;
  letter-spacing: 0.5px;
}

.ticker-value {
  color: #ffffff;
}

.modal-button-row {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
}

.m-btn {
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 11px 22px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.bg-emerald {
  background-color: #34d399;
  color: #0b0c10;
}
.bg-emerald:hover {
  background-color: #10b981;
}

.bg-crimson {
  background-color: #ef4444;
  color: #ffffff;
}
.bg-crimson:hover {
  background-color: #dc2626;
}

.m-btn-dismiss {
  background-color: transparent;
  border: 1px solid #333a4d;
  color: #cbd5e1;
}

.vault-loader {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background-color: #0b0c10;
}

.minimal-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(226, 228, 233, 0.15);
  border-top-color: #f1f5f9;
  border-radius: 50%;
  animation: spin 0.7s infinite linear;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}
</style>\n