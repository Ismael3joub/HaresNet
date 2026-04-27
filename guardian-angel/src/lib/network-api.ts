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
