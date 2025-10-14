import { ref, onUnmounted } from 'vue';

export const useStatusPoll = (interval = 4000) => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;
  const statusMap = ref<Record<string, boolean>>({});
  const url = `${apiBase}/status`;
  const { data, error, execute } = useFetch<Record<string, boolean>>(url, {
    immediate: false,
    server: false,
    baseURL: '',
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
