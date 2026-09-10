import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:5000", //http://localhost:5000 //"https://yale-books.onrender.com"
        changeOrigin: true,
        secure: false,
      },
      "/login": "http://localhost:5000",
      "/logout": "http://localhost:5000",
      "/login_callback": "http://localhost:5000"
    }
  },
});
