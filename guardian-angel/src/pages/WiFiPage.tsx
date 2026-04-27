import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Wifi, Eye, EyeOff, RefreshCw, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { wifiApi } from "@/lib/api";

const WiFiPage = () => {
  const queryClient = useQueryClient();
  const [showPassword, setShowPassword] = useState(false);

  // Router WiFi Configuration
  const [config, setConfig] = useState({
    ssid: "",
    password: "",
    security_mode: "WPA2",
    channel: "6",
    hidden: false,
  });

  // Fetch WiFi config
  const { data: wifiConfig, isLoading } = useQuery({
    queryKey: ['wifi-config'],
    queryFn: () => wifiApi.getConfig(),
  });

  const { data: wifiStatus } = useQuery({
    queryKey: ['wifi-status'],
    queryFn: () => wifiApi.getStatus(),
    refetchInterval: 10000,
  });

  useEffect(() => {
    if (wifiConfig) {
      setConfig({
        ssid: wifiConfig.ssid || "",
        password: wifiConfig.password || "",
        security_mode: wifiConfig.security_mode || "WPA2",
        channel: String(wifiConfig.channel || 6),
        hidden: wifiConfig.hidden || false,
      });
    }
  }, [wifiConfig]);

  const updateMutation = useMutation({
    mutationFn: (config: any) => wifiApi.updateConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wifi-config'] });
      toast.success("Wi-Fi configuration saved successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to update configuration");
    },
  });

  const restartMutation = useMutation({
    mutationFn: wifiApi.restart,
    onSuccess: () => {
      toast.success("Access point restarted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to restart AP");
    },
  });

  const handleSave = () => {
    updateMutation.mutate({
      ssid: config.ssid,
      password: config.password,
      security_mode: config.security_mode,
      channel: parseInt(config.channel),
      hidden: config.hidden,
    });
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Wi-Fi Settings" subtitle="Loading...">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Wi-Fi Settings"
      subtitle="Configure your wireless network"
    >
      <div className="max-w-2xl space-y-6 animate-fade-in">
        {/* Status Card */}
        <div className="glass-card rounded-xl border border-border p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 border border-primary/30">
              <Wifi className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">Access Point Status</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={`status-dot ${wifiStatus?.active ? 'status-online' : 'status-offline'}`} />
                <span className={`text-sm ${wifiStatus?.active ? 'text-success' : 'text-destructive'}`}>
                  {wifiStatus?.active ? 'Active' : 'Inactive'}
                </span>
                {wifiStatus?.clients_connected !== undefined && (
                  <span className="text-sm text-muted-foreground">
                    • {wifiStatus.clients_connected} clients connected
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Configuration Form */}
        <div className="glass-card rounded-xl border border-border p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Network Configuration</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Configure your router's Wi-Fi network settings (2.4GHz)
            </p>
          </div>

          <div className="space-y-4">
            {/* SSID */}
            <div className="space-y-2">
              <Label htmlFor="ssid">Network Name (SSID)</Label>
              <Input
                id="ssid"
                value={config.ssid}
                onChange={(e) => setConfig((prev) => ({ ...prev, ssid: e.target.value }))}
                placeholder="Enter network name"
                maxLength={32}
              />
              <p className="text-xs text-muted-foreground">1-32 characters</p>
            </div>

            {/* Password */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={config.password}
                  onChange={(e) => setConfig((prev) => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter password"
                  className="pr-10"
                  disabled={config.security_mode === 'OPEN'}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">8-63 characters</p>
            </div>

            {/* Security Mode */}
            <div className="space-y-2">
              <Label htmlFor="security">Security Mode</Label>
              <Select
                value={config.security_mode}
                onValueChange={(v) => setConfig((prev) => ({ ...prev, security_mode: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select security mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="WPA2">WPA2 (Recommended)</SelectItem>
                  <SelectItem value="WPA3">WPA3 (Newer devices)</SelectItem>
                  <SelectItem value="WPA2/WPA3">WPA2/WPA3 Mixed</SelectItem>
                  <SelectItem value="WEP">WEP (Insecure)</SelectItem>
                  <SelectItem value="OPEN">Open (No Password)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Channel */}
            <div className="space-y-2">
              <Label htmlFor="channel">Channel</Label>
              <Select
                value={config.channel}
                onValueChange={(v) => setConfig((prev) => ({ ...prev, channel: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select channel" />
                </SelectTrigger>
                <SelectContent>
                  {/* 2.4GHz channels */}
                  {Array.from({ length: 13 }, (_, i) => i + 1).map((ch) => (
                    <SelectItem key={ch} value={ch.toString()}>
                      Channel {ch}
                    </SelectItem>
                  ))}
                  <SelectItem value="0">Auto</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Hidden Network */}
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div>
                <Label htmlFor="hidden" className="cursor-pointer">Hidden Network</Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Network won't appear in device scans
                </p>
              </div>
              <Switch
                id="hidden"
                checked={config.hidden}
                onCheckedChange={(checked) => setConfig((prev) => ({ ...prev, hidden: checked }))}
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="gap-2"
            >
              {updateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save Configuration
            </Button>
            <Button
              variant="outline"
              onClick={() => restartMutation.mutate()}
              disabled={restartMutation.isPending}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${restartMutation.isPending ? 'animate-spin' : ''}`} />
              Restart AP
            </Button>
          </div>
        </div>

        {/* Info */}
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
          <p className="text-sm">
            <strong>Note:</strong> This router operates in 2.4GHz mode for maximum compatibility. Changes require restarting the access point to take effect.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default WiFiPage;
