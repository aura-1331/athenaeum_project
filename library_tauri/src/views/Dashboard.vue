<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { 
  Database, Activity, Globe, Layers, 
  Clock, ArrowRight, Book ,BookOpen,
  FileText,
  AlertTriangle,Search,
  ShieldCheck
} from 'lucide-vue-next'
import axios from 'axios' // 🚀 1. The Hybrid Engine
import logo from '@/assets/logo.png'
// 2. DATA STATE
const rawCatalogue = ref([]) 
const summaryStats = ref({
  total_items: 0,
  total_books: 0,
  total_works: 0,
  recent_activity: [] // Initialized as empty array to prevent .slice() errors
}) 
const isLoading = ref(true)

// LIVE DATE, TIME, AND PLACE STATE
const currentTime = ref('')
const currentDate = ref('')
const currentPlace = ref('')
let timeInterval = null

const updateClock = () => {
  const now = new Date()
  
  // Gets Time (e.g., 10:26:21 PM)
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  
  // Gets Date (e.g., Friday, March 13, 2026)
  currentDate.value = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  
  // Gets Place safely via Timezone
  try {
    const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone
    currentPlace.value = tzName.split('/').pop().replace('_', ' ')
  } catch (e) {
    currentPlace.value = 'Local'
  }
}

// 3. THE HYBRID FETCH FUNCTION
onMounted(async () => {
  // Start the clock immediately
  updateClock()
  timeInterval = setInterval(updateClock, 1000)

  try {
    // 🚀 We use Axios. The "Master Guard" in main.js handles the token!
    // No need for 'http://127.0.0.1:8000' anymore.
    const [summaryRes, catRes] = await Promise.all([
      axios.get('/dashboard/summary'),
      axios.get('/catalogue/', { params: { limit: 500 } }) 
    ])
    
    // 📦 Axios puts the JSON data inside the .data property
    const apiData = summaryRes.data

    summaryStats.value = summaryRes.data
    console.log("FULL SUMMARY RESPONSE:", summaryRes.data)    

    const catData = catRes.data
    // Map the catalogue results to our local ref
    rawCatalogue.value = catData.data || []
    console.log("SUMMARY API:", summaryRes.data)
    console.log("CATALOGUE API:", catData)
    console.log("FIRST BOOK:", rawCatalogue.value[0])
  } catch (err) { 
    console.error("❌ CONNECTION FAILED:", err) 
    // If token is expired, naturally redirect (requires router import if needed)
    if (err.response?.status === 401) {
       console.warn("🔐 Session expired. Please log in again.");
    }
  } finally {
    isLoading.value = false
  }
})

// Cleanup clock when leaving page
onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})

// 4. THE LOGIC (Computed Properties)
const totalCount = computed(() => rawCatalogue.value.length)

// SMART FEED HELPER: Matches Audit log ID to Book Title
const getBookTitle = (id) => {
  if (!rawCatalogue.value.length) return null; // Return null so template knows it's missing
  const book = rawCatalogue.value.find(b => String(b.serial_no) === String(id));
  return book ? book.title : null;
};

// NEWEST ARRIVALS (Top 5 highest serial numbers)
const newestArrivals = computed(() => {
  if (!rawCatalogue.value.length) return []

  return [...rawCatalogue.value]
    .sort((a, b) => b.serial_no - a.serial_no)
    .slice(0, 5)
})

// In Circulating Items
const inCirculationCount = computed(() => {
  return rawCatalogue.value.filter(
    book => book.status === "ISSUED"
  ).length
})

// CATEGORY BREAKDOWN
const categoryStats = computed(() => {
  const stats = { 'Fiction': 0, 'Non-Fiction': 0, 'Reference': 0, 'Religious': 0, 'Uncategorized': 0 }
  rawCatalogue.value.forEach(book => {
    const cat = book.category || 'Uncategorized'
    if (stats[cat] !== undefined) stats[cat]++
    else stats['Uncategorized']++
  })
  return stats
})

const totalGenres = computed(() => {
  const genres = new Set()
  rawCatalogue.value.forEach(book => {
    if (book.genre) {
      const parts = book.genre.split(/[/,]+/)
      parts.forEach(g => genres.add(g.trim()))
    }
  })
  return genres.size
})

const formatRelativeTime = (dateString) => {
  if (!dateString) return "Unknown time"

  const now = new Date()
  const date = new Date(dateString)
  const diffMs = now - date

  const minutes = Math.floor(diffMs / 60000)
  const hours = Math.floor(diffMs / 3600000)
  const days = Math.floor(diffMs / 86400000)

  if (minutes < 60) {
    return `${minutes} minutes ago`
  }

  if (hours < 24) {
    return `${hours} hours ago`
  }

  return `${days} days ago`
}

const formatDate = (dateString) => {
  if (!dateString) return "Unknown Date"

  return new Date(dateString).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric"
  })
}

</script>

<template>
  <div class="dashboard-wrapper">

    <!-- THE NEW LAYERED HERO SECTION -->
    <div class="hero-container">
      
      <!-- LAYER 1: The "Mystic" Background (Empty div, styles handle the image) -->
      <div class="hero-wallpaper"></div>

      <!-- LAYER 2: This is where you add your code -->
      <header class="hero-content">
        <img :src="logo" alt="Athenaeum Logo" class="hero-logo" />
        <p class="hero-label">ATHENAEUM ORBIS</p>

        <h1 class="hero-title">
          Digitised manuscripts <br />
          and archives
        </h1>

        <!-- NEW: Decorative Divider -->
        <div class="hero-divider">
          <span class="line"></span>
          <span class="diamond"></span>
          <span class="line"></span>
        </div>

        <p class="hero-subtitle">
          View thousands of digitised manuscripts and archival documents.
        </p>

        <!-- UPDATED: Search Button with Icon -->
        <button class="hero-search-btn" @click="$router.push('/search')">
          <Search :size="18" />
          <span>Search the Archive</span>
        </button>
          
      </header>

    </div>

    <!-- KPI STRIP -->
<div class="stats-row">

  <!-- TOTAL ACCESSIONS -->
  <div class="stat-card">
    <BookOpen
      class="stat-icon accessions-icon"
      :size="34"
    />

    <div>
      <h2>{{ summaryStats.total_accessions || 0 }}</h2>
      <p>Total Accessions</p>
    </div>
  </div>


  <!-- IN CIRCULATION -->
  <div class="stat-card">
    <FileText
      class="stat-icon"
      :class="{
        'icon-alert': inCirculationCount > 0
      }"
      :size="34"
      :color="inCirculationCount > 0 ? '#00e676' : '#8db26f'"
    />

    <div>
      <h2
        :class="{
          'active-count': inCirculationCount > 0
        }"
      >
        {{ inCirculationCount }}
      </h2>
      <p>In Circulation</p>
    </div>
  </div>


  <!-- MISSING ITEMS -->
  <div class="stat-card">
    <AlertTriangle
      class="stat-icon"
      :class="{
        'icon-alert': summaryStats.missing_items > 0
      }"
      :size="34"
      :color="summaryStats.missing_items > 0 ? '#ff2d55' : '#d6a04b'"
    />

    <div>
      <h2
        :class="{
          'danger-count': summaryStats.missing_items > 0
        }"
      >
        {{ summaryStats.missing_items || 0 }}
      </h2>
      <p>Missing Items</p>
    </div>
  </div>


  <!-- DAMAGED ITEMS -->
  <div class="stat-card">
    <ShieldCheck
      class="stat-icon"
      :class="{
        'icon-alert': summaryStats.damaged_items > 0
      }"
      :size="34"
      :color="summaryStats.damaged_items > 0 ? '#ff9500' : '#d6a04b'"
    />

    <div>
      <h2
        :class="{
          'warning-count': summaryStats.damaged_items > 0
        }"
      >
        {{ summaryStats.damaged_items || 0 }}
      </h2>
      <p>Damaged Items</p>
    </div>
  </div>

</div>

<!-- -------------------------------------------------- END OF KPI STRIP------------------------------------------------------- -->


    <!-- LOWER PANELS -->
    <div class="dashboard-panels">

  <div class="box activity-panel">
    <div class="panel-header">
      <h3 class="box-title"><Clock :size="14" /> Recent Activity</h3>
      <span class="view-all-link" @click="$router.push('/status-audit')">View all →</span>
    </div>

    <div v-for="log in (summaryStats.recent_activity || []).slice(0, 3)" :key="log.id" class="activity-row">
      <div class="activity-icon">
        <BookOpen :size="16" />
      </div>
      <div class="activity-content">
        <h4>{{ log.action }}</h4>
        <p>{{ getBookTitle(log.serial_no) || 'System Update' }}</p>
      </div>
      <div class="activity-time">
        {{ formatRelativeTime(log.changed_at) }}
      </div>
    </div>
  </div>

  <div class="box catalogue-panel">
    <div class="panel-header">
      <h3 class="box-title"><Book :size="14" /> Recently Catalogued</h3>
      <span class="view-all-link" @click="$router.push('/catalogue')">View all →</span>
    </div>

    <div v-for="book in newestArrivals.slice(0, 3)" :key="book.accession_no" class="catalogue-row">
      <div class="book-thumb"></div>
      <div class="book-info">
        <h4>{{ book.title }}</h4>
        <p>{{ book.author || 'Unknown Author' }} • {{ book.year || 'N/A' }}</p>
      </div>
      <div class="book-right">
        <h5>{{ book.accession_no }}</h5>
        <p>{{ formatDate(book.created_at) }}</p>
      </div>
    </div>
  </div>

</div>

    <!-- ANALYTICS -->
    <div class="analytics-row">

      <!-- Categories -->
      <div class="box">
        <h3 class="box-title">
          <Layers :size="14" />
          Categories
        </h3>

        <div
          v-for="(count, category) in categoryStats"
          :key="category"
          class="tag-row"
        >
          {{ category }}
          <span>{{ count }}</span>
        </div>
      </div>

      <!-- Languages -->
      <div class="box">
        <h3 class="box-title">
          <Globe :size="14" />
          Languages
        </h3>

        <div
          v-for="lang in summaryStats.languages"
          :key="lang.language"
          class="tag-row"
        >
          {{ lang.language }}
          <span>{{ lang.count }}</span>
        </div>

        <div class="genre-note">
          {{ totalGenres }} Unique Genres Cataloged
        </div>
      </div>

    </div>

  </div>
</template>

<style scoped>
/* ==========================================================================
   1. DASHBOARD WRAPPER & CORE
   ========================================================================== */
.dashboard-wrapper {
  width: 100% !important;
  margin: 0 !important;
  padding: 0 0 60px 0 !important; /* Bottom padding for scroll room */
  background-color: var(--content-bg) !important;
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
}

/* ==========================================================================
   2. LAYERED HERO SYSTEM (Atmosphere & Content)
   ========================================================================== */
.hero-container {
  width: 100%;
  min-height: 550px;
  position: relative;
  overflow: hidden;
}

/* LAYER 1: The Mystic Wallpaper (Warm Tone Edition) */
.hero-wallpaper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  
  background: 
    /* The Core Shadow (Inverted) */
    radial-gradient(circle at center, var(--content-bg) 0%, rgba(10, 9, 8, 0.6) 50%, transparent 100%),
    /* Horizontal Flow (Sides) */
    linear-gradient(to right, var(--content-bg) 0%, transparent 25%, transparent 75%, var(--content-bg) 100%),
    /* Vertical Flow (Top/Bottom) */
    linear-gradient(to bottom, var(--content-bg) 0%, transparent 30%, transparent 70%, var(--content-bg) 100%),
    /* The Image */
    url("@/assets/library-bg.png");

  background-size: cover;
  background-position: center;
  background-blend-mode: multiply;

  /* Adds that ancient library warmth */
  filter: sepia(0.2) brightness(0.9) contrast(1.1);

  /* Seamless fade into the dashboard */
  mask-image: linear-gradient(to bottom, transparent, black 20%, black 80%, transparent);
  -webkit-mask-image: linear-gradient(to bottom, transparent, black 20%, black 80%, transparent);
}

/* LAYER 2: Hero Text/Logo content */
.hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding-top: 50px; /* Pulls content up */
}

.hero-logo {
  width: 70px;
  height: 70px;
  object-fit: contain;
  margin-bottom: 12px;
  filter: drop-shadow(0 0 10px rgba(184, 146, 90, 0.3));
}

.hero-label {
  color: var(--accent);
  letter-spacing: 6px;
  font-size: 11px;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.hero-title {
  font-family: "Cormorant Garamond", serif;
  font-size: 56px;
  font-weight: 500;
  line-height: 1.1;
  color: #f5eee0;
  margin-bottom: 20px;
}

/* Decorative Divider */
.hero-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-bottom: 25px;
  width: 100%;
}

.hero-divider .line {
  height: 1px;
  width: 100px;
  background: linear-gradient(to var(--dir, right), rgba(184, 146, 90, 0.6), transparent);
}

.hero-divider .line:first-child { --dir: left; }

.hero-divider .diamond {
  width: 8px;
  height: 8px;
  border: 1px solid var(--accent);
  transform: rotate(45deg);
}

.hero-subtitle {
  color: var(--text-muted);
  font-size: 16px;
  max-width: 600px;
  line-height: 1.6;
}

.hero-search-btn {
  margin-top: 35px;
  background: rgba(184, 146, 90, 0.05);
  color: #f5eee0;
  border: 1px solid rgba(184, 146, 90, 0.25);
  padding: 14px 30px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  backdrop-filter: blur(10px);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.hero-search-btn:hover {
  background: rgba(184, 146, 90, 0.15);
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(184, 146, 90, 0.2);
}

.hero-search-btn:active {
  transform: scale(0.97);
}

/* ==========================================================================
   3. KPI STRIP
   ========================================================================== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  width: 92%; 
  margin: -60px auto 40px; 
  background: rgba(20, 18, 16, 0.45) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-main) !important;
  border-radius: 12px;
  overflow: hidden;
  z-index: 10;
  box-shadow: 0 10px 40px rgba(0,0,0,0.4);
}

.stat-card {
  padding: 25px;
  border-right: 1px solid rgba(184, 146, 90, 0.08);
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-card:last-child { border-right: none; }

.stat-card h2 {
  font-size: 28px;
  line-height: 1;
  font-family: "Cormorant Garamond", serif;
  color: #f5eee0;
  margin: 0;
}

.stat-card p {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--accent);
  margin-top: 6px;
}

.stat-icon {
  color: var(--accent);
  opacity: 0.8;
}

/* ==========================================================================
   4. BOXES & DATA ROWS
   ========================================================================== */
.dashboard-panels, .analytics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 25px;
  padding: 0 4%; 
  margin-bottom: 25px;
}
.analytics-row {
  margin-top: 0px; /* Removes the gap between top and bottom boxes */
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 25px;
  padding: 0 4%;
}
.box {
  background: rgba(20, 18, 16, 0.4) !important;
  border: 1px solid var(--border-main) !important;
  border-radius: 12px;
  padding: 16px 22px; /* Reduced vertical padding */
  min-height: 250px;   /* CRITICAL: Forces both boxes to align at the bottom */
  display: flex;
  flex-direction: column;
}



.box-title {
  font-family: "Cormorant Garamond", serif;
  font-size: 20px;
  color: #f5eee0;
  display: flex;
  align-items: center;
  gap: 10px;
  
  /* ADD THESE LINES */
  margin-bottom: 16px; 
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(184, 146, 90, 0.15); /* Subtle golden underline */
  width: 100%; /* Ensures line stretches across the box */
}

.panel-header span {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--accent);
  cursor: pointer;
}

/* Rows (Activity & Catalogue) */

.activity-row, .catalogue-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0; /* Thin lines like a focused manuscript */
  border-bottom: 1px solid rgba(184, 146, 90, 0.05);
}

.activity-row:last-child, .catalogue-row:last-child { border-bottom: none; }

.activity-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(184, 146, 90, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}
.activity-content, .book-info {
  flex: 1; 
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.activity-time, .book-right {
  text-align: right;
  min-width: 100px; /* Ensures enough space for dates */
  font-size: 11px;
  color: var(--accent);
  opacity: 0.8;
  font-variant-numeric: tabular-nums; /* Keeps numbers aligned */
}
.activity-content h4, .book-info h4 {
  font-size: 14px;
  margin: 0 0 2px 0;
  line-height: 1.2;
}

.activity-content p, .book-info p {
  font-size: 12px;
  margin: 0;
  color: var(--text-muted);
}

.activity-time, .book-right p {
  font-size: 12px;
  color: var(--accent);
  opacity: 0.8;
}

.book-thumb {
  width: 42px;
  height: 58px;
  background: rgba(184, 146, 90, 0.1);
  border: 1px solid rgba(184, 146, 90, 0.2);
  border-radius: 4px;
}

/* Tag Rows (Categories & Languages) */
.tag-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid rgba(184, 146, 90, 0.05);
  font-size: 14px;
  color: #f5eee0;
}

.tag-row span {
  font-family: "Cormorant Garamond", serif;
  color: var(--accent);
  font-weight: 600;
  font-size: 16px;
}

.view-all-link {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--accent);
  cursor: pointer;
  opacity: 0.6;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 4px 8px;
}

.view-all-link:hover {
  opacity: 1;
  text-shadow: 0 0 10px rgba(184, 146, 90, 0.6);
  transform: translateX(4px); /* Subtle slide to the right */
}
.activity-row:first-of-type, 
.catalogue-row:first-of-type, 
.tag-row:first-of-type {
  margin-top: 8px;
}
/* ==========================================================================
   5. UTILITIES & ANIMATIONS
   ========================================================================== */
.active-count { color: #00e676 !important; }
.danger-count { color: #ff2d55 !important; }
.warning-count { color: #ff9500 !important; }
/* Golden Interactive Seal for View All */

@keyframes statPulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}
.icon-alert { animation: statPulse 1.5s ease-in-out infinite; }
</style>