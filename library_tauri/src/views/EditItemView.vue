<template>
  <main class="edit-page">
    <div v-if="loading" class="loading-state">
      <span class="loader"></span>
      <p>Loading catalogue record…</p>
    </div>
    
    <section v-else-if="loadError" class="load-error" role="alert">
      <h2>Unable to load this record</h2>
      <p>{{ loadError }}</p>
      <button class="button button-primary" type="button" @click="fetchRecordData">Try again</button>
    </section>

    <template v-else-if="editableBook">
      <!-- Streamlined Sticky Topbar -->
      <header class="topbar">
        <div class="topbar-left">
          <button class="button button-back" type="button" @click="handleBackNavigation" title="Back to Dossier (Esc)">
            <span class="btn-glyph">←</span>
            <span>Back</span>
            <kbd class="kbd-badge">Esc</kbd>
          </button>
          <div class="topbar-title">
            <span class="eyebrow">CATALOGUE MANAGEMENT</span>
            <h1>Edit Record</h1>
          </div>
        </div>

        <div class="topbar-meta">
            <button class="button-back btn-sm" type="button" @click="navigateSection('prev')" title="Previous Section (←)">←</button>
            <span class="record-pill">{{ currentTabLabel }}</span>
            <button class="button-back btn-sm" type="button" @click="navigateSection('next')" title="Next Section (→)">→</button>
            <span class="status-dot"></span>
            <span>Editing Mode</span>
          </div>
      </header>

      <!-- Compact Identity Bar -->
      <section class="record-identity-bar" aria-label="Read-only record identifiers">
        <div class="identity-item">
          <span>Serial No</span>
          <strong>{{ editableBook.serial_no || '—' }}</strong>
        </div>
        <div class="identity-item">
          <span>Accession ID</span>
          <strong class="highlight-code">{{ editableBook.accession_no || '—' }}</strong>
        </div>
        <div class="identity-item">
          <span>Record ID</span>
          <strong>{{ editableBook.record_id || '—' }}</strong>
        </div>
        <div class="identity-item">
          <span>Work ID</span>
          <strong>#{{ editableBook.work_id || '—' }}</strong>
        </div>
      </section>

      <div class="workspace">
        <!-- Sidebar Navigation -->
        <aside class="sidebar">
          <div class="sidebar-intro">
            <span class="eyebrow">WORKSPACE</span>
            <h2>Record Details</h2>
            <p>Update bibliographic parameters and review before commit.</p>
          </div>

          <label class="search-label" for="field-search">Find a field</label>
          <div class="search-wrap">
            <span aria-hidden="true">⌕</span>
            <input id="field-search" v-model="searchQuery" placeholder="Search fields…" />
          </div>

          <nav class="section-nav" aria-label="Edit sections">
            <button 
              v-for="item in navTabs" 
              :key="item.key" 
              type="button" 
              class="nav-item" 
              :class="{ active: activeTab === item.key }" 
              @click="setTab(item.key as TabKey)"
            >
              <span class="nav-number">{{ item.number }}</span>
              <span class="nav-copy">
                <strong>{{ item.label }}</strong>
                <small>{{ item.hint }}</small>
              </span>
              <span v-if="tabChangesCount(item.key as TabKey)" class="change-count">{{ tabChangesCount(item.key as TabKey) }}</span>
              <span v-else class="nav-arrow">›</span>
            </button>
          </nav>

          <div class="sidebar-bottom">
            <div class="change-summary">
              <span class="summary-icon">✳</span>
              <div>
                <strong>{{ modifiedFieldsList.length }} changes</strong>
                <small>Compared with pristine</small>
              </div>
            </div>
            <button class="text-button" type="button" :disabled="!modifiedFieldsList.length" @click="revertAllModifications">
              Reset all changes
            </button>
          </div>
        </aside>

        <!-- Form Area -->
        <section class="editor-area">
          <div class="editor-heading">
            <div>
              <span class="eyebrow">CATALOGUE / EDIT</span>
              <h2>{{ currentTabLabel }}</h2>
              <p>Fields marked with <span class="required-star">*</span> are mandatory.</p>
            </div>
            <div class="heading-actions">
              <span class="change-chip" :class="{ 'has-changes': modifiedFieldsList.length }">
                {{ modifiedFieldsList.length ? `${modifiedFieldsList.length} modified` : 'No changes yet' }}
              </span>
              <button class="button button-quiet" type="button" @click="showAllSections = !showAllSections; searchQuery = ''">
                {{ showAllSections ? 'Show one section' : 'View all sections' }}
              </button>
            </div>
          </div>

          <div v-if="searchQuery.trim()" class="search-results-note">
            Showing fields matching “{{ searchQuery }}”. <button type="button" @click="searchQuery = ''">Clear search</button>
          </div>

          <div class="form-stack">
            <!-- 01 Core Details -->
            <section v-if="isSectionVisible('work', ['title', 'author', 'creator', 'core details', 'work_nature'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">01</div>
                <div><h3>Core Details</h3><p>Main identifying details for this literary work.</p></div>
              </div>
              <div class="field-grid">
                <div id="wrap-title" class="field-block span-2" :class="{ 'field-modified': isFieldModified('title') }">
                  <div class="label-line">
                    <label for="field-title">Work Title <span class="required-star">*</span></label>
                    <span v-if="isFieldModified('title')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-title" v-model="editableBook.title" class="input-control" placeholder="Enter complete title" required />
                  <div v-if="isFieldModified('title')" class="field-footer">
                    <span>Original: {{ pristineBook.title || 'Empty' }}</span>
                    <button type="button" @click="revertSingleField('title')">Undo</button>
                  </div>
                </div>

                <div id="wrap-author" class="field-block span-2 relative-position" :class="{ 'field-modified': isFieldModified('author') }">
                  <div class="label-line">
                    <label for="field-author">Author / Creator</label>
                    <span v-if="isFieldModified('author')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-author" 
                    v-model="editableBook.author" 
                    class="input-control" 
                    autocomplete="off" 
                    placeholder="Search or enter author name…" 
                    @input="searchAuthorsDebounced" 
                    @focus="searchAuthorsDebounced" 
                    @blur="hideSuggestionsWithDelay('author')" 
                  />
                  <div v-if="showAuthorSuggestions && authorSuggestions.length" class="suggestion-list">
                    <button v-for="person in authorSuggestions" :key="person.authority_id" type="button" class="suggestion-item" @mousedown.prevent="selectSuggestion('author', person)">
                      <span class="suggestion-avatar">{{ (person.preferred_name || '?').slice(0, 1) }}</span>
                      <span class="suggestion-copy">
                        <strong>{{ person.preferred_name }}</strong>
                        <small>{{ person.authority_code }}<span v-if="person.full_name"> · {{ person.full_name }}</span></small>
                      </span>
                      <span class="suggestion-status">{{ person.status }}</span>
                    </button>
                  </div>
                  <div v-if="isFieldModified('author')" class="field-footer">
                    <span>Original: {{ pristineBook.author || 'Empty' }}</span>
                    <button type="button" @click="revertSingleField('author')">Undo</button>
                  </div>
                </div>

                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('work_nature') }">
                  <div class="label-line">
                    <label for="field-work-nature">Work Nature</label>
                    <span v-if="isFieldModified('work_nature')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-work-nature" v-model="editableBook.work_nature" class="input-control" placeholder="e.g. Novel, Monograph, Play, Anthology, Translation" />
                </div>
              </div>
            </section>

            <!-- 02 Classification & Taxonomy -->
            <section v-if="isSectionVisible('taxonomy', ['classification', 'category', 'ddc', 'genre', 'taxonomy'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">02</div>
                <div><h3>Classification</h3><p>Taxonomy, Dewey Decimal standards, and subject genres.</p></div>
              </div>
              <div class="field-grid">
                <!-- Category Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('category') }">
                  <div class="label-line">
                    <label for="field-category">Collection Category</label>
                    <span v-if="isFieldModified('category')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-category" v-model="categorySelectValue" class="input-control" @change="handleCategorySelectChange">
                    <option value="">Select Category</option>
                    <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
                    <option value="__CUSTOM__">Other (Enter Manually)…</option>
                  </select>
                  <input 
                    v-if="categorySelectValue === '__CUSTOM__'" 
                    v-model="editableBook.category" 
                    class="input-control custom-subfield" 
                    placeholder="Type custom category name…" 
                  />
                </div>

                <!-- Strict DDC with regex validation -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('ddc') }">
                  <div class="label-line">
                    <label for="field-ddc">Dewey Decimal (DDC)</label>
                    <span v-if="!isDdcValid" class="validation-error-tag">Format: 3 digits [.decimals]</span>
                    <span v-else-if="isFieldModified('ddc')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-ddc" 
                    v-model="editableBook.ddc" 
                    class="input-control" 
                    :class="{ 'input-invalid': !isDdcValid }" 
                    placeholder="e.g. 823.914 or 894.812" 
                    maxlength="14" 
                  />
                  <p class="field-help">Strict 3-digit class followed by optional decimals (e.g. 894.812 for Malayalam).</p>
                </div>

                <!-- Unified Genre Multi-Tag Combobox -->
                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('genre') }">
                  <div class="label-line">
                    <label>Genre Tags (Multi-Select Combobox)</label>
                    <span v-if="isFieldModified('genre')" class="modified-label">Modified</span>
                  </div>
                  
                  <!-- Selected Chips -->
                  <div class="genre-chips">
                    <span v-for="chip in currentGenreList" :key="chip" class="genre-chip">
                      {{ chip }}
                      <button type="button" :aria-label="`Remove ${chip}`" @click="removeGenreChip(chip)">×</button>
                    </span>
                    <button v-if="currentGenreList.length" class="clear-genres" type="button" @click="clearAllGenres">Clear all</button>
                  </div>

                  <!-- Tag Input / Suggestions -->
                  <div class="combobox-entry-row">
                    <input 
                      v-model="newGenreInput" 
                      class="input-control" 
                      placeholder="Type a genre tag and press Enter or comma…" 
                      @keydown.enter.prevent="addGenreFromInput" 
                      @keydown.,.prevent="addGenreFromInput" 
                    />
                    <button class="button button-quiet" type="button" @click="addGenreFromInput">Add Tag</button>
                  </div>

                  <!-- Suggested Quick Badges -->
                  <div class="quick-genre-hints">
                    <small>Quick Pick:</small>
                    <button 
                      v-for="preset in popularIndianGenres" 
                      :key="preset" 
                      type="button" 
                      class="quick-pill" 
                      :class="{ selected: currentGenreList.includes(preset) }" 
                      @click="toggleGenrePill(preset)"
                    >
                      + {{ preset }}
                    </button>
                  </div>

                  <div v-if="isFieldModified('genre')" class="field-footer">
                    <span>Original: {{ pristineBook.genre || 'Empty' }}</span>
                    <button type="button" @click="revertSingleField('genre')">Undo</button>
                  </div>
                </div>
              </div>
            </section>

            <!-- 03 Languages -->
            <section v-if="isSectionVisible('languages', ['language', 'original language', 'languages'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">03</div>
                <div><h3>Languages</h3><p>Text edition language and source translations.</p></div>
              </div>
              <div class="field-grid">
                <div class="field-block" :class="{ 'field-modified': isFieldModified('language') }">
                  <div class="label-line">
                    <label for="field-language">Text Language <span class="required-star">*</span></label>
                    <span v-if="isFieldModified('language')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-language" v-model="editableBook.language" class="input-control" required>
                    <option value="">Select Language</option>
                    <option v-for="lang in availableLanguages" :key="lang" :value="lang">{{ lang }}</option>
                  </select>
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('original_language') }">
                  <div class="label-line">
                    <label for="field-orig-lang">Original Source Language</label>
                    <span v-if="isFieldModified('original_language')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-orig-lang" v-model="editableBook.original_language" class="input-control">
                    <option value="">Select Language (If translated)</option>
                    <option v-for="lang in availableLanguages" :key="'orig-' + lang" :value="lang">{{ lang }}</option>
                  </select>
                </div>
              </div>
            </section>

            <!-- 04 Publication & Standards -->
            <section v-if="isSectionVisible('publication', ['publication', 'publisher', 'year', 'isbn', 'imprint', 'lccn', 'oclc_no', 'edition_statement', 'series_title', 'series_volume'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">04</div>
                <div><h3>Publication & Standards</h3><p>Imprint metadata, numeric year, and ISBN formatters.</p></div>
              </div>
              <div class="field-grid">
                <div class="field-block relative-position" :class="{ 'field-modified': isFieldModified('publisher') }">
                  <div class="label-line">
                    <label for="field-publisher">Publisher / Imprint</label>
                    <span v-if="isFieldModified('publisher')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-publisher" 
                    v-model="editableBook.publisher" 
                    class="input-control" 
                    autocomplete="off" 
                    placeholder="e.g. DC Books, Mathrubhumi, Oxford" 
                    @input="searchPublishersDebounced" 
                    @focus="searchPublishersDebounced" 
                    @blur="hideSuggestionsWithDelay('publisher')" 
                  />
                  <div v-if="showPublisherSuggestions && publisherSuggestions.length" class="suggestion-list">
                    <button v-for="pub in publisherSuggestions" :key="pub" type="button" class="suggestion-item" @mousedown.prevent="selectSuggestion('publisher', pub)">
                      <span class="suggestion-copy"><strong>{{ pub }}</strong></span>
                      <span class="suggestion-status">Select</span>
                    </button>
                  </div>
                </div>

                <!-- Numeric only year -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('year') }">
                  <div class="label-line">
                    <label for="field-year">Publication Year</label>
                    <span v-if="isFieldModified('year')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-year" 
                    v-model="editableBook.year" 
                    class="input-control" 
                    type="text" 
                    inputmode="numeric" 
                    maxlength="4" 
                    placeholder="YYYY" 
                    @input="enforceNumbersOnly($event, 'year', 4)" 
                  />
                </div>

                <!-- Structured ISBN -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('isbn') }">
                  <div class="label-line">
                    <label for="field-isbn">ISBN (10 or 13 digits)</label>
                    <span v-if="!isIsbnValid" class="validation-error-tag">Invalid ISBN</span>
                    <span v-else-if="isFieldModified('isbn')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-isbn" 
                    v-model="editableBook.isbn" 
                    class="input-control" 
                    :class="{ 'input-invalid': !isIsbnValid }" 
                    placeholder="e.g. 978-81-264-1234-5" 
                    @blur="formatIsbnOnBlur" 
                  />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('edition_statement') }">
                  <div class="label-line">
                    <label for="field-edition">Edition Statement</label>
                    <span v-if="isFieldModified('edition_statement')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-edition" v-model="editableBook.edition_statement" class="input-control" placeholder="e.g. 1st Edition, Revised, Diamond Jubilee Ed." />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('series_title') }">
                  <div class="label-line">
                    <label for="field-series-title">Academic Series Title</label>
                    <span v-if="isFieldModified('series_title')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-series-title" v-model="editableBook.series_title" class="input-control" placeholder="Series name if part of an imprint series" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('series_volume') }">
                  <div class="label-line">
                    <label for="field-series-vol">Series Volume / No.</label>
                    <span v-if="isFieldModified('series_volume')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-series-vol" v-model="editableBook.series_volume" class="input-control" placeholder="e.g. Vol. 2" />
                </div>

                <!-- Expandable LCCN / OCLC Drawer -->
                <div class="field-block span-2">
                  <details class="advanced-drawer">
                    <summary>External Bibliographic Identifiers (LCCN / OCLC WorldCat)</summary>
                    <div class="field-grid drawer-grid">
                      <div class="field-block">
                        <label for="field-lccn">Library of Congress Control No. (LCCN)</label>
                        <input id="field-lccn" v-model="editableBook.lccn" class="input-control" placeholder="e.g. 2001012345" />
                      </div>
                      <div class="field-block">
                        <label for="field-oclc">OCLC WorldCat No.</label>
                        <input 
                          id="field-oclc" 
                          v-model="editableBook.oclc_no" 
                          class="input-control" 
                          inputmode="numeric" 
                          placeholder="e.g. 12345678" 
                          @input="enforceNumbersOnly($event, 'oclc_no')" 
                        />
                      </div>
                    </div>
                  </details>
                </div>
              </div>
            </section>

            <!-- 05 Lineage, Context & Rights -->
            <section v-if="isSectionVisible('lineage', ['lineage', 'original title', 'original author', 'translator', 'compiler', 'rights', 'copyright', 'subject_headings'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">05</div>
                <div><h3>Lineage, Context & Rights</h3><p>Attributions, translators, subject tags, and copyright.</p></div>
              </div>
              <div class="field-grid">
                <div class="field-block" :class="{ 'field-modified': isFieldModified('original_title') }">
                  <div class="label-line">
                    <label for="field-orig-title">Original Title</label>
                    <span v-if="isFieldModified('original_title')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-orig-title" v-model="editableBook.original_title" class="input-control" placeholder="Root title in source tongue" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('original_author') }">
                  <div class="label-line">
                    <label for="field-orig-author">Original Author</label>
                    <span v-if="isFieldModified('original_author')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-orig-author" v-model="editableBook.original_author" class="input-control" placeholder="Original author name" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('translator') }">
                  <div class="label-line">
                    <label for="field-translator">Translator</label>
                    <span v-if="isFieldModified('translator')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-translator" v-model="editableBook.translator" class="input-control" placeholder="Credited translator" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('compiler_editor') }">
                  <div class="label-line">
                    <label for="field-compiler">Compiler / Editor</label>
                    <span v-if="isFieldModified('compiler_editor')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-compiler" v-model="editableBook.compiler_editor" class="input-control" placeholder="Editor or compiler" />
                </div>

                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('translation_compilation') }">
                  <div class="label-line">
                    <label for="field-trans-comp">Translation & Compilation Notes</label>
                    <span v-if="isFieldModified('translation_compilation')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-trans-comp" v-model="editableBook.translation_compilation" class="input-control" placeholder="e.g. Translated from Russian text authorized edition" />
                </div>

                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('subject_headings') }">
                  <div class="label-line">
                    <label for="field-subjects">Subject Headings (Separated by commas)</label>
                    <span v-if="isFieldModified('subject_headings')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-subjects" v-model="editableBook.subject_headings" class="input-control" placeholder="e.g. Malayalam Fiction, Detective Stories, Travancore" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('target_audience_era') }">
                  <div class="label-line">
                    <label for="field-audience">Target Audience / Era</label>
                    <span v-if="isFieldModified('target_audience_era')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-audience" v-model="editableBook.target_audience_era" class="input-control" placeholder="e.g. 20th Century, General Reader" />
                </div>

                <!-- Copyright Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('copyright_status') }">
                  <div class="label-line">
                    <label for="field-copyright">Copyright Status</label>
                    <span v-if="isFieldModified('copyright_status')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-copyright" v-model="copyrightSelectValue" class="input-control" @change="handleCopyrightSelectChange">
                    <option value="">Select Status</option>
                    <option v-for="c in copyrightOptions" :key="c" :value="c">{{ c }}</option>
                    <option value="__CUSTOM__">Other (Specify)…</option>
                  </select>
                  <input 
                    v-if="copyrightSelectValue === '__CUSTOM__'" 
                    v-model="editableBook.copyright_status" 
                    class="input-control custom-subfield" 
                    placeholder="Enter custom copyright / license terms…" 
                  />
                </div>
              </div>
            </section>

            <!-- 06 Relational Series Grouping -->
            <section v-if="isSectionVisible('series', ['series', 'series_name', 'series_number', 'volume_number', 'related_work_id', 'grouping'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">06</div>
                <div><h3>Relational Series Grouping</h3><p>Group multi-volume works and connected catalogued items.</p></div>
              </div>
              <div class="field-grid">
                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('series_name') }">
                  <div class="label-line">
                    <label for="field-series-group">Series Group Name</label>
                    <span v-if="isFieldModified('series_name')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-series-group" v-model="editableBook.series_name" class="input-control" placeholder="e.g. Complete Works of Agatha Christie" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('series_number') }">
                  <div class="label-line">
                    <label for="field-series-num">Series Number (Digits Only)</label>
                    <span v-if="isFieldModified('series_number')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-series-num" 
                    v-model="editableBook.series_number" 
                    class="input-control" 
                    inputmode="numeric" 
                    placeholder="e.g. 4" 
                    @input="enforceNumbersOnly($event, 'series_number')" 
                  />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('volume_number') }">
                  <div class="label-line">
                    <label for="field-vol-num">Volume Number (Digits Only)</label>
                    <span v-if="isFieldModified('volume_number')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-vol-num" 
                    v-model="editableBook.volume_number" 
                    class="input-control" 
                    inputmode="numeric" 
                    placeholder="e.g. 1" 
                    @input="enforceNumbersOnly($event, 'volume_number')" 
                  />
                </div>

                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('related_work_id') }">
                  <div class="label-line">
                    <label for="field-rel-work">Related Work ID (Digits Only)</label>
                    <span v-if="isFieldModified('related_work_id')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-rel-work" 
                    v-model="editableBook.related_work_id" 
                    class="input-control" 
                    inputmode="numeric" 
                    placeholder="e.g. 505" 
                    @input="enforceNumbersOnly($event, 'related_work_id')" 
                  />
                </div>
              </div>
            </section>

            <!-- 07 Location -->
            <section v-if="isSectionVisible('location', ['location', 'shelf', 'call number', 'accession'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">07</div>
                <div><h3>Location</h3><p>Physical shelf placement and stack call number.</p></div>
              </div>
              <div class="field-grid">
                <div class="field-block" :class="{ 'field-modified': isFieldModified('shelf') }">
                  <div class="label-line">
                    <label for="field-shelf">Shelf Placement</label>
                    <span v-if="isFieldModified('shelf')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-shelf" v-model="editableBook.shelf" class="input-control" placeholder="e.g. S-0-S or Bay 4 / Shelf B" />
                </div>

                <div class="field-block" :class="{ 'field-modified': isFieldModified('call_no') }">
                  <div class="label-line">
                    <label for="field-call-no">Call Number</label>
                    <span v-if="isFieldModified('call_no')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-call-no" v-model="editableBook.call_no" class="input-control" placeholder="e.g. ML-FIC-26.0" />
                </div>
              </div>
            </section>

            <!-- 08 Preservation & Holding Details -->
            <section v-if="isSectionVisible('preservation', ['preservation', 'holding', 'condition', 'binding', 'provenance', 'fonds', 'pages', 'dimensions'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">08</div>
                <div><h3>Preservation & Holding Details</h3><p>Conservation, dimensions, provenance, and accessibility.</p></div>
              </div>
              <div class="field-grid">
                <!-- Extent Page Count: strictly numeric -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('extent_page_count') }">
                  <div class="label-line">
                    <label for="field-extent">Pages / Extent (Numbers Only)</label>
                    <span v-if="isFieldModified('extent_page_count')" class="modified-label">Modified</span>
                  </div>
                  <div class="input-with-unit">
                    <input 
                      id="field-extent" 
                      v-model="editableBook.extent_page_count" 
                      class="input-control" 
                      inputmode="numeric" 
                      placeholder="e.g. 420" 
                      @input="enforceNumbersOnly($event, 'extent_page_count')" 
                    />
                    <span class="unit-tag">pages</span>
                  </div>
                </div>

                <!-- Structured Dimension: Height × Width cm -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('physical_dimensions') }">
                  <div class="label-line">
                    <label>Physical Dimensions (Height × Width)</label>
                    <span v-if="isFieldModified('physical_dimensions')" class="modified-label">Modified</span>
                  </div>
                  <div class="dimension-input-group">
                    <input 
                      v-model="dimHeight" 
                      class="input-control dim-box" 
                      inputmode="numeric" 
                      placeholder="Height" 
                      @input="syncDimensions" 
                    />
                    <span class="dim-separator">×</span>
                    <input 
                      v-model="dimWidth" 
                      class="input-control dim-box" 
                      inputmode="numeric" 
                      placeholder="Width" 
                      @input="syncDimensions" 
                    />
                    <select v-model="dimUnit" class="input-control dim-unit-select" @change="syncDimensions">
                      <option value="cm">cm</option>
                      <option value="mm">mm</option>
                      <option value="in">inches</option>
                    </select>
                  </div>
                </div>

                <!-- Date Acquired: strict date with max="today" -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('date_acquired') }">
                  <div class="label-line">
                    <label for="field-acquired">Date Acquired</label>
                    <span v-if="isFieldModified('date_acquired')" class="modified-label">Modified</span>
                  </div>
                  <input 
                    id="field-acquired" 
                    v-model="editableBook.date_acquired" 
                    class="input-control" 
                    type="date" 
                    :max="todayDateString" 
                  />
                </div>

                <!-- Collection / Fonds -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('collection_fonds') }">
                  <div class="label-line">
                    <label for="field-fonds">Collection / Archival Fonds</label>
                    <span v-if="isFieldModified('collection_fonds')" class="modified-label">Modified</span>
                  </div>
                  <input id="field-fonds" v-model="editableBook.collection_fonds" class="input-control" placeholder="e.g. Rare Palm-Leaf Archival Fonds, Donor Collection" />
                </div>

                <!-- Physical Condition Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('physical_condition') }">
                  <div class="label-line">
                    <label for="field-condition">Physical Condition</label>
                    <span v-if="isFieldModified('physical_condition')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-condition" v-model="conditionSelectValue" class="input-control" @change="handleConditionSelectChange">
                    <option value="">Select Condition</option>
                    <option v-for="cond in conditionOptions" :key="cond" :value="cond">{{ cond }}</option>
                    <option value="__CUSTOM__">Other (Enter Manually)…</option>
                  </select>
                  <input 
                    v-if="conditionSelectValue === '__CUSTOM__'" 
                    v-model="editableBook.physical_condition" 
                    class="input-control custom-subfield" 
                    placeholder="Specific condition notes…" 
                  />
                </div>

                <!-- Binding Type Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('binding_type') }">
                  <div class="label-line">
                    <label for="field-binding">Binding Type</label>
                    <span v-if="isFieldModified('binding_type')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-binding" v-model="bindingSelectValue" class="input-control" @change="handleBindingSelectChange">
                    <option value="">Select Binding</option>
                    <option v-for="b in bindingOptions" :key="b" :value="b">{{ b }}</option>
                    <option value="__CUSTOM__">Other (Enter Manually)…</option>
                  </select>
                  <input 
                    v-if="bindingSelectValue === '__CUSTOM__'" 
                    v-model="editableBook.binding_type" 
                    class="input-control custom-subfield" 
                    placeholder="Specific binding style…" 
                  />
                </div>

                <!-- Provenance Source Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('provenance_source') }">
                  <div class="label-line">
                    <label for="field-provenance">Provenance Source</label>
                    <span v-if="isFieldModified('provenance_source')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-provenance" v-model="provenanceSelectValue" class="input-control" @change="handleProvenanceSelectChange">
                    <option value="">Select Provenance</option>
                    <option v-for="p in provenanceOptions" :key="p" :value="p">{{ p }}</option>
                    <option value="__CUSTOM__">Other (Specify Donor / Source)…</option>
                  </select>
                  <input 
                    v-if="provenanceSelectValue === '__CUSTOM__'" 
                    v-model="editableBook.provenance_source" 
                    class="input-control custom-subfield" 
                    placeholder="Name of donor or purchasing registry…" 
                  />
                </div>

                <!-- Access Restrictions Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('access_restrictions') }">
                  <div class="label-line">
                    <label for="field-restrictions">Access Restrictions</label>
                    <span v-if="isFieldModified('access_restrictions')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-restrictions" v-model="restrictionsSelectValue" class="input-control" @change="handleRestrictionsSelectChange">
                    <option value="">Select Policy</option>
                    <option v-for="r in restrictionOptions" :key="r" :value="r">{{ r }}</option>
                    <option value="__CUSTOM__">Other (Specify Restriction)…</option>
                  </select>
                  <input 
                    v-if="restrictionsSelectValue === '__CUSTOM__'" 
                    v-model="editableBook.access_restrictions" 
                    class="input-control custom-subfield" 
                    placeholder="Special access rule…" 
                  />
                </div>

                <!-- Digital Scan Boolean -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('digital_scan_available') }">
                  <div class="label-line">
                    <label for="field-scan">Digital Scan Available</label>
                    <span v-if="isFieldModified('digital_scan_available')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-scan" v-model="editableBook.digital_scan_available" class="input-control">
                    <option :value="false">No (Unscanned)</option>
                    <option :value="true">Yes (Archived Scan Available)</option>
                  </select>
                </div>

                <!-- OCR Status Combobox -->
                <div class="field-block" :class="{ 'field-modified': isFieldModified('ocr_status') }">
                  <div class="label-line">
                    <label for="field-ocr">OCR Status (Optical Recognition)</label>
                    <span v-if="isFieldModified('ocr_status')" class="modified-label">Modified</span>
                  </div>
                  <select id="field-ocr" v-model="editableBook.ocr_status" class="input-control">
                    <option value="">Select OCR Status</option>
                    <option v-for="ocr in ocrOptions" :key="ocr" :value="ocr">{{ ocr }}</option>
                  </select>
                </div>

                <div class="field-block span-2" :class="{ 'field-modified': isFieldModified('artifactual_notes') }">
                  <div class="label-line">
                    <label for="field-artifact-notes">Artifact Markers / Notes (Bookplates, Inscriptions, Seals)</label>
                    <span v-if="isFieldModified('artifactual_notes')" class="modified-label">Modified</span>
                  </div>
                  <textarea id="field-artifact-notes" v-model="editableBook.artifactual_notes" class="input-control textarea-control" rows="3" placeholder="Marginalia, signatures, archival stamps, stamps…"></textarea>
                </div>
              </div>
            </section>

            <!-- 09 Notes -->
            <section v-if="isSectionVisible('notes', ['notes', 'remarks', 'conservation'])" class="form-section">
              <div class="section-heading">
                <div class="section-index">09</div>
                <div><h3>Notes</h3><p>General holding remarks and cataloguing notes.</p></div>
              </div>
              <div class="field-block" :class="{ 'field-modified': isFieldModified('notes') }">
                <div class="label-line">
                  <label for="field-notes">Catalogue Notes</label>
                  <span v-if="isFieldModified('notes')" class="modified-label">Modified</span>
                </div>
                <textarea id="field-notes" v-model="editableBook.notes" class="input-control textarea-control" rows="5" placeholder="Add relevant notes about this catalogued item…"></textarea>
                <div v-if="isFieldModified('notes')" class="field-footer">
                  <span>Original: {{ pristineBook.notes || 'Empty' }}</span>
                  <button type="button" @click="revertSingleField('notes')">Undo</button>
                </div>
              </div>
            </section>
          </div>

          <!-- Audit Review Panel -->
          <section v-if="modifiedFieldsList.length" class="review-panel">
            <div class="review-heading">
              <div><span class="eyebrow">REVIEW</span><h3>Modified Fields In This Session</h3></div>
              <button class="text-button" type="button" @click="revertAllModifications">Discard all</button>
            </div>
            <div v-for="change in modifiedFieldsList" :key="change.key" class="review-row">
              <div><strong>{{ change.label }}</strong><small>{{ change.tabLabel }}</small></div>
              <div class="review-values">
                <span>{{ change.oldValue || 'Empty' }}</span>
                <span class="review-arrow">→</span>
                <span>{{ change.newValue || 'Empty' }}</span>
              </div>
              <button type="button" class="undo-icon" :aria-label="`Undo ${change.label}`" @click="revertSingleField(change.key)">↶</button>
            </div>
          </section>
        </section>
      </div>

      <!-- Bottom Savebar -->
      <footer class="savebar">
        <div class="savebar-info">
          <span class="save-indicator" :class="{ dirty: modifiedFieldsList.length }"></span>
          <span>{{ modifiedFieldsList.length ? `${modifiedFieldsList.length} unsaved field changes` : 'All changes saved' }}</span>
        </div>
        <div class="savebar-actions">
          <button class="button button-quiet" type="button" @click="handleBackNavigation">Cancel (Esc)</button>
          <button 
            class="button button-save-action" 
            type="button" 
            :disabled="!modifiedFieldsList.length || isSaving" 
            @click="triggerActionConfirm('commit')"
          >
            {{ isSaving ? 'Saving…' : (modifiedFieldsList.length ? 'Review & Save' : 'No Changes') }}
          </button>
        </div>
      </footer>
    </template>

    <!-- Confirmation Modal -->
    <div v-if="activeModalType" class="modal-backdrop" @click.self="!isSaving && closeModalPrompt()">
      <section class="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="modal-mark">{{ activeModalType === 'commit' ? '✓' : '↶' }}</div>
        <span class="eyebrow">CONFIRM ACTION</span>
        <h2 id="confirm-title">{{ activeModalType === 'commit' ? 'Save record updates?' : 'Discard unsaved changes?' }}</h2>
        <p>{{ activeModalType === 'commit' ? 'Your updates will be saved to the database ledger.' : 'You have unsaved edits. Discarding will revert to previous values.' }}</p>
        
        <template v-if="activeModalType === 'commit'">
          <label for="change-reason">Reason for change <span class="optional-label">(optional)</span></label>
          <textarea id="change-reason" v-model="changeReason" class="input-control textarea-control" rows="2" placeholder="Briefly describe this update…"></textarea>
        </template>

        <div class="modal-actions">
          <button class="button button-quiet" type="button" :disabled="isSaving" @click="closeModalPrompt">Go back</button>
          <button 
            class="button" 
            :class="activeModalType === 'commit' ? 'button-save-action' : 'button-primary'" 
            type="button" 
            :disabled="isSaving" 
            @click="executeConfirmedAction"
          >
            {{ isSaving ? 'Saving…' : (activeModalType === 'commit' ? 'Confirm Save' : 'Discard & Return') }}
          </button>
        </div>
      </section>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast-message" :class="toast.type" role="status">{{ toast.message }}</div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, nextTick, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"
import { dispatchAuditTrail } from '@/utils/audit'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loadError = ref('')
const isSaving = ref(false)
const editableBook = ref<any>(null)
const pristineBook = ref<any>(null)

type TabKey = 'work' | 'taxonomy' | 'languages' | 'publication' | 'lineage' | 'series' | 'location' | 'preservation' | 'notes'
const activeTab = ref<TabKey>('work')
const searchQuery = ref('')
const showAllSections = ref(false)
const activeModalType = ref<'commit' | 'abort' | null>(null)
const changeReason = ref<string>("")
let toastTimeout: ReturnType<typeof setTimeout> | null = null
let draftTimer: ReturnType<typeof setTimeout> | null = null

interface ToastNotification {
  message: string
  type: 'success' | 'error'
}
const toast = ref<ToastNotification | null>(null)

const todayDateString = computed(() => new Date().toISOString().split('T')[0])

const navTabs = [
  { key: 'work', number: '01', label: 'Core Details', hint: 'Title & Creator' },
  { key: 'taxonomy', number: '02', label: 'Classification', hint: 'DDC & Genres' },
  { key: 'languages', number: '03', label: 'Languages', hint: 'Text & Original' },
  { key: 'publication', number: '04', label: 'Publication', hint: 'Imprint & ISBN' },
  { key: 'lineage', number: '05', label: 'Lineage & Rights', hint: 'Translations & Rights' },
  { key: 'series', number: '06', label: 'Relational Series', hint: 'Fonds & Volumes' },
  { key: 'location', number: '07', label: 'Location', hint: 'Shelf & Call No' },
  { key: 'preservation', number: '08', label: 'Preservation', hint: 'Condition & Fonds' },
  { key: 'notes', number: '09', label: 'Notes', hint: 'Archival notes' }
]

const currentTabLabel = computed(() => {
  return navTabs.find(t => t.key === activeTab.value)?.label || 'Record Details'
})

// Options
const categoryOptions = ["Fiction", "Non-Fiction", "Reference", "Religious", "Poetry", "Manuscript / Rare", "Periodical"]
const categorySelectValue = ref("")

const copyrightOptions = [
  "Public Domain",
  "In Copyright (All Rights Reserved)",
  "In Copyright - Orphan Work",
  "Creative Commons (CC BY / CC BY-SA)",
  "Creative Commons Zero (CC0)",
  "Copyright Not Evaluated / Unknown"
]
const copyrightSelectValue = ref("")

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

const ocrOptions = ["NOT_APPLICABLE", "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"]

// Dynamic Deduplicated Language Registry
const systemLanguages = ref<string[]>([])
const standardLanguages = [
  "Malayalam", "English", "Sanskrit", "Tamil", "Hindi",
  "Arabic", "Bengali", "French", "German", "Gujarati",
  "Kannada", "Latin", "Marathi", "Persian", "Prakrit",
  "Punjabi", "Russian", "Spanish", "Telugu", "Urdu", "Multilingual"
]

const availableLanguages = computed(() => {
  const rawList = [
    ...standardLanguages,
    ...systemLanguages.value
  ]
  const cleaned = rawList
    .map(lang => {
      if (!lang) return ""
      const trimmed = String(lang).trim()
      if (trimmed.toLowerCase().replace(/[\s-]/g, "") === "multilingual") return "Multilingual"
      return trimmed
    })
    .filter(Boolean)

  const unique = Array.from(new Set(cleaned))
  const priority = ["Malayalam", "English", "Sanskrit", "Tamil", "Hindi", "Multilingual"]

  return unique.sort((a, b) => {
    const idxA = priority.indexOf(a)
    const idxB = priority.indexOf(b)
    if (idxA !== -1 && idxB !== -1) return idxA - idxB
    if (idxA !== -1) return -1
    if (idxB !== -1) return 1
    return a.localeCompare(b)
  })
})

async function fetchLanguageOptions() {
  try {
    const res = await axios.get("/catalogue/review/field-options")
    if (Array.isArray(res.data?.languages)) {
      systemLanguages.value = res.data.languages
    }
  } catch (err) {
    console.warn("Could not fetch remote language options:", err)
  }
}

// Genres
const newGenreInput = ref("")
const popularIndianGenres = [
  "NOVEL", "SHORT STORIES", "POETRY", "BIOGRAPHY", "DETECTIVE", 
  "HISTORICAL", "PHILOSOPHY", "DRAMA", "SATIRE", "FOLKLORE"
]

const currentGenreList = computed<string[]>(() => {
  if (!editableBook.value?.genre) return []
  return String(editableBook.value.genre)
    .split('/')
    .map((g: string) => g.trim().toUpperCase())
    .filter((g: string) => g.length > 0)
})

function addGenreFromInput() {
  const raw = newGenreInput.value.replace(/,/g, '').trim().toUpperCase()
  if (!raw) return
  if (!currentGenreList.value.includes(raw)) {
    const updated = [...currentGenreList.value, raw]
    editableBook.value.genre = updated.join('/')
  }
  newGenreInput.value = ""
}

function toggleGenrePill(tag: string) {
  if (currentGenreList.value.includes(tag)) {
    removeGenreChip(tag)
  } else {
    editableBook.value.genre = [...currentGenreList.value, tag].join('/')
  }
}

function removeGenreChip(tag: string) {
  const updated = currentGenreList.value.filter(t => t !== tag)
  editableBook.value.genre = updated.length ? updated.join('/') : null
}

function clearAllGenres() {
  editableBook.value.genre = null
}

// Dimensions handling (Height × Width cm)
const dimHeight = ref("")
const dimWidth = ref("")
const dimUnit = ref("cm")

function parseInitialDimensions(raw: string | undefined) {
  if (!raw) return
  const match = String(raw).match(/(\d+(?:\.\d+)?)\s*(?:[x×*])\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?/)
  if (match) {
    dimHeight.value = match[1] || ""
    dimWidth.value = match[2] || ""
    dimUnit.value = match[3] || "cm"
  } else {
    dimHeight.value = raw.replace(/\D/g, '')
  }
}

function syncDimensions() {
  if (!dimHeight.value && !dimWidth.value) {
    editableBook.value.physical_dimensions = null
    return
  }
  editableBook.value.physical_dimensions = `${dimHeight.value.trim()} × ${dimWidth.value.trim()} ${dimUnit.value}`
}

// Strictly numbers-only helper
function enforceNumbersOnly(event: Event, fieldKey: string, maxLen?: number) {
  const input = event.target as HTMLInputElement
  let digits = input.value.replace(/\D/g, "")
  if (maxLen && digits.length > maxLen) {
    digits = digits.slice(0, maxLen)
  }
  editableBook.value[fieldKey] = digits ? digits : null
  input.value = digits
}

// DDC validation: 3 digits before decimal, optional decimal parts
const isDdcValid = computed(() => {
  const val = editableBook.value?.ddc
  if (!val || String(val).trim() === "") return true
  return /^\d{3}(\.\d+)?$/.test(String(val).trim())
})

// ISBN Formatter & Validator
const isIsbnValid = computed(() => {
  const raw = editableBook.value?.isbn
  if (!raw || String(raw).trim() === "") return true
  const clean = String(raw).replace(/[-\s]/g, "")
  return clean.length === 10 || clean.length === 13
})

function formatIsbnOnBlur() {
  const raw = editableBook.value?.isbn
  if (!raw) return
  const clean = String(raw).replace(/[-\s]/g, "")
  if (clean.length === 13) {
    editableBook.value.isbn = `${clean.slice(0, 3)}-${clean.slice(3, 5)}-${clean.slice(5, 9)}-${clean.slice(9, 12)}-${clean.slice(12)}`
  } else if (clean.length === 10) {
    editableBook.value.isbn = `${clean.slice(0, 1)}-${clean.slice(1, 4)}-${clean.slice(4, 9)}-${clean.slice(9)}`
  }
}

// Combobox Sync Initializers
function setupComboboxValues() {
  categorySelectValue.value = categoryOptions.includes(editableBook.value.category) ? editableBook.value.category : (editableBook.value.category ? '__CUSTOM__' : '')
  copyrightSelectValue.value = copyrightOptions.includes(editableBook.value.copyright_status) ? editableBook.value.copyright_status : (editableBook.value.copyright_status ? '__CUSTOM__' : '')
  conditionSelectValue.value = conditionOptions.includes(editableBook.value.physical_condition) ? editableBook.value.physical_condition : (editableBook.value.physical_condition ? '__CUSTOM__' : '')
  bindingSelectValue.value = bindingOptions.includes(editableBook.value.binding_type) ? editableBook.value.binding_type : (editableBook.value.binding_type ? '__CUSTOM__' : '')
  provenanceSelectValue.value = provenanceOptions.includes(editableBook.value.provenance_source) ? editableBook.value.provenance_source : (editableBook.value.provenance_source ? '__CUSTOM__' : '')
  restrictionsSelectValue.value = restrictionOptions.includes(editableBook.value.access_restrictions) ? editableBook.value.access_restrictions : (editableBook.value.access_restrictions ? '__CUSTOM__' : '')
  parseInitialDimensions(editableBook.value.physical_dimensions)
}

function handleCategorySelectChange() {
  if (categorySelectValue.value !== '__CUSTOM__') {
    editableBook.value.category = categorySelectValue.value || null
  }
}

function handleCopyrightSelectChange() {
  if (copyrightSelectValue.value !== '__CUSTOM__') {
    editableBook.value.copyright_status = copyrightSelectValue.value || null
  }
}

function handleConditionSelectChange() {
  if (conditionSelectValue.value !== '__CUSTOM__') {
    editableBook.value.physical_condition = conditionSelectValue.value || null
  }
}

function handleBindingSelectChange() {
  if (bindingSelectValue.value !== '__CUSTOM__') {
    editableBook.value.binding_type = bindingSelectValue.value || null
  }
}

function handleProvenanceSelectChange() {
  if (provenanceSelectValue.value !== '__CUSTOM__') {
    editableBook.value.provenance_source = provenanceSelectValue.value || null
  }
}

function handleRestrictionsSelectChange() {
  if (restrictionsSelectValue.value !== '__CUSTOM__') {
    editableBook.value.access_restrictions = restrictionsSelectValue.value || null
  }
}

// Tracked Changes
interface TrackedFieldConfig {
  key: string
  label: string
  tab: TabKey
  tabLabel: string
}

const trackedFieldsConfig: TrackedFieldConfig[] = [
  { key: 'title', label: 'Work Title', tab: 'work', tabLabel: '01 Core' },
  { key: 'author', label: 'Author / Creator', tab: 'work', tabLabel: '01 Core' },
  { key: 'work_nature', label: 'Work Nature', tab: 'work', tabLabel: '01 Core' },
  { key: 'category', label: 'Collection Category', tab: 'taxonomy', tabLabel: '02 Taxonomy' },
  { key: 'ddc', label: 'Dewey Decimal (DDC)', tab: 'taxonomy', tabLabel: '02 Taxonomy' },
  { key: 'genre', label: 'Genre Tags', tab: 'taxonomy', tabLabel: '02 Taxonomy' },
  { key: 'language', label: 'Text Language', tab: 'languages', tabLabel: '03 Lang' },
  { key: 'original_language', label: 'Original Source Language', tab: 'languages', tabLabel: '03 Lang' },
  { key: 'publisher', label: 'Imprint Publisher', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'year', label: 'Publication Year', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'isbn', label: 'ISBN Identifier', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'edition_statement', label: 'Edition Statement', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'series_title', label: 'Academic Series', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'series_volume', label: 'Series Volume', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'lccn', label: 'LCCN', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'oclc_no', label: 'OCLC No.', tab: 'publication', tabLabel: '04 Imprint' },
  { key: 'original_title', label: 'Original Title', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'original_author', label: 'Original Author', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'translator', label: 'Translator', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'compiler_editor', label: 'Compiler / Editor', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'translation_compilation', label: 'Translation/Compilation', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'subject_headings', label: 'Subject Headings', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'target_audience_era', label: 'Target Audience / Era', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'copyright_status', label: 'Copyright Status', tab: 'lineage', tabLabel: '05 Lineage' },
  { key: 'series_name', label: 'Series Group Name', tab: 'series', tabLabel: '06 Series' },
  { key: 'series_number', label: 'Series Number', tab: 'series', tabLabel: '06 Series' },
  { key: 'volume_number', label: 'Volume Number', tab: 'series', tabLabel: '06 Series' },
  { key: 'related_work_id', label: 'Related Work ID', tab: 'series', tabLabel: '06 Series' },
  { key: 'shelf', label: 'Shelf Location', tab: 'location', tabLabel: '07 Location' },
  { key: 'call_no', label: 'Call Number', tab: 'location', tabLabel: '07 Location' },
  { key: 'extent_page_count', label: 'Extent / Pages', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'physical_dimensions', label: 'Physical Dimensions', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'date_acquired', label: 'Date Acquired', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'collection_fonds', label: 'Collection / Fonds', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'physical_condition', label: 'Physical Condition', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'binding_type', label: 'Binding Type', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'provenance_source', label: 'Provenance Source', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'access_restrictions', label: 'Access Restrictions', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'digital_scan_available', label: 'Digital Scan Available', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'ocr_status', label: 'OCR Status', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'artifactual_notes', label: 'Artifactual Notes', tab: 'preservation', tabLabel: '08 Holding' },
  { key: 'notes', label: 'Catalogue Notes', tab: 'notes', tabLabel: '09 Notes' }
]

function normalizeValue(val: any): string {
  if (val === null || val === undefined) return ""
  return String(val).trim()
}

const modifiedFieldsList = computed(() => {
  if (!editableBook.value || !pristineBook.value) return []
  const changes: Array<TrackedFieldConfig & { oldValue: string; newValue: string }> = []
  trackedFieldsConfig.forEach((cfg) => {
    const oldNorm = normalizeValue(pristineBook.value[cfg.key])
    const newNorm = normalizeValue(editableBook.value[cfg.key])
    if (oldNorm !== newNorm) {
      changes.push({ ...cfg, oldValue: oldNorm, newValue: newNorm })
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

async function revertSingleField(fieldKey: string) {
  if (!pristineBook.value || !editableBook.value) return
  editableBook.value[fieldKey] = pristineBook.value[fieldKey]
  setupComboboxValues()
  
  await nextTick()
  const el = document.getElementById(`field-${fieldKey}`)
  el?.focus()

  triggerToastNotification(`Field '${fieldKey}' restored.`, 'success')
}

function revertAllModifications() {
  if (!pristineBook.value) return
  const id = editableBook.value?.serial_no || route.params.id
  if (id) {
    localStorage.removeItem(`athenaeum_draft_item_${id}`)
  }
  editableBook.value = JSON.parse(JSON.stringify(pristineBook.value))
  setupComboboxValues()
  triggerToastNotification("All modifications reverted.", "success")
}

function setTab(tabKey: TabKey) {
  activeTab.value = tabKey
  showAllSections.value = false
}

function handleBackNavigation() {
  if (modifiedFieldsList.value.length > 0) {
    triggerActionConfirm('abort')
  } else {
    router.push(`/details/${route.params.id || editableBook.value?.serial_no}`)
  }
}

function navigateSection(direction: "next" | "prev") {
  const currentIndex = navTabs.findIndex(tab => tab.key === activeTab.value)
  if (currentIndex === -1) return

  let targetIndex = direction === "next" ? currentIndex + 1 : currentIndex - 1

  if (targetIndex < 0) targetIndex = 0
  if (targetIndex >= navTabs.length) targetIndex = navTabs.length - 1

  setTab(navTabs[targetIndex].key as TabKey)
}

function handleEditorKeyboard(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  const tagName = target?.tagName?.toUpperCase()
  const isTyping = tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT" || target?.isContentEditable

  if (event.key === 'Escape') {
    event.preventDefault()
    if (activeModalType.value) {
      closeModalPrompt()
    } else {
      handleBackNavigation()
    }
    return
  }

  // Prevent section navigation when the user is typing in a field or has a modal open
  if (isTyping || activeModalType.value) return

  if (event.key === "ArrowLeft") {
    event.preventDefault()
    navigateSection("prev")
  } else if (event.key === "ArrowRight") {
    event.preventDefault()
    navigateSection("next")
  }
}

watch(() => route.params.id, (newId: string | string[] | undefined) => {
  if (newId) {
    editableBook.value = null
    pristineBook.value = null
    fetchRecordData()
  }
})

// Auto-save changes to client-side localStorage without triggering API requests or audit logs
watch(
  () => editableBook.value,
  (newVal) => {
    if (!newVal || !pristineBook.value) return
    
    if (draftTimer) clearTimeout(draftTimer)
    draftTimer = setTimeout(() => {
      const id = newVal.serial_no || route.params.id
      if (!id) return
      
      const draftKey = `athenaeum_draft_item_${id}`
      if (modifiedFieldsList.value.length > 0) {
        localStorage.setItem(
          draftKey,
          JSON.stringify({
            data: newVal,
            savedAt: new Date().toISOString()
          })
        )
      } else {
        localStorage.removeItem(draftKey)
      }
    }, 400) // 400ms debounce
  },
  { deep: true }
)

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
  if (toastTimeout) clearTimeout(toastTimeout)
  toastTimeout = setTimeout(() => {
    toast.value = null
  }, 4000)
}

// Author & Publisher debounced search
interface AuthoritySuggestion {
  authority_id: number
  authority_code: string
  preferred_name: string
  full_name?: string
  status: string
}
const authorSuggestions = ref<AuthoritySuggestion[]>([])
const publisherSuggestions = ref<string[]>([])
const showAuthorSuggestions = ref(false)
const showPublisherSuggestions = ref(false)
let debounceAuthorTimeout: any = null
let debouncePublisherTimeout: any = null

function searchAuthorsDebounced() {
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  debounceAuthorTimeout = setTimeout(async () => {
    const query = editableBook.value?.author?.trim() || ""
    if (query.length < 2) {
      authorSuggestions.value = []
      showAuthorSuggestions.value = false
      return
    }
    try {
      const response = await axios.get('/authority/search', { params: { q: query, usable_only: true, limit: 10 } })
      authorSuggestions.value = Array.isArray(response.data) ? response.data : []
      showAuthorSuggestions.value = authorSuggestions.value.length > 0
    } catch {
      authorSuggestions.value = []
    }
  }, 200)
}

function searchPublishersDebounced() {
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
  debouncePublisherTimeout = setTimeout(async () => {
    const query = editableBook.value?.publisher?.trim() || ""
    if (query.length < 2) {
      publisherSuggestions.value = []
      showPublisherSuggestions.value = false
      return
    }
    try {
      const response = await axios.get(`/catalogue/publishers/search?q=${encodeURIComponent(query)}`)
      publisherSuggestions.value = response.data || []
      showPublisherSuggestions.value = publisherSuggestions.value.length > 0
    } catch {
      publisherSuggestions.value = []
    }
  }, 200)
}

function selectSuggestion(type: 'author' | 'publisher', value: AuthoritySuggestion | string) {
  if (type === 'author' && typeof value !== 'string') {
    editableBook.value.author = value.preferred_name
    authorSuggestions.value = []
    showAuthorSuggestions.value = false
  } else if (type === 'publisher' && typeof value === 'string') {
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
  loadError.value = ''
  const id = route.params.id
  try {
    if (!id) throw new Error('Record identifier is missing.')
    await fetchLanguageOptions()
    const response = await axios.get(`/catalogue/holding/${encodeURIComponent(String(id))}`)
    if (!response.data) throw new Error('The server returned an empty record.')
    pristineBook.value = JSON.parse(JSON.stringify(response.data))
    
    // Check if an unsaved desktop draft exists for this record
    const draftKey = `athenaeum_draft_item_${response.data.serial_no || id}`
    const cachedDraft = localStorage.getItem(draftKey)
    
    if (cachedDraft) {
      try {
        const parsed = JSON.parse(cachedDraft)
        editableBook.value = { ...response.data, ...parsed.data }
        triggerToastNotification("Restored unsaved local draft.", "success")
      } catch {
        editableBook.value = { ...response.data }
      }
    } else {
      editableBook.value = { ...response.data }
    }
    
    setupComboboxValues()
  } catch (err: any) {
    loadError.value = err?.response?.data?.message || err?.message || 'Failed to load record.'
  } finally {
    loading.value = false
  }
}

function triggerActionConfirm(actionType: 'commit' | 'abort') {
  if (actionType === 'commit') {
    if (!editableBook.value?.title || !editableBook.value.title.trim()) {
      triggerToastNotification("Validation Error: Title cannot be empty.", "error")
      setTab('work')
      return
    }
    if (!editableBook.value?.language) {
      triggerToastNotification("Validation Error: Language is required.", "error")
      setTab('languages')
      return
    }
    if (!isDdcValid.value) {
      triggerToastNotification("Validation Error: Check DDC format (e.g. 894.812).", "error")
      setTab('taxonomy')
      return
    }
  }
  activeModalType.value = actionType
  changeReason.value = ""
}

function executeConfirmedAction() {
  if (activeModalType.value === 'commit') saveRecord()
  else if (activeModalType.value === 'abort') router.push(`/details/${route.params.id || editableBook.value?.serial_no}`)
  closeModalPrompt()
}

function closeModalPrompt() {
  if (isSaving.value) return
  activeModalType.value = null
}

async function saveRecord() {
  if (isSaving.value) return
  const id = route.params.id || editableBook.value?.serial_no
  isSaving.value = true
  try {
    const operationalReason = changeReason.value.trim() || "Routine archival update"
    const token = authStore.accessToken || authStore.access_token
    
    await axios.patch(`/catalogue/${id}`, editableBook.value, {
      headers: {
        'X-Change-Reason': operationalReason,
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    })
    
    // Clear local draft upon confirmed backend commit
    localStorage.removeItem(`athenaeum_draft_item_${id}`)
    
    try {
      await dispatchAuditTrail('UPDATE', 'CATALOGUE', id, `Updated record details for ${editableBook.value.title}`, operationalReason, null, editableBook.value)
    } catch {}

    triggerToastNotification("Record saved successfully.", "success")
    setTimeout(() => { router.push(`/details/${id}`) }, 800)
  } catch {
    triggerToastNotification("Write Failure: Transaction rejected by registry.", "error")
  } finally {
    isSaving.value = false
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleEditorKeyboard)
  if (draftTimer) clearTimeout(draftTimer)
  if (toastTimeout) clearTimeout(toastTimeout)
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
})

onMounted(() => {
  window.addEventListener('keydown', handleEditorKeyboard)
  fetchRecordData()
})
</script>

<style scoped>
:global(*) { box-sizing: border-box; }

.edit-page {
  --page: #201424;
  --surface: #2e1d33;
  --surface-soft: #38233e;
  --ink: #fbf5fc;
  --muted: #bda5c7;
  --line: #4d2f59;
  --line-strong: #6c417d;
  --accent: #a855f7;
  --accent-dark: #9333ea;
  --accent-pale: #432454;
  min-height: 100vh;
  background: var(--page);
  color: var(--ink);
  font-family: inherit;
  padding-bottom: 96px;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  background: #28172d;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 100;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.button-back {
  background: #392242;
  border: 1px solid var(--line-strong);
  color: #fbf5fc;
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.button-back:hover {
  background: var(--accent);
  color: #fff;
}

.kbd-badge {
  background: #201424;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  padding: 0.08rem 0.35rem;
  font-size: 0.65rem;
  color: #e9d5ff;
}

.topbar-title h1 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #ffffff;
}

.eyebrow {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #d8b4fe;
  display: block;
}

.topbar-meta {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.8rem;
  color: var(--muted);
}

.record-pill {
  padding: 0.25rem 0.75rem;
  background: #392242;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-weight: 600;
  color: #ffffff;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #e11d48;
}

.record-identity-bar {
  position: sticky;
  top: 64px;
  z-index: 90;
  display: flex;
  gap: 1.5rem;
  padding: 0.55rem 2rem;
  background: #2b1830;
  border-bottom: 1px solid var(--line);
  font-size: 0.75rem;
}

.identity-item {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.identity-item span {
  color: var(--muted);
  text-transform: uppercase;
  font-weight: 700;
  font-size: 0.65rem;
}

.identity-item strong {
  color: #ffffff;
  font-family: monospace;
}

.highlight-code {
  color: #fb7185 !important;
}

.workspace {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 1.5rem;
  max-width: 1560px;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.sidebar {
  position: sticky;
  top: 120px;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1.15rem;
}

.sidebar-intro h2 {
  font-size: 1.05rem;
  margin: 0.35rem 0;
  color: #ffffff;
}

.sidebar-intro p {
  font-size: 0.75rem;
  color: var(--muted);
  margin-bottom: 0.95rem;
}

.search-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--muted);
  margin-bottom: 0.35rem;
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.35rem 0.65rem;
  margin-bottom: 1rem;
}

.search-wrap input {
  background: transparent;
  border: none;
  outline: none;
  color: #ffffff;
  font-size: 0.82rem;
  width: 100%;
}

.section-nav {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #fbf5fc;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: var(--surface-soft);
}

.nav-item.active {
  background: var(--accent-pale);
  border-color: var(--accent);
}

.nav-number {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--accent);
}

.nav-copy {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.nav-copy strong {
  font-size: 0.8rem;
}

.nav-copy small {
  font-size: 0.68rem;
  color: var(--muted);
}

.change-count {
  background: #db2777;
  color: #fff;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 999px;
}

.sidebar-bottom {
  margin-top: 1.25rem;
  padding-top: 0.95rem;
  border-top: 1px solid var(--line);
}

.change-summary {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.65rem;
  font-size: 0.75rem;
}

.text-button {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}

.text-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.editor-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 1.25rem;
}

.editor-heading h2 {
  font-size: 1.45rem;
  margin: 0.25rem 0 0.15rem 0;
  color: #ffffff;
}

.editor-heading p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--muted);
}

.heading-actions {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.change-chip {
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--line);
  font-size: 0.75rem;
  color: var(--muted);
}

.change-chip.has-changes {
  background: #9d174d;
  color: #ffffff;
  border-color: #f43f5e;
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-section, .review-panel {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1.4rem;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding-bottom: 0.85rem;
  margin-bottom: 1.15rem;
  border-bottom: 1px solid var(--line);
}

.section-index {
  width: 32px;
  height: 32px;
  background: var(--accent-pale);
  color: var(--accent);
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 0.8rem;
}

.section-heading h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #f472b6;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.section-heading p {
  margin: 0.15rem 0 0 0;
  font-size: 0.78rem;
  color: var(--muted);
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.15rem 1.25rem;
}

.span-2 {
  grid-column: span 2;
}

.field-block {
  display: flex;
  flex-direction: column;
}

.label-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.label-line label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #e9d5ff;
}

.required-star {
  color: #f43f5e;
}

.modified-label {
  font-size: 0.65rem;
  background: #9d174d;
  color: #fff;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.validation-error-tag {
  font-size: 0.68rem;
  color: #f87171;
  font-weight: 700;
}

.input-control {
  background: #231527;
  border: 1px solid var(--line-strong);
  color: #ffffff;
  padding: 0.55rem 0.8rem;
  border-radius: 8px;
  font-size: 0.85rem;
  outline: none;
  transition: all 0.15s ease;
}

.input-control:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(168, 85, 247, 0.25);
}

.input-invalid {
  border-color: #ef4444 !important;
  background: #34181f !important;
}

.custom-subfield {
  margin-top: 0.45rem;
  border-style: dashed;
}

.field-help {
  margin: 0.35rem 0 0 0;
  font-size: 0.7rem;
  color: var(--muted);
}

.field-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.35rem;
  font-size: 0.7rem;
  color: var(--muted);
}

.field-footer button {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 0.7rem;
  font-weight: 700;
}

/* Genre Combobox Styles */
.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}

.genre-chip {
  background: #9333ea;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.2rem 0.55rem;
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.genre-chip button {
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 0;
  font-size: 0.85rem;
  line-height: 1;
}

.clear-genres {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 0.7rem;
  cursor: pointer;
}

.combobox-entry-row {
  display: flex;
  gap: 0.5rem;
}

.quick-genre-hints {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.6rem;
}

.quick-genre-hints small {
  font-size: 0.68rem;
  color: var(--muted);
  margin-right: 0.25rem;
}

.quick-pill {
  background: #392242;
  border: 1px solid var(--line);
  color: #d8b4fe;
  padding: 0.18rem 0.5rem;
  border-radius: 6px;
  font-size: 0.68rem;
  cursor: pointer;
  transition: all 0.12s ease;
}

.quick-pill:hover, .quick-pill.selected {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

/* Dimensions Row */
.dimension-input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.dim-box {
  width: 90px;
  text-align: center;
}

.dim-separator {
  font-size: 1.1rem;
  color: var(--accent);
  font-weight: 700;
}

.dim-unit-select {
  width: 80px;
}

.input-with-unit {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-unit .input-control {
  width: 100%;
  padding-right: 3.5rem;
}

.unit-tag {
  position: absolute;
  right: 0.8rem;
  font-size: 0.75rem;
  color: var(--muted);
  pointer-events: none;
}

.advanced-drawer {
  background: #25162a;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.65rem 0.95rem;
  font-size: 0.8rem;
}

.advanced-drawer summary {
  cursor: pointer;
  font-weight: 700;
  color: #d8b4fe;
  user-select: none;
}

.drawer-grid {
  margin-top: 0.85rem;
}

/* Button & Savebar */
.button {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.button-quiet {
  background: #362240;
  border-color: var(--line-strong);
  color: #fbf5fc;
}

.button-quiet:hover {
  background: #472b54;
}

.button-primary {
  background: var(--accent);
  color: #fff;
}

.savebar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: #28172d;
  border-top: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  z-index: 100;
}

.save-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #734e87;
  display: inline-block;
  margin-right: 0.5rem;
}

.save-indicator.dirty {
  background: #e11d48;
  box-shadow: 0 0 6px #e11d48;
}

.button-save-action {
  background: #c026d3;
  color: #ffffff;
  border-color: #e879f9;
}

.button-save-action:hover:not(:disabled) {
  background: #a21caf;
}

.button-save-action:disabled {
  background: #3b2842;
  border-color: var(--line);
  color: var(--muted);
  cursor: not-allowed;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(14, 7, 18, 0.78);
  display: grid;
  place-items: center;
  z-index: 1000;
  padding: 1.5rem;
}

.confirm-modal {
  background: #321c38;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  padding: 1.6rem;
  max-width: 440px;
  width: 100%;
}

.modal-mark {
  width: 36px;
  height: 36px;
  background: var(--accent-pale);
  color: var(--accent);
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.65rem;
}

.confirm-modal h2 {
  margin: 0.25rem 0 0.5rem 0;
  font-size: 1.25rem;
  color: #fff;
}

.confirm-modal p {
  font-size: 0.8rem;
  color: var(--muted);
  line-height: 1.5;
  margin-bottom: 1rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  margin-top: 1rem;
}

.toast-message {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  background: #362240;
  border: 1px solid var(--line-strong);
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-size: 0.82rem;
  z-index: 2000;
}

.toast-message.success {
  border-left: 4px solid #10b981;
}

.toast-message.error {
  border-left: 4px solid #ef4444;
}

/* Ensure the input container can hold an absolute dropdown */
.relative-position {
  position: relative;
}

/* Floating Suggestion Menu */
.suggestion-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 50;
  margin-top: 4px;
  background: #2b1830;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
  max-height: 240px;
  overflow-y: auto;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* Individual Suggestion Item */
.suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.suggestion-item:hover {
  background: var(--accent-pale);
}

/* Avatar Badge (First Letter) */
.suggestion-avatar {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 50%;
  background: #472b54;
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.8rem;
  border: 1px solid var(--line-strong);
}

.suggestion-item:hover .suggestion-avatar {
  background: var(--accent);
  color: #ffffff;
}

/* Text Container (Name & Subtitle) */
.suggestion-copy {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.suggestion-copy strong {
  font-size: 0.85rem;
  font-weight: 600;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-copy small {
  font-size: 0.72rem;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Status Badge (VERIFIED, etc.) */
.suggestion-status {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 7px;
  border-radius: 4px;
  background: #1e3a2f;
  color: #34d399;
  border: 1px solid #065f46;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: static;
    max-height: none;
  }
  .field-grid {
    grid-template-columns: 1fr;
  }
  .span-2 {
    grid-column: span 1;
  }
}
</style>