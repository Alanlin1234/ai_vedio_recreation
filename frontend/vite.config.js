import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  // SWC 处理 JSX + Fast Refresh，不依赖 @babel/core（plugin-react 在 dev 下仍会为 react-refresh 调 Babel）
  plugins: [react()],
  // PostCSS 见 postcss.config.cjs（Tailwind + autoprefixer）
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
