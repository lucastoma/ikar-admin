<template>
  <div>
    <h2>ComfyUI Config</h2>
    <div class="meta" v-if="configPath">Config: {{ configPath }}</div>
    <div class="actions">
      <button @click="doValidate">Validate</button>
      <button @click="doInstall">Install/Repair Symlink</button>
    </div>
    <div class="content">
      <div>
        <h3>Current YAML</h3>
        <pre class="code-block">{{ rawConfig }}</pre>
      </div>
      <div>
        <h3>Validation</h3>
        <pre class="code-block">{{ validationResult }}</pre>
      </div>
    </div>
    <div v-if="toast.message" :class="['toast', toast.type]">{{ toast.message }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const { getRawConfig, validateConfig, installConfig } = useComfy();

const rawConfig = ref('');
const configPath = ref('');
const validationResult = ref('(not validated)');
const toast = ref({ message: '', type: '' });

const showToast = (message, type = 'success') => {
  toast.value = { message, type };
  setTimeout(() => {
    toast.value = { message: '', type: '' };
  }, 3000);
};

const loadRawConfig = async () => {
  try {
    const { text, path } = await getRawConfig();
    rawConfig.value = text || '(empty)';
    configPath.value = path;
  } catch (err) {
    rawConfig.value = '(failed to load config)';
    configPath.value = '';
    showToast('Failed to load raw config.', 'error');
  }
};

const doValidate = async () => {
  try {
    const result = await validateConfig();
    const lines = [
      `config: ${result.config_path}`,
      `present: ${result.present.length}`,
      ...result.present.map(p => `  ✓ ${p}`),
      `missing: ${result.missing.length}`,
      ...result.missing.map(p => `  ✗ ${p}`),
    ];
    validationResult.value = lines.join('\n');
  } catch (err) {
    validationResult.value = '(validation failed)';
    showToast('Failed to validate config.', 'error');
  }
};

const doInstall = async () => {
  try {
    const result = await installConfig();
    if (result.ok) {
      showToast('Install successful!');
      await loadRawConfig();
      await doValidate();
    } else {
      showToast(result.error || 'Install failed.', 'error');
    }
  } catch (err) {
    showToast('Failed to run install.', 'error');
  }
};

onMounted(async () => {
  await loadRawConfig();
  await doValidate();
});
</script>

<style scoped>
.meta {
  font-size: 0.9em;
  color: #8b949e;
  margin-bottom: 1rem;
}
.actions {
  display: flex;
  gap: 8px;
  margin-bottom: 1rem;
}
button {
  background-color: #21262d;
  color: #c9d1d9;
  border: 1px solid #30363d;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.code-block {
  white-space: pre-wrap;
  word-break: break-all;
  background: #010409;
  padding: 10px;
  border: 1px solid #30363d;
  border-radius: 6px;
  min-height: 200px;
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
