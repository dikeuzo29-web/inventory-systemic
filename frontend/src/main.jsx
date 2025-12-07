// frontend/src/main.jsx

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './style.css';
import { Workbox } from 'workbox-window';

const root = createRoot(document.getElementById('root'));
root.render(<App />);

// service worker registration using workbox-window
if ('serviceWorker' in navigator) {
  const wb = new Workbox('/static/sw.js');
  wb.addEventListener('controlling', () => {
    // When a new SW takes control
    window.location.reload();
  });

   // Detect new versions waiting to activate
  wb.addEventListener('waiting', () => {
    console.log('A new service worker is waiting to activate.');
    wb.messageSW({ type: 'SKIP_WAITING' });
  });

  wb.register();
}

