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
import AboutView from "@/views/AboutView.vue"

import SystemSettings from "@/views/admin/SystemSettings.vue"
import UserManagementView from "@/views/admin/UserManagementView.vue"
import ApprovalCenterView from "@/views/admin/ApprovalCenterView.vue"
import DocketView from "@/views/DocketView.vue"

const routes = [

  {
    path: "/login",
    name: "login",
    component: Login
  },

  {
    path: "/",
    redirect: "/login"
  },

  {
    path: "/dashboard",
    name: "dashboard",
    component: Dashboard,
    meta: {
      requiresAuth: true
    }
  },

  {
    path: "/catalogue",
    name: "catalogue",
    component: CatalogueView,
    meta: {
      requiresAuth: true
    }
  },

  {
    path: "/search",
    name: "search",
    component: Search,
    meta: {
      requiresAuth: true
    }
  },

  {
    path: "/audit-trail",
    name: "audit-trail",
    component: AuditTrailView,
    meta: {
      requiresAuth: true,
      permission: "audit.view"
    }
  },

  {
    path: "/details/:id",
    name: "details",
    component: DetailsView,
    meta: {
      requiresAuth: true,
      permission: "catalogue.view"
    }
  },

  {
    path: "/create-work",
    name: "create-work",
    component: CreateWorkView,
    meta: {
      requiresAuth: true,
      permission: "catalogue.create"
    }
  },

  {
    path: "/create-item",
    name: "create-item",
    component: CreateItemView,
    meta: {
      requiresAuth: true,
      permission: "catalogue.create"
    }
  },

  {
    path: "/operations/:accession",
    name: "operations",
    component: Operations,
    meta: {
      requiresAuth: true,
      permission: "operations.execute"
    }
  },

  {
    path: "/edit-item/:id",
    name: "edit-item",
    component: EditItemView,
    meta: {
      requiresAuth: true,
      permission: "catalogue.edit"
    }
  },

  {
    path: "/admin/settings",
    name: "admin-settings",
    component: SystemSettings,
    meta: {
      requiresAuth: true,
      roles: ["The Chief"]
    }
  },

  {
    path: "/admin/users",
    name: "user-management",
    component: UserManagementView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"]
    }
  },

  {
    path: "/admin/approvals",
    name: "approval-center",
    component: ApprovalCenterView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief"]
    }
  },

  {
    path: "/docket",
    name: "docket",
    component: DocketView,
    meta: {
      requiresAuth: true,
      roles: ["The Chief", "The Keeper"]
    }
  },

  {
    path: "/classification/authors",
    name: "Authors",
    component: AuthorsView,
    meta: {
      requiresAuth: true,
      permission: "classification.view"
    }
  },

  {
    path: "/classification/authorities",
    name: "Authorities",
    component: AuthoritiesView,
    meta: {
      requiresAuth: true,
      permission: "classification.view"
    }
  },

  {
    path: "/classification/subjects",
    name: "Subjects",
    component: SubjectsView,
    meta: {
      requiresAuth: true,
      permission: "classification.view"
    }
  },

  {
    path: "/incidents",
    name: "incidents",
    component: IncidentsView,
    meta: {
      requiresAuth: true,
      permission: "incidents.view"
    }
  },

  {
    path: "/reports",
    name: "reports",
    component: ReportsView,
    meta: {
      requiresAuth: true,
      permission: "reports.view"
    }
  },

  {
    path: "/about",
    name: "about",
    component: AboutView,
    meta: {
      requiresAuth: true,
      permission: "dashboard.view"
    }
  }

]


const router = createRouter({
  history: createWebHashHistory(),
  routes
})


router.beforeEach((to, from, next) => {

  const auth = useAuthStore()

  if (
    to.path === "/login" &&
    auth.isAuthenticated
  ) {
    next("/dashboard")
    return
  }

  if (
    to.meta.requiresAuth &&
    !auth.isAuthenticated
  ) {
    next("/login")
    return
  }

  if (
    to.meta.roles &&
    !to.meta.roles.includes(auth.userRole)
  ) {
    next("/dashboard")
    return
  }

  if (
    to.meta.permission &&
    !auth.hasPermission(
      to.meta.permission
    )
  ) {
    next("/dashboard")
    return
  }

  next()
})


export default router