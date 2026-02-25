import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // target: 'https://uu863331-bf26-3308ab9a.bjb2.seetacloud.com:8443',
        target: 'http://192.168.150.33:6008',
        changeOrigin: true,
      }
    }
  }
})
