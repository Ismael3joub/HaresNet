import axios from 'axios';

export const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await api.post('/auth/login', { username, password });
    return response.data;
  },
  verify2fa: async (code: string, tempToken: string) => {
    const response = await api.post('/auth/verify-2fa', { code }, {
      headers: { Authorization: `Bearer ${tempToken}` },
    });
    return response.data;
  },
  status: async () => {
    const response = await api.get('/auth/status');
    return response.data;
  },
  changePassword: async (currentPassword: string, newPassword: string) => {
    const response = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
  updateProfile: async (data: {
    current_password: string;
    username?: string;
    new_password?: string;
  }) => {
    const response = await api.put('/auth/update-profile', data);
    return response.data;
  },
  logout: async () => {
    const response = await api.post('/auth/logout');
    localStorage.removeItem('access_token');
    return response.data;
  },
  forgotPassword: async (username: string) => {
    const response = await api.post('/auth/forgot-password', { username });
    return response.data;
  },
  resetPassword: async (code: string, newPassword: string) => {
    const response = await api.post('/auth/reset-password', { code, new_password: newPassword });
    return response.data;
  },
  verifyResetCode: async (code: string) => {
    const response = await api.post('/auth/verify-reset-code', { code });
    return response.data;
  },
};

// Devices API
export const devicesApi = {
  getAll: async (group?: string, blocked?: boolean) => {
    const params = new URLSearchParams();
    if (group) params.append('group', group);
    if (blocked !== undefined) params.append('blocked', String(blocked));
    const response = await api.get(`/devices?${params.toString()}`);
    return response.data;
  },
  getOne: async (id: number) => {
    const response = await api.get(`/devices/${id}`);
    return response.data;
  },
  update: async (id: number, data: { label?: string; group?: string; child_safe?: boolean }) => {
    const response = await api.put(`/devices/${id}`, data);
    return response.data;
  },
  block: async (id: number) => {
    const response = await api.post(`/devices/${id}/block`);
    return response.data;
  },
  unblock: async (id: number) => {
    const response = await api.post(`/devices/${id}/unblock`);
    return response.data;
  },
  delete: async (id: number) => {
    const response = await api.delete(`/devices/${id}`);
    return response.data;
  },
  getGroups: async () => {
    const response = await api.get('/devices/groups');
    return response.data;
  },
  getTraffic: async (id: number, params?: { hours?: number; aggregate?: string }) => {
    const queryParams = new URLSearchParams();
    if (params?.hours) queryParams.append('hours', String(params.hours));
    if (params?.aggregate) queryParams.append('aggregate', params.aggregate);
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await api.get(`/devices/${id}/traffic${queryString}`);
    return response.data;
  },
  getTrafficRates: async () => {
    const response = await api.get('/devices/traffic/rates');
    return response.data;
  },
  getNetworkTraffic: async (params?: { hours?: number; aggregate?: string }) => {
    const queryParams = new URLSearchParams();
    if (params?.hours) queryParams.append('hours', String(params.hours));
    if (params?.aggregate) queryParams.append('aggregate', params.aggregate);
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await api.get(`/devices/traffic/network${queryString}`);
    return response.data;
  },
  getTopDevices: async (params?: { limit?: number; hours?: number; sort_by?: string }) => {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', String(params.limit));
    if (params?.hours) queryParams.append('hours', String(params.hours));
    if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await api.get(`/devices/traffic/top${queryString}`);
    return response.data;
  },
};

// WiFi API
export const wifiApi = {
  getConfig: async () => {
    const response = await api.get('/wifi/config');
    return response.data;
  },
  updateConfig: async (config: {
    ssid?: string;
    password?: string;
    security_mode?: string;
    channel?: number;
    hidden?: boolean;
  }) => {
    const response = await api.put('/wifi/config', config);
    return response.data;
  },
  restart: async () => {
    const response = await api.post('/wifi/restart');
    return response.data;
  },
  getStatus: async () => {
    const response = await api.get('/wifi/status');
    return response.data;
  },
};

// Firewall API
export const firewallApi = {
  getRules: async () => {
    const response = await api.get('/firewall/rules');
    return response.data;
  },
  getStatus: async () => {
    const response = await api.get('/firewall/status');
    return response.data;
  },
  applyRules: async () => {
    const response = await api.post('/firewall/apply');
    return response.data;
  },

};

// Schedules API
export const schedulesApi = {
  getAll: async (deviceId?: number) => {
    const params = deviceId ? `?device_id=${deviceId}` : '';
    const response = await api.get(`/schedules${params}`);
    return response.data;
  },
  create: async (schedule: {
    device_id: number;
    name: string;
    days: string[];
    start_time: string;
    end_time: string;
    action: 'block' | 'allow';
    enabled?: boolean;
  }) => {
    const response = await api.post('/schedules', schedule);
    return response.data;
  },
  update: async (id: number, schedule: Partial<{
    name: string;
    days: string[];
    start_time: string;
    end_time: string;
    action: 'block' | 'allow';
    enabled: boolean;
  }>) => {
    const response = await api.put(`/schedules/${id}`, schedule);
    return response.data;
  },
  delete: async (id: number) => {
    const response = await api.delete(`/schedules/${id}`);
    return response.data;
  },
  toggle: async (id: number) => {
    const response = await api.post(`/schedules/${id}/toggle`);
    return response.data;
  },
};

// System API
export const systemApi = {
  getStatus: async () => {
    const response = await api.get('/system/status');
    return response.data;
  },
  getInterfaces: async () => {
    const response = await api.get('/system/interfaces');
    return response.data;
  },
  getNetworkStats: async () => {
    const response = await api.get('/system/network-stats');
    return response.data;
  },
  runSpeedTest: async () => {
    const response = await api.post('/system/speedtest');
    return response.data;
  },
};

// Settings API
export const settingsApi = {
  getSettings: async () => {
    const response = await api.get('/settings');
    return response.data;
  },
  updateSettings: async (settings: {
    timezone?: string;
    ntfy_topic?: string;
    admin_email?: string;
    two_factor_enabled?: boolean;
  }) => {
    const response = await api.put('/settings', settings);
    return response.data;
  },
  getTimezones: async () => {
    const response = await api.get('/settings/timezones');
    return response.data;
  },
  getBlynkConfig: async () => {
    const response = await api.get('/settings/blynk');
    return response.data;
  },
  updateBlynkConfig: async (config: {
    template_id?: string;
    template_name?: string;
    auth_token?: string;
    enabled?: boolean;
  }) => {
    const response = await api.put('/settings/blynk', config);
    return response.data;
  },
};

// Network API
export const networkApi = {
  scan: async () => {
    const response = await api.get('/network/scan');
    return response.data;
  },
  getConfig: async () => {
    const response = await api.get('/network/config');
    return response.data;
  },
  setMode: async (config: {
    mode: 'router' | 'repeater';
    upstream_ssid?: string;
    upstream_password?: string;
    repeater_ssid?: string;
    repeater_password?: string;
    repeater_security_mode?: string;
    repeater_channel?: number;
    repeater_hidden?: boolean;
  }) => {
    const response = await api.post('/network/mode', config);
    return response.data;
  },
};

// Router API
export const routerApi = {
  getWanConfig: async () => {
    const response = await api.get('/router/wan');
    return response.data;
  },
  updateWanConfig: async (config: {
    mode: 'dhcp' | 'static';
    static_ip?: string;
    gateway?: string;
    subnet_mask?: string;
    dns_primary?: string;
    dns_secondary?: string;
  }) => {
    const response = await api.put('/router/wan', config);
    return response.data;
  },
  getLanConfig: async () => {
    const response = await api.get('/router/lan');
    return response.data;
  },
  updateLanConfig: async (config: {
    ip: string;
    dhcp_enabled: boolean;
    dhcp_start?: string;
    dhcp_end?: string;
    subnet_mask?: string;
  }) => {
    const response = await api.put('/router/lan', config);
    return response.data;
  },
};



// DNS Filter API
export const dnsFilterApi = {
  // Filter Groups
  getGroups: async () => {
    const response = await api.get('/dns_filter/groups');
    return response.data;
  },
  createGroup: async (data: {
    name: string;
    description?: string;
    list_type?: 'blocklist' | 'allowlist';
    source_url?: string;
    enabled?: boolean;
  }) => {
    const response = await api.post('/dns_filter/groups', data);
    return response.data;
  },
  getGroup: async (id: number) => {
    const response = await api.get(`/dns_filter/groups/${id}`);
    return response.data;
  },
  updateGroup: async (id: number, data: any) => {
    const response = await api.put(`/dns_filter/groups/${id}`, data);
    return response.data;
  },
  deleteGroup: async (id: number) => {
    const response = await api.delete(`/dns_filter/groups/${id}`);
    return response.data;
  },

  // Domain Filters
  getFilters: async (params?: { group_id?: number; enabled_only?: boolean; page?: number; per_page?: number }) => {
    const queryParams = new URLSearchParams();
    if (params?.group_id) queryParams.append('group_id', String(params.group_id));
    if (params?.enabled_only) queryParams.append('enabled_only', 'true');
    if (params?.page) queryParams.append('page', String(params.page));
    if (params?.per_page) queryParams.append('per_page', String(params.per_page));
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await api.get(`/dns_filter/filters${queryString}`);
    return response.data;
  },
  createFilter: async (data: {
    group_id: number;
    domain: string;
    pattern_type?: 'exact' | 'wildcard' | 'regex';
    regex_pattern?: string;
    enabled?: boolean;
    blocking_enabled?: boolean;
    reason?: string;
  }) => {
    const response = await api.post('/dns_filter/filters', data);
    return response.data;
  },
  getFilter: async (id: number) => {
    const response = await api.get(`/dns_filter/filters/${id}`);
    return response.data;
  },
  updateFilter: async (id: number, data: any) => {
    const response = await api.put(`/dns_filter/filters/${id}`, data);
    return response.data;
  },
  deleteFilter: async (id: number) => {
    const response = await api.delete(`/dns_filter/filters/${id}`);
    return response.data;
  },

  // Blocklists
  getBlocklists: async () => {
    const response = await api.get('/dns_filter/blocklists');
    return response.data;
  },
  addBlocklist: async (data: {
    name: string;
    url: string;
    category?: string;
    description?: string;
  }) => {
    const response = await api.post('/dns_filter/blocklists', data);
    return response.data;
  },
  addDefaultBlocklists: async () => {
    const response = await api.post('/dns_filter/blocklists/defaults', {});
    return response.data;
  },
  fetchBlocklist: async (id: number) => {
    const response = await api.post(`/dns_filter/blocklists/${id}/fetch`, {});
    return response.data;
  },
  updateAllBlocklists: async () => {
    const response = await api.post('/dns_filter/blocklists/update-all', {});
    return response.data;
  },
  deleteBlocklist: async (id: number) => {
    const response = await api.delete(`/dns_filter/blocklists/${id}`);
    return response.data;
  },

  // DNS Logs
  getLogs: async (params?: {
    page?: number;
    per_page?: number;
    blocked_only?: boolean;
    client_ip?: string;
    domain?: string;
    hours_back?: number;
  }) => {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', String(params.page));
    if (params?.per_page) queryParams.append('per_page', String(params.per_page));
    if (params?.blocked_only) queryParams.append('blocked_only', 'true');
    if (params?.client_ip) queryParams.append('client_ip', params.client_ip);
    if (params?.domain) queryParams.append('domain', params.domain);
    if (params?.hours_back) queryParams.append('hours', String(params.hours_back));
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await api.get(`/dns_filter/logs${queryString}`);
    return response.data;
  },
  cleanupLogs: async (days: number) => {
    const response = await api.post('/dns_filter/logs/cleanup', { days });
    return response.data;
  },

  // Statistics
  getStats: async () => {
    const response = await api.get('/dns_filter/stats');
    return response.data;
  },
  getDomainStats: async (domain: string) => {
    const response = await api.get(`/dns_filter/stats/domain/${domain}`);
    return response.data;
  },
  getTopDomains: async (limit?: number) => {
    const queryString = limit ? `?limit=${limit}` : '';
    const response = await api.get(`/dns_filter/stats/top-domains${queryString}`);
    return response.data;
  },
  getTopClients: async (limit?: number) => {
    const queryString = limit ? `?limit=${limit}` : '';
    const response = await api.get(`/dns_filter/stats/top-clients${queryString}`);
    return response.data;
  },
  getTimeline: async (hours?: number, interval?: number) => {
    const queryParams = new URLSearchParams();
    if (hours) queryParams.append('hours', String(hours));
    if (interval) queryParams.append('interval', String(interval));
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await api.get(`/dns_filter/stats/timeline${queryString}`);
    return response.data;
  },

  // Testing & Configuration
  testFilter: async (domain: string) => {
    const response = await api.get(`/dns_filter/test-filter/${domain}`);
    return response.data;
  },
  applyConfig: async () => {
    const response = await api.post('/dns_filter/config/apply', {});
    return response.data;
  },
};

export default api;

