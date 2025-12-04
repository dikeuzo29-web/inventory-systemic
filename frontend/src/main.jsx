// frontend/src/main.jsx

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
// 1. Import Workbox
import { Workbox } from 'workbox-window'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// 2. Register Service Worker
if ('serviceWorker' in navigator) {
  // We use the direct path because this runs in the browser
  const wb = new Workbox('/static/frontend/sw.js');

  wb.register();
}
