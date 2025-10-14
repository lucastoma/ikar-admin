<template>
  <div>
    <h2>Logs</h2>
    <div class="log-controls">
      <select v-model="selectedSource">
        <option value="events">Events</option>
        <option v-for="service in services" :key="service.name" :value="service.name">
          {{ service.title }}
        </option>
      </select>
      <input type="text" v-model="filter" placeholder="Filter logs...">
      <button @click="togglePolling">{{ polling ? 'Pause' : 'Resume' }}</button>
    </div>
    <pre class="log-output">{{ filteredLogs }}</pre>
    <div v-if="error" class="error-toast">{{ error.message }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const { data: services } = useServices();
const selectedSource = ref('events');
const filter = ref('');

const { logs, error, polling, startPolling, stopPolling, togglePolling } = useLogs(selectedSource);

const filteredLogs = computed(() => {
  if (!filter.value) {
    return logs.value;
  }
  const filterText = filter.value.toLowerCase();
  return logs.value
    .split('\n')
    .filter(line => line.toLowerCase().includes(filterText))
    .join('\n');
});

onMounted(() => {
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.log-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  margin-bottom: 1rem;
}
select, input[type=text], button {
  background-color: #0d1117;
  color: #c9d1d9;
  border: 1px solid #30363d;
  padding: 5px 8px;
  border-radius: 6px;
}
.log-output {
  white-space: pre-wrap;
  word-break: break-all;
  background: #010409;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #30363d;
  min-height: 400px;
}
.error-toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #da3633;
  color: #fff;
  padding: 1rem;
  border-radius: 6px;
}
</style>