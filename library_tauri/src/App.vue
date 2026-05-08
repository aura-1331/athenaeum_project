<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from "vue"
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router"
import { 
  LayoutDashboard, 
  Library, 
  Search, 
  ClipboardCheck, 
  PlusCircle, 
  BookPlus,
  Sun,
  Moon,
  LogOut
} from 'lucide-vue-next'

const theme = ref("dark")
const route = useRoute()
const router = useRouter()

import { listen } from '@tauri-apps/api/event'

listen('navigate-to', (event) => {
  router.push(event.payload)
})

// Logic to detect if we are in "Deep Focus" edit mode
const isEditing = computed(() => route.path.includes('edit-item'))

// --- LIVE CLOCK LOGIC ---
const currentTime = ref('')
const currentDate = ref('')
const currentPlace = ref('')
const lastUpdated = ref('')
let timeInterval = null

const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  currentDate.value = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  try {
    const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone
    currentPlace.value = tzName.split('/').pop().replace('_', ' ')
  } catch (e) {
    currentPlace.value = 'Local'
  }
}
const isAuthenticated = ref(!!localStorage.getItem("token"))

const updateSyncTime = () => {
  const now = new Date()
  lastUpdated.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t)
  localStorage.setItem("ui-theme", t)
}

function toggleTheme() {
  theme.value = theme.value === "dark" ? "light" : "dark"
  applyTheme(theme.value)
}
 // Ensure you have this or use the imported one

const handleLogout = () => {
  localStorage.removeItem("token")
  localStorage.removeItem("refresh_token")
  localStorage.removeItem("user_role")
  localStorage.removeItem("user_name")

  sessionStorage.clear()

  isAuthenticated.value = false
  window.dispatchEvent(new Event("auth-changed"))

  router.push("/login")
}
onMounted(() => {
  document.title = "Athenaeum Orbis | Library Management System"
  updateClock()
  updateSyncTime()
  timeInterval = setInterval(updateClock, 1000)

  const saved = localStorage.getItem("ui-theme") || "dark"
  theme.value = saved
  applyTheme(saved)
  window.addEventListener("auth-changed", () => {
  isAuthenticated.value = !!localStorage.getItem("token")
 })
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})

watch(() => route.path, () => {
  updateSyncTime()
})
</script>

<template>
  <div class="app" :class="{ 'details-window-theme': route.path.includes('/details/') }">
    
    <aside 
      v-if="isAuthenticated && !isEditing && !route.path.includes('/details/') && !route.path.includes('/print')" 
      class="sidebar"
    >
      <div class="logo-area">
        <div class="ao-seal">AO</div>
        <div class="brand-text">
          <h3 class="logo">Athenaeum Orbis</h3>
          <span class="tagline">Consulere et Conservare</span>
        </div>
      </div>

      <nav class="nav-links">
        <RouterLink to="/dashboard"><LayoutDashboard :size="18" /><span>Dashboard</span></RouterLink>
        <RouterLink to="/catalogue"><Library :size="18" /><span>Catalogue</span></RouterLink>
        <RouterLink to="/search"><Search :size="18" /><span>Search</span></RouterLink>
        <RouterLink to="/status-audit"><ClipboardCheck :size="18" /><span>Audit</span></RouterLink>
        <RouterLink to="/create-work"><PlusCircle :size="18" /><span>Create Work</span></RouterLink>
        <RouterLink to="/create-item"><BookPlus :size="18" /><span>Create Item</span></RouterLink>
      </nav>

      <button class="theme-btn" @click="toggleTheme">
        <component :is="theme === 'dark' ? Sun : Moon" :size="16" />
        <span>{{ theme === "dark" ? "Light Mode" : "Dark Mode" }}</span>
      </button>
      <div class="sidebar-footer">
  
  <button class="logout-btn" @click="handleLogout">
    <LogOut :size="16" />
    <span>Exit System</span>
  </button>
</div>
    </aside>

    <main class="content-wrapper" :class="{ 'no-padding': route.path.includes('/details/') }">
      
      <header 
        v-if="isAuthenticated && !isEditing && !route.path.includes('/details/') && !route.path.includes('/print')" 
        class="global-header"
      >
        <div class="breadcrumb">{{ route.name || 'Admin Panel' }}</div>
        <div class="live-meta">
          <span class="division-tag">Archive Division</span>
          <span class="date">{{ currentDate }}</span>
          <span class="time">{{ currentTime }}</span>
        </div>
      </header>

      <section class="page-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>
<style>
/* --- 1. DESIGN SYSTEM VARIABLES --- */
:root[data-theme="light"] {
  --sidebar-bg: #0d9488;      /* Keeps that beautiful Teal */
  --content-bg: #f8fafc;      /* Clean, off-white background */
  --card-bg: #ffffff;         /* Pure white cards (Fixes the screenshot) */
  --text-primary: #0f172a;    /* Bold charcoal text */
  --text-muted: #475569;      /* Clear grey for authors/subtitles */
  --border-main: #e2e8f0;     /* Soft border for card edges */
  --accent: #0d9488;          /* Matching the sidebar teal */
}
:root[data-theme="dark"] {
  --sidebar-bg: #111827;
  --content-bg: #030712;
  --card-bg: #0f172a;
  --text-primary: #f9fafb;
  --text-active: #2dd4bf;
  --text-muted: #9ca3af;
  --border-main: #1e293b;
  --accent: #2dd4bf;
  --curve-size: 25px;
}
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
}
/* --- 2. RESET & BASE --- */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', system-ui, sans-serif; -webkit-font-smoothing: antialiased; }

.app {
  display: flex;
  min-height: 100vh;
  width: 100%;
  background: var(--content-bg);
}

/* --- 3. SIDEBAR STYLES --- */
.sidebar {
  width: 240px;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  padding: 40px 0 30px 20px;
  z-index: 100;
}

.logo-area { 
  display: flex; 
  align-items: center; 
  gap: 12px; 
  padding-left: 15px; 
  margin-bottom: 50px; 
}


.ao-seal {
  background: #fbbf24;
  color: #064e3b;
  width: 36px;
  height: 36px;
  min-width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Georgia', serif;
  font-weight: 900;
  font-size: 16px;
  border-radius: 6px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
}

.brand-text { display: flex; flex-direction: column; }

.logo { 
  font-family: 'Georgia', serif;
  color: #fbbf24;
  font-size: 15px; 
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tagline {
  font-size: 8px;
  color: #2dd4bf;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-top: 2px;
  font-weight: 600;
}

/* --- 4. NAVIGATION LINKS --- */
.nav-links { display: flex; flex-direction: column; gap: 4px; }

.sidebar a {
  display: flex;
  align-items: center;
  gap: 14px;
  text-decoration: none;
  color: #9ca3af;
  padding: 14px 20px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 30px 0 0 30px;
  transition: all 0.2s ease;
}

.sidebar a:hover {
  color: #2dd4bf; /* Teal hover effect */
  background: rgba(45, 212, 191, 0.05);
  transition: all 0.2s ease;
}

.sidebar a.router-link-active {
  background: var(--content-bg);
  color: var(--accent);
  font-weight: 700;
  position: relative;
}

/* Scoop Curves */
.sidebar a.router-link-active::before, .sidebar a.router-link-active::after {
  content: ""; position: absolute; right: 0; width: 25px; height: 25px; 
  background: transparent; border-radius: 50%; pointer-events: none;
}
.sidebar a.router-link-active::before { top: -25px; box-shadow: 10px 10px 0 0 var(--content-bg); }
.sidebar a.router-link-active::after { bottom: -25px; box-shadow: 10px -10px 0 0 var(--content-bg); }

/* --- 5. MAIN CONTENT & HEADER --- */
.content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--content-bg);
 }

.global-header {
  height: 60px;
  background: var(--content-bg);
  border-bottom: 1px solid var(--border-main);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  flex-shrink: 0;
}

.breadcrumb {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 800;
  color: var(--text-muted);
}

.live-meta {
  display: flex;
  align-items: center;
  gap: 15px; /* This creates the space between the words */
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.divider { 
  margin: 0; /* Gap handled by the container now */
  opacity: 0.2; 
  font-weight: 300;
  color: var(--text-muted);
}

/* --- 3. Ensure the Archive Division stands out --- */
.division-tag {
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 11px;
  background: rgba(13, 148, 136, 0.1); /* Subtle teal background bubble */
  padding: 4px 10px;
  border-radius: 4px;
}
.page-content {
  flex: 1;
  padding: 0 40px 20px 40px;
  background: var(--content-bg);
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.page-content::-webkit-scrollbar { display: none; }

/* --- 6. THEME TOGGLE --- */
.theme-btn {
  margin: auto 20px 30px 0;
  padding: 12px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  display: flex; align-items: center; justify-content: center; gap: 10px;
  font-size: 13px; font-weight: 600;
}

/* --- 7. DETAILS WINDOW SPECIAL THEME --- */
.content-wrapper.no-padding {
  width: 100vw;
  margin: 0;
  padding: 0;
}


.details-window-theme .page-content:has(> .details-page) {
  padding: 0 !important;
  margin: 0 !important;
  height: 100vh;
  overflow: auto !important;
}

.details-window-theme .section {
  background-color: #065f46 !important; 
  border: 1px solid #0f766e !important; 
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Branding in Details View */
.library-branding {
  margin-right: auto;
  display: flex;
  flex-direction: column;
  border-left: 3px solid #fbbf24;
  padding-left: 15px;
}

.institution-name {
  font-family: 'Serif', 'Georgia', serif;
  font-size: 18px;
  font-weight: 800;
  color: #fbbf24;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.record-type {
  font-size: 10px;
  color: #2dd4bf;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-top: -2px;
}

/* Details Page Gold Title */
.details-window-theme .title {
  color: #fbbf24 !important;
  border-bottom: 2px solid #d97706 !important;
  padding-bottom: 12px;
  margin-bottom: 30px;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-weight: 800;
  display: inline-block;
}
/* --- SIDEBAR FOOTER DESIGN --- */
.sidebar-footer {
  margin-top: auto; /* Pushes to bottom */
  padding: 0 20px 30px 0; /* Align with your sidebar padding */
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Redesign the existing theme-btn to fit inside the footer container */
.sidebar-footer .theme-btn {
  margin: 0; /* Remove the old margin */
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-main);
  transition: all 0.3s ease;
}

.sidebar-footer .theme-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--accent);
}

/* The New Logout Button Design */
.logout-btn {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
  cursor: pointer;
  background: rgba(239, 68, 68, 0.1); 
  color: #f87171; /* Soft red for dark theme */
  display: flex; 
  align-items: center; 
  justify-content: center; 
  gap: 10px;
  font-size: 13px; 
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.logout-btn:hover {
  background: #ef4444; /* Alert Red */
  color: white;
  border-color: #ef4444;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
  transform: translateY(-1px);
}

.logout-btn:active {
  transform: scale(0.98);
}

/* --- 8. OFFICIAL ARCHIVE PRINT LAYOUT --- */
@media print {
  html, body, .app, .content-wrapper, .page-content, .details-page {
    background: white !important;
    color: black !important;
    margin: 0 !important;
    padding: 0 !important;
    height: auto !important;
    width: 100% !important;
  }
  
  .library-branding { border-left: 3px solid black !important; }
  .institution-name { color: black !important; }
  .record-type { color: #666 !important; }

  .action-bar, .theme-btn, .sidebar, .global-header {
    display: none !important;
  }

  .title {
    color: black !important;
    border-bottom: 2px solid black !important;
    font-size: 22pt !important;
    text-align: center;
    margin-bottom: 30px !important;
  }

  .section {
    background: white !important;
    border: 1px solid #ccc !important;
    break-inside: avoid;
    margin-bottom: 15px !important;
    padding: 15px !important;
    box-shadow: none !important;
  }

  .details-page::after {
    content: "Official Library Record - Athenaeum Orbis";
    display: block;
    text-align: center;
    font-size: 8pt;
    color: #999;
    margin-top: 50px;
    border-top: 1px solid #eee;
    padding-top: 10px;
  }

  .sync-info {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 11px;
  transition: color 0.3s ease; /* Smooth transition */
}
* {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}

/* Add this to make the text "blink" white for a split second when it updates */
.sync-info:active {
  color: var(--accent);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: #2dd4bf; 
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(45, 212, 191, 0.4);
  animation: sync-pulse 2s infinite;
}
.content-area.full-screen-editor {
  margin-left: 0 !important; /* Removes space where sidebar used to be */
  width: 100vw;
  height: 100vh;
  z-index: 100;
}

@keyframes sync-pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

</style>