// https://nuxt.com/docs/api/configuration/nuxt-config
const backendHost = process.env.IKAR_ADMIN_HOST || '127.0.0.1';
const backendPort = process.env.IKAR_ADMIN_PORT || '8610';
const backendProtocol = process.env.IKAR_ADMIN_PROTO || 'http';
const backendTarget = process.env.IKAR_ADMIN_BACKEND || `${backendProtocol}://${backendHost}:${backendPort}`;

export default defineNuxtConfig({
  devtools: { enabled: true },
  // Set explicit compatibility date to silence Nitro warning
  // and ensure deterministic behavior across environments.
  compatibilityDate: '2025-10-14',
  app: {
    baseURL: '/ikaros/ui/',
  },
  nitro: {
    preset: 'static',
  },
  runtimeConfig: {
    public: {
      // API prefix used by the backend (FastAPI)
      apiBase: '/ikaros',
      // Absolute backend origin used by client fetches (and SSR-safe)
      apiOrigin: backendTarget,
    },
  },
  vite: {
    server: {
      proxy: {
        // Proxy backend requests while leaving the Nuxt app at /ikaros/ui served by Vite.
        // Exclude /ikaros/ui (and its subpaths) from proxying to avoid the "Not Found" issue.
        '^/ikaros(?!/ui(?:/|$))': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  },
})
