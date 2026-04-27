import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { devicesApi } from '@/lib/api';
import { Loader2 } from 'lucide-react';
import { Device } from "@/types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';

interface DeviceActivityChartProps {
    device: Device;
    height?: number | string;
}

export function DeviceActivityChart({ device, height = 400 }: DeviceActivityChartProps) {
    const [hours, setHours] = useState(24);
    const [aggregate, setAggregate] = useState('5m');

    const { data: trafficData, isLoading } = useQuery({
        queryKey: ['device-traffic', device?.id, hours, aggregate],
        queryFn: () => device ? devicesApi.getTraffic(device.id, { hours, aggregate }) : Promise.resolve({ traffic: [] }),
        enabled: !!device,
        refetchInterval: 30000 // Update every 30 seconds
    });

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const formatAxisBytes = (bytes: number) => {
        if (bytes === 0) return '0';
        const k = 1024;
        const sizes = ['B', 'K', 'M', 'G'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + sizes[i];
    };

    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    // Process data for chart - filter out noise below 10KB
    const minThreshold = 10 * 1024; // 10KB in bytes
    const data = trafficData?.traffic?.map((t: any) => ({
        time: formatTime(t.timestamp),
        upload: t.upload > minThreshold ? t.upload : 0,
        download: t.download > minThreshold ? t.download : 0,
        fullTimestamp: t.timestamp
    })) || [];

    // Use a FIXED scale to prevent scrolling - always 0 to 100MB
    const maxValue = 100 * 1024 * 1024; // Fixed 100MB scale

    if (isLoading) {
        return (
            <div className="flex items-center justify-center w-full min-h-[300px]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className="space-y-4">
                {/* Controls */}
                <div className="flex gap-2 justify-end">
                    <Select value={String(hours)} onValueChange={(v) => setHours(Number(v))}>
                        <SelectTrigger className="w-[120px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="1">Last Hour</SelectItem>
                            <SelectItem value="6">Last 6 Hours</SelectItem>
                            <SelectItem value="24">Last 24 Hours</SelectItem>
                            <SelectItem value="48">Last 2 Days</SelectItem>
                            <SelectItem value="168">Last Week</SelectItem>
                        </SelectContent>
                    </Select>
                    <Select value={aggregate} onValueChange={setAggregate}>
                        <SelectTrigger className="w-[100px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="1m">1 min</SelectItem>
                            <SelectItem value="5m">5 min</SelectItem>
                            <SelectItem value="15m">15 min</SelectItem>
                            <SelectItem value="1h">1 hour</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex flex-col items-center justify-center min-h-[300px] text-muted-foreground">
                    <p>No traffic data available for this device.</p>
                    <p className="text-sm mt-2">Data will appear after the device transmits traffic.</p>
                    <p className="text-xs mt-1 text-muted-foreground/60">Try browsing the internet from {device.hostname || device.mac}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Controls */}
            <div className="flex gap-2 justify-end">
                <Select value={String(hours)} onValueChange={(v) => setHours(Number(v))}>
                    <SelectTrigger className="w-[120px]">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="1">Last Hour</SelectItem>
                        <SelectItem value="6">Last 6 Hours</SelectItem>
                        <SelectItem value="24">Last 24 Hours</SelectItem>
                        <SelectItem value="48">Last 2 Days</SelectItem>
                        <SelectItem value="168">Last Week</SelectItem>
                    </SelectContent>
                </Select>
                <Select value={aggregate} onValueChange={setAggregate}>
                    <SelectTrigger className="w-[100px]">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="1m">1 min</SelectItem>
                        <SelectItem value="5m">5 min</SelectItem>
                        <SelectItem value="15m">15 min</SelectItem>
                        <SelectItem value="1h">1 hour</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/20">
                    <p className="text-xs text-muted-foreground">Total Upload</p>
                    <p className="text-lg font-bold text-black dark:text-white">{trafficData?.summary?.total_upload_formatted || '0 B'}</p>
                </div>
                <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950/20">
                    <p className="text-xs text-muted-foreground">Total Download</p>
                    <p className="text-lg font-bold text-black dark:text-white">{trafficData?.summary?.total_download_formatted || '0 B'}</p>
                </div>
            </div>

            {/* Chart with fixed height */}
            <div style={{ width: '100%', height: '280px' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                        data={data}
                        margin={{
                            top: 10,
                            right: 10,
                            left: 0,
                            bottom: 0,
                        }}
                    >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                            dataKey="time"
                            minTickGap={30}
                            tick={{ fontSize: 12 }}
                        />
                        <YAxis
                            tickFormatter={formatAxisBytes}
                            tick={{ fontSize: 12 }}
                            domain={[0, maxValue]} // Fixed scale - never changes
                        />
                        <Tooltip
                            formatter={(value: number) => [formatBytes(value), '']}
                            contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                        />
                        <Area
                            type="monotone"
                            dataKey="download"
                            stackId="1"
                            stroke="#10b981"
                            fill="#10b981"
                            fillOpacity={0.6}
                            name="Download"
                        />
                        <Area
                            type="monotone"
                            dataKey="upload"
                            stackId="1"
                            stroke="#3b82f6"
                            fill="#3b82f6"
                            fillOpacity={0.6}
                            name="Upload"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex justify-center gap-8 text-sm">
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-green-500"></span>
                    <span className="text-muted-foreground">Download</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                    <span className="text-muted-foreground">Upload</span>
                </div>
            </div>
        </div>
    );
}
