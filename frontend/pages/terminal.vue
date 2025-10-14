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

onMounted(() => {
  if (process.client) {
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

    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${window.location.host}/ikaros/ws/pty`;
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

    window.addEventListener('resize', () => fitAddon.fit());
  }
});

onUnmounted(() => {
  if (ws) {
    ws.close();
  }
  if (term) {
    term.dispose();
  }
  if (fitAddon) {
    window.removeEventListener('resize', () => fitAddon.fit());
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