<template>
  <div class="about-container">
    <h2>The Athenaeum</h2>
    <p><strong>Created by:</strong> Aura</p>
    <p><strong>Version:</strong> v{{ appVersion }}</p>
    <p><strong>Copyright:</strong> &copy; 2026 Aura. All rights reserved.</p>

    <hr class="divider" />

    <button @click="checkForUpdates" :disabled="isChecking" class="update-btn">
      {{ isChecking ? 'Checking for updates...' : 'Check for Updates' }}
    </button>
    
    <p v-if="updateMessage" class="update-status">{{ updateMessage }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { getVersion } from '@tauri-apps/api/app';
import { check } from '@tauri-apps/plugin-updater';

const appVersion = ref('Loading...');
const isChecking = ref(false);
const updateMessage = ref('');

onMounted(async () => {
  // Automatically grab the version you set in tauri.conf.json
  appVersion.value = await getVersion();
});

const checkForUpdates = async () => {
  isChecking.value = true;
  updateMessage.value = 'Searching the archive...';
  
  try {
    const update = await check();
    
    if (update) {
      updateMessage.value = `Version ${update.version} found! Downloading and installing...`;
      await update.downloadAndInstall();
      updateMessage.value = 'Update installed successfully! Please close and reopen the app to apply changes.';
    } else {
      updateMessage.value = 'You are currently running the latest version.';
    }
  } catch (error) {
    console.error('Update check failed:', error);
    updateMessage.value = 'Unable to check for updates right now. Please ensure you are connected to the internet.';
  } finally {
    isChecking.value = false;
  }
};
</script>

<style scoped>
.about-container {
  padding: 30px;
  text-align: center;
  max-width: 500px;
  margin: 0 auto;
}

.divider {
  margin: 20px 0;
  border: 0;
  border-top: 1px solid #ccc;
}

.update-btn {
  padding: 10px 20px;
  font-size: 16px;
  cursor: pointer;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
}

.update-btn:disabled {
  background-color: #9e9e9e;
  cursor: not-allowed;
}

.update-status {
  margin-top: 15px;
  font-weight: bold;
  color: #333;
}
</style>