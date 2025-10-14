import type { ServiceDetail } from '~/types';

export const useService = (name: string) => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;
  const url = `${apiBase}/services/${name}`;

  return useFetch<ServiceDetail>(url, {
    key: `service-${name}`,
    server: false,
    baseURL: '',
  });
};
