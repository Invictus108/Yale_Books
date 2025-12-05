import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "https://yale-books.onrender.com", //http://localhost:5000
        changeOrigin: true,
        secure: false,
      },
      "/login": "https://yale-books.onrender.com",
      "/logout": "https://yale-books.onrender.com",
      "/login_callback": "https://yale-books.onrender.com"
    }
  },
});
