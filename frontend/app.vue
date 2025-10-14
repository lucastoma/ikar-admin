<template>
  <div class="app-container">
    <header class="app-header">
      <h1>ikar-admin</h1>
      <nav>
        <NuxtLink to="/">Dashboard</NuxtLink>
        <NuxtLink to="/logs">Logs</NuxtLink>
        <NuxtLink to="/env">Env</NuxtLink>
        <NuxtLink to="/terminal">Terminal</NuxtLink>
        <NuxtLink to="/comfy">Comfy</NuxtLink>
      </nav>
    </header>
    <main class="app-main">
      <NuxtPage />
    </main>
  </div>
</template>

<style>
:root {
  --bg-color: #0d1117;
  --text-color: #c9d1d9;
  --border-color: #30363d;
  --accent-color: #58a6ff;
  --header-bg: #161b22;
  --status-up: #238636;
  --status-down: #da3633;
  --status-missing: #8b949e;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
  background-color: var(--bg-color);
  color: var(--text-color);
  margin: 0;
  padding: 0;
}
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.app-header {
  background-color: var(--header-bg);
  border-bottom: 1px solid var(--border-color);
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.app-header h1 {
  margin: 0;
  font-size: 1.5em;
}
nav {
  display: flex;
  gap: 1rem;
}
nav a {
  color: var(--text-color);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
}
nav a.router-link-active {
  background-color: var(--accent-color);
  color: var(--bg-color);
  font-weight: 600;
}
.app-main {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>