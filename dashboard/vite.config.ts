import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// base: '/dash/' is required so that built asset paths are prefixed with /dash/
// when the app is served behind the NGINX reverse proxy at zksato.zeaz.dev/dash/
export default defineConfig({
  base: '/dash/',
  plugins: [react()],
})
