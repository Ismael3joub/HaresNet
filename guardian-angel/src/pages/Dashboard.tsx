import { useQuery } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { DeviceCard } from "@/components/dashboard/DeviceCard";
import { DeviceActivityWidget } from "@/components/dashboard/DeviceActivityWidget";
import { NetworkTrafficCard } from "@/components/dashboard/NetworkTrafficCard";
import { TopDevicesCard } from "@/components/dashboard/TopDevicesCard";
import { LiveTrafficRatesCard } from "@/components/dashboard/LiveTrafficRatesCard";
import {
  Laptop,
  Shield,
  Activity,
  ArrowDownToLine,
  ArrowUpFromLine,
  Wifi,
  Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { devicesApi, systemApi, wifiApi } from "@/lib/api";
import { toast } from "sonner";
import { Device } from "@/types";
import { useEffect } from "react";
import { socket } from "@/lib/socket";

const Dashboard = () => {
  const { data: devicesData, isLoading: devicesLoading, refetch: refetchDevices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.getAll(),
    refetchInterval: false, // Disabled - rely on socket events only
    staleTime: 2000,
  });

  const { data: systemStatus, isLoading: systemLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => systemApi.getStatus(),
    refetchInterval: 5000, // Refresh system stats more frequently
  });

  // Socket.IO for real-time updates
  useEffect(() => {
    console.log('[Dashboard] Initializing socket connection...');

    // Connect if not already connected
    if (!socket.connected) {
      socket.connect();
    }

    const handleConnect = () => {
      console.log('[Dashboard] ✅ Socket connected!', socket.id);
    };

    const handleDisconnect = (reason: string) => {
      console.log('[Dashboard] ❌ Socket disconnected:', reason);
    };

    const handleDeviceUpdate = (data: any) => {
      console.log('[Dashboard] 🔄 DEVICE UPDATE EVENT!', data);
      refetchDevices();
    };

    // Register listeners
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('device_update', handleDeviceUpdate);

    // Check if already connected
    if (socket.connected) {
      console.log('[Dashboard] Already connected:', socket.id);
    }

    return () => {
      console.log('[Dashboard] Cleanup: removing listeners (keeping socket alive)');
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('device_update', handleDeviceUpdate);
      // DO NOT DISCONNECT - keep socket alive for entire app
    };
  }, [refetchDevices]);



  const devices: Device[] = devicesData?.devices || [];

  const onlineDevices = devices.filter(d => {
    if (d.blocked) return false;
    // Use backend status if available
    if (d.is_online !== undefined) return d.is_online;

    // Fallback to timestamp check
    // Handle potential missing timezone - assume UTC if no 'Z'
    const timeString = d.last_seen.endsWith('Z') ? d.last_seen : `${d.last_seen}Z`;
    return new Date(timeString).getTime() > Date.now() - 8 * 1000; // 8 seconds (matches backend)
  }).length;
  const blockedDevices = devices.filter(d => d.blocked).length;



  const handleBlock = async (id: number) => {
    try {
      await devicesApi.block(id);
      refetchDevices();
      toast.success("Device blocked");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Failed to block device");
    }
  };

  const handleUnblock = async (id: number) => {
    try {
      await devicesApi.unblock(id);
      refetchDevices();
      toast.success("Device unblocked");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Failed to unblock device");
    }
  };

  const handleUpdate = async (device: Device) => {
    try {
      await devicesApi.update(device.id, {
        label: device.label,
        group: device.group,
        child_safe: device.child_safe
      });
      refetchDevices();
      toast.success("Device updated");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Failed to update device");
    }
  };

  const handleRestartAP = async () => {
    try {
      await wifiApi.restart();
      toast.success("Access point restarting...");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Failed to restart AP");
    }
  };

  if (devicesLoading || systemLoading) {
    return (
      <DashboardLayout title="Dashboard" subtitle="Loading...">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Dashboard"
      subtitle="Network overview and quick actions"
    >
      <div className="space-y-6 animate-fade-in">
        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Connected Devices"
            value={onlineDevices}
            subtitle={`${devices.length} total devices`}
            icon={Laptop}
            variant="default"
          />
          <StatCard
            title="Blocked Devices"
            value={blockedDevices}
            subtitle="Access restricted"
            icon={Shield}
            variant={blockedDevices > 0 ? "danger" : "default"}
          />
          <StatCard
            title="CPU Usage"
            value={`${systemStatus?.cpu?.percent || 0}%`}
            subtitle={`${systemStatus?.cpu?.count || 0} cores`}
            icon={ArrowDownToLine}
            variant={systemStatus?.cpu?.percent > 80 ? "danger" : "success"}
          />
          <StatCard
            title="Memory Usage"
            value={`${systemStatus?.memory?.percent || 0}%`}
            subtitle={`${Math.round((systemStatus?.memory?.total || 0) / 1024 / 1024 / 1024)} GB total`}
            icon={ArrowUpFromLine}
            variant={systemStatus?.memory?.percent > 80 ? "danger" : "default"}
          />
        </div>



        {/* Traffic Monitoring Section */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Network-Wide Traffic */}
          <NetworkTrafficCard />

          {/* Top Devices */}
          <TopDevicesCard />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Device Activity Widget */}
          <DeviceActivityWidget />

          {/* Live Traffic Rates */}
          <LiveTrafficRatesCard />
        </div>

        {/* Recent Devices */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Recent Devices</h2>
            <Link to="/devices">
              <Button variant="outline" size="sm">
                View All
              </Button>
            </Link>
          </div>
          {devices.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {devices.slice(0, 4).map((device) => (
                <DeviceCard
                  key={device.id}
                  device={device}
                  onBlock={handleBlock}
                  onUnblock={handleUnblock}
                  onEdit={() => { }}
                  onUpdate={handleUpdate}
                  onViewActivity={() => { }}
                />
              ))}
            </div>
          ) : (
            <div className="glass-card rounded-xl border border-border p-8 text-center">
              <Laptop className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-muted-foreground">No devices detected yet</p>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="glass-card rounded-xl border border-border p-6">
          <h3 className="mb-4 font-semibold text-foreground">Quick Actions</h3>
          <div className="flex flex-wrap gap-3">
            <Button className="gap-2" onClick={handleRestartAP}>
              <Wifi className="h-4 w-4" />
              Restart Access Point
            </Button>
            <Link to="/firewall">
              <Button variant="outline" className="gap-2">
                <Shield className="h-4 w-4" />
                Firewall Settings
              </Button>
            </Link>
            <Link to="/system">
              <Button variant="outline" className="gap-2">
                <Activity className="h-4 w-4" />
                System Status
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
