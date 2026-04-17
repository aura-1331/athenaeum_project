import { createRouter, createWebHashHistory } from "vue-router"

import Dashboard from "../views/Dashboard.vue"
import Search from "../views/Search.vue"
import Audit from "../views/Audit.vue"
import CatalogueView from "../views/CatalogueView.vue"
import CreateWorkView from "../views/CreateWorkView.vue"
import CreateItemView from "../views/CreateItemView.vue"
import Operations from "../views/Operations.vue"
import EditItemView from "../views/EditItemView.vue"
import DetailsView from "../views/DetailsView.vue"
import SystemSettings from "../views/admin/SystemSettings.vue"
import Login from "../views/Login.vue"

const routes = [
  { path: "/login", name: "login", component: Login },

  // ✅ CHANGE START PAGE HERE
  { path: "/", redirect: "/catalogue" },

  { path: "/dashboard", name: "dashboard", component: Dashboard },
  { path: "/catalogue", name: "catalogue", component: CatalogueView },
  { path: "/search", name: "search", component: Search },
  { path: "/status-audit", name: "audit", component: Audit },
  { path: "/details/:id", name: "details", component: DetailsView },

  { path: "/create-work", name: "create-work", component: CreateWorkView },
  { path: "/create-item", name: "create-item", component: CreateItemView },
  { path: "/operations/:accession", name: "operations", component: Operations },
  { path: "/edit-item/:id", name: "edit-item", component: EditItemView },

  { path: "/admin/settings", name: "admin-settings", component: SystemSettings }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// ✅ AUTH COMPLETELY DISABLED
router.beforeEach((to, from, next) => {
  next()
})

export default router