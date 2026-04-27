import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { firewallApi } from "@/lib/api";
import { Device } from "@/types";
import { Loader2, Server, Globe } from "lucide-react";
import { toast } from "sonner";

interface DeviceServicesDialogProps {
    device: Device | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function DeviceServicesDialog({ device, open, onOpenChange }: DeviceServicesDialogProps) {
    const queryClient = useQueryClient();

    // Fetch available services
    const { data: services, isLoading } = useQuery({
        queryKey: ['firewall-services'],
        queryFn: () => firewallApi.getServices(),
        enabled: open,
    });

    const toggleMutation = useMutation({
        mutationFn: ({ serviceId, blocked }: { serviceId: number; blocked: boolean }) =>
            firewallApi.toggleService(device!.id, serviceId, blocked),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['devices'] });
            // Don't toast on every toggle to allow rapid changes, or maybe small toast?
            // toast.success("Service updated");
        },
        onError: (err: any) => {
            toast.error(err.response?.data?.error || "Failed to update service");
        }
    });

    const handleToggle = (serviceId: number, currentBlocked: boolean) => {
        if (!device) return;
        toggleMutation.mutate({ serviceId, blocked: !currentBlocked });
    };

    const blockedServices = device?.blocked_services || [];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Manage Services</DialogTitle>
                    <DialogDescription>
                        Control access to specific services for {device?.label || device?.hostname || "this device"}.
                    </DialogDescription>
                </DialogHeader>

                {isLoading ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <div className="space-y-4 py-4">
                        {services && services.length > 0 ? (
                            services.map((service: any) => {
                                const isBlocked = blockedServices.includes(service.id);
                                const isProcessing = toggleMutation.isPending && toggleMutation.variables?.serviceId === service.id;

                                return (
                                    <div key={service.id} className="flex items-center justify-between rounded-lg border p-3">
                                        <div className="space-y-0.5">
                                            <div className="flex items-center gap-2">
                                                {/* We could use service.icon here if mapped, or generic icon */}
                                                {service.name === 'internet' ? <Globe className="h-4 w-4" /> : <Server className="h-4 w-4" />}
                                                <Label className="text-base">{service.label}</Label>
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                {service.ip_count} IP ranges
                                            </p>
                                        </div>
                                        <Switch
                                            checked={!isBlocked} // UI says "Allow" or "Enable"? Usually "Blocked" is the toggle state.
                                            // Let's make the switch represent "Access Allowed" (True) vs "Blocked" (False)
                                            // If !isBlocked => Access Allowed => Switch ON
                                            // If isBlocked => Access Denied => Switch OFF
                                            onCheckedChange={() => handleToggle(service.id, isBlocked)}
                                            disabled={isProcessing}
                                        />
                                    </div>
                                );
                            })
                        ) : (
                            <div className="text-center text-muted-foreground py-4">
                                No services defined. Go to Security page to add services (if applicable).
                            </div>
                        )}
                        <div className="text-xs text-muted-foreground mt-2">
                            Note: Switch <strong>ON</strong> means access is <strong>Allowed</strong>.
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
