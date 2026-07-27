import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(async () => ({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  clearScreen: false,
  
  server: {
    port: 1420,
    strictPort: true,
    host: true,
    // Added this watch block to fix the Windows EBUSY error
    watch: {
      ignored: ["**/src-tauri/**"],
    }
  }
}));