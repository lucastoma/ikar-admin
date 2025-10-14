# Ikaros Frontend

This directory contains the Nuxt 3 frontend for the Ikaros admin panel.

## Development

To start the development server, run:

```bash
npm run dev
```

This will start a development server on `http://localhost:3000/ikaros/ui` with hot-reloading enabled. The Vite proxy is configured to forward API requests from `/ikaros` to the FastAPI backend running at `http://127.0.0.1:8602`.

## Building for Production

To build the application for production, run:

```bash
npm run build
```

This will generate a static version of the application in the `.output/public` directory.

## Deployment

The Nuxt application is served as static files by the FastAPI backend. To deploy a new version:

1.  Build the application: `npm run build`
2.  Copy the contents of `.output/public` to `app/static/nuxt/`.
3.  The FastAPI server will automatically serve the new files from `/ikaros/ui`.

## Design Decisions

*   **Static Site Generation (SSG):** The frontend is a statically generated site (`nitro.preset = 'static'`). This is the most efficient way to serve the application, as it doesn't require a Node.js server in production. The entire UI is rendered in the browser and interacts with the backend via JSON APIs and WebSockets.
*   **Routing Prefix:** The application is served under the `/ikaros/ui` path (`app.baseURL`). This is to avoid conflicts with the existing HTML views, which are served from `/ikaros`. Once the Nuxt frontend has reached feature parity, it can replace the old UI.