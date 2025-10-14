// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  app: {
    baseURL: '/ikaros/ui/',
  },
  nitro: {
    preset: 'static',
  },
  runtimeConfig: {
    public: {
      apiBase: '/ikaros',
    },
  },
  vite: {
    server: {
      proxy: {
        '/ikaros': {
          target: 'http://127.0.0.1:8602',
          changeOrigin: true,
        },
      },
    },
  },
})