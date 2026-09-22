<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from "vue"
import axios from "axios"
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router"
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import BatchRegisterModal from '@/components/print/BatchRegisterModal.vue'
import LedgerHealth from './components/LedgerHealth.vue'
import {
  LayoutDashboard,
  Library,
  Search,
  Users,
  ClipboardCheck,
  PlusCircle,
  BookPlus,
  Sun,
  Moon,
  LogOut,
  Bell,
  BookOpen,
  FileText,
  AlertTriangle,
  ShieldCheck,
  Tag,
  Info,
  Menu,
  Printer
} from 'lucide-vue-next'
import { listen } from '@tauri-apps/api/event'

const theme = ref("dark")
const route = useRoute()
const router = useRouter()
const isMobileMenuOpen = ref(false)

// --- PRINT MODAL REF & TRIGGER ---
const batchModalRef = ref(null)
const openPrintModal = () => {
  batchModalRef.value?.openModal()
}

// --- PINIA AUTHENTICATION INTEGRATION ---
const authStore = useAuthStore()
const { isAuthenticated, userName: user_name, userRole: user_role } = storeToRefs(authStore)

let unlistenNav = null
const isEditing = computed(() => {
  return route.path.includes('edit-item')
})

const currentTime = ref('')
const currentDate = ref('')
const currentPlace = ref('Locating...')
const lastUpdated = ref('')
let timeInterval = null

const notifications = ref([])
let notificationPoller = null

const docketCount = ref(0)
let docketPoller = null

const unreadNotifications = computed(() =>
  notifications.value.filter(n => !n.is_read).length
)

const showNotifications = ref(false)

const toggleNotifications = async () => {
  if (showNotifications.value) {
    // Closing the panel clears notifications that were already read.
    notifications.value = notifications.value.filter(
      notification => !notification.is_read
    )

    showNotifications.value = false
    return
  }

  showNotifications.value = true

  try {
    await axios.post('/notifications/read')

    // Keep them visible while the panel is open so the Keeper can read them.
    // The badge disappears because they are now read.
    notifications.value = notifications.value.map(notification => ({
      ...notification,
      is_read: true
    }))
  } catch (err) {
    console.warn('Notification read update failed:', err)
  }
}

const handleNotificationOutsideClick = (event) => {
  if (!showNotifications.value) return

  const panel = document.querySelector('.notification-panel')
  const button = document.querySelector('.notification-btn')

  if (
    panel &&
    !panel.contains(event.target) &&
    button &&
    !button.contains(event.target)
  ) {
    showNotifications.value = false

    notifications.value = notifications.value.filter(
      notification => !notification.is_read
    )
  }
}

const loadNotifications = async () => {
  if (user_role.value !== 'The Keeper') return

  try {
    const response = await axios.get('/notifications')
    notifications.value = Array.isArray(response.data) ? response.data : []
  } catch (err) {
    console.warn('Notification load failed:', err)
  }
}


const loadDocketCount = async () => {
  if (user_role.value !== 'The Chief') {
    docketCount.value = 0
    return
  }

  try {
    const [worksResponse, itemsResponse] = await Promise.all([
      axios.get('/catalogue/pending-works'),
      axios.get('/catalogue/pending-items')
    ])

    const pendingWorks = Array.isArray(worksResponse.data)
      ? worksResponse.data.length
      : 0

    const pendingItems = Array.isArray(itemsResponse.data)
      ? itemsResponse.data.length
      : 0

    docketCount.value = pendingWorks + pendingItems
  } catch (err) {
    console.warn('Docket count load failed:', err)
  }
}
const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  currentDate.value = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

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

const handleLogout = () => {
  authStore.logout()
  router.push("/login")
}

// Global Ctrl+P shortcut to trigger the print popup
const handleGlobalKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {
    e.preventDefault()
    openPrintModal()
  }
}

watch(
  () => route.path,
  () => {
    updateSyncTime()
    isMobileMenuOpen.value = false
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
  loadNotifications()
  timeInterval = setInterval(updateClock, 1000)
  window.addEventListener('keydown', handleGlobalKeydown)

  document.addEventListener('click', handleNotificationOutsideClick)

  const saved = localStorage.getItem("ui-theme") || "dark"
  theme.value = saved
  applyTheme(saved)

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
  notificationPoller = setInterval(() => {
  if (user_role.value === 'The Keeper' && !showNotifications.value) {
    loadNotifications()
  }
 }, 10000)

 docketPoller = setInterval(() => {
  loadDocketCount()
}, 10000)

loadDocketCount()

})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  if (unlistenNav) unlistenNav()
  window.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('click', handleNotificationOutsideClick)
  if (notificationPoller) clearInterval(notificationPoller)
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
  <RouterLink to="/dashboard">
    <LayoutDashboard :size="18" :stroke-width="1.5" />
    <span>Dashboard</span>
  </RouterLink>

  <RouterLink to="/search">
    <Search :size="18" :stroke-width="1.5" />
    <span>Search Archive</span>
  </RouterLink>

  <RouterLink to="/catalogue">
    <Library :size="18" :stroke-width="1.5" />
    <span>Catalogue</span>
  </RouterLink>

  <RouterLink
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    to="/admin/users"
  >
    <Users :size="18" :stroke-width="1.5" />
    <span>Personnel & Access</span>
  </RouterLink>

   <RouterLink
  v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
  to="/docket"
>
  <ClipboardCheck :size="18" :stroke-width="1.5" />

  <span class="nav-label-with-count">
    <span>Docket</span>
    <span v-if="docketCount > 0" class="docket-badge">
      {{ docketCount }}
    </span>
  </span>
</RouterLink>


  <div
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    class="nav-section-label"
  >
    Inventory
  </div>

  <RouterLink
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    to="/create-work"
  >
    <FileText :size="18" :stroke-width="1.5" />
    <span>Works</span>
  </RouterLink>

  <RouterLink
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    to="/create-item"
  >
    <BookOpen :size="18" :stroke-width="1.5" />
    <span>Items</span>
  </RouterLink>

  <RouterLink
    v-if="user_role === 'The Chief'"
    to="/incidents"
  >
    <AlertTriangle :size="18" :stroke-width="1.5" />
    <span>Incidents</span>
  </RouterLink>

  <div
    v-if="user_role === 'The Chief'"
    class="nav-section-label"
  >
    Classification
  </div>

  <RouterLink
    v-if="user_role === 'The Chief'"
    to="/classification/authors"
  >
    <Users :size="18" :stroke-width="1.5" />
    <span>Authors</span>
  </RouterLink>

  <RouterLink
    v-if="user_role === 'The Chief'"
    to="/classification/authorities"
  >
    <ClipboardCheck :size="18" :stroke-width="1.5" />
    <span>Authorities</span>
  </RouterLink>

  <RouterLink
    v-if="user_role === 'The Chief'"
    to="/classification/subjects"
  >
    <Tag :size="18" :stroke-width="1.5" />
    <span>Subjects</span>
  </RouterLink>

  <div
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    class="nav-section-label"
  >
    System
  </div>

  <RouterLink
    v-if="user_role === 'The Chief'"
    to="/audit-trail"
  >
    <ShieldCheck :size="18" :stroke-width="1.5" />
    <span>Audit Trail</span>
  </RouterLink>

  <button
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    class="sidebar-action-btn"
    @click="openPrintModal"
    title="Print Filtered Catalogue Register"
  >
    <Printer :size="18" :stroke-width="1.5" />
    <span>Print Register</span>
  </button>

  <RouterLink
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    to="/reports"
  >
    <LayoutDashboard :size="18" :stroke-width="1.5" />
    <span>Reports</span>
  </RouterLink>

  <RouterLink
    v-if="user_role === 'The Chief' || user_role === 'The Keeper'"
    to="/about"
  >
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
        'authenticated-layout': isAuthenticated && !isEditing && !route.path.includes('/details/') && !route.path.includes('/print')
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
          <!-- CRYPTOGRAPHIC LEDGER HEALTH STATUS PILL -->
          <LedgerHealth />

          <div class="live-meta">
            <span class="division-tag">Archive Division</span>

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
          <button
            v-if="user_role === 'The Keeper'"
            class="header-icon-btn notification-btn"
            title="Notifications"
            @click="toggleNotifications"
          >
            <Bell :size="18" :stroke-width="1.5" />
            <span v-if="unreadNotifications > 0" class="notification-badge">
              {{ unreadNotifications }}
            </span>
          </button>
          <div
  v-if="user_role === 'The Keeper' && showNotifications"
  class="notification-panel"
>
  <div class="notification-panel-header">
    <span>Notifications</span>
    <span v-if="unreadNotifications > 0">
      {{ unreadNotifications }} unread
    </span>
  </div>

  <div v-if="notifications.length === 0" class="notification-empty">
    No notifications.
  </div>

  <div
    v-for="notification in notifications"
    :key="notification.notification_id"
    class="notification-item"
    :class="{ unread: !notification.is_read }"
  >
    <div class="notification-message">
      {{ notification.message }}
    </div>
    <div class="notification-time">
      {{ new Date(notification.created_at).toLocaleString() }}
    </div>
  </div>
</div>
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

    <!-- BATCH REGISTER MODAL (GLOBAL POPUP) -->
    <BatchRegisterModal ref="batchModalRef" />
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
  background: linear-gradient(135deg, var(--hover-bg), transparent);
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

.sidebar a,
.sidebar-action-btn {
  display: flex; align-items: center; gap: 16px; text-decoration: none;
  color: var(--text-muted); padding: 14px 24px; font-size: 14px; font-weight: 500;
  transition: all 0.2s ease;
  background: none;
  border: none;
  width: 100%;
  font-family: inherit;
  cursor: pointer;
  text-align: left;
}

.sidebar a:hover,
.sidebar-action-btn:hover {
  color: var(--accent);
  background: var(--hover-bg);
}

.sidebar a span,
.sidebar-action-btn span { transition: transform 0.2s ease; }

.sidebar a:hover span,
.sidebar-action-btn:hover span { transform: translateX(4px); }

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

.content-wrapper.no-padding {
  width: 100% !important;
  margin-left: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
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

.division-tag {
  color: var(--accent);
  background: var(--hover-bg);
  border: 1px solid var(--border-main);
}

.action-divider { width: 1px; height: 20px; background: var(--border-main); opacity: 0.3; margin: 0 8px; }

.header-icon-btn {
  background: transparent; border: none; color: var(--text-muted); cursor: pointer;
  padding: 8px; border-radius: 8px; display: flex; transition: all 0.2s ease;
}

.notification-btn {
  position: relative;
}

.notification-badge {
  position: absolute;
  top: 1px;
  right: 1px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--accent);
  color: var(--sidebar-bg);
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
}

.notification-panel {
  position: absolute;
  top: 48px;
  right: 0;
  width: 380px;
  max-height: 420px;
  overflow-y: auto;
  background: var(--surface-2);
  color: var(--text-primary);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  box-shadow: var(--shadow);
  z-index: 9999;
}

.notification-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-main);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.notification-empty {
  min-height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
}

.notification-item {
  position: relative;
  margin: 12px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 10px;
  color: var(--text-primary);
}

.notification-item.unread {
  background: var(--hover-bg);
  border-color: var(--accent);
}

.notification-message {
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
}

.notification-time {
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 11px;
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

.mobile-menu-toggle { display: block; }
.mobile-overlay { display: none; }
.header-left { display: flex; align-items: center; gap: 12px; }

.nav-label-with-count {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.docket-badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}

@media print {
  html, body, #app, .app {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    margin: 0 !important;
    padding: 0 !important;
    height: auto !important;
    width: 100% !important;
    box-shadow: none !important;
  }

  body.batch-print-active .sidebar,
  body.batch-print-active .global-header,
  body.batch-print-active .content-wrapper,
  body.batch-print-active .page-content,
  body.batch-print-active .mobile-overlay {
    display: none !important;
  }

  * {
    -webkit-print-color-adjust: economy !important;
    print-color-adjust: economy !important;
  }

}

@media (max-width: 768px) {
  .mobile-menu-toggle { display: block; }
  .app { flex-direction: column; }
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 260px;
    height: 100vh;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 1000;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border-main);
    padding-bottom: 20px;
  }
  .sidebar.mobile-open { transform: translateX(0); }
  .mobile-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(2px);
    z-index: 999;
  }
  .content-wrapper.authenticated-layout { margin-left: 0; }
  .global-header {
    padding: 0 15px;
    height: auto;
    min-height: 60px;
    gap: 10px;
    flex-wrap: wrap;
  }
  .logo-area { margin-bottom: 20px; }
}
</style>
