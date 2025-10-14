export const useEnv = (prefixes: Ref<string[]>) => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;
  const envVars = ref<Record<string, string>>({});
  const error = ref<Error | null>(null);

  const fetchEnv = async () => {
    try {
      const url = new URL(`${apiBase}/env.json`, 'http://localhost');
      if (prefixes.value.length > 0) {
        url.searchParams.set('prefix', prefixes.value.join(','));
      }
      const data = await $fetch<Record<string, string>>(url.pathname + url.search, { baseURL: '' });
      envVars.value = data;
      error.value = null;
    } catch (err) {
      error.value = err as Error;
    }
  };

  watch(prefixes, fetchEnv, { deep: true, immediate: true });

  return { envVars, error, fetchEnv };
};
