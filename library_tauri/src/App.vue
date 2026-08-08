<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from "vue"
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router"
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth' // <-- 1. IMPORT PINIA HERE
import { 
  LayoutDashboard, 
  Library, 
  Search, 
  ClipboardCheck, 
  PlusCircle, 
  BookPlus,
  Sun,
  Moon,
  LogOut,
  BookOpen,
  FileText,
  AlertTriangle,
  ShieldCheck,
  Users,
  Tag,
  Info,
  Menu
} from 'lucide-vue-next'
import { listen } from '@tauri-apps/api/event'

const theme = ref("dark")
const route = useRoute()
const router = useRouter()
const isMobileMenuOpen = ref(false)

// --- 2. PINIA AUTHENTICATION INTEGRATION ---
const authStore = useAuthStore()
// storeToRefs makes sure the template updates instantly when these change
const { isAuthenticated, userName: user_name, userRole: user_role } = storeToRefs(authStore)

let unlistenNav = null
const isEditing = computed(() => {
  return route.path.includes('edit-item') || route.path.includes('/classification/')
})

const currentTime = ref('')
const currentDate = ref('')
const currentPlace = ref('Locating...')
const lastUpdated = ref('')
let timeInterval = null

const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  currentDate.value = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  
}

// NEW FUNCTION: Robust dynamic location fetching
const fetchAccurateLocation = async () => {
  currentPlace.value = 'Locating...'

  if (!navigator.geolocation) {
    currentPlace.value = 'Local Terminal'
    return
  }

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        const lat = position.coords.latitude
        const lon = position.coords.longitude
        
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10`)
        const data = await res.json()
        
        if (data && data.address) {
          const city = data.address.city || data.address.town || data.address.village || data.address.state_district
          const country = data.address.country_code ? data.address.country_code.toUpperCase() : ''
          currentPlace.value = city ? `${city}, ${country}` : 'Thiruvananthapuram, IN'
        } else {
          currentPlace.value = 'Thiruvananthapuram, IN'
        }
      } catch (err) {
        console.warn("Reverse geocoding failed:", err)
        currentPlace.value = 'Thiruvananthapuram, IN'
      }
    },
    (error) => {
      console.warn("Geolocation permission denied:", error)
      currentPlace.value = 'Thiruvananthapuram, IN'
    },
    { timeout: 10000, maximumAge: 60000 }
  )
}
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

// --- 3. UPDATED LOGOUT FUNCTION ---
const handleLogout = () => {
  authStore.logout() // Pinia does all the heavy lifting now!
  router.push("/login")
}

watch(
  () => route.path,
  () => {
    updateSyncTime()
    isMobileMenuOpen.value = false
    // Security check: If they aren't authenticated and try to navigate, boot them to login
    if (!isAuthenticated.value && route.path !== "/login") {
      router.push("/login")
    }
  }
)

onMounted(async () => {
  document.title = "Athenaeum Orbis | Library Management System"
  updateClock()
  updateSyncTime()
  fetchAccurateLocation()
  timeInterval = setInterval(updateClock, 1000)

  const saved = localStorage.getItem("ui-theme") || "dark"
  theme.value = saved
  applyTheme(saved)

  // Initial security check on load
  if (!isAuthenticated.value && route.path !== "/login") {
    router.push("/login")
  }

  if (window.__TAURI__) {
    try {
      unlistenNav = await listen('navigate-to', (event) => {
        router.push(event.payload)
      })
    } catch (err) {
      console.warn("Tauri event listener failed:", err)
    }
  }
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  if (unlistenNav) unlistenNav()
})
</script>

<template>
  <div class="app" :class="{ 'details-window-theme': route.path.includes('/details/') }">
    <aside 
      v-if="isAuthenticated && !isEditing && !route.path.includes('/details/') && !route.path.includes('/print')" 
      class="sidebar"
      :class="{ 'mobile-open': isMobileMenuOpen }"
    >
      <div class="logo-area">
        <div class="ao-seal">AO</div>
        <div class="brand-text">
          <h3 class="logo">Athenaeum Orbis</h3>
          <span class="tagline">Consulere et Conservare</span>
        </div>
      </div>

      <nav class="nav-links">
        <RouterLink to="/dashboard"><LayoutDashboard :size="18" :stroke-width="1.5" /><span>Dashboard</span></RouterLink>
        <RouterLink to="/search"><Search :size="18" :stroke-width="1.5" /><span>Search Archive</span></RouterLink>
        <RouterLink to="/catalogue"><Library :size="18" :stroke-width="1.5" /><span>Catalogue</span></RouterLink>
        
        <div class="nav-section-label">Inventory</div>
        <RouterLink to="/create-work"><FileText :size="18" :stroke-width="1.5" /><span>Works</span></RouterLink>
        <RouterLink to="/create-item"><BookOpen :size="18" :stroke-width="1.5" /><span>Items</span></RouterLink>
        <RouterLink to="/incidents">  <AlertTriangle :size="18" :stroke-width="1.5" />  <span>Incidents</span></RouterLink>
        
        <div class="nav-section-label">Classification</div>
          <RouterLink to="/classification/authors">
            <Users :size="18" :stroke-width="1.5" />
            <span>Authors</span>
          </RouterLink>
          <RouterLink to="/classification/subjects">
            <Tag :size="18" :stroke-width="1.5" />
            <span>Subjects</span>
          </RouterLink>
        
        <div class="nav-section-label">System</div>
          <RouterLink to="/audit-trail"><ShieldCheck :size="18" :stroke-width="1.5" /><span>Audit Trail</span></RouterLink>
          <RouterLink to="/admin/settings"><LayoutDashboard :size="18" :stroke-width="1.5" /><span>Reports</span></RouterLink>
          <RouterLink to="/about">
            <Info :size="18" :stroke-width="1.5" />
            <span>About</span>
          </RouterLink>
      </nav>

      <div class="sidebar-user">
        <div class="user-avatar">
          <img :src="'https://ui-avatars.com/api/?name=' + encodeURIComponent(user_name) + '&background=161412&color=b8a88a&bold=true'" alt="User Avatar" />
        </div>
        <div class="user-info">
          <span class="user-name">{{ user_name }}</span>
          <span class="user-role">{{ user_role }}</span>
        </div>
      </div>
    </aside>
    <div 
      v-if="isMobileMenuOpen" 
      class="mobile-overlay" 
      @click="isMobileMenuOpen = false"
    ></div>
    <main 
      class="content-wrapper" 
      :class="{ 
        'no-padding': route.path.includes('/details/'), 
        'authenticated-layout': isAuthenticated && !isEditing 
      }"
    >
      <header 
        v-if="isAuthenticated && !isEditing && !route.path.includes('/details/') && !route.path.includes('/print')" 
        class="global-header"
      >
        <div class="header-left">
          <button class="header-icon-btn mobile-menu-toggle" @click="isMobileMenuOpen = !isMobileMenuOpen">
            <Menu :size="20" :stroke-width="1.5" />
          </button>
          <div class="breadcrumb">{{ route.name || 'Admin Panel' }}</div>
        </div>
        
        <div class="header-actions">
          <div class="live-meta">
            <span class="division-tag">Archive Division</span>
  
            <!-- NEW LOCATION ELEMENT -->
            <span class="location">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="location-icon">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              {{ currentPlace }}
            </span>

            <span class="date">{{ currentDate }}</span>
            <span class="time">{{ currentTime }}</span>
          </div>
          
          <div class="action-divider"></div>
          
          <button class="header-icon-btn" @click="toggleTheme" :title="theme === 'dark' ? 'Light Mode' : 'Dark Mode'">
            <component :is="theme === 'dark' ? Sun : Moon" :size="18" :stroke-width="1.5" />
          </button>
          
          <button class="header-icon-btn exit" @click="handleLogout" title="Exit System">
            <LogOut :size="18" :stroke-width="1.5" />
          </button>
        </div>
      </header>

      <section class="page-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', system-ui, sans-serif; -webkit-font-smoothing: antialiased; }

.app {
  display: flex;
  min-height: 100vh;
  width: 100%;
  background: var(--content-bg);
}

.sidebar {
  width: 260px;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-main);
  display: flex;
  flex-direction: column;
  padding: 40px 0 0 0;
  z-index: 100;
  overflow-y: auto;
}

.sidebar::-webkit-scrollbar { width: 3px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 10px; }

.logo-area { display: flex; align-items: center; gap: 12px; padding: 0 24px; margin-bottom: 50px; }

.ao-seal {
  width: 42px; height: 42px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(
    135deg,
    var(--hover-bg),
    transparent
);
  border: 1px solid var(--accent);
  color: var(--accent);
  font-family: "Cormorant Garamond", serif;
  font-weight: 700; font-size: 18px; border-radius: 50%;
}

.logo { font-family: "Cormorant Garamond", serif; color: var(--text-primary); font-size: 22px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.tagline { font-size: 9px; color: var(--accent); text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }

.nav-section-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px;
  color: var(--text-muted); padding: 20px 20px 8px 24px; opacity: 0.6; font-weight: 700;
}

.nav-links { display: flex; flex-direction: column; gap: 4px; }
.sidebar a {
  display: flex; align-items: center; gap: 16px; text-decoration: none;
  color: var(--text-muted); padding: 14px 24px; font-size: 14px; font-weight: 500;
  transition: all 0.2s ease;
}
.sidebar a:hover {
  color: var(--accent);
  background: var(--hover-bg);
}
.sidebar a span { transition: transform 0.2s ease; }
.sidebar a:hover span { transform: translateX(4px); }

.sidebar a.router-link-active {
  background: var(--active-bg);
  color: var(--accent);
  font-weight: 700;
  position: relative;
}

.content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--content-bg);
  height: 100vh;
  overflow: hidden;
}

.content-wrapper.authenticated-layout {
  margin-left: 260px;
}

.global-header {
  height: 60px; background: var(--content-bg); border-bottom: 1px solid var(--border-main);
  display: flex; justify-content: space-between; align-items: center; padding: 0 40px; flex-shrink: 0;
}

.breadcrumb { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 800; color: var(--text-muted); }

.header-actions { display: flex; align-items: center; gap: 12px; }
.live-meta { display: flex; align-items: center; gap: 15px; font-size: 13px; font-weight: 700; color: var(--accent); font-variant-numeric: tabular-nums; }
.location {
  display: flex;
  align-items: center;
  color: var(--text-primary);
  font-weight: 600;
}

.location-icon {
  margin-right: 4px;
  color: var(--accent);
  opacity: 0.8;
}
.division-tag{
    color: var(--accent);
    background: var(--hover-bg);
    border: 1px solid var(--border-main);
}

.action-divider { width: 1px; height: 20px; background: var(--border-main); opacity: 0.3; margin: 0 8px; }

.header-icon-btn {
  background: transparent; border: none; color: var(--text-muted); cursor: pointer;
  padding: 8px; border-radius: 8px; display: flex; transition: all 0.2s ease;
}
.header-icon-btn:hover {
    color: var(--accent);
    background: var(--hover-bg);
}
.header-icon-btn.exit:hover { color: #f87171; background: rgba(239, 68, 68, 0.1); }

.sidebar-user {
  margin-top: auto;
  padding: 20px;
  border-top: 1px solid var(--border-main);
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
}
.user-avatar img { width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--accent); object-fit: cover; }
.user-info { display: flex; flex-direction: column; justify-content: center; }
.user-name { font-size: 13px; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.user-role { font-size: 10px; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

.page-content { flex: 1; padding: 0 !important; overflow-y: auto; background: var(--content-bg); }
.page-content::-webkit-scrollbar { display: none; }

.sync-info { display: inline-flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 11px; }
.sync-info:active { color: var(--accent); }

.status-dot {
  width: 6px; height: 6px; background: #2dd4bf; border-radius: 50%;
  box-shadow: 0 0 8px rgba(45, 212, 191, 0.4); animation: sync-pulse 2s infinite;
}

@keyframes sync-pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(1.2); } 100% { opacity: 1; transform: scale(1); } }

.content-area.full-screen-editor { margin-left: 0 !important; width: 100vw; height: 100vh; z-index: 100; }
.content-wrapper.no-padding { width: 100vw; margin: 0; padding: 0; }

.details-window-theme .page-content:has(> .details-page) { padding: 0 !important; margin: 0 !important; height: 100vh; overflow: auto !important; }
.details-window-theme .section { background-color: #065f46 !important; border: 1px solid #0f766e !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }

.library-branding { margin-right: auto; display: flex; flex-direction: column; border-left: 3px solid #fbbf24; padding-left: 15px; }
.institution-name { font-family: 'Serif', 'Georgia', serif; font-size: 18px; font-weight: 800; color: #fbbf24; letter-spacing: 1px; text-transform: uppercase; }
.record-type { font-size: 10px; color: #2dd4bf; text-transform: uppercase; letter-spacing: 2px; margin-top: -2px; }

.details-window-theme .title { color: #fbbf24 !important; border-bottom: 2px solid #d97706 !important; padding-bottom: 12px; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 2px; font-weight: 800; display: inline-block; }
.mobile-menu-toggle { display: none; }
.mobile-overlay { display: none; }
.header-left { display: flex; align-items: center; gap: 12px; }


@media print {
  html, body, .app, .content-wrapper, .page-content, .details-page { background: white !important; color: black !important; margin: 0 !important; padding: 0 !important; height: auto !important; width: 100% !important; }
  .library-branding { border-left: 3px solid black !important; }
  .institution-name { color: black !important; }
  .record-type { color: #666 !important; }
  .sidebar, .global-header, .action-bar, .theme-btn, .header-icon-btn { display: none !important; }
  .content-wrapper { margin: 0 !important; }
  .title { color: black !important; border-bottom: 2px solid black !important; font-size: 22pt !important; text-align: center; margin-bottom: 30px !important; }
  .section { background: white !important; border: 1px solid #ccc !important; break-inside: avoid; margin-bottom: 15px !important; padding: 15px !important; box-shadow: none !important; }
  .details-page::after { content: "Official Library Record - Athenaeum Orbis"; display: block; text-align: center; font-size: 8pt; color: #999; margin-top: 50px; border-top: 1px solid #eee; padding-top: 10px; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}

/* =====================================================
   📱 MOBILE RESPONSIVENESS FIXES
===================================================== */
@media (max-width: 768px) {
  /* 1. Stack the app layout vertically */

  .mobile-menu-toggle { 
    display: block; 
  }
  .app {
    flex-direction: column;
  }

  /* 2. Un-fix the Sidebar so it doesn't overlap content */
  /* 2. Convert Sidebar to an off-screen drawer */
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 260px;
    height: 100vh;
    transform: translateX(-100%); /* Hides it off the left edge */
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 1000;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border-main);
    /* Mobile-specific padding adjustments if needed */
    padding-bottom: 20px; 
  }

  /* 3. Slide it in when active */
  .sidebar.mobile-open {
    transform: translateX(0);
  }

  /* 4. Display the dark backdrop overlay */
  .mobile-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(2px);
    z-index: 999; /* Sits just underneath the sidebar (1000) */
  }

  /* 3. Remove the 260px left margin that is squishing the tables */
  .content-wrapper.authenticated-layout {
    margin-left: 0; 
    /* height: auto;
    overflow: visible; */
  }

  /* 4. Adjust the Global Header for smaller screens */
  .global-header {
    padding: 0 15px; 
    height: auto;
    min-height: 60px;
    gap: 10px;
    flex-wrap: wrap; /* Allows header items to wrap if they run out of space */
  }

  /* 5. Make the logo area compact */
  .logo-area {
    margin-bottom: 20px;
  }
}
</style>