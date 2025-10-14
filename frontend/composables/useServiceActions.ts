export const useServiceActions = () => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;

  const startService = async (name: string) => {
    try {
      const response = await $fetch<{ ok: boolean; message: string; running: boolean }>(
        `${apiBase}/start/${name}`,
        {
          method: 'POST',
        }
      );
      return response;
    } catch (error) {
      console.error(`Error starting service ${name}:`, error);
      throw error;
    }
  };

  const stopService = async (name: string) => {
    try {
      const response = await $fetch<{ ok: boolean; message: string; running: boolean }>(
        `${apiBase}/stop/${name}`,
        {
          method: 'POST',
        }
      );
      return response;
    } catch (error) {
      console.error(`Error stopping service ${name}:`, error);
      throw error;
    }
  };

  return { startService, stopService };
};