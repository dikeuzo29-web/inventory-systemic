// frontend/vite.config.js

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  // Configure the base path for static assets, essential for Django serving
  // It tells Vite the files will be served from /static/frontend/
  base: '/static/frontend/', 

  plugins: [
    react(), // Required for React projects
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      
      // Configuration for the Service Worker (sw.js)
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}'],
        // The sw.js file must be located where Django can serve it
        swDest: '../static/frontend/sw.js',
      },

      // Configuration for the Web Manifest
      manifest: {
        name: 'Inventory System',
        short_name: 'Inventory',
        description: 'Your new modern inventory system.',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
    }),
  ],

  // Tell Vite to output the final built files into the Django static-friendly folder
  build: {
    // Output directory is relative to the project root (../static/frontend)
    outDir: '../static/frontend', 
    emptyOutDir: true,
    // Force consistent filenames
    rollupOptions: {
      output: {
        entryFileNames: 'assets/index.js',  // Forces "index.js"
        chunkFileNames: 'assets/[name].js', 
        assetFileNames: 'assets/[name].[ext]', // Forces "index.css"
      }
    }
  },
})
