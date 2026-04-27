import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { devicesApi } from '@/lib/api';
import { Loader2, ArrowDown, ArrowUp } from 'lucide-react';
import { Device } from "@/types";

interface DeviceActivityDialogProps {
    device: Device | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function DeviceActivityDialog({ device, open, onOpenChange }: DeviceActivityDialogProps) {
    const { data: trafficData, isLoading } = useQuery({
        queryKey: ['device-traffic', device?.id],
        queryFn: () => device ? devicesApi.getTraffic(device.id) : Promise.resolve({ traffic: [] }),
        enabled: !!device && open,
        refetchInterval: 60000 // Update every minute
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
        return parseFloat((bytes / Math.pow(k, i)).toFixed(0)) + sizes[i];
    };

    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    // Process data for chart
    const data = trafficData?.traffic?.map((t: any) => ({
        time: formatTime(t.timestamp),
        upload: t.upload,
        download: t.download,
        fullTimestamp: t.timestamp
    })) || [];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-3xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        Activity for {device?.label || device?.hostname || device?.mac}
                    </DialogTitle>
                    <DialogDescription>
                        Network traffic history for the last 24 hours.
                    </DialogDescription>
                </DialogHeader>

                <div className="h-[400px] w-full mt-4">
                    {isLoading ? (
                        <div className="flex h-full items-center justify-center">
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                    ) : data.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart
                                data={data}
                                margin={{
                                    top: 10,
                                    right: 30,
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
                                    fillOpacity={0.2}
                                    name="Download"
                                />
                                <Area
                                    type="monotone"
                                    dataKey="upload"
                                    stackId="1"
                                    stroke="#3b82f6"
                                    fill="#3b82f6"
                                    fillOpacity={0.2}
                                    name="Upload"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="flex h-full items-center justify-center flex-col text-muted-foreground">
                            <p>No traffic data available for this device.</p>
                            <p className="text-sm">Traffic recording starts after device connects.</p>
                        </div>
                    )}
                </div>

                <div className="flex justify-center gap-8 mt-4 text-sm">
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-green-500"></span>
                        <span className="text-muted-foreground">Download</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                        <span className="text-muted-foreground">Upload</span>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
