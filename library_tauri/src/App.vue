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
  LogOut,
  BookOpen,
  FileText,
  AlertTriangle,
  ShieldCheck,
  Users,
  Tag
} from 'lucide-vue-next'

const theme = ref("dark")
const route = useRoute()
const router = useRouter()

import { listen } from '@tauri-apps/api/event'

let unlistenNav = null
const isEditing = computed(() => route.path.includes('edit-item'))

const currentTime = ref('')
const currentDate = ref('')
const currentPlace = ref('')
const lastUpdated = ref('')
let timeInterval = null

// --- AUTHENTICATION & USER VARIABLES ---
const isAuthenticated = ref(false)
const user_name = ref("Archive Operator")
const user_role = ref("The Seeker")

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

const checkAuthStatus = () => {
  const storedToken = localStorage.getItem("access_token") || sessionStorage.getItem("access_token")
  
  if (!storedToken) {
    isAuthenticated.value = false
    if (route.path !== "/login") {
      router.push("/login")
    }
    return
  }

  isAuthenticated.value = true
  user_name.value = localStorage.getItem("user_name") || "Archive Operator"
  user_role.value = localStorage.getItem("user_role") || "The Seeker"
}

const handleLogout = () => {
  localStorage.removeItem("access_token")
  localStorage.removeItem("refresh_token")
  localStorage.removeItem("user_role")
  localStorage.removeItem("user_name")

  sessionStorage.clear()

  isAuthenticated.value = false
  window.dispatchEvent(new Event("auth-changed"))

  router.push("/login")
}

watch(
  () => route.path,
  () => {
    updateSyncTime()
    checkAuthStatus()
  }
)

onMounted(async () => {
  document.title = "Athenaeum Orbis | Library Management System"
  updateClock()
  updateSyncTime()
  timeInterval = setInterval(updateClock, 1000)

  const saved = localStorage.getItem("ui-theme") || "dark"
  theme.value = saved
  applyTheme(saved)

  checkAuthStatus()

  window.addEventListener("auth-changed", () => {
    checkAuthStatus()
  })

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
        
        <div class="nav-section-label">Classification</div>
        <RouterLink to="/authors"><Users :size="18" :stroke-width="1.5" /><span>Authors</span></RouterLink>
        <RouterLink to="/subjects"><Tag :size="18" :stroke-width="1.5" /><span>Subjects</span></RouterLink>
        
        <div class="nav-section-label">System</div>
        <RouterLink to="/status-audit"><ShieldCheck :size="18" :stroke-width="1.5" /><span>Audit Trail</span></RouterLink>
        <RouterLink to="/reports"><LayoutDashboard :size="18" :stroke-width="1.5" /><span>Reports</span></RouterLink>
      </nav>

      <div class="sidebar-user">
        <div class="user-avatar">
          <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="User Avatar" />
        </div>
        <div class="user-info">
          <span class="user-name">{{ user_name }}</span>
          <span class="user-role">{{ user_role }}</span>
        </div>
      </div>
    </aside>

    <main class="content-wrapper" :class="{ 'no-padding': route.path.includes('/details/'), 'authenticated-layout': isAuthenticated }">
      <header 
        v-if="isAuthenticated && !isEditing && !route.path.includes('/details/') && !route.path.includes('/print')" 
        class="global-header"
      >
        <div class="breadcrumb">{{ route.name || 'Admin Panel' }}</div>
        
        <div class="header-actions">
          <div class="live-meta">
            <span class="division-tag">Archive Division</span>
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
  border-right: 1px solid rgba(184, 146, 90, 0.1);
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
  background: linear-gradient(135deg, rgba(184, 146, 90, 0.05), transparent);
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
  color: #9ca3af; padding: 14px 24px; font-size: 14px; font-weight: 500;
  transition: all 0.2s ease;
}
.sidebar a:hover { color: var(--accent); background: rgba(184, 146, 90, 0.08); }
.sidebar a span { transition: transform 0.2s ease; }
.sidebar a:hover span { transform: translateX(4px); }

.sidebar a.router-link-active { 
  background: rgba(184, 146, 90, 0.12); 
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

.division-tag {
  color: var(--accent); text-transform: uppercase; letter-spacing: 1px; font-size: 11px;
  background: rgba(13, 148, 136, 0.1); padding: 4px 10px; border-radius: 4px;
}

.action-divider { width: 1px; height: 20px; background: var(--border-main); opacity: 0.3; margin: 0 8px; }

.header-icon-btn {
  background: transparent; border: none; color: var(--text-muted); cursor: pointer;
  padding: 8px; border-radius: 8px; display: flex; transition: all 0.2s ease;
}
.header-icon-btn:hover { color: var(--accent); background: rgba(184, 146, 90, 0.1); }
.header-icon-btn.exit:hover { color: #f87171; background: rgba(239, 68, 68, 0.1); }

.sidebar-user {
  margin-top: auto; padding: 20px; border-top: 1px solid rgba(184, 146, 90, 0.1);
  display: flex; align-items: center; gap: 12px; background: rgba(0, 0, 0, 0.2);
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
</style>