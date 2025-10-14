import { ref, onUnmounted } from 'vue';

export const useStatusPoll = (interval = 4000) => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;
  const statusMap = ref<Record<string, boolean>>({});
  const { data, error, execute } = useFetch<Record<string, boolean>>(`${apiBase}/status`, {
    immediate: false,
    server: false,
  });

  let intervalId: NodeJS.Timeout | null = null;

  const start = () => {
    if (intervalId) return;
    execute();
    intervalId = setInterval(execute, interval);
  };

  const stop = () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };

  watch(data, (newData) => {
    if (newData) {
      statusMap.value = newData;
    }
  });

  onUnmounted(() => {
    stop();
  });

  return { statusMap, error, start, stop };
};