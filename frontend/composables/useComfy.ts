type ValidationResponse = {
  ok: boolean;
  config_path: string;
  present: string[];
  missing: string[];
};

type InstallResponse = {
  ok: boolean;
  error?: string;
  config_path?: string;
};

const stripTrailingSlash = (value: string): string =>
  value.endsWith('/') ? value.slice(0, -1) : value;

const ensureLeadingSlash = (value: string): string =>
  value.startsWith('/') ? value : `/${value}`;

export const useComfy = () => {
  const config = useRuntimeConfig();
  const publicConfig = (config && config.public) || {};

  const resolvedBase =
    typeof publicConfig.apiBase === 'string' && publicConfig.apiBase.length > 0
      ? publicConfig.apiBase
      : '/ikaros';
  const resolvedOrigin =
    typeof publicConfig.apiOrigin === 'string' && publicConfig.apiOrigin.length > 0
      ? publicConfig.apiOrigin
      : '';
  const isDev = process.dev === true;

  const buildPath = (suffix: string): string => {
    const baseNormalized = stripTrailingSlash(resolvedBase);
    const suffixNormalized = ensureLeadingSlash(suffix);
    if (/^https?:\/\//i.test(baseNormalized)) {
      return `${stripTrailingSlash(baseNormalized)}${suffixNormalized}`;
    }
    return `${baseNormalized}${suffixNormalized}`;
  };

  const buildUrl = (suffix: string): string => {
    const candidate = buildPath(suffix);
    if (/^https?:\/\//i.test(candidate) || isDev) {
      return candidate;
    }
    if (!resolvedOrigin) {
      return candidate;
    }
    try {
      return new URL(candidate, resolvedOrigin).toString();
    } catch {
      return `${stripTrailingSlash(resolvedOrigin)}${candidate}`;
    }
  };

  const fetchText = async (suffix: string): Promise<{ text: string; path: string }> => {
    const response = await fetch(buildUrl(suffix), { credentials: 'same-origin' });
    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }
    const text = await response.text();
    return {
      text,
      path: response.headers.get('x-config-path') ?? '',
    };
  };

  const fetchJson = async <T>(suffix: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(buildUrl(suffix), {
      credentials: 'same-origin',
      ...init,
    });
    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }
    return (await response.json()) as T;
  };

  const getRawConfig = async () => fetchText('/comfy/config/raw');

  const validateConfig = async () =>
    fetchJson<ValidationResponse>('/comfy/config/validate');

  const installConfig = async () =>
    fetchJson<InstallResponse>('/comfy/config/install', { method: 'POST' });

  return { getRawConfig, validateConfig, installConfig };
};
