
import { createRouter, createWebHashHistory } from "vue-router"
import { useAuthStore } from "@/stores/auth"

import Login from "@/views/Login.vue"
import Dashboard from "@/views/Dashboard.vue"
import CatalogueView from "@/views/CatalogueView.vue"
import Search from "@/views/Search.vue"
import AuditTrailView from "@/views/AuditTrailView.vue"
import DetailsView from "@/views/DetailsView.vue"
import CreateWorkView from "@/views/CreateWorkView.vue"
import CreateItemView from "@/views/CreateItemView.vue"
import Operations from "@/views/Operations.vue"
import EditItemView from "@/views/EditItemView.vue"
import AuthorsView from "@/views/AuthorsView.vue"
import AuthoritiesView from "@/views/AuthoritiesView.vue"
import SubjectsView from "@/views/SubjectsView.vue"
import IncidentsView from "@/views/IncidentsView.vue"
import ReportsView from "@/views/ReportsView.vue"
import SettingsPage from "@/views/SettingsPage.vue"
import SystemSettings from "@/views/admin/SystemSettings.vue"
import UserManagementView from "@/views/admin/UserManagementView.vue"
import ApprovalCenterView from "@/views/admin/ApprovalCenterView.vue"
import DocketView from "@/views/DocketView.vue"
import ItemReviewView from "@/views/ItemReviewView.vue"
import WorkReviewView from "@/views/WorkReviewView.vue"
import CreateWorkChiefDirect from "@/views/CreateWorkChiefDirect.vue"

const routes = [
  {
    path: "/login",
    name: "Login",
    component: Login,
    meta: { public: true },
  },
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: Dashboard,
    meta: { requiresAuth: true },
  },
  {
    path: "/catalogue",
    name: "Catalogue",
    component: CatalogueView,
    meta: { requiresAuth: true },
  },
  {
    path: "/search",
    name: "Search",
    component: Search,
    meta: { requiresAuth: true },
  },
  {
    path: "/audit-trail",
    name: "AuditTrail",
    component: AuditTrailView,
    meta: { requiresAuth: true },
  },
  {
    path: "/details/:id",
    name: "Details",
    component: DetailsView,
    meta: { requiresAuth: true },
  },

  // Keeper registration
  {
    path: "/create-work",
    name: "CreateWork",
    component: CreateWorkView,
    meta: {
      requiresAuth: true,
      permission: "catalogue.create",
      roles: ["The Keeper"],
    },
  },
  {
    path: "/create-item",
    name: "CreateItem",
    component: CreateItemView,
    meta: {
      requiresAuth: true,
      permission: "catalogue.create",
      roles: ["The Keeper"],
    },
  },

  // Chief registration
  {
    path: "/chief/register-work",
    name: "ChiefRegisterWork",
    component: CreateWorkChiefDirect,
    meta: {
      requiresAuth: true,
      roles: ["The Chief"],
    },
  },
  {
    path: "/chief/register-item",
    name: "ChiefRegisterItem",
    component: CreateItemView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief"],
    },
  },

  {
    path: "/operations",
    name: "Operations",
    component: Operations,
    meta: { requiresAuth: true },
  },
  {
    path: "/edit-item/:id",
    name: "EditItem",
    component: EditItemView,
    meta: { requiresAuth: true },
  },

  // Classification pages: accessible to Chief and Keeper
  {
    path: "/classification/authors",
    name: "classification-authors",
    component: AuthorsView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"],
    },
  },
  {
    path: "/classification/authorities",
    name: "classification-authorities",
    component: AuthoritiesView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"],
    },
  },
  {
    path: "/classification/subjects",
    name: "classification-subjects",
    component: SubjectsView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"],
    },
  },

  {
    path: "/incidents",
    name: "Incidents",
    component: IncidentsView,
    meta: { requiresAuth: true },
  },
  {
    path: "/reports",
    name: "Reports",
    component: ReportsView,
    meta: { requiresAuth: true },
  },
  {
    path: "/settings",
    name: "Settings",
    component: SettingsPage,
    meta: { requiresAuth: true },
  },
  {
    path: "/admin/system-settings",
    name: "SystemSettings",
    component: SystemSettings,
    meta: { requiresAuth: true },
  },
  {
    path: "/admin/users",
    name: "UserManagement",
    component: UserManagementView,
    meta: { requiresAuth: true },
  },
  {
    path: "/admin/approval-center",
    name: "ApprovalCenter",
    component: ApprovalCenterView,
    meta: { requiresAuth: true },
  },

  // Shared workflow
  {
    path: "/docket",
    name: "Docket",
    component: DocketView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"],
    },
  },
  {
    path: "/review-work/:id",
    name: "WorkReview",
    component: WorkReviewView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"],
    },
  },
  {
    path: "/review-item/:id",
    name: "ItemReview",
    component: ItemReviewView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"],
    },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    return true
  }

  const authenticated =
    auth.isAuthenticated ?? Boolean(auth.token)

  if (to.meta.requiresAuth && !authenticated) {
    return { name: "Login" }
  }

  const role =
    auth.user?.role ??
    auth.currentUser?.role ??
    auth.role ??
    auth.userRole

  if (to.meta.roles && !to.meta.roles.includes(role)) {
    return { name: "Dashboard" }
  }

  if (to.meta.permission) {
    const allowed =
      typeof auth.hasPermission === "function"
        ? auth.hasPermission(to.meta.permission)
        : Array.isArray(auth.permissions) &&
          auth.permissions.includes(to.meta.permission)

    if (!allowed) {
      return { name: "Dashboard" }
    }
  }

  return true
})

export default router
