<template>
  <main class="edit-page">
    <div v-if="loading" class="loading-state"><span class="loader"></span><p>Loading catalogue record…</p></div>
    <template v-else-if="editableBook">
      <header class="topbar">
        <div class="brand-mark">C</div>
        <div class="topbar-title"><span class="eyebrow">CATALOGUE MANAGEMENT</span><h1>Edit record</h1></div>
        <div class="topbar-meta"><span class="record-pill">Record {{ editableBook.serial_no || editableBook.record_id || route.params.id }}</span><span class="status-dot"></span><span>Editing</span></div>
      </header>

      <section class="record-identity-bar" aria-label="Read-only record identifiers">
        <div class="identity-heading"><span class="identity-mark" aria-hidden="true">ID</span><div><strong>Record identifiers</strong><small>Reference details · read-only</small></div></div>
        <div class="identity-value"><span>Record identifier</span><strong>{{ editableBook.serial_no || 'Not assigned' }}</strong></div>
        <div class="identity-value"><span>Accession ID</span><strong>{{ editableBook.accession_no || 'Not assigned' }}</strong></div>
        <div class="identity-value"><span>Record ID</span><strong>{{ editableBook.record_id || 'Not assigned' }}</strong></div>
        <div class="identity-value"><span>Work ID</span><strong>{{ editableBook.work_id || 'Not assigned' }}</strong></div>
      </section>

      <div class="workspace">
        <aside class="sidebar">
          <div class="sidebar-intro"><span class="eyebrow">WORKSPACE</span><h2>Record details</h2><p>Update bibliographic information and review your changes before saving.</p></div>
          <label class="search-label" for="field-search">Find a field</label>
          <div class="search-wrap"><span aria-hidden="true">⌕</span><input id="field-search" v-model="searchQuery" placeholder="Search fields…" /></div>
          <nav class="section-nav" aria-label="Edit sections">
            <button v-for="item in [
              {key:'work',number:'01',label:'Core details',hint:'Title and creator'},
              {key:'taxonomy',number:'02',label:'Classification',hint:'Category and genres'},
              {key:'languages',number:'03',label:'Languages',hint:'Text and original'},
              {key:'publication',number:'04',label:'Publication',hint:'Publisher and ISBN'},
              {key:'location',number:'05',label:'Location',hint:'Shelf and call number'},
              {key:'notes',number:'06',label:'Notes',hint:'Additional details'}
            ]" :key="item.key" type="button" class="nav-item" :class="{active: activeTab === item.key}" @click="setTab(item.key as TabKey)">
              <span class="nav-number">{{ item.number }}</span><span class="nav-copy"><strong>{{ item.label }}</strong><small>{{ item.hint }}</small></span><span v-if="tabChangesCount(item.key as TabKey)" class="change-count">{{ tabChangesCount(item.key as TabKey) }}</span><span v-else class="nav-arrow">›</span>
            </button>
          </nav>
          <div class="sidebar-bottom"><div class="change-summary"><span class="summary-icon">✳</span><div><strong>{{ modifiedFieldsList.length }} changes</strong><small>Compared with original record</small></div></div><button class="text-button" type="button" :disabled="!modifiedFieldsList.length" @click="revertAllModifications">Reset all changes</button></div>
        </aside>

        <section class="editor-area">
          <div class="editor-heading"><div><span class="eyebrow">CATALOGUE / EDIT</span><h2>{{ ({work:'Core details',taxonomy:'Classification',languages:'Languages',publication:'Publication',location:'Location',notes:'Notes'} as Record<string,string>)[activeTab] }}</h2><p>Fields marked with <span class="required-star">*</span> are required.</p></div><div class="heading-actions"><span class="change-chip" :class="{'has-changes': modifiedFieldsList.length}">{{ modifiedFieldsList.length ? `${modifiedFieldsList.length} modified` : 'No changes yet' }}</span><button class="button button-quiet" type="button" @click="showAllSections = !showAllSections; searchQuery = ''">{{ showAllSections ? 'Show one section' : 'View all sections' }}</button></div></div>

          <div v-if="searchQuery.trim()" class="search-results-note">Showing fields matching “{{ searchQuery }}”. <button type="button" @click="searchQuery = ''">Clear search</button></div>
          <div v-if="showAllSections || searchQuery.trim()" class="all-sections-note">All sections are shown. Choose a section from the left to return to focused editing.</div>

          <div class="form-stack">
            <section v-if="isSectionVisible('work',['title','author','creator','core details'])" class="form-section">
              <div class="section-heading"><div class="section-index">01</div><div><h3>Core details</h3><p>The main identifying details for this work.</p></div></div>
              <div class="field-grid">
                <div id="wrap-title" class="field-block span-2" :class="{'field-modified':isFieldModified('title')}"><div class="label-line"><label for="field-title">Work title <span class="required-star">*</span></label><span v-if="isFieldModified('title')" class="modified-label">Modified</span></div><input id="field-title" v-model="editableBook.title" class="input-control" placeholder="Enter the full title" /><div v-if="isFieldModified('title')" class="field-footer"><span>Original: {{ pristineBook.title || 'Empty' }}</span><button type="button" @click="revertSingleField('title')">Undo</button></div></div>
                <div id="wrap-author" class="field-block span-2 relative-position" :class="{'field-modified':isFieldModified('author')}"><div class="label-line"><label for="field-author">Author / creator</label><span v-if="isFieldModified('author')" class="modified-label">Modified</span></div><input id="field-author" v-model="editableBook.author" class="input-control" autocomplete="off" placeholder="Search authority names…" @input="searchAuthorsDebounced" @focus="searchAuthorsDebounced" @blur="hideSuggestionsWithDelay('author')" /><div v-if="showAuthorSuggestions && authorSuggestions.length" class="suggestion-list"><button v-for="person in authorSuggestions" :key="person.authority_id" type="button" class="suggestion-item" @mousedown.prevent="selectSuggestion('author',person)"><span class="suggestion-avatar">{{ (person.preferred_name || '?').slice(0,1) }}</span><span class="suggestion-copy"><strong>{{ person.preferred_name }}</strong><small>{{ person.authority_code }}<span v-if="person.full_name"> · {{ person.full_name }}</span></small></span><span class="suggestion-status">{{ person.status }}</span></button></div><p class="field-help">Type at least two characters to search verified authority records.</p><div v-if="isFieldModified('author')" class="field-footer"><span>Original: {{ pristineBook.author || 'Empty' }}</span><button type="button" @click="revertSingleField('author')">Undo</button></div></div>
              </div>
            </section>

            <section v-if="isSectionVisible('taxonomy',['classification','category','ddc','genre','taxonomy'])" class="form-section">
              <div class="section-heading"><div class="section-index">02</div><div><h3>Classification</h3><p>Organise the work for discovery and shelving.</p></div></div>
              <div class="field-grid"><div class="field-block" :class="{'field-modified':isFieldModified('category')}"><div class="label-line"><label for="field-category">Collection category</label><span v-if="isFieldModified('category')" class="modified-label">Modified</span></div><select id="field-category" v-model="editableBook.category" class="input-control">
                  <option value="">Choose a category</option>
                  <option v-if="editableBook.category && !categoryOptions.includes(editableBook.category)" :value="editableBook.category">{{ editableBook.category }}</option>
                  <option v-for="category in categoryOptions" :key="category" :value="category">{{ category }}</option>
                </select></div><div class="field-block" :class="{'field-modified':isFieldModified('ddc')}"><div class="label-line"><label for="field-ddc">Dewey Decimal (DDC)</label><span v-if="isFieldModified('ddc')" class="modified-label">Modified</span></div><input id="field-ddc" v-model="editableBook.ddc" class="input-control" placeholder="e.g. 823.914" /></div>
                <div class="field-block span-2" :class="{'field-modified':isFieldModified('genre')}"><div class="label-line"><label>Genre tags</label><span v-if="isFieldModified('genre')" class="modified-label">Modified</span></div><div class="genre-chips" v-if="liveCompiledGenreChips.length"><span v-for="chip in liveCompiledGenreChips" :key="chip" class="genre-chip">{{ chip }}<button type="button" :aria-label="`Remove ${chip}`" @click="removeGenreChip(chip)">×</button></span><button class="clear-genres" type="button" @click="clearAllGenres">Clear all</button></div><div class="field-grid genre-selects"><div class="field-block"><label for="genre-a">Literary genre</label><select id="genre-a" v-model="selectedGroupAGenre" class="input-control" @change="syncGenreSelection"><option value="">Choose a genre</option><option v-for="genre in genreGroupA" :key="genre" :value="genre">{{ genre }}</option></select></div><div class="field-block"><label for="genre-b">Subject / form</label><select id="genre-b" v-model="selectedGroupBGenre" class="input-control" @change="syncGenreSelection"><option value="">Choose a subject</option><option v-for="genre in genreGroupB" :key="genre" :value="genre">{{ genre }}</option></select></div><div class="field-block"><label for="genre-c">Community genre</label><select id="genre-c" v-model="selectedGroupCGenre" class="input-control" @change="syncGenreSelection"><option value="">Choose a genre</option><option v-for="genre in dynamicCommunityGenres" :key="genre" :value="genre">{{ genre }}</option><option value="CUSTOM_MANUAL_OVERRIDE">Enter manually…</option></select></div><div v-if="showCustomManualGenreField" class="field-block"><label for="genre-custom">Custom genre</label><input id="genre-custom" v-model="customManualGenreText" class="input-control" placeholder="Enter genre" @input="syncManualGenreInput" /></div></div><div v-if="isFieldModified('genre')" class="field-footer"><span>Original: {{ pristineBook.genre || 'Empty' }}</span><button type="button" @click="revertSingleField('genre')">Undo</button></div></div>
              </div>
            </section>

            <section v-if="isSectionVisible('languages',['language','original language','languages'])" class="form-section"><div class="section-heading"><div class="section-index">03</div><div><h3>Languages</h3><p>Record the language of this edition and its source.</p></div></div><div class="field-grid"><div class="field-block" :class="{'field-modified':isFieldModified('language')}"><div class="label-line"><label for="field-language">Text language <span class="required-star">*</span></label><span v-if="isFieldModified('language')" class="modified-label">Modified</span></div><select id="field-language" v-model="editableBook.language" class="input-control" required>
                  <option value="">Choose a language</option>
                  <option v-if="editableBook.language && !languageOptions.includes(editableBook.language)" :value="editableBook.language">{{ editableBook.language }}</option>
                  <option v-for="language in languageOptions" :key="language" :value="language">{{ language }}</option>
                </select></div><div class="field-block" :class="{'field-modified':isFieldModified('original_language')}"><div class="label-line"><label for="field-original-language">Original source language</label><span v-if="isFieldModified('original_language')" class="modified-label">Modified</span></div><select id="field-original-language" v-model="editableBook.original_language" class="input-control">
                  <option value="">Choose a language (optional)</option>
                  <option v-if="editableBook.original_language && !languageOptions.includes(editableBook.original_language)" :value="editableBook.original_language">{{ editableBook.original_language }}</option>
                  <option v-for="language in languageOptions" :key="language" :value="language">{{ language }}</option>
                </select></div></div></section>

            <section v-if="isSectionVisible('publication',['publication','publisher','year','isbn','imprint'])" class="form-section"><div class="section-heading"><div class="section-index">04</div><div><h3>Publication</h3><p>Edition, publisher and standard identifiers.</p></div></div><div class="field-grid"><div class="field-block relative-position" :class="{'field-modified':isFieldModified('publisher')}"><div class="label-line"><label for="field-publisher">Publisher / imprint</label><span v-if="isFieldModified('publisher')" class="modified-label">Modified</span></div><input id="field-publisher" v-model="editableBook.publisher" class="input-control" autocomplete="off" placeholder="Publisher name" @input="searchPublishersDebounced" @focus="searchPublishersDebounced" @blur="hideSuggestionsWithDelay('publisher')" /><div v-if="showPublisherSuggestions && publisherSuggestions.length" class="suggestion-list"><button v-for="publisher in publisherSuggestions" :key="publisher" type="button" class="suggestion-item" @mousedown.prevent="selectSuggestion('publisher',publisher)"><span class="suggestion-copy"><strong>{{ publisher }}</strong></span><span class="suggestion-status">Use</span></button></div></div><div class="field-block" :class="{'field-modified':isFieldModified('year')}"><div class="label-line"><label for="field-year">Publication year</label><span v-if="isFieldModified('year')" class="modified-label">Modified</span></div><input id="field-year" v-model="editableBook.year" class="input-control" type="text" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="YYYY" aria-describedby="field-year-help" @input="limitYearLength" />
<div id="field-year-help" class="field-help">Enter a whole-number publication year (1000–{{ new Date().getFullYear() }}).</div></div><div class="field-block span-2" :class="{'field-modified':isFieldModified('isbn')}"><div class="label-line"><label for="field-isbn">ISBN</label><span v-if="isFieldModified('isbn')" class="modified-label">Modified</span></div><input id="field-isbn" v-model="editableBook.isbn" class="input-control" placeholder="ISBN-10 or ISBN-13" /></div></div></section>

            <section v-if="isSectionVisible('location',['location','shelf','call number','accession'])" class="form-section"><div class="section-heading"><div class="section-index">05</div><div><h3>Location</h3><p>Where the physical item is stored.</p></div></div><div class="field-grid"><div class="field-block" :class="{'field-modified':isFieldModified('shelf')}"><div class="label-line"><label for="field-shelf">Shelf location</label><span v-if="isFieldModified('shelf')" class="modified-label">Modified</span></div><input id="field-shelf" v-model="editableBook.shelf" class="input-control" placeholder="Shelf or collection location" /></div><div class="field-block" :class="{'field-modified':isFieldModified('call_no')}"><div class="label-line"><label for="field-call-no">Call number</label><span v-if="isFieldModified('call_no')" class="modified-label">Modified</span></div><input id="field-call-no" v-model="editableBook.call_no" class="input-control" placeholder="Classification / call number" /></div></div></section>

            <section v-if="isSectionVisible('notes',['notes','remarks','conservation'])" class="form-section"><div class="section-heading"><div class="section-index">06</div><div><h3>Notes</h3><p>Additional information for cataloguers and collection staff.</p></div></div><div class="field-block" :class="{'field-modified':isFieldModified('notes')}"><div class="label-line"><label for="field-notes">Catalogue notes</label><span v-if="isFieldModified('notes')" class="modified-label">Modified</span></div><textarea id="field-notes" v-model="editableBook.notes" class="input-control textarea-control" rows="5" placeholder="Add relevant notes about this item…"></textarea><div v-if="isFieldModified('notes')" class="field-footer"><span>Original: {{ pristineBook.notes || 'Empty' }}</span><button type="button" @click="revertSingleField('notes')">Undo</button></div></div></section>
          </div>

          <section v-if="modifiedFieldsList.length" class="review-panel"><div class="review-heading"><div><span class="eyebrow">REVIEW</span><h3>Changes in this session</h3></div><button class="text-button" type="button" @click="revertAllModifications">Discard all</button></div><div v-for="change in modifiedFieldsList" :key="change.key" class="review-row"><div><strong>{{ change.label }}</strong><small>{{ change.tabLabel }}</small></div><div class="review-values"><span>{{ change.oldValue || 'Empty' }}</span><span class="review-arrow">→</span><span>{{ change.newValue || 'Empty' }}</span></div><button type="button" class="undo-icon" :aria-label="`Undo ${change.label}`" @click="revertSingleField(change.key)">↶</button></div></section>
        </section>
      </div>

      <footer class="savebar"><div class="savebar-info"><span class="save-indicator" :class="{'dirty':modifiedFieldsList.length}"></span><span>{{ modifiedFieldsList.length ? `${modifiedFieldsList.length} unsaved field changes` : 'No unsaved changes' }}</span></div><div class="savebar-actions"><button class="button button-quiet" type="button" @click="previewOpen = true">Preview document</button><button class="button button-quiet" type="button" @click="triggerActionConfirm('abort')">Cancel</button><button class="button button-save-action" type="button" :disabled="!modifiedFieldsList.length" :aria-disabled="!modifiedFieldsList.length" @click="triggerActionConfirm('commit')">{{ modifiedFieldsList.length ? 'Review & save' : 'No changes to save' }} <span aria-hidden="true">→</span></button></div></footer>
    </template>

    <div v-if="previewOpen && editableBook" class="preview-backdrop" @click.self="previewOpen = false">
      <section class="document-preview" role="dialog" aria-modal="true" aria-labelledby="preview-title">
        <header class="preview-toolbar"><div><span class="eyebrow">CATALOGUE / DOCUMENT PREVIEW</span><h2 id="preview-title">Review edited record</h2><p>Changed fields are highlighted. Review the full record before saving.</p></div><button type="button" class="preview-close" aria-label="Close preview" @click="previewOpen = false">×</button></header>
        <article class="document-sheet">
          <div class="document-brand"><span class="document-monogram">C</span><div><strong>CATALOGUE RECORD</strong><small>Bibliographic record · edit preview</small></div><span class="document-record-id">Record {{ editableBook.serial_no || editableBook.record_id || route.params.id }}</span></div>
          <h1 class="document-title">{{ editableBook.title || 'Untitled work' }}</h1>
          <p class="document-subtitle">{{ editableBook.author || 'Creator not specified' }}</p>
          <div class="document-rule"></div>
          <section class="document-group"><h3>01 · Core details</h3><div class="document-fields"><div v-for="field in [{key:'title',label:'Work title'},{key:'author',label:'Author / creator'}]" :key="field.key" class="document-field" :class="{'document-field-changed':isFieldModified(field.key)}"><span class="document-field-label">{{ field.label }}</span><div v-if="isFieldModified(field.key)" class="document-value-comparison"><div class="document-previous"><small>PREVIOUS VALUE</small><strong>{{ pristineBook[field.key] || '—' }}</strong></div><div class="document-current"><small>NEW VALUE</small><strong>{{ editableBook[field.key] || '—' }}</strong></div></div><strong v-else class="document-current-value">{{ editableBook[field.key] || '—' }}</strong><em v-if="isFieldModified(field.key)">EDITED</em></div></div></section>
          <section class="document-group"><h3>02 · Classification</h3><div class="document-fields"><div v-for="field in [{key:'category',label:'Collection category'},{key:'ddc',label:'Dewey Decimal (DDC)'},{key:'genre',label:'Genre tags'}]" :key="field.key" class="document-field" :class="{'document-field-changed':isFieldModified(field.key)}"><span class="document-field-label">{{ field.label }}</span><div v-if="isFieldModified(field.key)" class="document-value-comparison"><div class="document-previous"><small>PREVIOUS VALUE</small><strong>{{ pristineBook[field.key] || '—' }}</strong></div><div class="document-current"><small>NEW VALUE</small><strong>{{ editableBook[field.key] || '—' }}</strong></div></div><strong v-else class="document-current-value">{{ editableBook[field.key] || '—' }}</strong><em v-if="isFieldModified(field.key)">EDITED</em></div></div></section>
          <section class="document-group"><h3>03 · Languages</h3><div class="document-fields"><div v-for="field in [{key:'language',label:'Text language'},{key:'original_language',label:'Original source language'}]" :key="field.key" class="document-field" :class="{'document-field-changed':isFieldModified(field.key)}"><span class="document-field-label">{{ field.label }}</span><div v-if="isFieldModified(field.key)" class="document-value-comparison"><div class="document-previous"><small>PREVIOUS VALUE</small><strong>{{ pristineBook[field.key] || '—' }}</strong></div><div class="document-current"><small>NEW VALUE</small><strong>{{ editableBook[field.key] || '—' }}</strong></div></div><strong v-else class="document-current-value">{{ editableBook[field.key] || '—' }}</strong><em v-if="isFieldModified(field.key)">EDITED</em></div></div></section>
          <section class="document-group"><h3>04 · Publication</h3><div class="document-fields"><div v-for="field in [{key:'publisher',label:'Publisher / imprint'},{key:'year',label:'Publication year'},{key:'isbn',label:'ISBN'}]" :key="field.key" class="document-field" :class="{'document-field-changed':isFieldModified(field.key)}"><span class="document-field-label">{{ field.label }}</span><div v-if="isFieldModified(field.key)" class="document-value-comparison"><div class="document-previous"><small>PREVIOUS VALUE</small><strong>{{ pristineBook[field.key] || '—' }}</strong></div><div class="document-current"><small>NEW VALUE</small><strong>{{ editableBook[field.key] || '—' }}</strong></div></div><strong v-else class="document-current-value">{{ editableBook[field.key] || '—' }}</strong><em v-if="isFieldModified(field.key)">EDITED</em></div></div></section>
          <section class="document-group"><h3>05 · Location</h3><div class="document-fields"><div v-for="field in [{key:'shelf',label:'Shelf location'},{key:'call_no',label:'Call number'}]" :key="field.key" class="document-field" :class="{'document-field-changed':isFieldModified(field.key)}"><span class="document-field-label">{{ field.label }}</span><div v-if="isFieldModified(field.key)" class="document-value-comparison"><div class="document-previous"><small>PREVIOUS VALUE</small><strong>{{ pristineBook[field.key] || '—' }}</strong></div><div class="document-current"><small>NEW VALUE</small><strong>{{ editableBook[field.key] || '—' }}</strong></div></div><strong v-else class="document-current-value">{{ editableBook[field.key] || '—' }}</strong><em v-if="isFieldModified(field.key)">EDITED</em></div></div></section>
          <section class="document-group"><h3>06 · Notes</h3><div class="document-fields"><div class="document-field" :class="{'document-field-changed':isFieldModified('notes')}"><span class="document-field-label">Catalogue notes</span><div v-if="isFieldModified('notes')" class="document-value-comparison"><div class="document-previous"><small>PREVIOUS VALUE</small><strong class="document-long-value">{{ pristineBook.notes || '—' }}</strong></div><div class="document-current"><small>NEW VALUE</small><strong class="document-long-value">{{ editableBook.notes || '—' }}</strong></div></div><strong v-else class="document-long-value document-current-value">{{ editableBook.notes || '—' }}</strong><em v-if="isFieldModified('notes')">EDITED</em></div></div></section>
          <footer class="document-footer"><span>{{ modifiedFieldsList.length }} field(s) changed</span><span>Preview only · not yet saved</span></footer>
        </article>
        <footer class="preview-actions"><span class="preview-legend"><i></i> Highlighted fields have unsaved edits</span><button type="button" class="button button-quiet" @click="previewOpen = false">Continue editing</button><button type="button" class="button button-save-action" :disabled="!modifiedFieldsList.length" @click="previewOpen = false; triggerActionConfirm('commit')">Review & save →</button></footer>
      </section>
    </div>

    <div v-if="toast" class="toast-message" :class="toast.type" role="status">{{ toast.message }}</div>
    <div v-if="activeModalType" class="modal-backdrop" @click.self="closeModalPrompt"><section class="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><div class="modal-mark">{{ activeModalType === 'commit' ? '✓' : '↶' }}</div><span class="eyebrow">CONFIRM ACTION</span><h2 id="confirm-title">{{ activeModalType === 'commit' ? 'Save record changes?' : 'Cancel editing?' }}</h2><p>{{ activeModalType === 'commit' ? 'Your updates will be sent to the catalogue and recorded in the audit trail.' : 'You will leave this page. Any unsaved edits will be discarded.' }}</p><template v-if="activeModalType === 'commit'"><label for="change-reason">Reason for change <span class="optional-label">(optional)</span></label><textarea id="change-reason" v-model="changeReason" class="input-control textarea-control" rows="3" placeholder="Briefly describe why this record is being updated…"></textarea></template><div class="countdown-note">{{ countdownTimerSeconds > 0 ? `Confirming automatically in ${countdownTimerSeconds}s` : 'Processing…' }}</div><div class="modal-actions"><button class="button button-quiet" type="button" @click="closeModalPrompt">Go back</button><button class="button" :class="activeModalType === 'commit' ? 'button-save-action' : 'button-primary'" type="button" :disabled="activeModalType === 'commit' && !modifiedFieldsList.length" @click="executeConfirmedAction">{{ activeModalType === 'commit' ? 'Confirm save' : 'Discard edits' }}</button></div></section></div>
  </main>
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
const previewOpen = ref(false)

const activeModalType = ref<'commit' | 'abort' | null>(null)
const changeReason = ref<string>("")
const countdownTimerSeconds = ref<number>(0)
let nativeIntervalReference: any = null

const selectedAuthority = ref<AuthoritySuggestion | null>(null)

interface ToastNotification {
  message: string
  type: 'success' | 'error'
}
const toast = ref<ToastNotification | null>(null)

const categoryOptions = ["Fiction", "Non-Fiction", "Reference", "Religious", "Poetry"]
const languageOptions = [
  "Assamese", "Arabic", "Bengali", "Chinese", "English", "French", "German",
  "Gujarati", "Hindi", "Japanese", "Kannada", "Latin", "Malayalam", "Marathi",
  "Nepali", "Odia", "Pali", "Persian", "Prakrit", "Punjabi", "Sanskrit", "Spanish",
  "Tamil", "Telugu", "Urdu", "Other"
]

function limitYearLength(event: Event) {
  const input = event.target as HTMLInputElement
  const digits = input.value.replace(/\D/g, "").slice(0, 4)
  editableBook.value.year = digits
  input.value = digits
}

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

interface AuthoritySuggestion {
  authority_id: number
  authority_code: string
  preferred_name: string
  full_name?: string
  authority_type?: string
  status: string
}

const authorSuggestions = ref<AuthoritySuggestion[]>([])
const publisherSuggestions = ref<string[]>([])

const showAuthorSuggestions = ref(false)
const showPublisherSuggestions = ref(false)

let debounceAuthorTimeout: any = null
let debouncePublisherTimeout: any = null



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

const sectionOrder: TabKey[] = ['work', 'taxonomy', 'languages', 'publication', 'location', 'notes']

function handleEditorKeyboard(event: KeyboardEvent) {
  if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) return

  const target = event.target as HTMLElement | null
  const tagName = target?.tagName?.toLowerCase()
  const isTyping = !!target && (
    tagName === 'input' ||
    tagName === 'textarea' ||
    tagName === 'select' ||
    target.isContentEditable
  )

  if (event.key === 'Escape') {
    event.preventDefault()
    if (activeModalType.value) {
      closeModalPrompt()
    } else {
      triggerActionConfirm('abort')
    }
    return
  }

  if (event.key === 'Enter' && activeModalType.value) {
    event.preventDefault()
    executeConfirmedAction()
    return
  }

  const isMultilineOrSelect = tagName === 'textarea' || tagName === 'select' || !!target?.isContentEditable
  const suggestionsOpen = showAuthorSuggestions.value || showPublisherSuggestions.value
  if (event.key === 'Enter' && !isMultilineOrSelect && !suggestionsOpen) {
    event.preventDefault()
    triggerActionConfirm('commit')
    return
  }

  // Keep normal cursor movement and text editing intact inside form controls.
  if (isTyping || activeModalType.value) return

  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    event.preventDefault()
    const currentIndex = sectionOrder.indexOf(activeTab.value)
    const direction = event.key === 'ArrowRight' ? 1 : -1
    const nextIndex = Math.min(sectionOrder.length - 1, Math.max(0, currentIndex + direction))
    if (nextIndex !== currentIndex) {
      setTab(sectionOrder[nextIndex])
      showAllSections.value = false
      nextTick(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
    }
  }
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

interface CatalogueGenreRecord {
  id?: number | string
  work_id?: number | string
  serial_no?: number | string
  title?: string
  author?: string
  genre?: string | null
}

async function harvestSystemGenresMatrix() {
  try {
    const pageSize = 100
    let offset = 0
    const genresFound = new Set<string>()
    const seenPageSignatures = new Set<string>()

    while (true) {
      const response = await axios.get('/catalogue', {
        params: { limit: pageSize, offset }
      })

      const rawItems: unknown = response.data?.data ?? response.data
      const items: CatalogueGenreRecord[] = Array.isArray(rawItems)
        ? rawItems as CatalogueGenreRecord[]
        : []

      if (items.length === 0) break

      const pageSignature = JSON.stringify(
        items.map((item: CatalogueGenreRecord) =>
          item.id ??
          item.work_id ??
          item.serial_no ??
          `${item.title ?? ''}|${item.author ?? ''}`
        )
      )

      if (seenPageSignatures.has(pageSignature)) {
        console.warn(
          'Catalogue pagination appears not to advance; stopping genre harvest.'
        )
        break
      }
      seenPageSignatures.add(pageSignature)

      items.forEach((item: CatalogueGenreRecord) => {
        if (typeof item.genre === 'string' && item.genre.trim()) {
          item.genre.split('/').forEach((g: string) => {
            const clean = g.trim().toUpperCase()
            if (
              clean &&
              !genreGroupA.value.includes(clean) &&
              !genreGroupB.value.includes(clean)
            ) {
              genresFound.add(clean)
            }
          })
        }
      })

      if (items.length < pageSize) break
      offset += items.length
    }

    dynamicCommunityGenres.value = Array.from(genresFound)
      .sort((a: string, b: string) => a.localeCompare(b))
  } catch (err) {
    console.error(
      'Failed to dynamically harvest taxonomy metrics:', err
    )
  }
}


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
      const response = await axios.get('/authority/search', {
        params: {
          q: query,
          usable_only: true,
          limit: 10
        }
      })

      authorSuggestions.value = Array.isArray(response.data)
      ? response.data
      : []

      showAuthorSuggestions.value = authorSuggestions.value.length > 0
    } catch (err) {
      console.error("Authority search failed:", err)
      authorSuggestions.value = []
    }
  }, 200)
}


function searchPublishersDebounced() {
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
  debouncePublisherTimeout = setTimeout(async () => {
    const query = editableBook.value.publisher?.trim() || ""
    if (query.length < 2) {
      publisherSuggestions.value = []
      showPublisherSuggestions.value = false
      return
    }
    try {
      const response = await axios.get(`/catalogue/publishers/search?q=${encodeURIComponent(query)}`)
      publisherSuggestions.value = response.data || []
      showPublisherSuggestions.value = publisherSuggestions.value.length > 0
    } catch (err) {
      console.error("Publisher micro-lookup breakdown:", err)
    }
  }, 200)
}


function selectSuggestion(
  type: 'author' | 'publisher',
  value: AuthoritySuggestion | string
) {
  if (type === 'author' && typeof value !== 'string') {
    editableBook.value.author = value.preferred_name

    // Keep the selected registry record available for the next step.
    selectedAuthority.value = value

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
  // Saving is only allowed when at least one tracked field differs from the original record.
  if (actionType === 'commit' && modifiedFieldsList.value.length === 0) {
    triggerToastNotification('No changes to save.', 'error')
    return
  }

  if (actionType === 'commit') {
    const year = Number(editableBook.value?.year)
    const currentYear = new Date().getFullYear()
    if (editableBook.value?.year !== null && editableBook.value?.year !== undefined && String(editableBook.value.year).trim() !== '' && (!/^\d{4}$/.test(String(editableBook.value.year)) || !Number.isInteger(year) || year < 1000 || year > currentYear)) {
      triggerToastNotification(`Year must be between 1000 and ${currentYear}.`, 'error')
      setTab('publication')
      nextTick(() => document.getElementById('field-year')?.focus())
      return
    }

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
  // Guard against saving unchanged data, including calls outside the disabled button.
  if (modifiedFieldsList.value.length === 0) {
    triggerToastNotification('No changes to save.', 'error')
    return
  }

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

  // Publication year is optional, but must be valid when provided.
  const yearValue = editableBook.value.year
  const currentYear = new Date().getFullYear()
  if (yearValue !== null && yearValue !== undefined && String(yearValue).trim() !== '') {
    const year = Number(yearValue)
    if (!/^\d{4}$/.test(String(editableBook.value.year)) || !Number.isInteger(year) || year < 1000 || year > currentYear) {
      triggerToastNotification(`Year must be between 1000 and ${currentYear}.`, 'error')
      setTab('publication')
      nextTick(() => document.getElementById('field-year')?.focus())
      return
    }
    editableBook.value.year = year
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
  window.removeEventListener('keydown', handleEditorKeyboard)
  if (nativeIntervalReference) clearInterval(nativeIntervalReference)
  if (debounceAuthorTimeout) clearTimeout(debounceAuthorTimeout)
  if (debouncePublisherTimeout) clearTimeout(debouncePublisherTimeout)
})

onMounted(() => {
  window.addEventListener('keydown', handleEditorKeyboard)
  fetchRecordData()
})
</script>

<style scoped>
/* ==========================================================================
   1. CORE PAGE VARIABLES & LAYOUT BASICS
   ================================================================---------- */
:global(*) { box-sizing: border-box; }

.edit-page {
  --page: #f1f5f9;
  --surface: #ffffff;
  --surface-soft: #f8fafc;
  --ink: #0f172a;
  --muted: #64748b;
  --line: #e2e8f0;
  --line-strong: #cbd5e1;
  --accent: #2563eb;
  --accent-dark: #1d4ed8;
  --accent-pale: #eff6ff;
  --rose: #e0e7ff;
  min-height: 100vh;
  background: var(--page);
  color: var(--ink);
  font-family: "Noto Sans Malayalam", "Noto Sans", "Nirmala UI", "Kartika", "Arial Unicode MS", sans-serif;
  padding-bottom: 84px;
}

/* ==========================================================================
   2. TYPOGRAPHY HIERARCHY (Headings, Inputs, and Field Values)
   ================================================================---------- */
/* Field Headings & Labels */
.label-line label, 
.field-block > label, 
.confirm-modal label, 
.search-label,
.document-field > .document-field-label,
.section-heading h3,
.topbar h1 {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
  font-weight: 800 !important;
  color: #7b586d !important;
  font-size: 14px;
  letter-spacing: .025em;
}

/* Field Values & Inputs */
.input-control,
.search-wrap input,
.textarea-control,
.read-only-value,
.document-field > strong, 
.document-value-comparison strong,
.document-current-value,
.review-values span {
  font-family: Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif !important;
  font-size: 15px !important;
  font-weight: 500;
  color: #20131b !important;
}

.input-control {
  width: 100%;
  min-width: 0;
  min-height: 48px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: #f7f0ed;
  padding: 10px 12px;
  outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.input-control::placeholder { color: #b0a1a8; }
.input-control:focus { border-color: var(--accent); box-shadow: 0 0 0 3px #94678320; }
.textarea-control { resize: vertical; min-height: 115px; line-height: 1.7; }

/* ==========================================================================
   3. PLAYFUL SIDEBAR STYLING
   ================================================================---------- */
.sidebar {
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
  position: sticky;
  top: 178px;
  max-height: calc(100vh - 198px);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
}

.sidebar,
.sidebar-intro h2,
.sidebar-intro p,
.search-label,
.search-wrap input {
  font-family: 'Comic Sans MS', 'Chalkboard SE', 'Comic Neue', 'Bubblegum Sans', 'Trebuchet MS', sans-serif !important;
}

.sidebar-intro {
  width: 100%;
  margin: 0 0 20px;
  padding: 0 0 18px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--line);
}
.sidebar-intro h2 { font: 700 20px Manrope, sans-serif; letter-spacing: -.04em; margin: 8px 0; }
.sidebar-intro p, .editor-heading p, .section-heading p { font-size: 13px; line-height: 1.6; color: var(--muted); margin: 0; }

.search-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f0e7e4;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  padding: 0 12px;
  margin-bottom: 18px;
  color: var(--accent);
  font-size: 20px;
  min-height: 44px;
}
.search-wrap input { width: 100%; height: 42px; border: 0; outline: 0; background: transparent; color: var(--ink); }

.section-nav {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 5px;
  width: 100%;
  margin: 0;
  padding: 0;
}

.section-nav .nav-item {
  font-family: 'Comic Sans MS', 'Chalkboard SE', 'Comic Neue', 'Trebuchet MS', sans-serif !important;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 56px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 14px !important;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease !important;
}
.section-nav .nav-item:hover { transform: translateX(4px) scale(1.02); background: #e5d8dc; }
.section-nav .nav-item.active { background-color: #f7d6e0 !important; border-color: #e0b1c5 !important; box-shadow: 0 4px 12px rgba(129, 87, 111, 0.15) !important; }
.nav-number { font-family: 'Comic Sans MS', 'Chalkboard SE', 'Trebuchet MS', sans-serif !important; font-weight: 700; letter-spacing: -0.05em; color: #a18b96; }
.section-nav .nav-item.active .nav-number { color: var(--accent); }
.nav-copy { display: grid; grid-template-columns: minmax(0, 1fr); gap: 3px; align-self: center; }
.nav-copy strong { font-size: 13px; font-weight: 700; line-height: 1.4; }
.nav-copy small { font-size: 11px; color: var(--muted); line-height: 1.4; }
.nav-arrow, .change-count { justify-self: end; }
.change-count { min-width: 20px; height: 20px; border-radius: 7px; display: grid; place-items: center; background: #e7cbd6; color: #704258; font-size: 10px; font-weight: 700; }

.sidebar-bottom { margin-top: 22px; padding: 16px 0 0; border-top: 1px solid var(--line); width: 100%; }
.change-summary { display: flex; align-items: center; gap: 10px; }
.summary-icon { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 10px; background: #e2d1da; color: var(--accent); font-size: 16px; }
.change-summary div { display: grid; gap: 3px; }
.change-summary strong { font-size: 13px; }
.change-summary small { font-size: 11px; color: var(--muted); }
.text-button { border: 0; background: transparent; color: var(--accent-dark); font: 600 11px 'DM Sans', sans-serif; padding: 9px 0; cursor: pointer; }
.text-button:disabled { opacity: .35; cursor: default; }
.sidebar-bottom > .text-button { margin-left: 42px; }

/* ==========================================================================
   4. TOPBAR & RECORD IDENTIFIER BAR
   ================================================================---------- */
.topbar {
  height: 82px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 clamp(20px, 4vw, 64px);
  background: #eee5e2;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 130;
}
.brand-mark { width: 38px; height: 38px; display: grid; place-items: center; background: var(--accent); color: white; border-radius: 12px; font: 800 19px Manrope, sans-serif; }
.topbar-title { display: flex; flex-direction: column; gap: 2px; }
.eyebrow { font-size: 11px; letter-spacing: .15em; font-weight: 700; color: var(--accent); display: block; }
.topbar h1 { margin: 0; letter-spacing: -.03em; }
.topbar-meta { margin-left: auto; display: flex; align-items: center; gap: 9px; color: var(--muted); font-size: 12px; }
.record-pill { padding: 7px 10px; border: 1px solid var(--line); border-radius: 8px; background: #f0e7e4; color: var(--ink); }
.status-dot, .save-indicator { width: 7px; height: 7px; border-radius: 50%; background: #b7a3ad; display: inline-block; }

/* Record Identifier Bar */
.record-identity-bar {
  position: sticky;
  top: 82px;
  z-index: 120;
  display: grid;
  grid-template-columns: minmax(190px, 1.15fr) repeat(4, minmax(120px, 1fr));
  align-items: stretch;
  margin: 0;
  padding: 12px clamp(20px, 3vw, 44px);
  background: #eee2e5f5;
  border-top: 1px solid #d9c4cc;
  border-bottom: 1px solid #d2b7c2;
  box-shadow: 0 5px 16px rgba(73, 62, 67, .09);
  backdrop-filter: blur(12px);
}
.identity-heading { display: flex; align-items: center; gap: 11px; min-width: 0; padding-right: 16px; }
.identity-mark { display: grid; place-items: center; flex: 0 0 38px; height: 38px; border-radius: 11px; background: #946783; color: #fff; font: 800 11px 'DM Sans', sans-serif; letter-spacing: .04em; }
.identity-heading > div { display: grid; gap: 4px; min-width: 0; }
.identity-heading strong { font-family: 'Trebuchet MS', 'Segoe UI', sans-serif !important; font-weight: 700 !important; font-size: 12px !important; color: #493e43 !important; }
.identity-heading small { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important; font-size: 10px !important; letter-spacing: 0.1em !important; color: #7b4f69 !important; }
.identity-value { display: flex; flex-direction: column; justify-content: center; gap: 6px; min-width: 0; padding: 3px 15px; border-left: 1px solid #d5c0c8; }
.identity-value span { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important; font-size: 10px !important; font-weight: 800; letter-spacing: 0.1em !important; text-transform: uppercase; color: #7b4f69 !important; }

/* Unique Selector Rule for Identifier Bar Values Color & Font */
.record-identity-bar .identity-value strong {
  font-family: Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
  color: #20131b !important;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

/* ==========================================================================
   5. WORKSPACE & EDITOR CONTENT AREA
   ================================================================---------- */
.workspace {
  display: grid;
  grid-template-columns: minmax(230px, 250px) minmax(0, 1fr);
  column-gap: 28px;
  align-items: start;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 28px clamp(20px, 3vw, 44px) 42px;
}

.editor-area { width: 100%; min-width: 0; margin: 0; }
.editor-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; margin: 0 0 24px; }
.editor-heading h2 { font: 800 clamp(25px, 3vw, 32px) Manrope, sans-serif; letter-spacing: -.055em; margin: 7px 0 6px; }
.required-star { color: #a94e6c; }

.heading-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
.change-chip { font-size: 11px; color: var(--muted); padding: 8px 10px; border: 1px solid var(--line); background: #f0e7e4; border-radius: 8px; white-space: nowrap; }
.change-chip.has-changes { background: #ead3dc; border-color: #ebcbd6; color: #87465f; }

.button { min-height: 39px; border-radius: 9px; padding: 0 14px; display: inline-flex; align-items: center; justify-content: center; gap: 9px; font: 700 12px 'DM Sans', sans-serif; cursor: pointer; transition: background .15s, border-color .15s; }
.button-quiet { border: 1px solid var(--line-strong); background: #f0e7e4; color: #6d5963; }
.button-quiet:hover { background: #f7eef2; }
.button-primary { border: 1px solid var(--accent); background: var(--accent); color: #fff; }
.button-primary:hover { background: var(--accent-dark); }

.form-stack { display: grid; gap: 18px; }
.form-section, .review-panel { background: #f0e7e4; border: 1px solid var(--line); border-radius: 14px; padding: 24px clamp(18px, 3vw, 30px); box-shadow: 0 3px 12px #5f40500a; min-width: 0; }
.section-heading { display: flex; align-items: center; gap: 15px; padding-bottom: 19px; margin-bottom: 20px; border-bottom: 1px solid #eee4e7; }
.section-index { flex: 0 0 36px; width: 36px; height: 36px; display: grid; place-items: center; background: #e2d1da; border-radius: 9px; color: var(--accent-dark); font: 800 11px Manrope, sans-serif; }
.section-heading h3 { line-height: 1.35; margin: 0 0 4px; }
.section-heading p { line-height: 1.5; }

.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px 18px; }
.field-block { min-width: 0; position: relative; }
.span-2 { grid-column: span 2; }
.label-line { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.label-line label { margin-bottom: 8px; }

.field-help { font-size: 13px; color: var(--muted); margin: 9px 0 0; line-height: 1.5; }
.read-only-value { min-height: 43px; height: 43px; display: flex; align-items: center; border: 1px dashed var(--line-strong); border-radius: 8px; background: #e8ddda; padding: 10px 12px; font-size: 12px; }
.field-modified { padding: 10px; border: 1px solid #d6b2c1; background: #f0e1e5; border-radius: 10px; margin: -10px; }
.modified-label { font-size: 9px; font-weight: 700; color: #704258; background: #e7cbd6; padding: 4px 7px; border-radius: 5px; margin-bottom: 7px; }
.field-footer { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-top: 8px; font-size: 10px; color: var(--muted); }
.field-footer span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.field-footer button { border: 0; background: transparent; color: var(--accent-dark); font-size: 10px; font-weight: 700; cursor: pointer; }

#wrap-author { display: flex; flex-direction: column; gap: 0; padding-bottom: 2px; }
#wrap-author .input-control { flex: 0 0 auto; }
#wrap-author .field-footer { margin-top: 8px; }
#wrap-title .input-control { font-size: 14px; line-height: 1.5; }

.genre-chips { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.genre-chip { display: inline-flex; align-items: center; gap: 8px; background: #e5d4de; border: 1px solid #cdb6c3; border-radius: 7px; padding: 6px 8px; color: #684257; font-size: 10px; font-weight: 700; }
.genre-chip button { border: 0; background: transparent; color: #684257; font-size: 15px; line-height: 1; cursor: pointer; padding: 0; }
.clear-genres { border: 0; background: transparent; color: var(--muted); font-size: 10px; cursor: pointer; }
.genre-selects { gap: 14px; }
.genre-selects .field-block label { font-size: 10px; }

.suggestion-list { position: absolute; top: calc(100% + 5px); left: 0; right: 0; z-index: 1000; background: #f0e7e4; border: 1px solid var(--line-strong); border-radius: 10px; box-shadow: 0 12px 28px #493e4320; overflow: hidden; max-height: 270px; overflow-y: auto; }
.suggestion-item { display: flex; align-items: center; gap: 10px; width: 100%; padding: 11px 12px; border: 0; border-bottom: 1px solid #f0e7eb; background: #f0e7e4; text-align: left; cursor: pointer; color: var(--ink); }
.suggestion-item:last-child { border-bottom: 0; }
.suggestion-item:hover { background: #f8edf3; }
.suggestion-avatar { width: 30px; height: 30px; border-radius: 9px; background: #e2d1da; color: var(--accent-dark); display: grid; place-items: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.suggestion-copy { display: grid; gap: 4px; min-width: 0; flex: 1; }
.suggestion-copy strong { font-size: 12px; overflow-wrap: anywhere; }
.suggestion-copy small { font-size: 10px; color: var(--muted); }
.suggestion-status { font-size: 9px; text-transform: uppercase; letter-spacing: .04em; color: #806274; background: #f3e9ef; border-radius: 5px; padding: 4px 6px; }

.review-panel { margin-top: 18px; }
.review-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.review-row { display: grid; grid-template-columns: minmax(130px, .7fr) minmax(0, 1.5fr) 28px; gap: 12px; align-items: center; padding: 12px 0; border-top: 1px solid #eee4e7; }
.review-row > div:first-child { display: grid; gap: 4px; }
.review-row strong { font-size: 11px; }
.review-row small { font-size: 9px; color: var(--muted); }
.review-values { display: flex; align-items: center; gap: 8px; min-width: 0; font-size: 10px; }
.review-values span:not(.review-arrow) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 45%; color: #887780; }
.review-values span:last-child { color: #704a68; font-weight: 700; }
.review-arrow { color: #b69eaa; }
.undo-icon { width: 27px; height: 27px; border: 1px solid var(--line); border-radius: 7px; background: #fff; color: var(--accent); font-size: 16px; cursor: pointer; }

/* ==========================================================================
   6. SAVE BAR & ACTION BUTTONS
   ================================================================---------- */
.savebar {
  position: fixed;
  z-index: 20;
  bottom: 0;
  left: 0;
  right: 0;
  min-height: 68px;
  padding: 12px clamp(16px, 3vw, 44px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  background: #eee5e2;
  backdrop-filter: blur(14px);
  border-top: 1px solid var(--line);
}
.savebar-info { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 11px; min-width: 0; flex: 1 1 auto; overflow: hidden; }
.savebar-info .save-indicator { flex: 0 0 7px; }
.savebar-info > span:last-child { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.save-indicator.dirty { background: #b85b79; box-shadow: 0 0 0 4px #f8e8ed; }
.savebar-actions { display: flex; gap: 9px; flex: 0 0 auto; min-width: 0; }

.button-save-action {
  color: #ffffff;
  background: #176b67;
  border: 1px solid #176b67;
  box-shadow: 0 3px 8px rgba(23, 107, 103, 0.18);
}
.button-save-action:hover:not(:disabled) { background: #10534f; border-color: #10534f; }
.button-save-action:focus-visible { outline: 3px solid rgba(23, 107, 103, 0.28); outline-offset: 2px; }
.button-save-action:disabled { color: #777b7b; background: #e3e5e4; border-color: #d4d8d6; box-shadow: none; cursor: not-allowed; opacity: 1; }

/* ==========================================================================
   7. MODALS, TOASTS & PREVIEW WINDOW
   ================================================================---------- */
.loading-state { min-height: 70vh; display: grid; align-content: center; justify-items: center; gap: 12px; color: var(--muted); font-size: 13px; }
.loader { width: 28px; height: 28px; border: 3px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.toast-message { position: fixed; z-index: 10002; top: 20px; right: 22px; max-width: min(420px, calc(100vw - 40px)); padding: 14px 18px; border-radius: 10px; background: #f0e7e4; border: 1px solid var(--line-strong); box-shadow: 0 10px 30px #493e4320; font-size: 12px; }
.toast-message.success { border-left: 4px solid #946783; }
.toast-message.error { border-left: 4px solid #ad526c; }

.modal-backdrop { position: fixed; inset: 0; z-index: 10001; background: #352a31a6; display: grid; place-items: center; padding: 20px; }
.confirm-modal { width: min(460px, 100%); background: #f0e7e4; border: 1px solid var(--line); border-radius: 16px; padding: 28px; box-shadow: 0 24px 70px #26172040; }
.modal-mark { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 12px; background: #e2d1da; color: var(--accent-dark); font-size: 20px; margin-bottom: 17px; }
.confirm-modal h2 { font: 800 23px Manrope, sans-serif; letter-spacing: -.04em; margin: 8px 0; }
.confirm-modal p { font-size: 12px; line-height: 1.7; color: var(--muted); margin: 0 0 20px; }
.optional-label { font-weight: 400; color: var(--muted); }
.countdown-note { font-size: 10px; color: var(--muted); margin-top: 10px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 22px; }

.search-results-note, .all-sections-note { background: #e6d8df; border: 1px solid #d0bbc6; border-radius: 9px; padding: 10px 13px; font-size: 11px; color: #5e4b55; margin: -10px 0 18px; }
.search-results-note button { border: 0; background: transparent; color: var(--accent-dark); font-weight: 700; cursor: pointer; }
.all-sections-note { background: #f0e7e4; color: var(--muted); }

/* Document Preview Styles */
.preview-backdrop { position: fixed; inset: 0; z-index: 10000; background: rgba(35, 26, 32, .72); display: grid; place-items: center; padding: 18px; }
.document-preview { width: min(1050px, 100%); max-height: calc(100vh - 36px); display: flex; flex-direction: column; overflow: hidden; border-radius: 16px; background: #e8dfdc; box-shadow: 0 24px 80px rgba(20, 10, 18, .35); }
.preview-toolbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; padding: 20px 26px; border-bottom: 1px solid #d0c0c5; background: #f2eae7; }
.preview-toolbar h2 { margin: 5px 0; font: 800 22px Manrope, sans-serif; color: #40363b; }
.preview-toolbar p { margin: 0; color: #76676e; font-size: 13px; }
.preview-close { width: 36px; height: 36px; flex: 0 0 auto; border: 1px solid #cbb8c1; border-radius: 9px; background: #f8f1ee; color: #684257; font-size: 25px; cursor: pointer; }
.document-sheet { width: min(820px, calc(100% - 32px)); margin: 22px auto; padding: 34px 42px; overflow-y: auto; background: #fffdf9; color: #393137; box-shadow: 0 5px 24px rgba(61, 41, 51, .13); }
.document-brand { display: flex; align-items: center; gap: 12px; padding-bottom: 22px; border-bottom: 2px solid #81576f; }
.document-monogram { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 10px; background: #81576f; color: white; font: 800 19px Manrope, sans-serif; }
.document-brand div { display: grid; gap: 4px; }
.document-brand strong { color: #684257; font: 800 12px Manrope, sans-serif; letter-spacing: .12em; }
.document-brand small { color: #76676e; font-size: 11px; }
.document-record-id { margin-left: auto; color: #76676e; font-size: 11px; text-align: right; }
.document-title { margin: 28px 0 7px; color: #352b31; font: 800 30px/1.25 Manrope, sans-serif; overflow-wrap: anywhere; }
.document-subtitle { margin: 0 0 24px; color: #76676e; font: 500 16px 'DM Sans', sans-serif; }
.document-rule { height: 1px; background: #e4d8dd; margin-bottom: 24px; }
.document-group { margin: 0 0 22px; }
.document-group h3 { margin: 0 0 10px; color: #684257; font: 800 13px Manrope, sans-serif; letter-spacing: .035em; }
.document-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.document-field { position: relative; min-width: 0; display: grid; gap: 6px; padding: 12px 13px; border: 1px solid #e7dfe0; border-radius: 7px; background: #fffdfa; }
.document-field > .document-field-label { display: block; color: #762b50; font: 800 13px/1.4 Manrope, sans-serif; letter-spacing: .025em; text-transform: uppercase; border-bottom: 1px solid #ead6df; padding-bottom: 7px; }
.document-field > strong, .document-value-comparison strong { display: block; color: #29212a; font: 500 15px/1.65 'DM Sans', sans-serif; overflow-wrap: anywhere; white-space: pre-wrap; }
.document-field-changed { border: 1.5px solid #c45b7a; background: #fff0f4; box-shadow: inset 4px 0 #c45b7a; padding-left: 16px; }
.document-value-comparison { display: grid; gap: 8px; }
.document-previous, .document-current { min-width: 0; padding: 9px 10px; border-radius: 6px; }
.document-previous { background: #f2eeee; border: 1px solid #ded5d9; }
.document-previous small, .document-current small { display: block; margin-bottom: 4px; font: 800 9px/1.4 Manrope, sans-serif; letter-spacing: .09em; }
.document-previous small { color: #796c73; }
.document-previous strong { color: #6e6269; font-size: 13px; font-weight: 400; text-decoration: line-through; text-decoration-color: #a99aa2; }
.document-current { background: #ffe2eb; border: 1px solid #e5a8bc; box-shadow: inset 3px 0 #bd3f69; }
.document-current small { color: #9c3157; }
.document-current strong { color: #552039; font-weight: 700; }
.document-current-value { padding-top: 2px; }
.document-field em { justify-self: start; padding: 3px 6px; border-radius: 4px; background: #f4d5df; color: #8e3454; font: 800 9px Manrope, sans-serif; letter-spacing: .06em; font-style: normal; }
.document-long-value { min-height: 24px; }
.document-footer { display: flex; justify-content: space-between; gap: 12px; margin-top: 28px; padding-top: 14px; border-top: 1px solid #e4d8dd; color: #76676e; font-size: 10px; }
.preview-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding: 14px 22px; border-top: 1px solid #d0c0c5; background: #f2eae7; }
.preview-legend { margin-right: auto; display: flex; align-items: center; gap: 8px; color: #76676e; font-size: 11px; }
.preview-legend i { width: 12px; height: 12px; border: 1px solid #c45b7a; background: #fff0f4; border-radius: 3px; }

/* ==========================================================================
   8. MEDIA QUERIES & RESPONSIVENESS
   ================================================================---------- */
@media (max-width: 1050px) {
  .record-identity-bar { grid-template-columns: repeat(4, minmax(0, 1fr)); row-gap: 10px; }
  .identity-heading { grid-column: 1 / -1; padding: 0 0 9px; }
  .identity-value:first-of-type { border-left: 0; padding-left: 0; }
}

@media (max-width: 980px) {
  .workspace { grid-template-columns: 220px minmax(0, 1fr); column-gap: 20px; padding: 24px 20px 38px; }
  .editor-heading { align-items: flex-start; flex-direction: column; }
  .heading-actions { justify-content: flex-start; align-items: flex-end; }
  .section-nav .nav-copy small { display: none; }
}

@media (max-width: 700px) {
  .topbar { height: 70px; padding: 0 16px; }
  .topbar-meta > span:not(.record-pill):not(.status-dot) { display: none; }
  .record-identity-bar { position: sticky; top: 70px; grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 10px 14px; }
  .identity-heading { grid-column: 1 / -1; }
  .identity-value { min-height: 48px; padding: 7px 10px; border-left: 1px solid #d5c0c8; border-top: 1px solid #d5c0c8; }
  .identity-value:nth-of-type(2n) { border-left: 0; padding-left: 0; }
  .identity-value strong { font-size: 12px; }
  
  .workspace { display: block; width: 100%; padding: 20px 14px 28px; }
  .sidebar { width: 100%; position: static; margin: 0 0 22px; max-height: none; overflow: visible; }
  .sidebar-intro { border-bottom: 1px solid var(--line); padding-bottom: 14px; }
  .sidebar-intro p { max-width: 420px; }
  .search-label, .sidebar-bottom { display: none; }
  .search-wrap { margin-bottom: 12px; }
  
  .section-nav { display: flex; flex-direction: row; align-items: stretch; overflow-x: auto; gap: 6px; padding-bottom: 5px; }
  .section-nav .nav-item { display: flex; flex: 0 0 auto; width: auto; min-width: max-content; padding: 10px; background: #f0e7e4; }
  .nav-number, .nav-arrow, .change-count { display: none; }
  .nav-copy strong { white-space: nowrap; }

  .editor-area { width: 100%; }
  .editor-heading h2 { font-size: 27px; }
  .form-section { padding: 19px 16px; }
  .field-grid { grid-template-columns: minmax(0, 1fr); gap: 17px; }
  .span-2 { grid-column: auto; }
  .genre-selects { grid-template-columns: minmax(0, 1fr); }
  
  .review-row { grid-template-columns: 1fr 26px; }
  .review-values { grid-column: 1/2; grid-row: 2; }
  .undo-icon { grid-column: 2; grid-row: 1/3; }
  .review-values span:not(.review-arrow) { max-width: 44%; }

  .savebar { padding: 10px 14px; min-height: 68px; gap: 10px; }
  .savebar-info { font-size: 10px; flex-basis: 0; }
  .savebar-actions { gap: 6px; }
  .button { padding: 0 10px; font-size: 11px; }

  .preview-backdrop { padding: 0; }
  .document-preview { width: 100%; max-height: 100vh; height: 100vh; border-radius: 0; }
  .preview-toolbar { padding: 16px; }
  .document-sheet { width: calc(100% - 20px); margin: 10px auto; padding: 22px 17px; }
  .document-title { font-size: 24px; }
  .document-fields { grid-template-columns: 1fr; }
  .document-record-id { max-width: 100px; overflow-wrap: anywhere; }
  .preview-actions { flex-wrap: wrap; padding: 12px; }
  .preview-legend { flex: 1 0 100%; }
  .preview-actions .button { flex: 1; }
}
/* --- PROPER SCOPED FIX FOR RECORD IDENTIFIER VALUES --- */
:deep(.record-identity-bar) .identity-value strong {
  font-family: Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
  color: #14be47 !important;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

@media (max-width: 420px) {
  .savebar { align-items: flex-start; flex-direction: column; padding-top: 9px; padding-bottom: 9px; }
  .savebar-info { width: 100%; flex: 0 0 auto; }
  .savebar-actions { width: 100%; justify-content: flex-end; }
  .edit-page { padding-bottom: 116px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
</style>