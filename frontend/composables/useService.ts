import type { ServiceDetail } from '~/types';

export const useService = (name: string) => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;

  return useFetch<ServiceDetail>(`${apiBase}/services/${name}`, {
    key: `service-${name}`,
    server: false,
  });
};