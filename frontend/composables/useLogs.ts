import { ref, onUnmounted, watch } from 'vue';

export const useLogs = (source: Ref<string>, n = 500) => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;
  const logs = ref<string>('');
  const error = ref<Error | null>(null);
  const polling = ref(true);

  let intervalId: NodeJS.Timeout | null = null;

  const getUrl = () => {
    const src = source.value;
    if (src === 'events') {
      return `${apiBase}/events?n=${n}`;
    }
    return `${apiBase}/logs/${src}?n=${n}`;
  };

  const fetchLogs = async () => {
    if (!polling.value) return;
    try {
      const url = getUrl();
      const response = await $fetch<string>(url, { responseType: 'text' });
      logs.value = response;
      error.value = null;
    } catch (err) {
      error.value = err as Error;
    }
  };

  const startPolling = (interval = 4000) => {
    stopPolling();
    fetchLogs();
    intervalId = setInterval(fetchLogs, interval);
  };

  const stopPolling = () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };

  const togglePolling = () => {
    polling.value = !polling.value;
  };

  watch(source, () => {
    logs.value = '';
    fetchLogs();
  });

  onUnmounted(() => {
    stopPolling();
  });

  return { logs, error, polling, startPolling, stopPolling, togglePolling, fetchLogs };
};