/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["logo-icon.svg", "logo-full.svg", "logo-white.svg"],
      manifest: {
        name: "Saturna",
        short_name: "Saturna",
        description: "Entregas inteligentes, retiros en segundos",
        lang: "es-BO",
        theme_color: "#0B1445",
        background_color: "#0B1445",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "logo-icon.svg", sizes: "any", type: "image/svg+xml" },
          { src: "logo-icon.svg", sizes: "192x192", type: "image/svg+xml" },
          { src: "logo-icon.svg", sizes: "512x512", type: "image/svg+xml" },
          { src: "logo-icon.svg", sizes: "512x512", type: "image/svg+xml", purpose: "maskable" },
        ],
      },
      workbox: {
        // La app carga sin conexión; las llamadas a la API nunca se cachean (datos siempre frescos).
        navigateFallbackDenylist: [/^\/api/],
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
      },
    }),
  ],
  server: { port: 5173 },
  test: { environment: "node" },
});
