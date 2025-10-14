export const useComfy = () => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;

  const getRawConfig = async () => {
    const response = await $fetch.raw(`${apiBase}/comfy/config/raw`);
    return {
      text: await response.text(),
      path: response.headers.get('x-config-path'),
    };
  };

  const validateConfig = async () => {
    return await $fetch<{
      ok: boolean;
      config_path: string;
      present: string[];
      missing: string[];
    }>(`${apiBase}/comfy/config/validate`);
  };

  const installConfig = async () => {
    return await $fetch<{ ok: boolean; error?: string }>(`${apiBase}/comfy/config/install`, {
      method: 'POST',
    });
  };

  return { getRawConfig, validateConfig, installConfig };
};