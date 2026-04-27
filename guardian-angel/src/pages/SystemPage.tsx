import { useQuery } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { Cpu, HardDrive, MemoryStick, Clock, Network, ArrowUp, ArrowDown, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { systemApi } from "@/lib/api";
import { NetworkInterface } from "@/types";

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatUptime = (bootTime: number) => {
  const now = Date.now() / 1000;
  const uptime = now - bootTime;
  const days = Math.floor(uptime / 86400);
  const hours = Math.floor((uptime % 86400) / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  
  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};

const SystemPage = () => {
  const { data: systemStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => systemApi.getStatus(),
    refetchInterval: 5000,
  });

  const { data: interfacesData, isLoading: interfacesLoading } = useQuery({
    queryKey: ['system-interfaces'],
    queryFn: () => systemApi.getInterfaces(),
  });

  const { data: networkStats } = useQuery({
    queryKey: ['network-stats'],
    queryFn: () => systemApi.getNetworkStats(),
    refetchInterval: 5000,
  });

  const isLoading = statusLoading || interfacesLoading;

  if (isLoading) {
    return (
      <DashboardLayout title="System" subtitle="Loading...">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  const interfaces: NetworkInterface[] = interfacesData?.interfaces || [];

  return (
    <DashboardLayout 
      title="System" 
      subtitle="Server status and performance"
    >
      <div className="space-y-6 animate-fade-in">
        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="CPU Usage"
            value={`${systemStatus?.cpu?.percent || 0}%`}
            subtitle={`${systemStatus?.cpu?.count || 0} cores available`}
            icon={Cpu}
            variant={systemStatus?.cpu?.percent > 80 ? "danger" : systemStatus?.cpu?.percent > 50 ? "warning" : "success"}
          />
          <StatCard
            title="Memory Usage"
            value={`${systemStatus?.memory?.percent || 0}%`}
            subtitle={formatBytes(systemStatus?.memory?.total || 0)}
            icon={MemoryStick}
            variant={systemStatus?.memory?.percent > 80 ? "danger" : systemStatus?.memory?.percent > 50 ? "warning" : "default"}
          />
        </div>

        {/* Resource Meters */}
        <div className="glass-card rounded-xl border border-border p-6">
          <h3 className="text-lg font-semibold text-foreground mb-6">Resource Utilization</h3>
          
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">CPU</span>
                <span className="text-foreground font-medium">{systemStatus?.cpu?.percent || 0}%</span>
              </div>
              <Progress value={systemStatus?.cpu?.percent || 0} className="h-2" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Memory</span>
                <span className="text-foreground font-medium">
                  {systemStatus?.memory?.percent || 0}% ({formatBytes(systemStatus?.memory?.available || 0)} available)
                </span>
              </div>
              <Progress value={systemStatus?.memory?.percent || 0} className="h-2" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Disk</span>
                <span className="text-foreground font-medium">
                  {systemStatus?.disk?.percent || 0}% ({formatBytes(systemStatus?.disk?.free || 0)} free)
                </span>
              </div>
              <Progress value={systemStatus?.disk?.percent || 0} className="h-2" />
            </div>
          </div>
        </div>

        {/* Network Interfaces */}
        <div className="glass-card rounded-xl border border-border p-6">
          <h3 className="text-lg font-semibold text-foreground mb-6">Network Interfaces</h3>
          
          {interfaces.length > 0 ? (
            <div className="space-y-4">
              {interfaces.map((iface) => (
                <div
                  key={iface.name}
                  className="flex items-center justify-between rounded-lg border border-border bg-muted/30 p-4"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                      <Network className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-semibold text-foreground">{iface.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {iface.ipv4 || "No IP"} {iface.mac && `• ${iface.mac}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2">
                      <span className={`status-dot ${iface.is_up ? 'status-online' : 'status-offline'}`} />
                      <span className={`text-sm ${iface.is_up ? 'text-success' : 'text-destructive'} capitalize`}>
                        {iface.is_up ? 'Up' : 'Down'}
                      </span>
                    </div>
                    {iface.speed > 0 && (
                      <p className="text-sm text-muted-foreground">{iface.speed} Mbps</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Network className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-muted-foreground">No network interfaces found</p>
            </div>
          )}
        </div>

        {/* Network Stats */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="glass-card rounded-xl border border-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <ArrowDown className="h-5 w-5 text-primary" />
              <h3 className="font-semibold text-foreground">Bytes Received</h3>
            </div>
            <p className="text-3xl font-bold text-foreground">
              {formatBytes(networkStats?.bytes_recv || 0)}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {networkStats?.packets_recv?.toLocaleString() || 0} packets
            </p>
          </div>

          <div className="glass-card rounded-xl border border-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <ArrowUp className="h-5 w-5 text-success" />
              <h3 className="font-semibold text-foreground">Bytes Sent</h3>
            </div>
            <p className="text-3xl font-bold text-foreground">
              {formatBytes(networkStats?.bytes_sent || 0)}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {networkStats?.packets_sent?.toLocaleString() || 0} packets
            </p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default SystemPage;
