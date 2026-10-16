<template>
  <div class="archive-dashboard">
      <!-- HEADER -->
      <header class="dashboard-header">
        <div>
          <div class="dashboard-brand">ATHENAEUM ORBIS</div>
          <h1>Archive Dashboard</h1>
          <p class="header-subtitle">
            The current state of the collection and anything that needs attention.
          </p>
        </div>

        <div class="header-actions">
         

          <button
            class="refresh-control"
            :class="{ spinning: refreshing }"
            :disabled="refreshing"
            title="Refresh archive data"
            :aria-busy="refreshing"
            @click="loadDashboard"
          >
            <RefreshCw :size="17" />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      <div v-if="loading" class="dashboard-loading" aria-live="polite">
        <div class="loading-orbit" aria-hidden="true"></div>
        <span>Loading archive data…</span>
      </div>

      <div v-if="loadError" class="dashboard-error" role="alert">
        <span>{{ loadError }}</span>
        <button type="button" @click="loadDashboard">Retry</button>
      </div>

      <!-- ATTENTION: RENDERED ONLY WHEN THERE IS SOMETHING TO SAY -->
      <section
        v-if="!loading && attentionSignals.length"
        class="attention-section"
        aria-labelledby="attention-title"
      >
        <div class="section-heading">
          <div>
            <div class="section-kicker attention-kicker">ATTENTION</div>
            <h2 id="attention-title">Action Required</h2>
          </div>

          <span class="attention-summary">
            Actionable archive exceptions
          </span>
        </div>

        <div class="attention-list">
          <RouterLink
            v-for="signal in attentionSignals"
            :key="signal.id"
            :to="signal.to"
            class="attention-item"
            :class="`tone-${signal.tone}`"
          >
            <div class="attention-icon">
              <component :is="signal.icon" :size="19" />
            </div>

            <div class="attention-copy">
              <strong>{{ signal.title }}</strong>
              <em v-if="signal.subtitle">{{ signal.subtitle }}</em>
              <span>{{ signal.description }}</span>
            </div>

            <div class="attention-count">{{ signal.count }}</div>
            <ArrowUpRight :size="17" class="attention-arrow" />
          </RouterLink>
        </div>
      </section>

      <!-- COLLECTION STATE -->
      <section v-if="!loading" class="collection-section" aria-labelledby="collection-title">
        <div class="section-heading collection-heading">
          <div>
            <div class="section-kicker">COLLECTION</div>
            <h2 id="collection-title">Archive at a glance</h2>
          </div>

          <RouterLink
            v-if="can('catalogue.view')"
            to="/catalogue"
            class="text-link"
          >
            Open catalogue <ArrowUpRight :size="15" />
          </RouterLink>
        </div>

        <div class="collection-overview">
          <div class="collection-primary">
            <strong>{{ totalItems.toLocaleString() }}</strong>
            <span>items</span>
          </div>

          <div class="collection-facts">
            <div class="collection-fact">
              <span>Titles</span>
              <strong>{{ numberOrZero(summaryStats.total_works) }}</strong>
            </div>

            <div class="collection-fact">
              <span>Categories</span>
              <strong>{{ totalCategories }}</strong>
            </div>

            <div class="collection-fact">
              <span>Genres</span>
              <strong>{{ totalGenres }}</strong>
            </div>

            <div class="collection-fact">
              <span>Languages</span>
              <strong>{{ totalLanguages }}</strong>
            </div>
          </div>
        </div>
      </section>

      <!-- DISTRIBUTION: ONLY RENDER NON-EMPTY DATASETS -->
      <section
        v-if="!loading && distributionSections.length"
        class="distribution-section"
        aria-label="Collection composition"
      >
        <article
          v-for="section in distributionSections"
          :key="section.key"
          class="distribution"
        >
          <div class="distribution-heading">
            <div>
              <div class="section-kicker">{{ section.kicker }}</div>
              <h3>{{ section.title }}</h3>
            </div>
            <span class="distribution-total">{{ section.totalLabel }}</span>
          </div>

          <div class="distribution-list">
            <div
              v-for="row in section.rows"
              :key="row.label"
              class="distribution-row"
            >
              <div class="distribution-label">
                <span>{{ row.label }}</span>
                <strong>{{ row.count.toLocaleString() }}</strong>
              </div>

              <div class="distribution-track">
                <div
                  class="distribution-fill"
                  :class="`fill-${section.key}`"
                  :style="{ width: `${row.percent}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div v-if="section.hasMore" class="distribution-footer">
            Showing the {{ section.rows.length }} largest groups.
          </div>
        </article>
      </section>

      <!-- LATEST ACCESSIONS: MAXIMUM 5 -->
      <section
        v-if="!loading && latestAccessions.length"
        class="recent-section"
        aria-labelledby="latest-accessions-title"
      >
        <div class="section-heading recent-heading">
          <div>
            <div class="section-kicker">ACCESSIONING</div>
            <h2 id="latest-accessions-title">Latest Accessions</h2>
          </div>
          <RouterLink
            v-if="can('catalogue.view')"
            to="/catalogue"
            class="text-link"
          >
            View catalogue <ArrowUpRight :size="15" />
          </RouterLink>
        </div>

        <div class="recent-list">
          <div
            v-for="record in latestAccessions.slice(0, 5)"
            :key="record.serial_no"
            class="recent-item"
          >
            <div class="accession-badge">
              {{ record.accession_no || `#${record.serial_no}` }}
            </div>

            <div class="recent-copy">
              <strong>{{ record.title || "Untitled work" }}</strong>
              <span>{{ record.author || "Creator not recorded" }}</span>
            </div>

            <BookOpen :size="16" class="recent-icon" />
          </div>
        </div>
      </section>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import axios from "axios"
import { RouterLink } from "vue-router"
import { useAuthStore } from "@/stores/auth"

import {
  AlertTriangle,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
} from "lucide-vue-next"

const auth = useAuthStore()

function can(permission) {
  try {
    return typeof auth?.hasPermission === "function"
      ? auth.hasPermission(permission)
      : false
  } catch (error) {
    return false
  }
}

const rawCatalogue = ref([])
const catalogueTotal = ref(null)
const latestAccessions = ref([])
const pendingWorks = ref([])
const pendingItems = ref([])
const keeperAttention = ref({
  rejected_works: [],
  rejected_items: [],
})
const summaryStats = ref({
  total_works: 0,
  total_items: 0,
  missing_items: 0,
  damaged_items: 0,
  categories: [],
  genres: [],
  languages: [],
})

const refreshing = ref(false)
const loading = ref(true)
const loadError = ref("")
const requestErrors = ref({
  summary: false,
  catalogue: false,
  latest: false,
  pendingWorks: false,
  pendingItems: false,
})

let dashboardController = null
let loadGeneration = 0

function withTimeout(requestFactory, ms = 8000, parentSignal = null) {
  const controller = new AbortController()
  const abort = () => controller.abort()

  if (parentSignal?.aborted) {
    controller.abort()
  } else {
    parentSignal?.addEventListener("abort", abort, { once: true })
  }

  const timer = window.setTimeout(abort, ms)

  return requestFactory(controller.signal).finally(() => {
    window.clearTimeout(timer)
    parentSignal?.removeEventListener("abort", abort)
  })
}

async function loadDashboard() {
  const generation = ++loadGeneration

  refreshing.value = true
  if (!rawCatalogue.value.length && !latestAccessions.value.length) {
    loading.value = true
  }
  loadError.value = ""

  requestErrors.value = {
    summary: false,
    catalogue: false,
    latest: false,
    pendingWorks: false,
    pendingItems: false,
  }

  // Never present an older operational queue as current after a refresh.
  pendingWorks.value = []
  pendingItems.value = []
  keeperAttention.value = {
    rejected_works: [],
    rejected_items: [],
  }

  dashboardController?.abort()
  const controller = new AbortController()
  dashboardController = controller
  const signal = controller.signal

  try {
    const requests = [
      withTimeout(
        (requestSignal) => axios.get("/dashboard/summary", { signal: requestSignal }),
        8000,
        signal,
      ),
      withTimeout(
        (requestSignal) => axios.get("/catalogue/", {
          params: { limit: 100 },
          signal: requestSignal,
        }),
        8000,
        signal,
      ),
      withTimeout(
        (requestSignal) => axios.get("/catalogue/", {
          params: { limit: 5, order: "desc" },
          signal: requestSignal,
        }),
        8000,
        signal,
      ),
    ]

if (can("operations.view")) {
  requests.push(
    withTimeout(
      (requestSignal) => axios.get("/catalogue/pending-works", { signal: requestSignal }),
      8000,
      signal,
    ),
    withTimeout(
      (requestSignal) => axios.get("/catalogue/pending-items", { signal: requestSignal }),
      8000,
      signal,
    ),
  )
}

requests.push(
  withTimeout(
    (requestSignal) =>
      axios.get("/dashboard/keeper-attention", {
        signal: requestSignal,
      }),
    8000,
    signal,
  ),
)

const results = await Promise.allSettled(requests)

    // A newer refresh always wins.
    if (generation !== loadGeneration || signal.aborted) return

    const summaryRes = results[0]
    const catalogueRes = results[1]
    const latestRes = results[2]

    let resultIndex = 3
    let pendingWorksRes = null
    let pendingItemsRes = null

    if (can("operations.view")) {
      pendingWorksRes = results[resultIndex]
      pendingItemsRes = results[resultIndex + 1]
      resultIndex += 2
    }

    const keeperAttentionRes = results[resultIndex]

    requestErrors.value.summary = summaryRes.status === "rejected"
    requestErrors.value.catalogue = catalogueRes.status === "rejected"
    requestErrors.value.latest = latestRes.status === "rejected"

    if (summaryRes.status === "fulfilled") {
      const data = summaryRes.value?.data
      if (data && typeof data === "object" && !Array.isArray(data)) {
        summaryStats.value = {
          ...summaryStats.value,
          ...data,
        }
      }
    }

    if (catalogueRes.status === "fulfilled") {
      const data = catalogueRes.value?.data
      rawCatalogue.value = Array.isArray(data?.data)
        ? data.data
        : Array.isArray(data)
          ? data
          : []

      const reportedTotal = Number(data?.total)
      catalogueTotal.value = Number.isFinite(reportedTotal) && reportedTotal >= 0
        ? reportedTotal
        : Array.isArray(data)
          ? data.length
          : null
    }

    if (latestRes.status === "fulfilled") {
      const data = latestRes.value?.data
      latestAccessions.value = Array.isArray(data?.data)
        ? data.data.slice(0, 5)
        : Array.isArray(data)
          ? data.slice(0, 5)
          : []
    }

    if (can("operations.view")) {
      requestErrors.value.pendingWorks = pendingWorksRes?.status === "rejected"
      requestErrors.value.pendingItems = pendingItemsRes?.status === "rejected"

      if (pendingWorksRes?.status === "fulfilled") {
        const data = pendingWorksRes.value?.data
        pendingWorks.value = Array.isArray(data)
          ? data
          : Array.isArray(data?.data)
            ? data.data
            : []
      }

      if (pendingItemsRes?.status === "fulfilled") {
        const data = pendingItemsRes.value?.data
        pendingItems.value = Array.isArray(data)
          ? data
          : Array.isArray(data?.data)
            ? data.data
            : []
      }
    }

    // Keeper attention has its own backend role check, so process it
    // independently of the operations.view permission.
    if (keeperAttentionRes?.status === "fulfilled") {
      const data = keeperAttentionRes.value?.data

      keeperAttention.value = {
        rejected_works: Array.isArray(data?.rejected_works)
          ? data.rejected_works
          : [],
        rejected_items: Array.isArray(data?.rejected_items)
          ? data.rejected_items
          : [],
      }
    }

    const coreFailed =
      summaryRes.status === "rejected" &&
      catalogueRes.status === "rejected" &&
      latestRes.status === "rejected"

    if (coreFailed) {
      loadError.value = "Live archive data is unavailable. Showing the dashboard shell."
    } else if (
      summaryRes.status === "rejected" ||
      catalogueRes.status === "rejected" ||
      latestRes.status === "rejected"
    ) {
      loadError.value = "Some archive data could not be loaded. Showing the available information."
    }
  } catch (error) {
    if (
      generation === loadGeneration &&
      error?.code !== "ERR_CANCELED" &&
      error?.name !== "CanceledError"
    ) {
      console.error("Dashboard load failed:", error)
      loadError.value = "Live archive data is unavailable. Showing the dashboard shell."
    }
  } finally {
    if (generation === loadGeneration) {
      refreshing.value = false
      loading.value = false
    }
  }
}

function daysWaiting(createdAt) {
  if (!createdAt) return 0

  const created = new Date(createdAt)
  if (Number.isNaN(created.getTime())) return 0

  return Math.max(0, Math.floor((Date.now() - created.getTime()) / 86400000))
}

function oldestPendingDays(records) {
  return records.reduce((oldest, record) => {
    return Math.max(oldest, daysWaiting(record?.created_at))
  }, 0)
}

function pendingDescription(records, label) {
  const count = records.length
  const oldestDays = oldestPendingDays(records)
  const noun = `${label}${count === 1 ? "" : "s"}`

  if (oldestDays > 0) {
    return `${count === 1 ? "One" : count} ${noun} ${count === 1 ? "is" : "are"} waiting for verification; oldest has been waiting ${oldestDays} ${oldestDays === 1 ? "day" : "days"}.`
  }

  return `${count === 1 ? "One" : count} ${noun} ${count === 1 ? "is" : "are"} waiting for verification.`
}

/*
 * Attention is intentionally limited to information that represents
 * an unresolved archive task or preservation exception. History belongs
 * in Audit Trail; incident, user and docket details stay in their
 * dedicated sections.
 */
const attentionSignals = computed(() => {
  const signals = []

  if (can("operations.view")) {
    if (pendingWorks.value.length) {
      signals.push({
        id: "pending-works",
        title: "Pending Archival Work",
        description: pendingDescription(pendingWorks.value, "archival work record"),
        count: pendingWorks.value.length,
        tone: "violet",
        icon: CheckCircle2,
        to:
          pendingWorks.value.length === 1
            ? `/review-work/${pendingWorks.value[0].work_id}`
            : "/docket",
      })
    }

    if (pendingItems.value.length) {
      signals.push({
        id: "pending-items",
        title: "Pending Physical Item",
        description: pendingDescription(pendingItems.value, "physical item record"),
        count: pendingItems.value.length,
        tone: "orange",
        icon: BookOpen,
        to:
          pendingItems.value.length === 1
            ? `/review-item/${pendingItems.value[0].serial_no}`
            : "/docket",
      })
    }

    const missing = Number(summaryStats.value.missing_items || 0)
    const damaged = Number(summaryStats.value.damaged_items || 0)

    if (missing > 0) {
      signals.push({
        id: "missing-items",
        title: "Items recorded as missing",
        description: "Review the affected preservation records.",
        count: missing,
        tone: "danger",
        icon: AlertTriangle,
        to: "/catalogue",
      })
    }

    if (damaged > 0) {
      signals.push({
        id: "damaged-items",
        title: "Items recorded as damaged",
        description: "Review condition and preservation records.",
        count: damaged,
        tone: "warning",
        icon: ShieldAlert,
        to: "/catalogue",
      })
    }
  }

  // Keeper attention is independent of operations.view because the
  // backend endpoint already restricts this data to the current Keeper.
  const rejectedWorks = keeperAttention.value.rejected_works
  const rejectedItems = keeperAttention.value.rejected_items

  if (rejectedWorks.length > 0) {
    signals.push({
      id: "keeper-rejected-works",
      title: "Archival Work",
      subtitle: "Returned for Re-evaluation",
      description:
        rejectedWorks.length === 1
          ? "1 archival work submitted by you was returned by the Chief and requires your action."
          : `${rejectedWorks.length} archival works submitted by you were returned by the Chief and require your action.`,
      count: rejectedWorks.length,
      tone: "danger",
      icon: CheckCircle2,
      to:
        rejectedWorks.length === 1
          ? `/review-work/${rejectedWorks[0].work_id}`
          : { path: "/docket", query: { filter: "ATTENTION" } },
    })
  }

  if (rejectedItems.length > 0) {
    signals.push({
      id: "keeper-rejected-items",
      title: "Physical Items",
      subtitle: "Returned for Re-evaluation",
      description:
        rejectedItems.length === 1
          ? "1 physical item submitted by you was returned by the Chief and requires your action."
          : `${rejectedItems.length} physical items submitted by you were returned by the Chief and require your action.`,
      count: rejectedItems.length,
      tone: "danger",
      icon: BookOpen,
      to:
        rejectedItems.length === 1
          ? `/review-item/${rejectedItems[0].serial_no}`
          : { path: "/docket", query: { filter: "ATTENTION" } },
    })
  }

  return signals
})

function numberOrZero(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

const totalItems = computed(() => {
  if (summaryStats.value.total_items != null) {
    const total = Number(summaryStats.value.total_items)
    if (Number.isFinite(total) && total >= 0) return total
  }

  const catalogueCount = Number(catalogueTotal.value)
  return Number.isFinite(catalogueCount) && catalogueCount >= 0
    ? catalogueCount
    : rawCatalogue.value.length
})

function aggregateRows(source, labelKey = "label", countKey = "count") {
  if (!Array.isArray(source)) return []

  return source
    .map((row) => {
      if (row == null) return null

      if (Array.isArray(row)) {
        return [String(row[0] ?? "").trim(), Number(row[1] ?? 0)]
      }

      const label = row[labelKey] ?? row.category ?? row.genre ?? row.language
      const count = row[countKey] ?? row.total ?? 0
      return [String(label ?? "").trim(), Number(count ?? 0)]
    })
    .filter(([label, count]) => label && Number.isFinite(count) && count >= 0)
    .sort((a, b) => b[1] - a[1])
}

function rowsFromEntries(entries, limit) {
  const visible = entries.slice(0, limit)
  const max = visible[0]?.[1] || 1

  return {
    rows: visible.map(([label, count]) => ({
      label,
      count,
      percent: Math.max(3, Math.min(100, (count / max) * 100)),
    })),
    hasMore: entries.length > limit,
  }
}

const categoryEntries = computed(() => {
  // Prefer complete server-side aggregates.
  const serverRows = aggregateRows(summaryStats.value.categories)
  if (serverRows.length) return serverRows

  // Only aggregate the catalogue locally when it is demonstrably complete.
  const total = Number(summaryStats.value.total_items)
  if (
    !requestErrors.value.summary &&
    Number.isFinite(total) &&
    total > 0 &&
    total <= rawCatalogue.value.length
  ) {
    const stats = {}

    rawCatalogue.value.forEach((record) => {
      const category = String(record?.category || "").trim() || "Uncategorised"
      stats[category] = (stats[category] || 0) + 1
    })

    return Object.entries(stats).sort((a, b) => b[1] - a[1])
  }

  // Do not display misleading partial statistics.
  return []
})

const categoryRows = computed(() => rowsFromEntries(categoryEntries.value, categoryEntries.value.length))

const genreEntries = computed(() => {
  const serverRows = aggregateRows(summaryStats.value.genres)
  if (serverRows.length) return serverRows

  const total = Number(summaryStats.value.total_items)
  if (
    !requestErrors.value.summary &&
    Number.isFinite(total) &&
    total > 0 &&
    total <= rawCatalogue.value.length
  ) {
    const stats = {}

    rawCatalogue.value.forEach((record) => {
      const genreValue = String(record?.genre || "").trim() || "Uncategorised"

      genreValue
        .split(/[/,]+/)
        .map((value) => value.trim())
        .filter(Boolean)
        .forEach((genre) => {
          stats[genre] = (stats[genre] || 0) + 1
        })
    })

    return Object.entries(stats).sort((a, b) => b[1] - a[1])
  }

  return []
})

const genreRows = computed(() => rowsFromEntries(genreEntries.value, 5))

const languageEntries = computed(() => {
  const serverRows = aggregateRows(summaryStats.value.languages, "language")
  if (!serverRows.length) return []

  const stats = {}

  serverRows.forEach(([label, count]) => {
    const language =
      !label || label.toLowerCase() === "unknown"
        ? "Uncategorised"
        : label

    stats[language] = (stats[language] || 0) + count
  })

  return Object.entries(stats).sort((a, b) => b[1] - a[1])
})
const languageRows = computed(() => rowsFromEntries(languageEntries.value, 5))

const distributionSections = computed(() => {
  const sections = []

  if (categoryRows.value.rows.length) {
    sections.push({
      key: "categories",
      kicker: "COMPOSITION",
      title: "Categories",
      totalLabel: `${totalCategories.value} categories`,
      ...categoryRows.value,
    })
  }

  if (genreRows.value.rows.length) {
    sections.push({
      key: "genres",
      kicker: "COMPOSITION",
      title: "Genres",
      totalLabel: `${totalGenres.value} genres`,
      ...genreRows.value,
    })
  }

  if (languageRows.value.rows.length) {
    sections.push({
      key: "languages",
      kicker: "COMPOSITION",
      title: "Languages",
      totalLabel: `${totalLanguages.value} languages`,
      ...languageRows.value,
    })
  }

  return sections
})

const totalCategories = computed(() => categoryEntries.value.length)

const totalGenres = computed(() => genreEntries.value.length)

const totalLanguages = computed(() => languageEntries.value.length)


onMounted(() => {
  loadDashboard()
})

onUnmounted(() => {
  loadGeneration += 1
  dashboardController?.abort()
  dashboardController = null
})
</script>

<style scoped>
.dashboard-brand {
  margin-bottom: 7px;
  color: #8B5CF6;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.8px;
  text-transform: uppercase;
}

/* =========================================================
   NEW DASHBOARD SYSTEM
   - No fixed KPI strip
   - No recent activity/audit duplication
   - No empty reserved panels
   - Attention-first
   - Fluid reflow
========================================================= */

.archive-dashboard {
  --dash-bg: var(--content-bg, #f1f5f2);
  --dash-surface: var(--surface, #ffffff);
  --dash-surface-2: var(--hover-bg, #e9f4ed);
  --dash-text: var(--text-primary, #14221b);
  --dash-muted: var(--text-muted, #65746c);
  --dash-border: var(--border-main, #d6e2da);

  --dash-green: #13a36b;
  --dash-green-dark: #08794d;
  --dash-coral: #f05d4e;
  --dash-violet: #7658e8;
  --dash-violet-soft: #e9e3ff;

  --dash-orange: #ed9a28;
  min-height: 100vh;
  padding: 30px clamp(20px, 3vw, 48px) 48px;
  background:
    radial-gradient(circle at 92% 0%, rgba(19, 163, 107, 0.11), transparent 30%),
    radial-gradient(circle at 4% 38%, rgba(118, 88, 232, 0.07), transparent 24%),
    var(--dash-bg);
  color: var(--dash-text);
}

/* Header */
.dashboard-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 30px;
}

.section-kicker {
  margin-bottom: 7px;
  color: var(--dash-green-dark);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.8px;
  text-transform: uppercase;
}

.dashboard-header h1 {
  margin: 0;
  font-size: clamp(28px, 3vw, 42px);
  line-height: 1;
  letter-spacing: -1.5px;
  font-weight: 800;
}

.header-subtitle {
  max-width: 650px;
  margin: 10px 0 0;
  color: var(--dash-muted);
  font-size: 13px;
  line-height: 1.6;
}

.refresh-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid var(--dash-border);
  border-radius: 12px;
  background: var(--dash-surface);
  color: var(--dash-text);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}

.refresh-control:hover {
  border-color: var(--dash-green);
  box-shadow: 0 8px 24px rgba(20, 34, 27, .08);
  transform: translateY(-1px);
}

.refresh-control:focus-visible,
.text-link:focus-visible,
.attention-item:focus-visible,
.dashboard-error button:focus-visible {
  outline: 3px solid var(--dash-violet);
  outline-offset: 3px;
}

.refresh-control.spinning svg {
  animation: spin .8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Attention */
.attention-section {
  margin-bottom: 30px;
  padding: 22px;
  border: 1px solid #f6c7c1;
  border-radius: 20px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--dash-coral) 10%, var(--dash-surface)), var(--dash-surface) 65%);
  box-shadow: 0 12px 36px rgba(240, 93, 78, .07);
}

.attention-kicker {
  color: var(--dash-coral);
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.section-heading h2 {
  margin: 0;
  font-size: 22px;
  line-height: 1.15;
  letter-spacing: -.5px;
}

.attention-summary {
  color: var(--dash-muted);
  font-size: 11px;
}

.attention-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.attention-item {
  display: grid;
  grid-template-columns: 40px 1fr auto 18px;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 9px 12px;
  border: 1px solid var(--dash-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--dash-surface) 92%, var(--dash-bg));
  color: inherit;
  text-decoration: none;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}

.attention-item:hover {
  transform: translateY(-2px);
  border-color: #efaaa1;
  box-shadow: 0 10px 24px rgba(20, 34, 27, .08);
}

.attention-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
}

.tone-danger .attention-icon {
  color: var(--dash-coral);
  background: color-mix(in srgb, var(--dash-coral) 14%, var(--dash-surface));
}

.tone-warning .attention-icon {
  color: #bd7100;
  background: color-mix(in srgb, var(--dash-orange) 14%, var(--dash-surface));
}
 
.tone-violet .attention-icon {
  color: var(--dash-violet);
  background: color-mix(in srgb, var(--dash-violet) 14%, var(--dash-surface));
}

.tone-orange .attention-icon {
  color: var(--dash-orange);
  background: color-mix(in srgb, var(--dash-orange) 14%, var(--dash-surface));
}

.attention-copy {
  min-width: 0;
}

.attention-copy strong,
.attention-copy span {
  display: block;
}

.attention-copy strong {
  margin-bottom: 3px;
  font-size: 12px;
}

.attention-copy em {
  display: block;
  margin-bottom: 5px;
  color: var(--dash-coral);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
  letter-spacing: .4px;
  text-transform: uppercase;
}

.attention-copy span {
  color: var(--dash-text);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.5;
}

.attention-count {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -1px;
}

.attention-arrow {
  color: var(--dash-muted);
}

/* Collection */
.collection-section {
  margin-bottom: 30px;
}

.collection-heading {
  margin-bottom: 9px;
}

.text-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--dash-green-dark);
  font-size: 11px;
  font-weight: 800;
  text-decoration: none;
}

.text-link:hover {
  text-decoration: underline;
}

.collection-overview {
  display: flex;
  align-items: center;
  gap: 0;
  overflow: hidden;
  min-height: 66px;
  border: 1px solid var(--dash-border);
  border-radius: 14px;
  background: var(--dash-surface);
  box-shadow: 0 6px 20px rgba(20, 34, 27, .04);
}

.collection-primary {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 150px;
  padding: 12px 18px;
}

.collection-primary strong {
  font-size: 24px;
  line-height: 1;
  letter-spacing: -1px;
}

.collection-primary span {
  color: var(--dash-muted);
  font-size: 11px;
  font-weight: 700;
}

.collection-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(90px, 1fr));
  flex: 1;
  border-left: 1px solid var(--dash-border);
  background: color-mix(in srgb, var(--dash-surface-2) 55%, var(--dash-surface));
}

.collection-fact {
  padding: 8px 14px;
  border-right: 1px solid var(--dash-border);
}

.collection-fact:last-child {
  border-right: 0;
}

.collection-fact span {
  display: block;
  margin-bottom: 2px;
  color: var(--dash-muted);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .8px;
  text-transform: uppercase;
}

.collection-fact strong {
  font-size: 15px;
  letter-spacing: -.4px;
}

/* Distributions */
.distribution-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 30px;
}

.distribution {
  min-width: 0;
  padding: 20px;
  border: 1px solid var(--dash-border);
  border-radius: 18px;
  background: var(--dash-surface);
  box-shadow: 0 8px 28px rgba(20, 34, 27, .05);
}

.distribution-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.distribution-heading .section-kicker {
  margin-bottom: 5px;
}

.distribution-heading h3 {
  margin: 0;
  font-size: 17px;
  letter-spacing: -.2px;
}

.distribution-total {
  white-space: nowrap;
  color: var(--dash-muted);
  font-size: 10px;
  font-weight: 700;
}

.distribution-row {
  margin-top: 13px;
}

.distribution-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 11px;
}

.distribution-label span {
  min-width: 0;
  overflow: hidden;
  color: var(--dash-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.distribution-label strong {
  flex: 0 0 auto;
  font-size: 11px;
}

.distribution-track {
  height: 7px;
  overflow: hidden;
  border-radius: 99px;
  background: color-mix(in srgb, var(--dash-text) 9%, var(--dash-surface));
}

.distribution-fill {
  height: 100%;
  min-width: 3px;
  border-radius: inherit;
}

.fill-categories { background: var(--dash-green); }
.fill-genres { background: var(--dash-violet); }
.fill-languages { background: var(--dash-coral); }

.distribution-footer {
  margin-top: 15px;
  color: var(--dash-muted);
  font-size: 10px;
}

/* Latest accessions */
.recent-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid var(--dash-border);
  border-radius: 18px;
  background: var(--dash-surface);
  box-shadow: 0 8px 28px rgba(20, 34, 27, .05);
}

.recent-heading {
  margin-bottom: 12px;
}

.recent-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.recent-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--dash-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--dash-surface-2) 88%, var(--dash-surface));
}

.accession-badge {
  max-width: 86px;
  overflow: hidden;
  padding: 7px 8px;
  border-radius: 8px;
  background: var(--dash-violet-soft);
  color: #5940c8;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .4px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-copy {
  min-width: 0;
}

.recent-copy strong,
.recent-copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-copy strong {
  color: var(--dash-text);
  font-size: 11px;
}

.recent-copy span {
  margin-top: 3px;
  color: var(--dash-muted);
  font-size: 10px;
}

.recent-icon {
  color: var(--dash-green);
  opacity: .85;
}

/* The dashboard uses the application's existing theme variables for its
   surfaces, text, borders, and background, so the same component follows
   both light and dark themes without duplicating theme architecture. */

/* Header actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

/* Non-blocking API error */
.dashboard-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  padding: 12px 14px;
  border: 1px solid rgba(239, 68, 68, .25);
  border-radius: 12px;
  background: color-mix(in srgb, var(--dash-coral) 10%, var(--dash-surface));
  color: var(--dash-text);
  font-size: 12px;
}

.dashboard-error button {
  border: 0;
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  background: var(--dash-violet);
  color: white;
  font-size: 12px;
}

/* Loading */
.dashboard-loading {
  min-height: 60vh;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 14px;
  color: var(--dash-muted);
  font-size: 12px;
}

.loading-orbit {
  width: 32px;
  height: 32px;
  border: 3px solid #dce8e1;
  border-top-color: var(--dash-green);
  border-right-color: var(--dash-violet);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

/* Responsive */
@media (max-width: 850px) {
  .dashboard-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .collection-overview {
    display: block;
  }

  .collection-primary {
    border-bottom: 1px solid var(--dash-border);
  }

  .collection-facts {
    border-top: 1px solid var(--dash-border);
    border-left: 0;
  }
}

@media (max-width: 600px) {
  .archive-dashboard {
    padding: 22px 16px 36px;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }


  .collection-overview {
    display: block;
  }

  .collection-primary {
    padding: 12px 14px;
    border-bottom: 1px solid var(--dash-border);
  }

  .collection-facts {
    padding: 0;
  }

  .attention-item {
    grid-template-columns: 36px 1fr auto;
  }

  .attention-arrow {
    display: none;
  }

  .recent-list,
  .distribution-section {
    grid-template-columns: 1fr;
  }
}
</style>
