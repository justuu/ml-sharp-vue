import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://cfjtbv1gf9ht37zf-6008.container.x-gpu.com',
        // target: 'http://192.168.150.33:6008',
        changeOrigin: true,
      }
    }
  }
})
