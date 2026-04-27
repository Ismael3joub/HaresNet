import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { devicesApi } from '@/lib/api';
import { DeviceActivityChart } from './DeviceActivityChart';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Activity } from 'lucide-react';
import { Device } from "@/types";

export function DeviceActivityWidget() {
    const [selectedDeviceId, setSelectedDeviceId] = useState<string>("all");

    const { data: devicesData } = useQuery({
        queryKey: ['devices'],
        queryFn: () => devicesApi.getAll(),
    });

    const devices: Device[] = devicesData?.devices || [];

    // Sort devices by last seen (most recent first)
    const sortedDevices = [...devices].sort((a, b) => {
        const timeA = new Date(a.last_seen).getTime();
        const timeB = new Date(b.last_seen).getTime();
        return timeB - timeA;
    });

    // Auto-select first device if none selected and devices exist
    useEffect(() => {
        if (selectedDeviceId === "all" && sortedDevices.length > 0) {
            setSelectedDeviceId(String(sortedDevices[0].id));
        }
    }, [sortedDevices, selectedDeviceId]);

    const selectedDevice = devices.find(d => String(d.id) === selectedDeviceId);

    return (
        <div className="glass-card rounded-xl border border-border p-6 h-full flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    <h3 className="font-semibold text-foreground">Device Activity</h3>
                </div>

                <Select
                    value={selectedDeviceId}
                    onValueChange={setSelectedDeviceId}
                >
                    <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select device" />
                    </SelectTrigger>
                    <SelectContent>
                        {sortedDevices.map((device) => (
                            <SelectItem key={device.id} value={String(device.id)}>
                                {device.label || device.hostname || device.mac}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            <div className="flex-1 min-h-[300px]">
                {selectedDevice ? (
                    <DeviceActivityChart device={selectedDevice} height="100%" />
                ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                        No devices available
                    </div>
                )}
            </div>
        </div>
    );
}
