import { createRouter, createWebHashHistory } from "vue-router"

import Dashboard from "../views/Dashboard.vue"
import Search from "../views/Search.vue"
import AuditTrailView from '../views/AuditTrailView.vue'
import CatalogueView from "../views/CatalogueView.vue"
import CreateWorkView from "../views/CreateWorkView.vue"
import CreateItemView from "../views/CreateItemView.vue"
import Operations from "../views/Operations.vue"
import EditItemView from "../views/EditItemView.vue"
import DetailsView from "../views/DetailsView.vue"
import SystemSettings from "../views/admin/SystemSettings.vue"
import Login from "../views/Login.vue"
import AuthorsView from "../views/AuthorsView.vue"
import SubjectsView from "../views/SubjectsView.vue"

const routes = [
  { path: "/login", name: "login", component: Login },
  
  { path: "/", redirect: "/login" },

  { path: "/dashboard", name: "dashboard", component: Dashboard, meta: { requiresAuth: true } },
  { path: "/catalogue", name: "catalogue", component: CatalogueView, meta: { requiresAuth: true } },
  { path: "/search", name: "search", component: Search, meta: { requiresAuth: true } },
  { path: '/audit-trail', name: 'audit-trail', component: AuditTrailView, meta: { requiresAuth: true } },
  { path: "/details/:id", name: "details", component: DetailsView, meta: { requiresAuth: true } },

  { path: "/create-work", name: "create-work", component: CreateWorkView, meta: { requiresAuth: true } },
  { path: "/create-item", name: "create-item", component: CreateItemView, meta: { requiresAuth: true } },
  { path: "/operations/:accession", name: "operations", component: Operations, meta: { requiresAuth: true } },
  { path: "/edit-item/:id", name: "edit-item", component: EditItemView, meta: { requiresAuth: true } },

  { path: "/admin/settings", name: "admin-settings", component: SystemSettings, meta: { requiresAuth: true } },
  { path: "/classification/authors", name: "Authors", component: AuthorsView, meta: { requiresAuth: true } },
  { path: "/classification/subjects", name: "Subjects", component: SubjectsView, meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token")

  if (to.path === '/login' && token) {
    next('/dashboard')
    return
  }

  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  next()
})

export default router