<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { 
  Database, Activity, Globe, Layers, 
  Clock, ArrowRight, Book 
} from 'lucide-vue-next'
import axios from 'axios' // 🚀 1. The Hybrid Engine

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
    summaryStats.value = summaryRes.data
    
    const catData = catRes.data
    // Map the catalogue results to our local ref
    rawCatalogue.value = catData.data || []

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
  if (!rawCatalogue.value.length) return 'System Event'
  const book = rawCatalogue.value.find(b => String(b.serial_no) === String(id))
  return book ? book.title : 'General Update'
}

// NEWEST ARRIVALS (Top 5 highest serial numbers)
const newestArrivals = computed(() => {
  if (!rawCatalogue.value.length) return []
  return [...rawCatalogue.value]
    .sort((a, b) => b.serial_no - a.serial_no) 
    .slice(0, 5)
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

// LANGUAGE BREAKDOWN
const languageStats = computed(() => {
  const counts = {}
  rawCatalogue.value.forEach(book => {
    const lang = book.language_id || 'Unknown'
    counts[lang] = (counts[lang] || 0) + 1
  })
  return counts
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
</script>

<template>
  <div class="dashboard-wrapper">
    <header class="header">
  <p class="brand-subtitle">Athenaeum Orbis Digital Records Ledger</p>
  <h1>System Summary</h1>
  </header>

    <div class="grid">
      <aside class="col">
        <div class="card main-card">
          <Database :size="24" />
          <div class="card-content">
            <span class="label">Total Accessions</span>
            <span class="value">{{ summaryStats.total_accessions || 0 }}</span>
          </div>
        </div>

        <div class="box">
          <h3 class="box-title"><Activity :size="14" /> Audit Health</h3>
          <div class="health-list">
            <div class="health-row">Missing: <span class="red">0</span></div>
            <div class="health-row">Damaged: <span class="orange">0</span></div>
            <div class="health-row">In Circulation: <span>{{ summaryStats.total_issued || 0 }}</span></div>
          </div>
        </div>
      </aside>

  <main class="col center">
  <h3 class="box-title"><Clock :size="14" /> Activity Feed</h3>
  <div class="timeline">
    <div class="spine"></div>
    <div v-if="isLoading" class="msg">Loading system activity...</div>
    
    <div v-for="log in (summaryStats.recent_activity || []).slice(0, 5)" :key="log.id" class="event">
      <div class="node"></div>
      <div class="event-card">
        <span class="time">{{ new Date(log.changed_at).toLocaleDateString() }}</span>
        <h4 class="smart-title">
          {{ getBookTitle(log.serial_no) }} 
          <span class="dim">#{{ log.serial_no }}</span>
        </h4>
        <div class="path">
          <span class="tag">{{ log.old_status || 'N/A' }}</span>
          <ArrowRight :size="12" />
          <span class="tag active">{{ log.new_status || 'UPDATED' }}</span>
        </div>
      </div> 
    </div> </div> <div class="box mt-20">
    <h3 class="box-title"><Book :size="14" /> Recently Cataloged</h3>
    <div v-if="isLoading" class="msg">Loading books...</div>
    <div class="arrivals-list">
      <div v-for="book in newestArrivals" :key="book.accession_no" class="arrival-item">
        <div class="arrival-main">
          <span class="arrival-title">{{ book.title }}</span>
          <span class="arrival-author">by {{ book.author || 'Unknown' }}</span>
        </div>
        <span class="arrival-acc tag">#{{ book.accession_no }}</span>
      </div>
    </div>
  </div>
</main>

      <aside class="col">
        <div class="box">
          <h3 class="box-title"><Layers :size="14" /> Categories</h3>
          <div v-for="log in (summaryStats.recent_activity || []).slice(0, 5)" :key="log.id" class="event">
    <span class="time">{{ new Date(log.changed_at).toLocaleDateString() }}</span>
    
    <h4 class="smart-title">
      {{ getBookTitle(log.serial_no) }} 
      <span class="dim">#{{ log.serial_no }}</span>
    </h4>

    <div class="path">
      <span class="tag">{{ log.old_status || 'N/A' }}</span>
      <ArrowRight :size="12" />
      <span class="tag active">{{ log.new_status || 'UPDATED' }}</span>
    </div>
</div>
        </div>

        <div class="box mt-20">
          <h3 class="box-title"><Globe :size="14" /> Languages</h3>
          <div class="lang-tags">
            <div v-for="(count, lang) in languageStats" :key="lang" class="tag-row">
              {{ lang }}: <span>{{ count }}</span>
            </div>
          </div>
          <div class="genre-note">
            {{ totalGenres }} Unique Genres Cataloged
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
/* 1. Fix the main background */
.dashboard-wrapper { 
  padding: 30px; 
  background: var(--content-bg); 
  min-height: 100vh; 
  color: var(--text-primary); 
  font-family: sans-serif; 
}

.header { margin-bottom: 30px; }
.header h1 { font-size: 24px; font-weight: 800; color: var(--text-primary); }

.grid { display: grid; grid-template-columns: 260px 1fr 260px; gap: 30px; align-items: start; }

/* --- THE FIX: Universal Card Styling --- */
.box, .event-card, .arrival-item { 
  background: var(--card-bg); 
  border: 1px solid var(--border-main); 
  border-radius: 16px; 
  padding: 20px; 
  transition: all 0.3s ease;
}

/* The "Total Accessions" card stays Brand Teal for prestige */
.main-card { 
  background: #0d9488; 
  color: white; 
  border: none; 
  margin-bottom: 20px; 
  display: flex; 
  align-items: center; 
  gap: 15px; 
  padding: 20px;
  border-radius: 16px;
}
.main-card .value { font-size: 40px; font-weight: 800; line-height: 1; display: block; }
.main-card .label { font-size: 11px; text-transform: uppercase; opacity: 0.8; }

.box-title { 
  font-size: 11px; 
  text-transform: uppercase; 
  color: var(--text-muted); 
  margin-bottom: 15px; 
  display: flex; 
  align-items: center; 
  gap: 8px; 
  font-weight: 700; 
}

/* Timeline specific tweaks */
.spine { position: absolute; left: 10px; top: 0; bottom: 0; width: 2px; background: var(--border-main); }
.node { 
  position: absolute; 
  left: -24px; 
  top: 18px; 
  width: 8px; 
  height: 8px; 
  background: #0d9488; 
  border-radius: 50%; 
  border: 3px solid var(--card-bg); 
}

.event-card { padding: 12px; border-radius: 12px; }
.time { font-size: 10px; color: var(--text-muted); }
.smart-title { margin: 4px 0; font-size: 13px; font-weight: 600; color: var(--text-primary); }
.dim { color: var(--text-muted); font-weight: 400; font-size: 11px; }

/* Tag Styling */
.tag { background: var(--border-main); padding: 2px 6px; border-radius: 4px; color: var(--text-muted); }
.tag.active { color: #2dd4bf; background: rgba(45, 212, 191, 0.1); }

/* Arrivals List Fix */
.arrival-item { padding: 10px; border-radius: 8px; margin-bottom: 8px; }
.arrival-author { font-size: 10px; color: var(--text-muted); }

/* Category Bars */
.bar-bg { height: 4px; background: var(--border-main); border-radius: 10px; }
.bar-fill { height: 100%; background: #0d9488; border-radius: 10px; transition: width 0.5s ease; }

.tag-row { font-size: 12px; font-weight: 600; padding: 6px 0; border-bottom: 1px solid var(--border-main); color: var(--text-primary); }
.tag-row span { color: #2dd4bf; }
.genre-note { margin-top: 15px; font-size: 10px; color: var(--text-muted); font-weight: 800; text-transform: uppercase; }

/* Helpers */
.mt-20 { margin-top: 20px; }
.red { color: #ef4444; }
.orange { color: #f59e0b; }
.msg { color: var(--text-muted); font-size: 12px; }
.bar-fill { 
  background: #0d9488; /* Match the teal from your main card */
}

.count, .tag-row span {
  color: #fbbf24; /* Use the brand gold for the numbers */
}

</style>