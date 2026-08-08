import { createRouter, createWebHashHistory } from "vue-router"
import { useAuthStore } from "@/stores/auth" // <-- 1. IMPORT PINIA STORE

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
import AboutView from "../views/AboutView.vue" 
import IncidentsView from "../views/IncidentsView.vue"
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
  { path: "/classification/subjects", name: "Subjects", component: SubjectsView, meta: { requiresAuth: true } },
  {
  path: "/incidents",  name: "incidents",  component: IncidentsView,  meta: { requiresAuth: true }},
  
  { path: "/about", name: "about", component: AboutView, meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 2. UPDATED BOUNCER LOGIC
router.beforeEach((to, from, next) => {
  // We must call useAuthStore INSIDE the beforeEach function
  const auth = useAuthStore()

  // If they try to go to the login page but are already logged in
  if (to.path === '/login' && auth.isAuthenticated) {
    next('/dashboard')
    return
  }

  // If the page requires login and they are NOT logged in
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
    return
  }

  // Otherwise, let them through!
  next()
})

export default router