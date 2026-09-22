<template>
  <div class="dashboard">

    <!-- =====================================================
         LOADING STATE
    ====================================================== -->
    <div v-if="loading" class="dashboard-loading">
      <div class="loading-ring"></div>
      <span>Loading archive data...</span>
    </div>

    <template v-else>

      <!-- =====================================================
           TOP BAR
      ====================================================== -->
      <section class="topbar">
        <div class="brand">
          <div class="brand-mark"></div>

          <div>
            <span class="eyebrow">ATHENAEUM ORBIS</span>
            <h1>Archive Intelligence Console</h1>
          </div>
        </div>

        <div class="system-info">
          <button
            class="refresh-btn"
            :class="{ 'is-loading': loading }"
            :disabled="loading"
            @click="loadDashboard"
            title="Refresh archive data"
          >
            <RefreshCw :size="16" />
          </button>
        </div>
      </section>


      <!-- =====================================================
           KPI GRID
      ====================================================== -->
      <section class="kpi-grid">

        <div class="kpi">
          <BookOpen class="kpi-icon" />
          <span>Works</span>
          <h2>{{ summaryStats.total_works ?? 0 }}</h2>
        </div>

        <div class="kpi">
          <Book class="kpi-icon" />
          <span>Items</span>
          <h2>{{ summaryStats.total_items ?? 0 }}</h2>
        </div>

        <div v-if="auth.hasPermission('operations.view')" class="kpi">
          <FileText class="kpi-icon" />
          <span>In Circulation</span>
          <h2>{{ inCirculation }}</h2>
        </div>

        <div class="kpi">
          <Layers class="kpi-icon" />
          <span>Categories</span>
          <h2>{{ totalCategories }}</h2>
        </div>

        <div v-if="auth.hasPermission('operations.view')" class="kpi">
          <AlertTriangle class="kpi-icon" />
          <span>Missing</span>
          <h2>{{ summaryStats.missing_items || 0 }}</h2>
        </div>

        <div v-if="auth.hasPermission('operations.view')" class="kpi">
          <ShieldCheck class="kpi-icon" />
          <span>Damaged</span>
          <h2>{{ summaryStats.damaged_items || 0 }}</h2>
        </div>

      </section>


      <!-- =====================================================
           MAIN GRID
      ====================================================== -->
      <section class="grid">

        <!-- ===================================================
             PANEL 1: RECENT ACTIVITY
        ==================================================== -->
        <div v-if="auth.hasPermission('audit.view')" class="panel">

          <div class="panel-header">
            <h3>
              <Activity :size="17" />
              Recent Activity
            </h3>

            <RouterLink
              v-if="auth.hasPermission('audit.view')"
              to="/audit-trail"
              class="view-all-link"
            >
              View All &rarr;
            </RouterLink>
          </div>

          <div
            v-if="recentActivities.length === 0"
            class="empty-state"
          >
            No operational events logged yet.
          </div>

          <div
            v-else
            class="activity"
            v-for="log in recentActivities"
            :key="log.id"
          >
            <div
              class="timeline"
              :class="getTimelineClass(log.action_type || log.action)"
            ></div>

            <div class="activity-content">
              <div class="activity-title-row">
                <strong>
                  {{ formatActionTitle(log.action_type || log.action) }}
                </strong>

                <span class="actor-tag">
                  {{ log.actor_username || 'Operator' }}
                </span>
              </div>

              <p>
                {{ log.summary || log.details || getBookTitle(log.serial_no) }}
              </p>
            </div>

            <small>
              {{ formatRelativeTime(log.timestamp || log.changed_at) }}
            </small>
          </div>

        </div>


        <!-- ===================================================
             PANEL 2: LATEST ACCESSIONS
        ==================================================== -->
        <div class="panel">

          <div class="panel-header">
            <h3>
              <Book :size="17" />
              Latest Accessions
            </h3>
          </div>

          <div
            class="book"
            v-for="book in newestArrivals"
            :key="book.serial_no"
          >
            <div class="book-no">
              {{ book.accession_no }}
            </div>

            <div class="book-info">
              <strong>{{ book.title }}</strong>
              <span>{{ book.author }}</span>
            </div>

            <small>
              {{ formatDate(book.created_at) }}
            </small>
          </div>

        </div>


        <!-- ===================================================
             PANEL 3: CATEGORIES
        ==================================================== -->
        <div class="panel">

          <div class="panel-header">
            <h3>
              <Layers :size="17" />
              Categories
            </h3>
          </div>

          <div
            class="bar-row"
            v-for="(count, name) in categoryStats"
            :key="name"
          >
            <label>{{ name }}</label>

            <div class="bar">
              <div
                class="fill"
                :style="{
                  width: totalItems > 0
                    ? (count / totalItems * 100) + '%'
                    : '0%'
                }"
              ></div>
            </div>

            <strong>{{ count }}</strong>
          </div>

        </div>


        <!-- ===================================================
             PANEL 4: LANGUAGES
        ==================================================== -->
        <div class="panel">

          <div class="panel-header">
            <h3>
              <Globe :size="17" />
              Languages
            </h3>
          </div>

          <div
            class="bar-row"
            v-for="lang in summaryStats.languages"
            :key="lang.language"
          >
            <label>{{ lang.language }}</label>

            <div class="bar">
              <div
                class="fill"
                :style="{
                  width: totalItems > 0
                    ? (lang.count / totalItems * 100) + '%'
                    : '0%'
                }"
              ></div>
            </div>

            <strong>{{ lang.count }}</strong>
          </div>

          <div class="genre-footer">
            {{ totalGenres }} Genres Catalogued
          </div>

        </div>


        <!-- ===================================================
             PANEL 5: QUICK ACTIONS
        ==================================================== -->
        <div class="panel">

          <div class="panel-header">
            <h3>
              <ArrowRight :size="17" />
              Quick Actions
            </h3>
          </div>

          <div class="actions">

            <!-- Create Work -->
            <RouterLink
              v-if="auth.hasPermission('catalogue.create')"
              to="/create-work"
            >
              + New Work
            </RouterLink>

            <!-- Create Item -->
            <RouterLink
              v-if="auth.hasPermission('catalogue.create')"
              to="/create-item"
            >
              + New Item
            </RouterLink>

            <!-- Catalogue -->
            <RouterLink
              v-if="auth.hasPermission('catalogue.view')"
              to="/catalogue"
            >
              Catalogue
            </RouterLink>

            <!-- Search -->
            <RouterLink
              v-if="auth.hasPermission('search.view')"
              to="/search"
            >
              Search
            </RouterLink>

          </div>

        </div>


        <!-- ===================================================
             PANEL 6: ARCHIVE STATUS
        ==================================================== -->
        <div class="panel">

          <div class="panel-header">
            <h3>
              <Database :size="17" />
              Archive Status
            </h3>
          </div>

          <div class="status">
            <span>Database</span>
            <div class="dot"></div>
          </div>

          <div class="status">
            <span>Archive Loaded</span>
            <strong>{{ totalItems }}</strong>
          </div>

          <div class="status">
            <span>Languages</span>
            <strong>
              {{
                (summaryStats.languages &&
                summaryStats.languages.length) || 0
              }}
            </strong>
          </div>

          <div class="status">
            <span>Categories</span>
            <strong>{{ totalCategories }}</strong>
          </div>

        </div>

      </section>

    </template>
  </div>
</template>


<script setup>
import { ref, computed, onMounted } from "vue"
import axios from "axios"
import { useAuthStore } from "@/stores/auth"
import { RouterLink } from "vue-router"

import {
  BookOpen,
  Book,
  FileText,
  AlertTriangle,
  ShieldCheck,
  Layers,
  Globe,
  Database,
  ArrowRight,
  Activity,
  RefreshCw
} from "lucide-vue-next"


/* =====================================================
   AUTH
===================================================== */

const auth = useAuthStore()


/* =====================================================
   DATA
===================================================== */

const rawCatalogue = ref([])
const recentActivities = ref([])

const summaryStats = ref({
  total_accessions: 0,
  missing_items: 0,
  damaged_items: 0,
  languages: [],
  recent_activity: []
})

const loading = ref(true)


/* =====================================================
   FETCH DATA
===================================================== */

async function loadDashboard() {
  loading.value = true

  try {
    const [
      summaryRes,
      catRes,
      auditRes
    ] = await Promise.allSettled([
      axios.get("/dashboard/summary"),

      axios.get("/catalogue/", {
        params: {
          limit: 500
        }
      }),

      axios.get("/status_audit/system-logs", {
        params: {
          limit: 8
        }
      })
    ])


    /* -----------------------------------------------
       DASHBOARD SUMMARY
    ------------------------------------------------ */

    if (summaryRes.status === "fulfilled") {
      summaryStats.value = summaryRes.value.data || {}
    }


    /* -----------------------------------------------
       CATALOGUE
    ------------------------------------------------ */

    if (catRes.status === "fulfilled") {
      rawCatalogue.value =
        catRes.value.data?.data || []
    }


    /* -----------------------------------------------
       AUDIT / RECENT ACTIVITY
    ------------------------------------------------ */

    if (
      auditRes.status === "fulfilled" &&
      auditRes.value.data?.items
    ) {
      recentActivities.value =
        auditRes.value.data.items

    } else if (
      summaryStats.value.recent_activity?.length
    ) {
      recentActivities.value =
        summaryStats.value.recent_activity
    }

  } catch (e) {
    console.error(
      "Failed to load dashboard data:",
      e
    )

  } finally {
    loading.value = false
  }
}


/* =====================================================
   COMPUTED
===================================================== */

const totalItems = computed(() => {
  return rawCatalogue.value.length
})


const newestArrivals = computed(() => {
  return [...rawCatalogue.value]
    .sort(
      (a, b) =>
        (b.serial_no || 0) -
        (a.serial_no || 0)
    )
    .slice(0, 8)
})


const categoryStats = computed(() => {
  const stats = {}

  rawCatalogue.value.forEach(book => {
    const cat =
      book.category || "General"

    stats[cat] =
      (stats[cat] || 0) + 1
  })

  return stats
})


const inCirculation = computed(() => {
  return rawCatalogue.value.filter(
    b =>
      b.availability_status ===
      "IN_RESEARCH_USE"
  ).length
})


const totalGenres = computed(() => {
  const genres = new Set()

  rawCatalogue.value.forEach(book => {

    if (book.genre) {

      book.genre
        .split(/[/,]+/)
        .forEach(g => {
          genres.add(g.trim())
        })

    }
  })

  return genres.size
})


const totalCategories = computed(() => {
  return Object.keys(
    categoryStats.value
  ).length
})


/* =====================================================
   HELPERS & FORMATTERS
===================================================== */

function getBookTitle(id) {

  if (!id) {
    return "System Action"
  }

  const book =
    rawCatalogue.value.find(
      b =>
        String(b.serial_no) ===
        String(id)
    )

  return book
    ? book.title
    : "Catalogue Record"
}


function formatActionTitle(action) {

  if (!action) {
    return "SYSTEM EVENT"
  }

  return action.replace(
    /_/g,
    " "
  )
}


function getTimelineClass(action) {

  if (!action) {
    return ""
  }

  const act =
    action.toUpperCase()

  if (act.includes("LOGIN")) {
    return "login"
  }

  if (act.includes("LOGOUT")) {
    return "logout"
  }

  if (
    act.includes("CREATE") ||
    act.includes("ADD") ||
    act.includes("NEW")
  ) {
    return "create"
  }

  if (
    act.includes("DELETE") ||
    act.includes("DROP") ||
    act.includes("REJECT")
  ) {
    return "danger"
  }

  return ""
}


function formatRelativeTime(dateStr) {

  if (!dateStr) {
    return ""
  }

  let date =
    new Date(dateStr)

  if (
    typeof dateStr === "string" &&
    !dateStr.endsWith("Z") &&
    !dateStr.includes("+")
  ) {
    date =
      new Date(
        dateStr.replace(
          " ",
          "T"
        ) + "Z"
      )
  }

  const diffMinutes =
    Math.floor(
      (
        Date.now() -
        date.getTime()
      ) / 60000
    )

  if (
    isNaN(diffMinutes) ||
    diffMinutes < 1
  ) {
    return "Just now"
  }

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`
  }

  if (diffMinutes < 1440) {
    return `${Math.floor(
      diffMinutes / 60
    )}h ago`
  }

  return `${Math.floor(
    diffMinutes / 1440
  )}d ago`
}


function formatDate(date) {

  if (!date) {
    return ""
  }

  return new Date(
    date
  ).toLocaleDateString(
    [],
    {
      month: "short",
      day: "numeric",
      year: "numeric"
    }
  )
}


/* =====================================================
   LIFECYCLE
===================================================== */

onMounted(async () => {
  await loadDashboard()
})
</script>


<style scoped>

/* ===========================================================
   ATHENAEUM ORBIS: ARCHIVE INTELLIGENCE CONSOLE
=========================================================== */

.dashboard {
  min-height: 100vh;
  background: var(--content-bg);
  padding: 28px;
  color: var(--text-primary);
}


/* ===========================================================
   TOP BAR
=========================================================== */

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}


.brand {
  display: flex;
  align-items: center;
  gap: 18px;
}


.brand-mark {
  width: 14px;
  height: 50px;
  border-radius: 30px;
  background: var(--accent);
  box-shadow: 0 0 18px var(--hover-bg);
}


.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: var(--accent);
}


.brand h1 {
  margin-top: 6px;
  font-family: "Cormorant Garamond", serif;
  font-size: 34px;
  color: var(--text-primary);
}


/* ===========================================================
   REFRESH BUTTON
=========================================================== */

.refresh-btn {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  cursor: pointer;
  background: var(--surface);
  border: 1px solid var(--border-main);
  color: var(--accent);
  transition:
    background .2s ease,
    border-color .2s ease,
    color .2s ease,
    transform .2s ease;
}


.refresh-btn:hover {
  background: var(--hover-bg);
  border-color: var(--accent);
  color: var(--accent);
  transform: rotate(15deg);
}


.refresh-btn.is-loading svg {
  animation:
    refresh-spin .8s linear infinite;
}


.refresh-btn:disabled {
  cursor: wait;
  opacity: .7;
}


@keyframes refresh-spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}


/* ===========================================================
   KPI GRID
=========================================================== */

.kpi-grid {
  display: grid;
  grid-template-columns:
    repeat(6, 1fr);
  gap: 18px;
  margin-bottom: 28px;
}


.kpi {
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 14px;
  padding: 18px;
  transition: .25s;
}


.kpi:hover {
  transform: translateY(-4px);
  border-color: var(--accent);
}


.kpi-icon {
  width: 17px;
  height: 17px;
  color: var(--accent);
  margin-bottom: 14px;
  opacity: .85;
}


.kpi span {
  display: block;
  color: var(--text-muted);
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 1.2px;
}


.kpi h2 {
  margin-top: 12px;
  font-size: 34px;
  font-family: "Cormorant Garamond", serif;
  color: var(--text-primary);
}


.danger h2 {
  color: #ef4444;
}


.warning h2 {
  color: #f59e0b;
}


/* ===========================================================
   PANELS GRID
=========================================================== */

.grid {
  display: grid;
  grid-template-columns:
     1fr 1fr;
  gap: 18px;
}


.panel {
  background: var(--surface);
  border: 1px solid var(--border-main);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
  align-items: start;
}


.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}


.panel-header h3 {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 16px;
  font-family:
    "Cormorant Garamond",
    serif;
  font-weight: 600;
  letter-spacing: .3px;
  color: var(--text-primary);
}


.view-all-link {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--accent);
  text-decoration: none;
  transition: opacity .2s ease;
}


.view-all-link:hover {
  opacity: 0.8;
}


/* ===========================================================
   RECENT ACTIVITY
=========================================================== */

.empty-state {
  padding: 36px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}


.activity {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-main);
  transition: background .2s ease;
}


.activity:last-child {
  border: none;
}


.activity:hover {
  background: var(--hover-bg);
}


.timeline {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow:
    0 0 10px
    rgba(184, 146, 90, .4);
  flex-shrink: 0;
}


.timeline.login {
  background: #3b82f6;
  box-shadow:
    0 0 10px
    rgba(59, 130, 246, .4);
}


.timeline.logout {
  background: var(--accent);
  box-shadow:
    0 0 10px
    rgba(184, 146, 90, .4);
}


.timeline.create {
  background: #22c55e;
  box-shadow:
    0 0 10px
    rgba(34, 197, 94, .4);
}


.timeline.danger {
  background: #ef4444;
  box-shadow:
    0 0 10px
    rgba(239, 68, 68, .4);
}


.activity-content {
  flex: 1;
  min-width: 0;
}


.activity-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}


.activity-content strong {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: .5px;
}


.actor-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--content-bg);
  border: 1px solid var(--border-main);
  color: var(--text-muted);
}


.activity-content p {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}


.activity small {
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
}


/* ===========================================================
   BOOKS & ACCESSIONS
=========================================================== */

.book {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-main);
  transition: background .2s ease;
}


.book:last-child {
  border: none;
}


.book:hover {
  background: var(--hover-bg);
}


.book-no {
  width: 90px;
  color: var(--accent);
  font-weight: 700;
  font-size: 11px;
  letter-spacing: .8px;
  font-family: monospace;
}


.book-info {
  flex: 1;
  min-width: 0;
}


.book-info strong {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}


.book-info span {
  color: var(--text-muted);
  font-size: 11px;
}


.book small {
  color: var(--text-muted);
  font-size: 11px;
}


/* ===========================================================
   BARS & DISTRIBUTIONS
=========================================================== */

.bar-row {
  display: grid;
  grid-template-columns:
    110px 1fr 35px;
  gap: 10px;
  align-items: center;
  margin: 12px 0;
}


.bar {
  height: 8px;
  background: var(--hover-bg);
  border-radius: 20px;
  overflow: hidden;
}


.fill {
  height: 100%;
  background: var(--accent);
  border-radius: 20px;
  transition: width .4s ease;
}


.genre-footer {
  margin-top: 22px;
  color: var(--text-muted);
  font-size: 12px;
}


/* ===========================================================
   QUICK ACTIONS
=========================================================== */

.actions {
  display: grid;
  grid-template-columns:
    repeat(2, 1fr);
  gap: 14px;
}


.actions a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-decoration: none;
  color: var(--text-primary);
  background: var(--content-bg);
  border: 1px solid var(--border-main);
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 12px;
  font-weight: 600;
  transition: .25s;
}


.actions a:hover {
  border-color: var(--accent);
  transform: translateY(-3px);
}


/* ===========================================================
   ARCHIVE STATUS
=========================================================== */

.status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 13px 0;
  border-bottom: 1px solid var(--border-main);
  font-size: 12px;
}


.status:last-child {
  border: none;
}


.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow:
    0 0 10px
    rgba(34, 197, 94, .65);
}


/* ===========================================================
   LOADING STATE
=========================================================== */

.dashboard-loading {
  min-height: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);
}


.loading-ring {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-main);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation:
    dashboard-loading-spin
    .8s linear infinite;
}


@keyframes dashboard-loading-spin {
  to {
    transform: rotate(360deg);
  }
}


/* ===========================================================
   RESPONSIVE
=========================================================== */

@media (max-width: 1200px) {

  .kpi-grid {
    grid-template-columns:
      repeat(2, 1fr);
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }

}


@media (max-width: 768px) {

  .dashboard {
    padding: 18px;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .actions {
    grid-template-columns: 1fr;
  }

  .bar-row {
    grid-template-columns:
      90px 1fr 35px;
  }

}

</style>