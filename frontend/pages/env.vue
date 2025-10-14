<template>
  <div>
    <h2>Environment Variables</h2>
    <div class="env-controls">
      <div class="chip-container">
        <span v-for="(prefix, index) in prefixes" :key="index" class="chip">
          {{ prefix }}
          <button @click="removePrefix(index)">&times;</button>
        </span>
      </div>
      <div class="input-group">
        <input type="text" v-model="newPrefix" @keydown.enter="addPrefix" placeholder="Add prefix (e.g. DATA_)">
        <button @click="addPrefix">Add</button>
      </div>
    </div>
    <table class="env-table">
      <thead>
        <tr>
          <th>Key</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(value, key) in sortedEnvVars" :key="key">
          <td>{{ key }}</td>
          <td>{{ maskedValue(key, value) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-if="error" class="error-toast">{{ error.message }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';

const prefixes = ref([]);
const newPrefix = ref('');
const { envVars, error, fetchEnv } = useEnv(prefixes);

const sortedEnvVars = computed(() => {
  return Object.entries(envVars.value)
    .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
    .reduce((obj, [key, value]) => {
      obj[key] = value;
      return obj;
    }, {});
});

const maskedValue = (key, value) => {
  const lowerKey = key.toLowerCase();
  if (lowerKey.includes('secret') || lowerKey.endsWith('key') || lowerKey.includes('token') || lowerKey.includes('password')) {
    return '••••••';
  }
  return value;
};

const loadPrefixes = () => {
  const stored = localStorage.getItem('ikar-env-prefixes');
  if (stored) {
    prefixes.value = JSON.parse(stored);
  } else {
    prefixes.value = ["DATA_", "COMFYUI_", "IKAR_", "FILEBROWSER_", "CODE_SERVER_", "COMFYUI_PORT"];
  }
};

const savePrefixes = () => {
  localStorage.setItem('ikar-env-prefixes', JSON.stringify(prefixes.value));
};

const addPrefix = () => {
  const prefix = newPrefix.value.trim();
  if (prefix && !prefixes.value.includes(prefix)) {
    prefixes.value.push(prefix);
    savePrefixes();
    fetchEnv();
  }
  newPrefix.value = '';
};

const removePrefix = (index) => {
  prefixes.value.splice(index, 1);
  savePrefixes();
  fetchEnv();
};

onMounted(() => {
  loadPrefixes();
});
</script>

<style scoped>
.env-controls {
  background: #161b22;
  border: 1px solid #30363d;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}
.chip-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 1rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #30363d;
  color: #c9d1d9;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.85em;
}
.chip button {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 1.2em;
  padding: 0;
  line-height: 1;
}
.input-group {
  display: flex;
  gap: 8px;
}
input[type=text] {
  flex: 1;
  background-color: #0d1117;
  color: #c9d1d9;
  border: 1px solid #30363d;
  padding: 5px 8px;
  border-radius: 6px;
}
button {
  background-color: #21262d;
  color: #c9d1d9;
  border: 1px solid #30363d;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.env-table {
  width: 100%;
  border-collapse: collapse;
}
.env-table th, .env-table td {
  border: 1px solid #30363d;
  padding: 10px 14px;
  text-align: left;
}
.env-table th {
  background-color: #161b22;
}
.env-table td:last-child {
  word-break: break-all;
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