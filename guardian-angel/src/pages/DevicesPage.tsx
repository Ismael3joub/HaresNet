import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { DeviceCard } from "@/components/dashboard/DeviceCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Search, Filter, Laptop, Loader2 } from "lucide-react";
import { devicesApi } from "@/lib/api";
import { toast } from "sonner";
import { Device } from "@/types";
import { socket } from "@/lib/socket";

import { DeviceActivityDialog } from "@/components/dashboard/DeviceActivityDialog";
import { DeviceServicesDialog } from "@/components/dashboard/DeviceServicesDialog";

const DevicesPage = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("All");
  const [showBlocked, setShowBlocked] = useState<"all" | "blocked" | "active">("all");
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [viewingDeviceActivity, setViewingDeviceActivity] = useState<Device | null>(null);
  const [managingServicesForDevice, setManagingServicesForDevice] = useState<Device | null>(null);
  const [editLabel, setEditLabel] = useState("");

  const [editGroup, setEditGroup] = useState("");
  const [editDailyLimit, setEditDailyLimit] = useState<number>(0);
  const [editHourlyLimit, setEditHourlyLimit] = useState<number>(0);

  useEffect(() => {
    console.log('[DevicesPage] Initializing socket connection...');

    // Connect if not already connected
    if (!socket.connected) {
      socket.connect();
    }

    const handleConnect = () => {
      console.log('[DevicesPage] ✅ Socket connected!', socket.id);
    };

    const handleDisconnect = (reason: string) => {
      console.log('[DevicesPage] ❌ Socket disconnected:', reason);
    };

    const handleDeviceUpdate = (data: any) => {
      console.log('[DevicesPage] 🔄 DEVICE UPDATE EVENT!', data);
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    };

    // Register listeners
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('device_update', handleDeviceUpdate);

    // Check if already connected
    if (socket.connected) {
      console.log('[DevicesPage] Already connected:', socket.id);
    }

    return () => {
      console.log('[DevicesPage] Cleanup: removing listeners (keeping socket alive)');
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('device_update', handleDeviceUpdate);
      // DO NOT DISCONNECT - keep socket alive for entire app
    };
  }, [queryClient]);

  const { data: devicesData, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.getAll(),
    refetchInterval: false, // Disabled - rely on socket events only
    staleTime: 2000,
  });

  const { data: groupsData } = useQuery({
    queryKey: ['device-groups'],
    queryFn: () => devicesApi.getGroups(),
  });

  const blockMutation = useMutation({
    mutationFn: devicesApi.block,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      toast.success("Device blocked");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to block device");
    },
  });

  const unblockMutation = useMutation({
    mutationFn: devicesApi.unblock,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      toast.success("Device unblocked");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to unblock device");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { label?: string; group?: string; traffic_limit_daily_mb?: number; traffic_limit_hourly_mb?: number; } }) =>
      devicesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      queryClient.invalidateQueries({ queryKey: ['device-groups'] });
      toast.success("Device updated");
      setEditingDevice(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to update device");
    },
  });

  const devices: Device[] = devicesData?.devices || [];
  const rawGroups = groupsData?.groups || [];
  const validGroups = rawGroups.filter((g: string) => g && g.trim().length > 0);
  const groups = ["All", ...validGroups];

  const filteredDevices = devices.filter((device) => {
    const matchesSearch =
      device.label?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      device.mac?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      device.ip?.includes(searchQuery) ||
      device.hostname?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesGroup = selectedGroup === "All" || device.group === selectedGroup;

    const matchesBlocked =
      showBlocked === "all" ||
      (showBlocked === "blocked" && device.blocked) ||
      (showBlocked === "active" && !device.blocked);

    return matchesSearch && matchesGroup && matchesBlocked;
  });

  const handleEdit = (device: Device) => {
    setEditingDevice(device);
    setEditLabel(device.label || "");

    setEditGroup(device.group || "");
    setEditDailyLimit(device.traffic_limit_daily_mb || 0);
    setEditHourlyLimit(device.traffic_limit_hourly_mb || 0);
  };

  const handleSaveEdit = () => {
    if (editingDevice) {
      updateMutation.mutate({
        id: editingDevice.id,
        data: {
          label: editLabel,
          group: editGroup,
          traffic_limit_daily_mb: editDailyLimit,
          traffic_limit_hourly_mb: editHourlyLimit
        },
      });
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Devices" subtitle="Loading...">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Devices"
      subtitle={`${devices.length} devices detected`}
    >
      <div className="space-y-6 animate-fade-in">
        {/* Filters */}
        <div className="glass-card rounded-xl border border-border p-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search by name, MAC, or IP..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            <div className="flex items-center gap-3">
              <Select value={selectedGroup} onValueChange={setSelectedGroup}>
                <SelectTrigger className="w-40">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Group" />
                </SelectTrigger>
                <SelectContent>
                  {groups.map((group) => (
                    <SelectItem key={group} value={group}>
                      {group}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={showBlocked} onValueChange={(v) => setShowBlocked(v as any)}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="blocked">Blocked</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Device Stats */}
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="status-dot status-online" />
            <span className="text-muted-foreground">
              {devices.filter(d => !d.blocked && new Date(d.last_seen + (d.last_seen.endsWith("Z") ? "" : "Z")).getTime() > Date.now() - 5 * 1000).length} Online
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="status-dot status-offline" />
            <span className="text-muted-foreground">
              {devices.filter(d => !d.blocked && new Date(d.last_seen + (d.last_seen.endsWith("Z") ? "" : "Z")).getTime() <= Date.now() - 5 * 1000).length} Offline
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="status-dot status-blocked" />
            <span className="text-muted-foreground">
              {devices.filter(d => d.blocked).length} Blocked
            </span>
          </div>
        </div>

        {/* Devices Grid */}
        {filteredDevices.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredDevices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                onBlock={(id) => blockMutation.mutate(id)}
                onUnblock={(id) => unblockMutation.mutate(id)}
                onEdit={handleEdit}
                onUpdate={(updatedDevice) => updateMutation.mutate({ id: updatedDevice.id, data: updatedDevice })}
                onViewActivity={(device) => setViewingDeviceActivity(device)}
                onManageServices={(device) => setManagingServicesForDevice(device)}
              />
            ))}
          </div>
        ) : (
          <div className="glass-card rounded-xl border border-border p-12 text-center">
            <Laptop className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold text-foreground">No devices found</h3>
            <p className="mt-2 text-muted-foreground">
              {devices.length === 0
                ? "Waiting for devices to connect to the network"
                : "Try adjusting your search or filter criteria"}
            </p>
          </div>
        )}

        {/* Edit Dialog */}
        <Dialog open={!!editingDevice} onOpenChange={() => setEditingDevice(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Edit Device</DialogTitle>
              <DialogDescription>
                Update the device label and group assignment.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="label">Device Label</Label>
                <Input
                  id="label"
                  value={editLabel}
                  onChange={(e) => setEditLabel(e.target.value)}
                  placeholder="e.g., MacBook Pro"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="group">Group</Label>
                <Input
                  id="group"
                  value={editGroup}
                  onChange={(e) => setEditGroup(e.target.value)}
                  placeholder="e.g., Office, Living Room"
                />
              </div>
              <div className="space-y-4 pt-4 border-t border-border">
                <h4 className="font-medium text-foreground">Traffic Limits</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="daily_limit">Daily Limit (MB)</Label>
                    <Input
                      id="daily_limit"
                      type="number"
                      min="0"
                      value={editDailyLimit}
                      onChange={(e) => setEditDailyLimit(Number(e.target.value))}
                      placeholder="0 = No Limit"
                    />
                    <p className="text-xs text-muted-foreground">0 to disable</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hourly_limit">Hourly Limit (MB)</Label>
                    <Input
                      id="hourly_limit"
                      type="number"
                      min="0"
                      value={editHourlyLimit}
                      onChange={(e) => setEditHourlyLimit(Number(e.target.value))}
                      placeholder="0 = No Limit"
                    />
                    <p className="text-xs text-muted-foreground">0 to disable</p>
                  </div>
                </div>
              </div>
              <div className="rounded-lg bg-muted p-3 text-sm text-muted-foreground">
                <p><strong>MAC:</strong> {editingDevice?.mac}</p>
                <p><strong>IP:</strong> {editingDevice?.ip}</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingDevice(null)}>
                Cancel
              </Button>
              <Button onClick={handleSaveEdit} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Activity Dialog */}
        <DeviceActivityDialog
          device={viewingDeviceActivity}
          open={!!viewingDeviceActivity}
          onOpenChange={(open) => !open && setViewingDeviceActivity(null)}
        />

        {/* Services Dialog */}
        <DeviceServicesDialog
          device={devices.find(d => d.id === managingServicesForDevice?.id) || null}
          open={!!managingServicesForDevice}
          onOpenChange={(open) => !open && setManagingServicesForDevice(null)}
        />
      </div>
    </DashboardLayout>
  );
};

export default DevicesPage;
