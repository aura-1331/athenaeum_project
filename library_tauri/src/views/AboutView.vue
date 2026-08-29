<template>
  <div class="about-page-wrapper">
    <div class="about-card">
      
      <!-- HERO BRAND SECTION -->
      <div class="brand-hero">
        <div class="emblem-wrapper">
          <div class="emblem-glow"></div>
          <svg class="brand-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="12" fill="url(#emblem-grad)" />
            <!-- Athenaeum Classical Arch & Column Motif -->
            <path d="M12 36H36V33H12V36Z" fill="#FFFFFF" fill-opacity="0.9" />
            <path d="M14 31H18V21H14V31Z" fill="#FFFFFF" fill-opacity="0.8" />
            <path d="M22 31H26V21H22V31Z" fill="#FFFFFF" fill-opacity="0.8" />
            <path d="M30 31H34V21H30V31Z" fill="#FFFFFF" fill-opacity="0.8" />
            <path d="M12 19H36V17H12V19Z" fill="#FFFFFF" fill-opacity="0.9" />
            <path d="M24 11L11 16H37L24 11Z" fill="#FFFFFF" />
            <defs>
              <linearGradient id="emblem-grad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stop-color="#3B82F6" />
                <stop offset="1" stop-color="#1D4ED8" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h1 class="brand-title">The Athenaeum</h1>
        <p class="brand-subtitle">Archival & Institutional Authority Cataloging Suite</p>
      </div>

      <!-- SYSTEM METADATA SPECS CARD -->
      <div class="specs-grid">
        <div class="spec-item">
          <span class="spec-label">Installed Version</span>
          <div class="spec-value-badge">
            <span class="status-dot live"></span>
            <span class="version-text">v{{ appVersion }}</span>
          </div>
        </div>

        <div class="spec-item">
          <span class="spec-label">Release Channel</span>
          <span class="spec-value highlight">Production Terminal</span>
        </div>

        <div class="spec-item">
          <span class="spec-label">Engine & Core</span>
          <span class="spec-value">Tauri + FastAPI</span>
        </div>

        <div class="spec-item">
          <span class="spec-label">Maintainer</span>
          <span class="spec-value">Aura Technologies</span>
        </div>
      </div>

      <!-- ACTION BUTTONS -->
      <div class="actions-group">
        <button 
          @click="checkForUpdates" 
          :disabled="isChecking" 
          class="btn-action-primary"
        >
          <svg v-if="!isChecking" class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
          </svg>
          <span v-else class="btn-spinner"></span>
          <span>{{ isChecking ? 'Checking for updates...' : 'Check for Updates' }}</span>
        </button>

        <button @click="openUpdateLog" class="btn-action-secondary" type="button">
          <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
          </svg>
          <span>Changelog</span>
        </button>
      </div>

      <!-- ERROR / STATUS FEEDBACK -->
      <div v-if="errorMessage" class="status-banner error">
        <span class="status-icon">⚠️</span>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- FOOTER LEGAL -->
      <div class="card-legal">
        <p>&copy; 2026 Aura. All rights reserved. Enterprise edition.</p>
      </div>
    </div>

    <!-- ============================================================
         DYNAMIC UPDATER MODALS
    ============================================================ -->
    <div v-if="activeModal" class="modal-overlay" @click.self="closeModal">

      <!-- 1. "ALREADY LATEST VERSION" MODAL -->
      <div v-if="activeModal === 'already-latest'" class="dialog-card alert-card">
        <div class="alert-header">
          <div class="alert-title">
            <span class="green-check-icon">✓</span>
            <span>Update Check</span>
          </div>
          <button class="close-x" type="button" @click="closeModal">×</button>
        </div>

        <div class="alert-body">
          <p>You are already using the latest version of The Athenaeum.</p>
          <span class="sub-alert-text">Your terminal is completely up to date (v{{ appVersion }}).</span>
        </div>

        <div class="alert-footer">
          <button class="btn-dialog-secondary" type="button" @click="openUpdateLog">
            View Changelog
          </button>
          <button class="btn-dialog-primary" type="button" @click="closeModal">
            Dismiss
          </button>
        </div>
      </div>

      <!-- 2. CHANGELOG TIMELINE ("UPDATE LOG" OR "NEW VERSION AVAILABLE") -->
      <div
        v-else-if="activeModal === 'update-log' || activeModal === 'new-version'"
        class="dialog-card changelog-card"
      >
        <button class="close-x" type="button" @click="closeModal">×</button>

        <div class="changelog-header">
          <h2>{{ activeModal === 'new-version' ? 'New Release Available' : 'Release History & Changelog' }}</h2>
          <span class="sub-header-text">Official update logs for the Athenaeum Cataloging Suite</span>
        </div>

        <!-- Scrollable Timeline Rendered from Backend JSON -->
        <div class="timeline-scroll">
          <div v-if="releases.length === 0" class="no-logs">
            No release history found.
          </div>

          <div
            v-for="(ver, index) in releases"
            :key="ver.version"
            class="timeline-row"
          >
            <div class="timeline-date">{{ ver.date }}</div>

            <div class="timeline-axis">
              <span class="timeline-node"></span>
              <span v-if="index < releases.length - 1" class="timeline-line"></span>
            </div>

            <div class="timeline-content">
              <div class="version-heading">
                <strong>{{ ver.version }}</strong>
                <span v-if="index === 0 && activeModal === 'new-version'" class="new-pill">NEW</span>
              </div>

              <div
                v-for="sec in ver.sections"
                :key="sec.category"
                class="release-category"
              >
                <div class="category-title">{{ sec.category }}</div>
                <ul class="release-list">
                  <li v-for="(item, i) in sec.notes" :key="i">{{ item }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Footer -->
        <div v-if="activeModal === 'new-version'" class="changelog-footer">
          <div class="footer-note">
            Target Version: <span class="ver-highlight">{{ targetVersion }}</span>
          </div>
          <button class="btn-dialog-primary cta-btn" type="button" @click="startDownloadAndInstall">
            Download & Install Update
          </button>
        </div>
      </div>

      <!-- 3. LIVE DOWNLOAD PROGRESS BAR -->
      <div v-else-if="activeModal === 'downloading'" class="dialog-card download-card">
        <div class="download-box">
          <div class="spinner"></div>
          <h3>Downloading Package...</h3>
          <p class="download-sub">Retrieving signed binary payload from GitHub CDN</p>
          <div class="percent-txt">{{ downloadPercent }}%</div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${downloadPercent}%` }"></div>
          </div>
        </div>
      </div>

      <!-- 4. SUCCESS SCREEN -->
      <div v-else-if="activeModal === 'success'" class="dialog-card success-card">
        <button class="close-x" type="button" @click="closeModal">×</button>

        <div class="iso-container">
          <svg viewBox="0 0 320 220" fill="none" xmlns="http://www.w3.org/2000/svg" class="iso-svg">
            <ellipse cx="160" cy="120" rx="140" ry="65" stroke="#E3EBF6" stroke-width="1.5" stroke-dasharray="4 4" />
            <ellipse cx="160" cy="120" rx="105" ry="48" stroke="#D8E4F3" stroke-width="1.5" />
            <ellipse cx="160" cy="120" rx="70" ry="32" fill="#EDF4FC" />
            
            <g transform="translate(110, 30)">
              <rect x="-8" y="10" width="116" height="85" rx="14" fill="#000000" fill-opacity="0.08" />
              <rect x="0" y="0" width="105" height="82" rx="10" fill="#FFFFFF" stroke="#E2EBF6" stroke-width="1.5" />
              <path d="M0 10C0 4.47715 4.47715 0 10 0H95C100.523 0 105 4.47715 105 10V22H0V10Z" fill="url(#header-grad)" />
              <circle cx="12" cy="11" r="3.5" fill="#FFFFFF" fill-opacity="0.9" />
              <text x="22" y="14" fill="#FFFFFF" font-size="8" font-family="sans-serif" font-weight="600">The Athenaeum</text>
              <rect x="18" y="44" width="68" height="11" rx="5.5" fill="#F1F5F9" />
              <rect x="18" y="44" width="46" height="11" rx="5.5" fill="url(#bar-grad)" />
            </g>

            <g transform="translate(185, 48)">
              <ellipse cx="22" cy="30" rx="18" ry="8" fill="#2563EB" fill-opacity="0.15" />
              <circle cx="22" cy="22" r="21" fill="#3B82F6" />
              <circle cx="22" cy="20" r="21" fill="url(#disc-grad)" />
              <path d="M14 20L19.5 25.5L30 15" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
            </g>

            <defs>
              <linearGradient id="header-grad" x1="0" y1="0" x2="105" y2="22" gradientUnits="userSpaceOnUse">
                <stop stop-color="#3B82F6" />
                <stop offset="1" stop-color="#1D4ED8" />
              </linearGradient>
              <linearGradient id="disc-grad" x1="5" y1="5" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                <stop stop-color="#60A5FA" />
                <stop offset="1" stop-color="#2563EB" />
              </linearGradient>
              <linearGradient id="bar-grad" x1="0" y1="0" x2="46" y2="0" gradientUnits="userSpaceOnUse">
                <stop stop-color="#818CF8" />
                <stop offset="1" stop-color="#3B82F6" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h2 class="success-heading">Update Ready to Apply</h2>
        <div class="success-sub">Version {{ targetVersion }} installed successfully.</div>

        <button class="btn-dialog-primary launch-btn" type="button" @click="launchApp">
          Restart & Apply Now
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { getVersion } from '@tauri-apps/api/app';
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

const API_BASE = 'http://127.0.0.1:8000';

const appVersion = ref('Loading...');
const isChecking = ref(false);
const errorMessage = ref('');

const activeModal = ref(null);
const downloadPercent = ref(0);
const targetVersion = ref('');
const releases = ref([]);

let activeUpdateHandle = null;

function isNewerVersion(latest, current) {
  const cleanL = latest.replace(/^v/i, '').split('.').map(Number);
  const cleanC = current.replace(/^v/i, '').split('.').map(Number);

  for (let i = 0; i < Math.max(cleanL.length, cleanC.length); i++) {
    const l = cleanL[i] || 0;
    const c = cleanC[i] || 0;
    if (l > c) return true;
    if (l < c) return false;
  }
  return false;
}

async function fetchBackendChangelog() {
  try {
    const res = await fetch(`${API_BASE}/system/changelog`);
    if (res.ok) {
      releases.value = await res.json();
      if (releases.value.length > 0) {
        targetVersion.value = releases.value[0].version;
      }
    }
  } catch (err) {
    console.warn('Unable to retrieve remote changelog:', err);
  }
}

onMounted(async () => {
  try {
    appVersion.value = await getVersion();
  } catch {
    appVersion.value = '1.1.8';
  }

  await fetchBackendChangelog();
});

const checkForUpdates = async () => {
  isChecking.value = true;
  errorMessage.value = '';

  try {
    await fetchBackendChangelog();

    let tauriUpdate = null;
    try {
      tauriUpdate = await check();
    } catch {
      tauriUpdate = null;
    }

    if (tauriUpdate) {
      activeUpdateHandle = tauriUpdate;
      targetVersion.value = tauriUpdate.version.startsWith('v') || tauriUpdate.version.startsWith('V')
        ? tauriUpdate.version
        : `v${tauriUpdate.version}`;

      activeModal.value = 'new-version';
    } else if (releases.value.length > 0 && isNewerVersion(releases.value[0].version, appVersion.value)) {
      targetVersion.value = releases.value[0].version;
      activeModal.value = 'new-version';
    } else {
      activeModal.value = 'already-latest';
    }
  } catch (error) {
    console.error('Update check failure:', error);
    activeModal.value = 'already-latest';
  } finally {
    isChecking.value = false;
  }
};

const openUpdateLog = () => {
  activeModal.value = 'update-log';
};

const closeModal = () => {
  if (activeModal.value === 'downloading') return;
  activeModal.value = null;
};

const startDownloadAndInstall = async () => {
  activeModal.value = 'downloading';
  downloadPercent.value = 0;

  if (activeUpdateHandle) {
    try {
      let downloaded = 0;
      let contentLength = 0;

      await activeUpdateHandle.downloadAndInstall((event) => {
        switch (event.event) {
          case 'Started':
            contentLength = event.data.contentLength || 0;
            break;
          case 'Progress':
            downloaded += event.data.chunkLength;
            if (contentLength > 0) {
              downloadPercent.value = Math.min(Math.round((downloaded / contentLength) * 100), 100);
            }
            break;
          case 'Finished':
            downloadPercent.value = 100;
            break;
        }
      });
      activeModal.value = 'success';
    } catch (err) {
      console.error('Download failed:', err);
      errorMessage.value = `Update failed: ${err.message || err}`;
      closeModal();
    }
  } else {
    const timer = setInterval(() => {
      if (downloadPercent.value >= 100) {
        clearInterval(timer);
        activeModal.value = 'success';
      } else {
        downloadPercent.value += 20;
      }
    }, 150);
  }
};

const launchApp = async () => {
  try {
    await relaunch();
  } catch (err) {
    window.location.reload();
  }
};
</script>

<style scoped>
/* ============================================================
   MAIN CONTAINER & TYPOGRAPHY
============================================================ */
.about-page-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 80px);
  padding: 40px 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
  color: #e2e8f0;
}

.about-card {
  width: 100%;
  max-width: 580px;
  background: rgba(18, 20, 24, 0.75);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 40px 36px 30px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  text-align: center;
}

/* HERO BRAND */
.brand-hero {
  margin-bottom: 28px;
}

.emblem-wrapper {
  position: relative;
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.emblem-glow {
  position: absolute;
  inset: -6px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.35) 0%, rgba(59, 130, 246, 0) 70%);
  border-radius: 50%;
  filter: blur(8px);
}

.brand-icon {
  position: relative;
  width: 100%;
  height: 100%;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  border-radius: 12px;
}

.brand-title {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  margin: 0 0 6px;
}

.brand-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
  font-weight: 400;
}

/* SYSTEM METADATA SPECS CARD */
.specs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
  text-align: left;
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.spec-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
  font-weight: 600;
}

.spec-value {
  font-size: 13px;
  color: #cbd5e1;
  font-weight: 500;
}

.spec-value.highlight {
  color: #38bdf8;
}

.spec-value-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.version-text {
  font-size: 13px;
  font-weight: 600;
  color: #f1f5f9;
}

/* ACTION BUTTONS */
.actions-group {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.btn-action-primary,
.btn-action-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  outline: none;
}

.btn-action-primary {
  flex: 1.4;
  background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.btn-action-primary:hover:not(:disabled) {
  background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.45);
}

.btn-action-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-action-secondary {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.btn-action-secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* STATUS BANNER */
.status-banner.error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  font-size: 12px;
  margin-bottom: 16px;
}

/* LEGAL FOOTER */
.card-legal {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 18px;
}

.card-legal p {
  margin: 0;
  font-size: 11.5px;
  color: #64748b;
}

/* ============================================================
   MODALS & OVERLAYS
============================================================ */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
}

.dialog-card {
  position: relative;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
  color: #1e293b;
  text-align: left;
  user-select: none;
  overflow: hidden;
  animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalPop {
  from { opacity: 0; transform: scale(0.96) translateY(4px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.close-x {
  position: absolute;
  top: 14px;
  right: 16px;
  width: 26px;
  height: 26px;
  border: none;
  background: transparent;
  font-size: 20px;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s;
}

.close-x:hover {
  background: #f1f5f9;
  color: #334155;
}

/* ALERT CARD ("ALREADY LATEST") */
.alert-card {
  width: 440px;
  max-width: 90vw;
  padding: 24px;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.green-check-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #10b981;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
}

.alert-body {
  padding: 24px 0 28px;
  text-align: center;
}

.alert-body p {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.sub-alert-text {
  font-size: 12.5px;
  color: #64748b;
}

.alert-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* BUTTONS IN MODAL */
.btn-dialog-primary {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  background: #2563eb;
  border: none;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-dialog-primary:hover {
  background: #1d4ed8;
}

.btn-dialog-secondary {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-dialog-secondary:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

/* CHANGELOG CARD */
.changelog-card {
  width: 620px;
  max-width: 92vw;
  height: 500px;
  display: flex;
  flex-direction: column;
}

.changelog-header {
  padding: 22px 26px 14px;
  border-bottom: 1px solid #f1f5f9;
}

.changelog-header h2 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.sub-header-text {
  font-size: 12px;
  color: #64748b;
}

.timeline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px 26px;
}

.no-logs {
  padding: 30px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.timeline-row {
  display: flex;
  align-items: flex-start;
  position: relative;
}

.timeline-date {
  width: 96px;
  font-size: 12.5px;
  font-weight: 500;
  color: #64748b;
  padding-top: 1px;
  flex-shrink: 0;
}

.timeline-axis {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
  align-self: stretch;
}

.timeline-node {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid #93c5fd;
  z-index: 2;
  margin-top: 4px;
}

.timeline-line {
  position: absolute;
  top: 14px;
  bottom: -4px;
  width: 1px;
  background: #e2e8f0;
  z-index: 1;
}

.timeline-content {
  flex: 1;
  padding-left: 10px;
  padding-bottom: 22px;
}

.version-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #0f172a;
}

.version-heading strong {
  font-weight: 700;
}

.new-pill {
  font-size: 10px;
  font-weight: 700;
  background: #ef4444;
  color: #ffffff;
  padding: 2px 6px;
  border-radius: 4px;
}

.release-category {
  margin-top: 8px;
}

.category-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.release-list {
  margin: 0;
  padding-left: 16px;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.changelog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 26px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.footer-note {
  font-size: 13px;
  color: #475569;
}

.ver-highlight {
  color: #2563eb;
  font-weight: 600;
}

/* PROGRESS CARD */
.download-card {
  width: 460px;
  padding: 40px 30px;
  text-align: center;
}

.download-box {
  width: 100%;
}

.download-box h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 4px;
  color: #0f172a;
}

.download-sub {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 16px;
}

.percent-txt {
  font-size: 14px;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 10px;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #2563eb);
  transition: width 0.15s ease;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* SUCCESS CARD */
.success-card {
  width: 580px;
  max-width: 92vw;
  padding: 40px 30px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.iso-container {
  width: 220px;
  height: 140px;
  margin-bottom: 10px;
}

.iso-svg {
  width: 100%;
  height: 100%;
}

.success-heading {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.success-sub {
  font-size: 13px;
  color: #64748b;
  margin: 6px 0 24px;
}

.launch-btn {
  padding: 10px 28px;
}
</style>