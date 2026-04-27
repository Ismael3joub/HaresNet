import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { routerApi } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { toast } from "sonner";
import { Loader2, Save, Globe, Network } from "lucide-react";

export default function NetworkSettings() {
    const queryClient = useQueryClient();

    // WAN Settings
    const [wanMode, setWanMode] = useState<'dhcp' | 'static'>('dhcp');
    const [wanStaticIp, setWanStaticIp] = useState("");
    const [wanGateway, setWanGateway] = useState("");
    const [wanDnsPrimary, setWanDnsPrimary] = useState("8.8.8.8");
    const [wanDnsSecondary, setWanDnsSecondary] = useState("8.8.4.4");
    const [wanSubnet, setWanSubnet] = useState("255.255.255.0");

    // LAN Settings
    const [lanIp, setLanIp] = useState("192.168.10.1");
    const [lanSubnet, setLanSubnet] = useState("255.255.255.0");
    const [lanDhcpEnabled, setLanDhcpEnabled] = useState(true);
    const [lanDhcpStart, setLanDhcpStart] = useState("192.168.10.100");
    const [lanDhcpEnd, setLanDhcpEnd] = useState("192.168.10.200");

    // Fetch WAN config
    const { data: wanConfig } = useQuery({
        queryKey: ['router-wan-config'],
        queryFn: routerApi.getWanConfig,
    });

    // Fetch LAN config
    const { data: lanConfig } = useQuery({
        queryKey: ['router-lan-config'],
        queryFn: routerApi.getLanConfig,
    });

    // Sync WAN config
    useEffect(() => {
        if (wanConfig) {
            setWanMode(wanConfig.mode || 'dhcp');
            setWanStaticIp(wanConfig.static_ip || "");
            setWanGateway(wanConfig.gateway || "");
            setWanSubnet(wanConfig.subnet_mask || "255.255.255.0");
            setWanDnsPrimary(wanConfig.dns_primary || "8.8.8.8");
            setWanDnsSecondary(wanConfig.dns_secondary || "8.8.4.4");
        }
    }, [wanConfig]);

    // Sync LAN config
    useEffect(() => {
        if (lanConfig) {
            setLanIp(lanConfig.ip || "192.168.10.1");
            setLanSubnet(lanConfig.subnet_mask || "255.255.255.0");
            setLanDhcpEnabled(lanConfig.dhcp_enabled !== false);
            setLanDhcpStart(lanConfig.dhcp_start || "192.168.10.100");
            setLanDhcpEnd(lanConfig.dhcp_end || "192.168.10.200");
        }
    }, [lanConfig]);

    // Save mutations
    const updateWanMutation = useMutation({
        mutationFn: routerApi.updateWanConfig,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['router-wan-config'] });
        }
    });

    const updateLanMutation = useMutation({
        mutationFn: routerApi.updateLanConfig,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['router-lan-config'] });
        }
    });

    const handleSave = async () => {
        // Validation
        if (wanMode === 'static') {
            if (!wanStaticIp || !wanGateway) {
                toast.error("Static IP and Gateway are required for Static IP mode");
                return;
            }
        }
        if (!lanIp) {
            toast.error("LAN IP is required");
            return;
        }

        try {
            // Save WAN config
            await updateWanMutation.mutateAsync({
                mode: wanMode,
                static_ip: wanStaticIp,
                gateway: wanGateway,
                subnet_mask: wanSubnet,
                dns_primary: wanDnsPrimary,
                dns_secondary: wanDnsSecondary
            });

            // Save LAN config
            await updateLanMutation.mutateAsync({
                ip: lanIp,
                subnet_mask: lanSubnet,
                dhcp_enabled: lanDhcpEnabled,
                dhcp_start: lanDhcpStart,
                dhcp_end: lanDhcpEnd
            });

            toast.success("Router configuration saved successfully");
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Failed to save settings");
            console.error("Failed to save settings", error);
        }
    };

    const isSaving = updateWanMutation.isPending || updateLanMutation.isPending;

    return (
        <DashboardLayout
            title="Network Settings"
            subtitle="Configure router internet connection and local network"
        >
            <div className="space-y-6 animate-fade-in max-w-4xl">
                {/* WAN Settings */}
                <Card className="glass-card border-2 border-primary/30">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Globe className="h-5 w-5 text-primary" />
                            Internet Connection (WAN)
                        </CardTitle>
                        <CardDescription>
                            Configure how the router connects to the internet via Ethernet cable.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <Label>Connection Type</Label>
                            <Select value={wanMode} onValueChange={(val: 'dhcp' | 'static') => setWanMode(val)}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select connection type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="dhcp">DHCP (Automatic IP)</SelectItem>
                                    <SelectItem value="static">Static IP</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {wanMode === 'static' && (
                            <div className="grid gap-4 md:grid-cols-2 animate-in slide-in-from-top-2">
                                <div className="space-y-2">
                                    <Label htmlFor="wan-ip">IP Address</Label>
                                    <Input id="wan-ip" value={wanStaticIp} onChange={(e) => setWanStaticIp(e.target.value)} placeholder="192.168.1.50" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="wan-gateway">Gateway</Label>
                                    <Input id="wan-gateway" value={wanGateway} onChange={(e) => setWanGateway(e.target.value)} placeholder="192.168.1.1" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="wan-subnet">Subnet Mask</Label>
                                    <Input id="wan-subnet" value={wanSubnet} onChange={(e) => setWanSubnet(e.target.value)} placeholder="255.255.255.0" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="wan-dns1">Primary DNS</Label>
                                    <Input id="wan-dns1" value={wanDnsPrimary} onChange={(e) => setWanDnsPrimary(e.target.value)} placeholder="8.8.8.8" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="wan-dns2">Secondary DNS</Label>
                                    <Input id="wan-dns2" value={wanDnsSecondary} onChange={(e) => setWanDnsSecondary(e.target.value)} placeholder="8.8.4.4" />
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* LAN Settings */}
                <Card className="glass-card border-2 border-primary/30">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Network className="h-5 w-5 text-primary" />
                            Local Network (LAN)
                        </CardTitle>
                        <CardDescription>
                            Configure the local network IP address and DHCP server settings.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="lan-ip">Router IP Address</Label>
                                <Input id="lan-ip" value={lanIp} onChange={(e) => setLanIp(e.target.value)} placeholder="192.168.10.1" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="lan-subnet">Subnet Mask</Label>
                                <Input id="lan-subnet" value={lanSubnet} onChange={(e) => setLanSubnet(e.target.value)} placeholder="255.255.255.0" />
                            </div>
                        </div>

                        <div className="flex items-center justify-between rounded-lg border border-border p-4">
                            <div>
                                <Label htmlFor="lan-dhcp" className="cursor-pointer">DHCP Server</Label>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Automatically assign IP addresses to connected devices
                                </p>
                            </div>
                            <Switch
                                id="lan-dhcp"
                                checked={lanDhcpEnabled}
                                onCheckedChange={setLanDhcpEnabled}
                            />
                        </div>

                        {lanDhcpEnabled && (
                            <div className="grid gap-4 md:grid-cols-2 animate-in slide-in-from-top-2">
                                <div className="space-y-2">
                                    <Label htmlFor="dhcp-start">Start IP</Label>
                                    <Input id="dhcp-start" value={lanDhcpStart} onChange={(e) => setLanDhcpStart(e.target.value)} placeholder="192.168.10.100" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="dhcp-end">End IP</Label>
                                    <Input id="dhcp-end" value={lanDhcpEnd} onChange={(e) => setLanDhcpEnd(e.target.value)} placeholder="192.168.10.200" />
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Save Button */}
                <div className="flex justify-end">
                    <Button
                        size="lg"
                        onClick={handleSave}
                        disabled={isSaving}
                        className="w-full md:w-auto gap-2"
                    >
                        {isSaving ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Saving Configuration...
                            </>
                        ) : (
                            <>
                                <Save className="h-4 w-4" />
                                Save Network Settings
                            </>
                        )}
                    </Button>
                </div>

                {/* Info */}
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                    <p className="text-sm">
                        <strong>Router Mode:</strong> Connect your internet source (modem/ISP) to the WAN port via Ethernet cable. The router will provide WiFi access and manage your local network.
                    </p>
                </div>
            </div>
        </DashboardLayout>
    );
}
