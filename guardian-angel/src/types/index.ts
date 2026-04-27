export interface Device {
  id: number;
  mac: string;
  ip: string;
  hostname?: string;
  vendor?: string;
  label?: string;
  group?: string;
  blocked: boolean;
  first_seen: string;
  last_seen: string;
  is_online?: boolean;
  child_safe?: boolean;
  traffic_limit_daily_mb?: number;
  traffic_limit_hourly_mb?: number;
  blocked_services?: number[];
}

export interface Schedule {
  id: number;
  device_id: number;
  name: string;
  days: string[];
  start_time: string;
  end_time: string;
  action: 'block' | 'allow';
  enabled: boolean;
  created_at: string;
}

export interface WiFiConfig {
  ssid: string;
  password: string;
  security_mode: string;
  channel: number;
  hidden: boolean;
}

export interface SystemStatus {
  cpu: {
    percent: number;
    count: number;
  };
  memory: {
    total: number;
    available: number;
    percent: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    percent: number;
  };
  uptime: number;
}

export interface NetworkInterface {
  name: string;
  ipv4: string | null;
  mac: string | null;
  is_up: boolean;
  speed: number;
}

export interface NetworkStats {
  bytes_sent: number;
  bytes_recv: number;
  packets_sent: number;
  packets_recv: number;
  errin: number;
  errout: number;
  dropin: number;
  dropout: number;
}

export interface FirewallRule {
  id: number;
  type: 'block' | 'allow';
  target: string;
  description: string;
  active: boolean;
}
