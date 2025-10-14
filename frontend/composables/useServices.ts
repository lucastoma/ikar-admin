import type { ServiceSummary } from '~/types';

export const useServices = () => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;

  return useFetch<{ services: ServiceSummary[] }>(`${apiBase}/services`, {
    key: 'services',
    transform: (data) => data.services,
    server: false,
  });
};