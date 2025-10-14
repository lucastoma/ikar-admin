<template>
  <div>
    <h2>Dashboard</h2>
    <div v-if="pending" class="loading">Loading services...</div>
    <div v-else-if="error" class="error-message">Error loading services: {{ error.message }}</div>
    <div v-else class="service-cards">
      <div v-for="service in services" :key="service.name" class="card">
        <div class="card-header">
          <h3>{{ service.title }}</h3>
          <span :class="['status-badge', statusClass(service.name, service.available)]">
            {{ statusLabel(service.name, service.available) }}
          </span>
        </div>
        <p>{{ service.description }}</p>
        <div class="tags">
          <span v-for="tag in service.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
        <div class="card-footer">
          <div class="links">
            <a v-for="link in service.links" :key="link.url" :href="link.url" target="_blank">{{ link.label }}</a>
          </div>
          <div class="actions">
            <button @click="start(service.name)" v-if="service.supports.start" :disabled="isActionInProgress(service.name)">Start</button>
            <button @click="stop(service.name)" v-if="service.supports.stop" :disabled="isActionInProgress(service.name)">Stop</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="toast.message" :class="['toast', toast.type]">{{ toast.message }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const { data: services, pending, error } = useServices();
const { statusMap, start: startPolling, stop: stopPolling } = useStatusPoll();
const { startService, stopService } = useServiceActions();

const actionInProgress = ref({});
const toast = ref({ message: '', type: '' });

const statusLabel = (name, available) => {
  if (!available) return 'MISSING';
  return statusMap.value[name] ? 'UP' : 'DOWN';
};

const statusClass = (name, available) => {
  const label = statusLabel(name, available).toLowerCase();
  return `status-${label}`;
};

const isActionInProgress = (name) => {
  return actionInProgress.value[name];
};

const showToast = (message, type = 'success') => {
  toast.value = { message, type };
  setTimeout(() => {
    toast.value = { message: '', type: '' };
  }, 3000);
};

const handleAction = async (name, action) => {
  actionInProgress.value[name] = true;
  try {
    const response = await action(name);
    if (response.ok) {
      statusMap.value[name] = response.running;
      showToast(`${name}: ${response.message}`, 'success');
    } else {
      showToast(`${name}: ${response.message}`, 'error');
    }
  } catch (err) {
    showToast(`Error performing action on ${name}`, 'error');
  } finally {
    actionInProgress.value[name] = false;
  }
};

const start = (name) => handleAction(name, startService);
const stop = (name) => handleAction(name, stopService);

onMounted(() => {
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.loading, .error-message {
  text-align: center;
  padding: 2rem;
  font-size: 1.2rem;
}
.service-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}
.card {
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 1rem;
  background-color: #161b22;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header h3 {
  margin: 0;
}
.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 600;
  color: #fff;
}
.status-up { background-color: #238636; }
.status-down { background-color: #da3633; }
.status-missing { background-color: #8b949e; }
.tags {
  margin-top: 0.5rem;
}
.tag {
  display: inline-block;
  background-color: #30363d;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8em;
  margin-right: 0.5rem;
}
.card-footer {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.links a {
  color: #58a6ff;
  text-decoration: none;
}
.links a:hover {
  text-decoration: underline;
}
.actions button {
  background-color: #21262d;
  color: #c9d1d9;
  border: 1px solid #30363d;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.actions button:hover:not(:disabled) {
  background-color: #30363d;
}
.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  color: #fff;
  padding: 1rem;
  border-radius: 6px;
}
.toast.success {
  background-color: #238636;
}
.toast.error {
  background-color: #da3633;
}
</style>