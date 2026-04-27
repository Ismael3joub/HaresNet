import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { devicesApi } from '@/lib/api';
import { Loader2, Network, TrendingUp, TrendingDown } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';

export function NetworkTrafficCard() {
    const [hours, setHours] = useState(24);
    const [aggregate, setAggregate] = useState('5m');

    const { data: networkData, isLoading } = useQuery({
        queryKey: ['network-traffic', hours, aggregate],
        queryFn: () => devicesApi.getNetworkTraffic({ hours, aggregate }),
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

    // Process data for chart
    const chartData = networkData?.traffic?.map((t: any) => ({
        time: formatTime(t.timestamp),
        upload: t.upload,
        download: t.download,
    })) || [];

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Network className="h-5 w-5 text-primary" />
                        <div>
                            <CardTitle>Network Traffic</CardTitle>
                            <CardDescription>Total traffic across all devices</CardDescription>
                        </div>
                    </div>
                    <div className="flex gap-2">
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
                </div>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="flex items-center justify-center h-[300px]">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                ) : chartData.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
                        <p>No network traffic data available</p>
                    </div>
                ) : (
                    <>
                        {/* Summary Stats */}
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <div className="flex items-center gap-3 p-4 rounded-lg bg-blue-50 dark:bg-blue-950/20">
                                <TrendingUp className="h-8 w-8 text-blue-500" />
                                <div>
                                    <p className="text-sm text-muted-foreground">Total Upload</p>
                                    <p className="text-2xl font-bold text-black dark:text-white">{networkData?.summary?.total_upload_formatted || '0 B'}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-950/20">
                                <TrendingDown className="h-8 w-8 text-green-500" />
                                <div>
                                    <p className="text-sm text-muted-foreground">Total Download</p>
                                    <p className="text-2xl font-bold text-black dark:text-white">{networkData?.summary?.total_download_formatted || '0 B'}</p>
                                </div>
                            </div>
                        </div>

                        {/* Chart */}
                        <div className="h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart
                                    data={chartData}
                                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
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
                                    />
                                    <Tooltip
                                        formatter={(value: number) => formatBytes(value)}
                                        contentStyle={{
                                            backgroundColor: 'var(--background)',
                                            borderColor: 'var(--border)'
                                        }}
                                    />
                                    <Legend />
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
                    </>
                )}
            </CardContent>
        </Card>
    );
}
