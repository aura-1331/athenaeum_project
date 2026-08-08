<style scoped>

/* ===========================================================
   ATHENAEUM ORBIS
   ARCHIVE INTELLIGENCE CONSOLE
=========================================================== */

.dashboard{

    min-height:100vh;

    background:var(--content-bg);

    padding:28px;

    color:var(--text-primary);

}

/* ===========================================================
   TOPBAR
=========================================================== */

.topbar{

    display:flex;

    justify-content:space-between;

    align-items:center;

    margin-bottom:28px;

}

.brand{

    display:flex;

    align-items:center;

    gap:18px;

}

.brand-mark{

    width:14px;

    height:50px;

    border-radius:30px;

    background:var(--accent);

    box-shadow:0 0 18px var(--hover-bg);

}

.eyebrow{

    font-size:11px;

    text-transform:uppercase;

    letter-spacing:3px;

    color:var(--accent);

}

.brand h1{

    margin-top:6px;

    font-family:"Cormorant Garamond",serif;

    font-size:34px;

    color:var(--text-primary);

}

/* ===========================================================
   REFRESH BUTTON
=========================================================== */

.refresh-btn{

    width:42px;

    height:42px;

    display:flex;

    align-items:center;

    justify-content:center;

    border-radius:10px;

    cursor:pointer;

    background:var(--surface);

    border:1px solid var(--border-main);

    color:var(--accent);

}

.refresh-btn:hover{

    background:var(--hover-bg);

    border-color:var(--accent);

    color:var(--accent);

    transform:rotate(15deg);

}


.refresh-btn.is-loading svg{

    animation:refresh-spin .8s linear infinite;

}

.refresh-btn:disabled{

    cursor:wait;

    opacity:.7;

}

@keyframes refresh-spin{

    from{
        transform:rotate(0deg);
    }

    to{
        transform:rotate(360deg);
    }

}

.refresh-btn{

    transition:
        background .2s ease,
        border-color .2s ease,
        color .2s ease,
        transform .2s ease;

}

/* ===========================================================
   KPI
=========================================================== */

.kpi-grid{

    display:grid;

    grid-template-columns:repeat(6,1fr);

    gap:18px;

    margin-bottom:28px;

}

.kpi{

    background:var(--surface);

    border:1px solid var(--border-main);

    border-radius:14px;

    padding:18px;

    transition:.25s;

}

.kpi:hover{

    transform:translateY(-4px);

    border-color:var(--accent);

}

.kpi-icon{

    width:17px;
    height:17px;

    color:var(--accent);

    margin-bottom:14px;

    opacity:.85;

}

.kpi span{

    display:block;

    color:var(--text-muted);

    text-transform:uppercase;

    font-size:11px;

    letter-spacing:1.2px;

}

.kpi h2{

    margin-top:12px;

    font-size:34px;

    font-family:"Cormorant Garamond",serif;

    color:var(--text-primary);

}

.danger h2{

    color:#ef4444;

}

.warning h2{

    color:#f59e0b;

}

/* ===========================================================
   GRID
=========================================================== */

.grid{

    display:grid;

    grid-template-columns:1.15fr .85fr;

    gap:18px;

}

.panel{

    background:var(--surface);

    border:1px solid var(--border-main);

    border-radius:12px;

    padding:20px;

    box-shadow:var(--shadow);

}

.panel-header{

    display:flex;

    justify-content:space-between;

    align-items:center;

    margin-bottom:16px;

}

.panel-header h3{

    display:flex;

    align-items:center;

    gap:9px;

    font-size:16px;

    font-family:"Cormorant Garamond",serif;

    font-weight:600;

    letter-spacing:.3px;

    color:var(--text-primary);

}

/* ===========================================================
   ACTIVITY
=========================================================== */

.activity{

    display:flex;

    align-items:center;

    gap:14px;

    padding:12px 0;

    border-bottom:1px solid var(--border-main);

    transition:background .2s ease;

}

.activity:last-child{

    border:none;

}
.activity:hover{

    background:var(--hover-bg);

}
.timeline{

    width:10px;

    height:10px;

    border-radius:50%;

    background:var(--accent);

    box-shadow:0 0 10px rgba(184,146,90,.4);

}

.activity-content{

    flex:1;

}

.activity-content strong{

    display:block;

    margin-bottom:4px;

    font-size:13px;

    font-weight:600;

    color:var(--text-primary);

}

.activity-content p{

    color:var(--text-muted);

    font-size:12px;

    line-height:1.4;

}

/* ===========================================================
   BOOKS
=========================================================== */

.book{
    display:flex;
    align-items:center;
    gap:14px;
    padding:12px 0;
    border-bottom:1px solid var(--border-main);
    transition:background .2s ease;
}

.book:last-child{

    border:none;

}
.book:hover{
    background:var(--hover-bg);
}
.book-no{

    width:90px;

    color:var(--accent);

    font-weight:700;

    font-size:11px;

    letter-spacing:.8px;

    font-family:monospace;

}

.book-info{

    flex:1;

}

.book-info strong{

    display:block;

    margin-bottom:4px;

    font-size:13px;

    font-weight:600;

    color:var(--text-primary);

    white-space:nowrap;

    overflow:hidden;

    text-overflow:ellipsis;

}

.book-info span{

    color:var(--text-muted);

    font-size:11px;

}

/* ===========================================================
   BARS
=========================================================== */

.bar-row{

    display:grid;

    grid-template-columns:110px 1fr 35px;

    gap:10px;

    align-items:center;

    margin:12px 0;

}

.bar{

    height:8px;

    background:var(--hover-bg);

    border-radius:20px;

    overflow:hidden;

}

.fill{

    height:100%;

    background:var(--accent);

    border-radius:20px;

}

.genre-footer{

    margin-top:22px;

    color:var(--text-muted);

}

/* ===========================================================
   ACTIONS
=========================================================== */

.actions{

    display:grid;

    grid-template-columns:repeat(2,1fr);

    gap:14px;

}

.actions a{

    display:flex;

    align-items:center;

    justify-content:space-between;

    text-decoration:none;

    color:var(--text-primary);

    background:var(--content-bg);

    border:1px solid var(--border-main);

    border-radius:10px;

    padding:14px 16px;

    font-size:12px;

    font-weight:600;

    transition:.25s;

}

.actions a:hover{

    border-color:var(--accent);

    transform:translateY(-3px);

}

/* ===========================================================
   STATUS
=========================================================== */

.status{

    display:flex;

    justify-content:space-between;

    align-items:center;

    padding:13px 0;

    border-bottom:1px solid var(--border-main);

    font-size:12px;

}

.status:last-child{

    border:none;

}

.dot{

    width:8px;

    height:8px;

    border-radius:50%;

    background:#22c55e;

    box-shadow:0 0 10px rgba(34,197,94,.65);

}

/* ===========================================================
   DASHBOARD LOADING
=========================================================== */
.dashboard-loading{

    min-height:420px;

    display:flex;

    flex-direction:column;

    align-items:center;

    justify-content:center;

    gap:16px;

    color:var(--text-muted);

}

.loading-ring{

    width:28px;

    height:28px;

    border:2px solid var(--border-main);

    border-top-color:var(--accent);

    border-radius:50%;

    animation:dashboard-loading-spin .8s linear infinite;

}

@keyframes dashboard-loading-spin{

    to{
        transform:rotate(360deg);
    }

}
/* ===========================================================
   MOBILE
=========================================================== */

@media(max-width:1200px){

    .kpi-grid{

        grid-template-columns:repeat(2,1fr);

    }

    .grid{

        grid-template-columns:1fr;

    }

    .topbar{

        flex-direction:column;

        align-items:flex-start;

        gap:18px;

    }

    .system-info{

        flex-wrap:wrap;

    }

}

@media(max-width:768px){

    .dashboard{

        padding:18px;

    }

    .kpi-grid{

        grid-template-columns:1fr;

    }

    .actions{

        grid-template-columns:1fr;

    }

    .bar-row{

        grid-template-columns:90px 1fr 35px;

    }

}

</style>
```
<template>

<div class="dashboard">

  <div    v-if="loading"    class="dashboard-loading"
 >
 <div class="loading-ring"></div>

    <span>
        Loading archive data...
    </span>

 </div>
 <template v-else>
    <!-- =====================================================
         TOP BAR
    ====================================================== -->

    <section class="topbar">

        <div class="brand">

            <div class="brand-mark"></div>

            <div>

                <span class="eyebrow">

                    ATHENAEUM ORBIS

                </span>

                <h1>

                    Archive Intelligence Console

                </h1>

            </div>

        </div>

        <div class="system-info">

            <!-- <div class="system-block">

                <Clock :size="15"/>

                <span>{{ currentTime }}</span>

            </div>

            <div class="system-block">

                {{ currentDate }}

            </div>

            <div class="system-block">

                <Globe :size="15"/>

                {{ currentPlace }}

            </div> -->

            <button
                class="refresh-btn"
                :class="{ 'is-loading': loading }"
                :disabled="loading"
                @click="loadDashboard"
                title="Refresh archive data"
            >
                <RefreshCw :size="16"/>
            </button>

        </div>

    </section>



    <!-- =====================================================
         KPI GRID
    ====================================================== -->

    <section class="kpi-grid">

        <div class="kpi">

            <BookOpen class="kpi-icon"/>

            <span>

                Works

            </span>

            <h2>

                {{ summaryStats.total_accessions }}

            </h2>

        </div>


        <div class="kpi">

            <Book class="kpi-icon"/>

            <span>

                Items

            </span>

            <h2>

                {{ totalItems }}

            </h2>

        </div>


        <div class="kpi">

            <FileText class="kpi-icon"/>

            <span>

                In Circulation

            </span>

            <h2>

                {{ inCirculation }}

            </h2>

        </div>


        <div class="kpi">

    <Layers class="kpi-icon"/>

    <span>
        Categories
    </span>

    <h2>
        {{ totalCategories }}
    </h2>

  </div>
        <div class="kpi danger">

            <AlertTriangle class="kpi-icon"/>

            <span>

                Missing

            </span>

            <h2>

                {{ summaryStats.missing_items }}

            </h2>

        </div>

        

        <div class="kpi warning">

            <ShieldCheck class="kpi-icon"/>

            <span>

                Damaged

            </span>

            <h2>

                {{ summaryStats.damaged_items }}

            </h2>

        </div>

    </section>



    <!-- =====================================================
         MAIN GRID
    ====================================================== -->

    <section class="grid">

        <!-- ===================================== -->

        <div class="panel">

            <div class="panel-header">

                <h3>

                    <Activity :size="17"/>

                    Recent Activity

                </h3>

            </div>

            <div

                class="activity"

                v-for="log in summaryStats.recent_activity"

                :key="log.id"

            >

                <div class="timeline"></div>

                <div class="activity-content">

                    <strong>

                        {{ log.action }}

                    </strong>

                    <p>

                        {{ getBookTitle(log.serial_no) }}

                    </p>

                </div>

                <small>

                    {{ formatRelativeTime(log.changed_at) }}

                </small>

            </div>

        </div>

        <!-- ===================================== -->

        <div class="panel">

            <div class="panel-header">

                <h3>

                    <Book :size="17"/>

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

                    <strong>

                        {{ book.title }}

                    </strong>

                    <span>

                        {{ book.author }}

                    </span>

                </div>

                <small>

                    {{ formatDate(book.created_at) }}

                </small>

            </div>

        </div>



        <!-- ===================================== -->

        <div class="panel">

            <div class="panel-header">

                <h3>

                    <Layers :size="17"/>

                    Categories

                </h3>

            </div>

            <div

                class="bar-row"

                v-for="(count,name) in categoryStats"

                :key="name"

            >

                <label>

                    {{ name }}

                </label>

                <div class="bar">

                    <div

                        class="fill"

                        :style="{

                            width:(count/totalItems*100)+'%'

                        }"

                    ></div>

                </div>

                <strong>

                    {{ count }}

                </strong>

            </div>

        </div>



        <!-- ===================================== -->

        <div class="panel">

            <div class="panel-header">

                <h3>

                    <Globe :size="17"/>

                    Languages

                </h3>

            </div>

            <div

                class="bar-row"

                v-for="lang in summaryStats.languages"

                :key="lang.language"

            >

                <label>

                    {{ lang.language }}

                </label>

                <div class="bar">

                    <div

                        class="fill"

                        :style="{

                           width:(lang.count/totalItems*100)+'%'

                        }"

                    ></div>

                </div>

                <strong>

                    {{ lang.count }}

                </strong>

            </div>

            <div class="genre-footer">

                {{ totalGenres }} Genres Catalogued

            </div>

        </div>



        <!-- ===================================== -->

        <div class="panel">

            <div class="panel-header">

                <h3>

                    <ArrowRight :size="17"/>

                    Quick Actions

                </h3>

            </div>

            <div class="actions">

                <RouterLink to="/create-work">

                    + New Work

                </RouterLink>

                <RouterLink to="/create-item">

                    + New Item

                </RouterLink>

                <RouterLink to="/catalogue">

                    Catalogue

                </RouterLink>

                <RouterLink to="/search">

                    Search

                </RouterLink>

            </div>

        </div>



        <!-- ===================================== -->

        <div class="panel">

            <div class="panel-header">

                <h3>

                    <Database :size="17"/>

                    Archive Status

                </h3>

            </div>

            <div class="status">

                <span>

                    Database

                </span>

                <div class="dot"></div>

            </div>

            <div class="status">

                <span>

                    Archive Loaded

                </span>

                <strong>

                    {{ totalItems }}

                </strong>

            </div>

            <div class="status">

                <span>

                    Languages

                </span>

                <strong>

                    {{ summaryStats.languages.length }}

                </strong>

            </div>
            
            <div class="status">

                <span>

                    Categories

                </span>

                <strong>

                    {{ Object.keys(categoryStats).length }}

                </strong>

            </div>

        </div>

    </section>
    </template>

</div>

</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue"
import axios from "axios"

import {
  BookOpen,
  Book,
  FileText,
  AlertTriangle,
  ShieldCheck,
  Clock,
  Layers,
  Globe,
  Database,
  Search,
  Plus,
  ArrowRight,
  Activity,
  RefreshCw
} from "lucide-vue-next"

/* =====================================================
   DATA
===================================================== */

const rawCatalogue = ref([])

const summaryStats = ref({
  total_accessions: 0,
  missing_items: 0,
  damaged_items: 0,
  languages: [],
  recent_activity: []
})

const loading = ref(true)

/* =====================================================
   CLOCK
===================================================== */

const currentTime = ref("")
const currentDate = ref("")
const currentPlace = ref("")

let timer = null

function updateClock(){

    const now=new Date()

    currentTime.value=now.toLocaleTimeString([],{
        hour:"2-digit",
        minute:"2-digit",
        second:"2-digit"
    })

    currentDate.value=now.toLocaleDateString([],{
        weekday:"long",
        year:"numeric",
        month:"long",
        day:"numeric"
    })

    try{

        const tz=Intl.DateTimeFormat()
            .resolvedOptions()
            .timeZone

        currentPlace.value=
            tz.split("/")
            .pop()
            .replace("_"," ")

    }catch{

        currentPlace.value="Local"

    }

}

/* =====================================================
   FETCH
===================================================== */

async function loadDashboard(){

    loading.value=true

    try{

        const [summaryRes,catRes]=await Promise.all([

            axios.get("/dashboard/summary"),

            axios.get("/catalogue/",{
                params:{
                    limit:500
                }
            })

        ])

        summaryStats.value=summaryRes.data

        rawCatalogue.value=
            catRes.data.data || []

    }catch(e){

        console.error(e)

    }finally{

        loading.value=false

    }

}

/* =====================================================
   COMPUTED
===================================================== */

const totalItems=computed(()=>rawCatalogue.value.length)

const newestArrivals=computed(()=>{

    return [...rawCatalogue.value]

        .sort((a,b)=>b.serial_no-a.serial_no)

        .slice(0,8)

})

const categoryStats=computed(()=>{

    const stats={}

    rawCatalogue.value.forEach(book=>{

        const cat=
            book.category || "Unknown"

        stats[cat]=(stats[cat]||0)+1

    })

    return stats

})

const inCirculation=computed(()=>{

    return rawCatalogue.value.filter(

        b=>b.availability_status==="IN_RESEARCH_USE"

    ).length

})

const totalGenres=computed(()=>{

    const genres=new Set()

    rawCatalogue.value.forEach(book=>{

        if(book.genre){

            book.genre
                .split(/[/,]+/)
                .forEach(g=>genres.add(g.trim()))

        }

    })

    return genres.size

})

const totalCategories = computed(() => {
    return Object.keys(categoryStats.value).length
})

/* =====================================================
   HELPERS
===================================================== */

function getBookTitle(id){

    const book=
        rawCatalogue.value.find(

            b=>String(b.serial_no)===String(id)

        )

    return book
        ? book.title
        : "Unknown Record"

}

function formatRelativeTime(date){

    if(!date) return ""

    const diff=
        Math.floor(
            (Date.now()-new Date(date))/60000
        )

    if(diff<60)
        return `${diff} min ago`

    if(diff<1440)
        return `${Math.floor(diff/60)} hr ago`

    return `${Math.floor(diff/1440)} days ago`

}

function formatDate(date){

    if(!date) return ""

    return new Date(date)
        .toLocaleDateString([],{
            month:"short",
            day:"numeric",
            year:"numeric"
        })

}

/* =====================================================
   LIFE CYCLE
===================================================== */

onMounted(async()=>{

    updateClock()

    timer=setInterval(updateClock,1000)

    await loadDashboard()

})

onUnmounted(()=>{

    clearInterval(timer)

})
</script>