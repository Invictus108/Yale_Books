import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import axios from 'axios'
import { API_URL } from './config'

// configure axios
axios.defaults.withCredentials = true;
axios.defaults.baseURL = API_URL;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
