import type { ServiceSummary } from '~/types';

export const useServices = () => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;
  const url = `${apiBase}/services`;

  return useFetch<{ services: ServiceSummary[] }>(url, {
    key: 'services',
    transform: (data) => data.services,
    server: false,
    baseURL: '',
  });
};
