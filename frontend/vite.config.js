import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

export default defineConfig({
  base: '/static/frontend/',        // important for Django static path
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false, // we'll control registration from our React code
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,jpg,svg,json}'],
      },
      manifest: {
        name: 'Inventory App',
        short_name: 'Inventory',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#000000',
        icons: [
          { src: '/static/images/itekton-logo.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      // Use injectManifest to allow custom background sync code in src-sw.js
      srcDir: 'src',
      filename: 'sw.js',
      strategies: 'injectManifest',
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,png,jpg,svg,json}']
      }
    })
  ],
  build: {
    outDir: path.resolve(__dirname, '../static/frontend'),
    emptyOutDir: true,
    manifest: true,
  },
});

