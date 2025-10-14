export interface ServiceSummary {
  name: string;
  title: string;
  description: string | null;
  tags: string[];
  available: boolean;
  running: boolean;
  port: number | null;
  links: {
    label: string;
    url: string;
    kind: string;
  }[];
  log_path: string | null;
  supports: {
    start: boolean;
    stop: boolean;
    logs: boolean;
    terminal: boolean;
  };
}

export interface ServiceDetail {
  name: string;
  meta: {
    title: string;
    description: string | null;
    tags: string[];
    links: {
      label: string;
      url: string;
      kind: string;
    }[];
  };
  status: {
    available: boolean;
    running: boolean;
    health: {
      http?: {
        url: string;
        timeout: number;
      };
      tcp?: {
        host: string;
        port: number;
        timeout: number;
      };
    };
    log_path: string | null;
    port: number | null;
  };
  lifecycle: {
    has_start: boolean;
    has_stop: boolean;
    systemd_unit: string | null;
    pid_file: string | null;
    start_timeout: number;
    stop_timeout: number;
  };
}