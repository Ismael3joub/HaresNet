import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useQuery } from '@tanstack/react-query';
import { devicesApi } from '@/lib/api';
import { Loader2, ArrowUp, ArrowDown, Trophy } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';
import { Progress } from '@/components/ui/progress';

export function TopDevicesCard() {
    const [hours, setHours] = useState(24);
    const [sortBy, setSortBy] = useState('total');

    const { data: topDevicesData, isLoading } = useQuery({
        queryKey: ['top-devices', hours, sortBy],
        queryFn: () => devicesApi.getTopDevices({ limit: 10, hours, sort_by: sortBy }),
        refetchInterval: 60000 // Update every minute
    });

    const devices = topDevicesData?.top_devices || [];
    const maxValue = devices.length > 0
        ? Math.max(...devices.map((d: any) => d.total))
        : 1;

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Trophy className="h-5 w-5 text-primary" />
                        <div>
                            <CardTitle>Top Devices</CardTitle>
                            <CardDescription>Devices with highest traffic usage</CardDescription>
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
                                <SelectItem value="168">Last Week</SelectItem>
                            </SelectContent>
                        </Select>
                        <Select value={sortBy} onValueChange={setSortBy}>
                            <SelectTrigger className="w-[110px]">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="total">Total</SelectItem>
                                <SelectItem value="upload">Upload</SelectItem>
                                <SelectItem value="download">Download</SelectItem>
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
                ) : devices.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
                        <p>No device traffic data available</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {devices.map((device: any, index: number) => {
                            const percentage = (device.total / maxValue) * 100;

                            return (
                                <div key={device.device_id} className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-bold text-sm">
                                                {index + 1}
                                            </div>
                                            <div>
                                                <p className="font-medium text-sm">
                                                    {device.hostname || device.mac}
                                                </p>
                                                {device.hostname && (
                                                    <p className="text-xs text-muted-foreground">{device.mac}</p>
                                                )}
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-bold text-sm">{device.total_formatted}</p>
                                            <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                <span className="flex items-center gap-1">
                                                    <ArrowUp className="h-3 w-3 text-blue-500" />
                                                    {device.upload_formatted}
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <ArrowDown className="h-3 w-3 text-green-500" />
                                                    {device.download_formatted}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <Progress value={percentage} className="h-2" />
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
