<template>
  <div class="settings-page-wrapper">
    <div class="settings-shell">
      
      <!-- SIDEBAR NAVIGATION -->
      <aside class="settings-sidebar">
        <div class="sidebar-header">
          <h2 class="sidebar-title">Settings</h2>
          <p class="sidebar-subtitle">Preferences & system options</p>
        </div>

        <nav class="settings-nav">
          <button 
            type="button"
            class="nav-item" 
            :class="{ active: currentTab === 'general' }"
            @click="currentTab = 'general'"
          >
            <span class="nav-icon">⚙️</span>
            <span>General</span>
          </button>

          <button 
            type="button"
            class="nav-item" 
            :class="{ active: currentTab === 'appearance' }"
            @click="currentTab = 'appearance'"
          >
            <span class="nav-icon">🎨</span>
            <span>Appearance</span>
          </button>

          <button 
            type="button"
            class="nav-item" 
            :class="{ active: currentTab === 'updates' }"
            @click="currentTab = 'updates'"
          >
            <span class="nav-icon">🔄</span>
            <span>Updates</span>
          </button>

          <button 
            type="button"
            class="nav-item" 
            :class="{ active: currentTab === 'about' }"
            @click="currentTab = 'about'"
          >
            <span class="nav-icon">🏛️</span>
            <span>About</span>
          </button>
        </nav>
      </aside>

      <!-- MAIN CONTENT PANEL -->
      <main class="settings-content">
        
        <!-- 1. GENERAL TAB -->
        <section v-if="currentTab === 'general'" class="settings-panel">
          <div class="panel-header-block">
            <h2 class="panel-heading">General</h2>
            <p class="panel-subheading">Manage your application workspace preferences.</p>
          </div>

          <div class="settings-group">
            <h3 class="group-title">Notifications & Workspace</h3>

            <div class="setting-item">
              <div class="setting-text">
                <span class="setting-title">Desktop Notifications</span>
                <span class="setting-caption">Display system alerts for record approvals, catalog changes, and reminders.</span>
              </div>
              <label class="toggle-control">
                <input type="checkbox" v-model="notificationsEnabled" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </section>

        <!-- 2. APPEARANCE TAB -->
        <section v-if="currentTab === 'appearance'" class="settings-panel">
          <div class="panel-header-block">
            <h2 class="panel-heading">Appearance</h2>
            <p class="panel-subheading">Customize how your application looks.</p>
          </div>

          <div class="settings-group">
            <div class="setting-item">
              <div class="setting-text">
                <span class="setting-title">Interface Theme</span>
                <span class="setting-caption">Choose between dark mode, light mode, or follow your computer system.</span>
              </div>
              <select v-model="selectedTheme" class="select-dropdown">
                <option value="dark">Dark Theme (Default)</option>
                <option value="light">Light Theme</option>
                <option value="system">Follow System</option>
              </select>
            </div>
          </div>
        </section>

        <!-- 3. UPDATES TAB (WIRED & PERMISSION-BASED) -->
        <section v-if="currentTab === 'updates'" class="settings-panel">
          <div class="panel-header-block">
            <h2 class="panel-heading">Software Updates</h2>
            <p class="panel-subheading">Keep The Athenaeum up to date with the latest features and security enhancements.</p>
          </div>

          <div class="settings-group">
            <h3 class="group-title">Version & Release Status</h3>
            
            <div class="update-card-premium">
              <div class="update-info">
                <div class="update-status-row">
                  <span class="status-badge-live"></span>
                  <span class="version-name">The Athenaeum {{ appVersion }}</span>
                  <span class="tag-latest">Current</span>
                </div>
                <p class="update-caption">Your system is connected to the official release channel.</p>
              </div>

              <div class="update-actions">
                <button 
                  type="button"
                  @click="checkForUpdates" 
                  :disabled="isChecking" 
                  class="btn-check-update"
                >
                  <span v-if="isChecking" class="action-spinner"></span>
                  <span>{{ isChecking ? 'Checking...' : 'Check for Updates' }}</span>
                </button>

                <button 
                  type="button"
                  @click="openUpdateLog" 
                  class="btn-view-notes"
                >
                  Release Notes
                </button>
              </div>
            </div>

            <div v-if="errorMessage" class="error-notice">
              <span class="error-icon">⚠️</span>
              <span>{{ errorMessage }}</span>
            </div>
          </div>

          <div class="settings-group">
            <h3 class="group-title">Update Preferences</h3>

            <div class="setting-item">
              <div class="setting-text">
                <span class="setting-title">Automatic Update Checks</span>
                <span class="setting-caption">Notify me when a new release is available without installing anything automatically.</span>
              </div>
              <label class="toggle-control">
                <input type="checkbox" v-model="autoCheckUpdates" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </section>

        <!-- 4. ABOUT TAB (PRESTIGIOUS, REFINED & JARGON-FREE) -->
        <section v-if="currentTab === 'about'" class="about-panel">
          <div class="about-card-refined">
            
            <!-- ELEGANT LOGO PLACEHOLDER -->
            <div class="emblem-wrapper">
              <div class="emblem-cube">
                <span class="emblem-mark">ATH</span>
              </div>
            </div>

            <!-- PRODUCT IDENTITY -->
            <h1 class="product-title">The Athenaeum</h1>
            <p class="product-version">Version {{ appVersion }} &bull; Enterprise Edition</p>
            
            <p class="product-summary">
              Archival and institutional authority cataloging suite, designed for high-integrity records preservation and tamper-evident custodial management.
            </p>

            <div class="fine-divider"></div>

            <!-- COPYRIGHT & LEGAL -->
            <div class="legal-block">
              <p>&copy; 2026 Aura Technologies. All rights reserved.</p>
              <p class="legal-sub">Licensed for institutional deployment.</p>
            </div>

          </div>
        </section>

      </main>
    </div>

    <!-- ============================================================
         CONFIRMATION & PERMISSION MODALS
    ============================================================ -->
    <div v-if="activeModal" class="modal-backdrop" @click.self="closeModal">

      <!-- 1. ALREADY LATEST VERSION -->
      <div v-if="activeModal === 'already-latest'" class="dialog-box">
        <div class="dialog-top">
          <div class="dialog-headline">
            <span class="check-pill">✓</span>
            <span>Up to Date</span>
          </div>
          <button class="dialog-x" type="button" @click="closeModal">×</button>
        </div>

        <div class="dialog-message">
          <p class="dialog-main-text">You are already using the latest version of The Athenaeum.</p>
          <span class="dialog-sub-text">Version {{ appVersion }} is currently installed and up to date.</span>
        </div>

        <div class="dialog-buttons">
          <button class="btn-subtle" type="button" @click="openUpdateLog">
            View Release Notes
          </button>
          <button class="btn-highlight" type="button" @click="closeModal">
            Done
          </button>
        </div>
      </div>

      <!-- 2. CONNECTION ERROR -->
      <div v-else-if="activeModal === 'check-failed'" class="dialog-box">
        <div class="dialog-top">
          <div class="dialog-headline">
            <span class="cross-pill">✕</span>
            <span>Check Failed</span>
          </div>
          <button class="dialog-x" type="button" @click="closeModal">×</button>
        </div>

        <div class="dialog-message">
          <p class="dialog-main-text">Unable to check for updates at this time.</p>
          <span class="dialog-sub-text">{{ errorMessage || 'Please check your internet connection and try again.' }}</span>
        </div>

        <div class="dialog-buttons">
          <button class="btn-highlight" type="button" @click="closeModal">
            Dismiss
          </button>
        </div>
      </div>

      <!-- 3. NEW RELEASE AVAILABLE (EXPLICIT CONFIRMATION REQUIRED) -->
      <div 
        v-else-if="activeModal === 'update-log' || activeModal === 'new-version'" 
        class="dialog-box notes-box"
      >
        <button class="dialog-x" type="button" @click="closeModal">×</button>

        <div class="dialog-top-simple">
          <h2>{{ activeModal === 'new-version' ? 'New Update Available' : 'Release Notes' }}</h2>
          <span class="dialog-sub-text">
            {{ activeModal === 'new-version' ? 'Would you like to install this update? Nothing will download without your consent.' : 'Updates and enhancements for The Athenaeum' }}
          </span>
        </div>

        <div class="notes-scroll">
          <div v-if="releases.length === 0" class="empty-notes">
            No release history found.
          </div>

          <div 
            v-for="(ver, index) in releases" 
            :key="ver.version" 
            class="note-entry"
          >
            <div class="note-date">{{ ver.date || 'Recent' }}</div>

            <div class="note-line-col">
              <span class="note-dot"></span>
              <span v-if="index < releases.length - 1" class="note-line"></span>
            </div>

            <div class="note-body">
              <div class="note-version-title">
                <strong>{{ ver.version }}</strong>
                <span v-if="index === 0 && activeModal === 'new-version'" class="new-tag">NEW</span>
              </div>

              <div 
                v-for="sec in ver.sections" 
                :key="sec.category" 
                class="note-section"
              >
                <div class="section-label">{{ sec.category }}</div>
                <ul class="section-list">
                  <li v-for="(item, i) in sec.notes" :key="i">{{ item }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeModal === 'new-version'" class="notes-bottom">
          <button class="btn-subtle" type="button" @click="closeModal">
            Not Now
          </button>
          <button class="btn-highlight" type="button" @click="startDownloadAndInstall">
            Yes, Download & Install
          </button>
        </div>
      </div>

      <!-- 4. LIVE DOWNLOAD PROGRESS -->
      <div v-else-if="activeModal === 'downloading'" class="dialog-box progress-box">
        <div class="spinner-ring"></div>
        <h3 class="progress-title">Downloading Update...</h3>
        <p class="progress-subtitle">Retrieving verified update package</p>
        <div class="progress-percentage">{{ downloadPercent }}%</div>
        
        <div class="progress-bar-bg">
          <div class="progress-bar-val" :style="{ width: `${downloadPercent}%` }"></div>
        </div>

        <button class="btn-cancel" type="button" @click="cancelDownload">
          Cancel Download
        </button>
      </div>

      <!-- 5. RESTART CONFIRMATION -->
      <div v-else-if="activeModal === 'success'" class="dialog-box success-box">
        <button class="dialog-x" type="button" @click="closeModal">×</button>

        <div class="success-ring">
          <span class="success-check">✓</span>
        </div>

        <h2 class="dialog-main-text text-xl">Ready to Apply</h2>
        <p class="dialog-sub-text">Version {{ targetVersion }} has finished downloading. Would you like to restart now to finish updating?</p>

        <div class="dialog-buttons mt-4">
          <button class="btn-subtle" type="button" @click="closeModal">
            Later
          </button>
          <button class="btn-highlight" type="button" @click="launchApp">
            Restart Now
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { getVersion } from '@tauri-apps/api/app';
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

import { API_BASE } from '@/config'

// Current tab navigation
const currentTab = ref('general');

// Saved preferences in local storage so choices actually stick
const savedAutoCheck = localStorage.getItem('athenaeum_auto_check_updates');
const autoCheckUpdates = ref(savedAutoCheck !== null ? savedAutoCheck === 'true' : true);

const savedNotifications = localStorage.getItem('athenaeum_notifications_enabled');
const notificationsEnabled = ref(savedNotifications !== null ? savedNotifications === 'true' : true);

const savedTheme = localStorage.getItem('athenaeum_theme');
const selectedTheme = ref(savedTheme || 'dark');

// Watchers to save choices automatically
watch(autoCheckUpdates, (val) => {
  localStorage.setItem('athenaeum_auto_check_updates', String(val));
});

watch(notificationsEnabled, (val) => {
  localStorage.setItem('athenaeum_notifications_enabled', String(val));
});

watch(selectedTheme, (val) => {
  localStorage.setItem('athenaeum_theme', val);
});

// App Status
const appVersion = ref('Loading...');
const isChecking = ref(false);
const errorMessage = ref('');

// Modals
const activeModal = ref(null);
const downloadPercent = ref(0);
const targetVersion = ref('');
const releases = ref([]);

let activeUpdateHandle = null;
let downloadAborted = false;

function parseVersionNumbers(v) {
  if (!v) return [0, 0, 0];
  const cleaned = v.replace(/^v/i, '').trim();
  const [coreNumbers] = cleaned.split('-');
  return coreNumbers.split('.').map(num => parseInt(num, 10) || 0);
}

function isNewerVersion(latest, current) {
  const latestParts = parseVersionNumbers(latest);
  const currentParts = parseVersionNumbers(current);

  for (let i = 0; i < 3; i++) {
    const l = latestParts[i] || 0;
    const c = currentParts[i] || 0;
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
    console.warn('Unable to retrieve changelog:', err);
  }
}

// Quiet background check that ONLY notifies if an update exists, never installing without consent
const checkQuietlyForUpdates = async () => {
  try {
    let tauriUpdate = null;
    try {
      tauriUpdate = await check();
    } catch {
      tauriUpdate = null;
    }

    if (tauriUpdate) {
      activeUpdateHandle = tauriUpdate;
      targetVersion.value = tauriUpdate.version.startsWith('v')
        ? tauriUpdate.version
        : `v${tauriUpdate.version}`;
      activeModal.value = 'new-version';
    } else if (releases.value.length > 0 && isNewerVersion(releases.value[0].version, appVersion.value)) {
      activeUpdateHandle = null;
      targetVersion.value = releases.value[0].version;
      activeModal.value = 'new-version';
    }
  } catch {
    // If quiet check fails, silently do nothing so the user isn't disturbed
  }
};

onMounted(async () => {
  try {
    appVersion.value = await getVersion();
  } catch {
    appVersion.value = '2.2.3';
  }

  await fetchBackendChangelog();

  // If automatic update checks are turned on, look quietly and ask permission if found
  if (autoCheckUpdates.value) {
    checkQuietlyForUpdates();
  }
});

const checkForUpdates = async () => {
  isChecking.value = true;
  errorMessage.value = '';

  try {
    await fetchBackendChangelog();

    let tauriUpdate = null;
    try {
      tauriUpdate = await check();
    } catch (checkErr) {
      console.warn('Native updater check failed:', checkErr);
      tauriUpdate = null;
    }

    if (tauriUpdate) {
      activeUpdateHandle = tauriUpdate;
      targetVersion.value = tauriUpdate.version.startsWith('v')
        ? tauriUpdate.version
        : `v${tauriUpdate.version}`;
      activeModal.value = 'new-version';
    } else if (releases.value.length > 0 && isNewerVersion(releases.value[0].version, appVersion.value)) {
      activeUpdateHandle = null;
      targetVersion.value = releases.value[0].version;
      activeModal.value = 'new-version';
    } else {
      activeModal.value = 'already-latest';
    }
  } catch (error) {
    console.error('Update check failure:', error);
    errorMessage.value = 'Could not check for updates. Please check your network connection.';
    activeModal.value = 'check-failed';
  } finally {
    isChecking.value = false;
  }
};

const openUpdateLog = () => {
  activeModal.value = 'update-log';
};

const closeModal = () => {
  activeModal.value = null;
};

const cancelDownload = () => {
  downloadAborted = true;
  activeModal.value = null;
  downloadPercent.value = 0;
  errorMessage.value = 'Update download was cancelled.';
};

const startDownloadAndInstall = async () => {
  downloadAborted = false;
  activeModal.value = 'downloading';
  downloadPercent.value = 0;

  if (activeUpdateHandle) {
    try {
      let downloaded = 0;
      let contentLength = 0;

      await activeUpdateHandle.downloadAndInstall((event) => {
        if (downloadAborted) return;

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

      if (!downloadAborted) {
        activeModal.value = 'success';
      }
    } catch (err) {
      console.error('Download failed:', err);
      errorMessage.value = `Update failed: ${err.message || err}`;
      closeModal();
    }
  } else {
    errorMessage.value = 'Automatic download is not available for this release. Please download it directly from your portal.';
    closeModal();
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
/* PAGE SHELL */
.settings-page-wrapper {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: calc(100vh - 80px);
  padding: 32px 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
  color: #e2e8f0;
}

.settings-shell {
  display: flex;
  width: 100%;
  max-width: 940px;
  min-height: 560px;
  background: rgba(15, 17, 23, 0.94);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

/* SIDEBAR */
.settings-sidebar {
  width: 220px;
  background: rgba(10, 12, 16, 0.98);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 26px 14px;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 3px;
  letter-spacing: -0.01em;
}

.sidebar-subtitle {
  font-size: 11px;
  color: #64748b;
  margin: 0 0 22px;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #f1f5f9;
}

.nav-item.active {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  border-color: rgba(59, 130, 246, 0.25);
  font-weight: 600;
}

.nav-icon {
  font-size: 14px;
}

/* MAIN CONTENT */
.settings-content {
  flex: 1;
  padding: 34px 38px;
  overflow-y: auto;
}

.panel-header-block {
  margin-bottom: 24px;
}

.panel-heading {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  margin: 0 0 4px;
}

.panel-subheading {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

.settings-group {
  margin-bottom: 28px;
}

.group-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

/* SETTING ROWS */
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.setting-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 460px;
}

.setting-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #f1f5f9;
}

.setting-caption {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}

.select-dropdown {
  background: #141720;
  border: 1px solid #262c3c;
  border-radius: 6px;
  color: #f1f5f9;
  padding: 7px 12px;
  font-size: 13px;
  outline: none;
}

.toggle-control {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.toggle-control input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: #242938;
  transition: 0.2s;
  border-radius: 22px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.2s;
  border-radius: 50%;
}

input:checked + .toggle-slider {
  background-color: #2563eb;
}

input:checked + .toggle-slider:before {
  transform: translateX(18px);
}

/* EXECUTIVE SOFTWARE UPDATE CARD */
.update-card-premium {
  background: rgba(22, 26, 36, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.update-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.update-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-badge-live {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.version-name {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.tag-latest {
  font-size: 10.5px;
  font-weight: 600;
  color: #34d399;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 1px 6px;
  border-radius: 4px;
}

.update-caption {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.update-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-check-update {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  background: #2563eb;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.15s ease;
}

.btn-check-update:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-check-update:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-view-notes {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.04);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.15s ease;
}

.btn-view-notes:hover {
  background: rgba(255, 255, 255, 0.07);
  color: #ffffff;
}

.action-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  font-size: 12px;
  margin-top: 10px;
}

/* ABOUT PANEL */
.about-panel {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px 0;
}

.about-card-refined {
  width: 100%;
  max-width: 520px;
  background: rgba(20, 24, 32, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 40px 32px 30px;
  text-align: center;
}

.emblem-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 18px;
}

.emblem-cube {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(30, 41, 59, 0.35) 100%);
  border: 1px solid rgba(59, 130, 246, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}

.emblem-mark {
  font-family: monospace;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #60a5fa;
}

.product-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  margin: 0 0 4px;
}

.product-version {
  font-size: 12.5px;
  color: #94a3b8;
  margin: 0 0 16px;
}

.product-summary {
  font-size: 13px;
  color: #cbd5e1;
  line-height: 1.6;
  margin: 0 auto 24px;
  max-width: 440px;
}

.fine-divider {
  width: 100%;
  height: 1px;
  background: rgba(255, 255, 255, 0.05);
  margin-bottom: 18px;
}

.legal-block p {
  margin: 0 0 3px;
  font-size: 11.5px;
  color: #64748b;
}

.legal-block .legal-sub {
  font-size: 10.5px;
  color: #475569;
}

/* MODALS */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
}

.dialog-box {
  position: relative;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.35);
  color: #1e293b;
  overflow: hidden;
  width: 420px;
  max-width: 90vw;
  padding: 22px;
}

.dialog-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-headline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.check-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #10b981;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
}

.cross-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ef4444;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
}

.dialog-x {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
}

.dialog-message {
  padding: 16px 0 20px;
  text-align: center;
}

.dialog-main-text {
  margin: 0 0 4px;
  font-size: 13.5px;
  font-weight: 600;
  color: #1e293b;
}

.dialog-sub-text {
  font-size: 12px;
  color: #64748b;
}

.dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-highlight {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #ffffff;
  background: #2563eb;
  border: none;
  cursor: pointer;
}

.btn-subtle {
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  color: #475569;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  cursor: pointer;
}

/* NOTES MODAL */
.notes-box {
  width: 580px;
  max-width: 92vw;
  height: 460px;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.dialog-top-simple {
  padding: 18px 22px 12px;
  border-bottom: 1px solid #f1f5f9;
}

.dialog-top-simple h2 {
  margin: 0 0 3px;
  font-size: 15px;
  color: #0f172a;
}

.notes-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
}

.empty-notes {
  padding: 24px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 12.5px;
}

.note-entry {
  display: flex;
  align-items: flex-start;
  position: relative;
}

.note-date {
  width: 80px;
  font-size: 11.5px;
  font-weight: 500;
  color: #64748b;
  flex-shrink: 0;
}

.note-line-col {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 22px;
  flex-shrink: 0;
  align-self: stretch;
}

.note-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid #93c5fd;
  z-index: 2;
  margin-top: 3px;
}

.note-line {
  position: absolute;
  top: 12px;
  bottom: -4px;
  width: 1px;
  background: #e2e8f0;
}

.note-body {
  flex: 1;
  padding-left: 6px;
  padding-bottom: 18px;
}

.note-version-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: #0f172a;
}

.new-tag {
  font-size: 9.5px;
  font-weight: 700;
  background: #ef4444;
  color: #ffffff;
  padding: 1px 5px;
  border-radius: 3px;
}

.note-section {
  margin-top: 5px;
}

.section-label {
  font-size: 10.5px;
  font-weight: 600;
  color: #334155;
  text-transform: uppercase;
}

.section-list {
  margin: 0;
  padding-left: 14px;
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}

.notes-bottom {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 22px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

/* PROGRESS */
.progress-box {
  text-align: center;
  padding: 32px 24px;
}

.spinner-ring {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

.progress-title {
  margin: 0 0 3px;
  font-size: 15px;
  color: #0f172a;
}

.progress-subtitle {
  font-size: 11.5px;
  color: #64748b;
  margin: 0 0 12px;
}

.progress-percentage {
  font-size: 13px;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 6px;
}

.progress-bar-bg {
  width: 100%;
  height: 6px;
  background: #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-bar-val {
  height: 100%;
  background: #2563eb;
  transition: width 0.15s ease;
}

.btn-cancel {
  background: transparent;
  border: 1px solid #cbd5e1;
  color: #64748b;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 11.5px;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #f1f5f9;
  color: #1e293b;
}

/* SUCCESS */
.success-box {
  text-align: center;
  padding: 30px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.success-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #ecfdf5;
  border: 2px solid #a7f3d0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.success-check {
  color: #059669;
  font-size: 20px;
  font-weight: bold;
}

.text-xl {
  font-size: 16px;
}

.mt-4 {
  margin-top: 14px;
}
</style>
