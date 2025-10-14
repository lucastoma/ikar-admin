<template>
  <div>
    <h2>Web Terminal</h2>
    <div id="terminal-container" ref="terminalContainer"></div>
    <div id="terminal-status" :style="{ color: statusColor }">{{ status }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import 'xterm/css/xterm.css';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';

const terminalContainer = ref(null);
const status = ref('Connecting...');
const statusColor = ref('#8b949e');
let term;
let ws;
let fitAddon;
let resizeHandler;

onMounted(() => {
  if (process.client) {
    const config = useRuntimeConfig();
    const publicConfig = (config && config.public) || {};
    const apiBase =
      typeof publicConfig.apiBase === 'string' && publicConfig.apiBase.length > 0
        ? publicConfig.apiBase
        : '/ikaros';
    const apiOrigin =
      typeof publicConfig.apiOrigin === 'string' && publicConfig.apiOrigin.length > 0
        ? publicConfig.apiOrigin
        : window.location.origin;

    const buildWsUrl = () => {
      try {
        const origin = new URL(apiOrigin);
        origin.protocol = origin.protocol === 'https:' ? 'wss:' : 'ws:';
        const base = apiBase.endsWith('/') ? apiBase.slice(0, -1) : apiBase;
        return `${origin.origin}${base}/ws/pty`;
      } catch (err) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const base = apiBase.startsWith('/') ? apiBase : `/${apiBase}`;
        return `${wsProtocol}://${window.location.host}${base}/ws/pty`;
      }
    };

    term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
      },
    });

    fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(terminalContainer.value);
    fitAddon.fit();

    resizeHandler = () => fitAddon.fit();
    window.addEventListener('resize', resizeHandler);

    const wsUrl = buildWsUrl();
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      status.value = 'Connected';
      statusColor.value = '#238636';
      term.focus();
      fitAddon.fit();
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onclose = () => {
      status.value = 'Connection closed';
      statusColor.value = '#da3633';
      term.write('\r\n\nConnection closed.\r\n');
    };

    ws.onerror = () => {
      status.value = 'WebSocket error';
      statusColor.value = '#da3633';
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });
  }
});

onUnmounted(() => {
  if (ws) {
    ws.close();
  }
  if (term) {
    term.dispose();
  }
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
  }
});
</script>

<style scoped>
#terminal-container {
  border: 1px solid #30363d;
  margin-top: 20px;
  min-height: 400px;
}
#terminal-status {
  margin-top: 8px;
  font-size: 0.9em;
}
</style>
