export const API_URL = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? 'https://yale-books.onrender.com' : 'http://localhost:5000')
).replace(/\/$/, '');
