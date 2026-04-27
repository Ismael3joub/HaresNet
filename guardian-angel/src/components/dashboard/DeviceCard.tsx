import { MoreVertical, Laptop, Smartphone, Tv, Wifi } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface Device {
  id: number;
  mac: string;
  ip: string;
  hostname?: string;
  vendor?: string;
  label?: string;
  group?: string;
  blocked: boolean;
  first_seen: string;
  last_seen: string;
  is_online?: boolean;
  child_safe?: boolean;
}

interface DeviceCardProps {
  device: Device;
  onBlock: (id: number) => void;
  onUnblock: (id: number) => void;
  onEdit: (device: Device) => void;
  onUpdate?: (device: Device) => void;
  onViewActivity: (device: Device) => void;
  onManageServices?: (device: Device) => void;
}

const getDeviceIcon = (label?: string) => {
  const lowerLabel = label?.toLowerCase() || "";
  if (lowerLabel.includes("phone") || lowerLabel.includes("iphone") || lowerLabel.includes("android")) {
    return Smartphone;
  }
  if (lowerLabel.includes("tv") || lowerLabel.includes("roku") || lowerLabel.includes("chromecast")) {
    return Tv;
  }
  return Laptop;
};

export function DeviceCard({ device, onBlock, onUnblock, onEdit, onUpdate, onViewActivity, onManageServices }: DeviceCardProps) {
  const Icon = getDeviceIcon(device.label);

  // Use backend provided status, fallback to calculation if missing (for backward compatibility)
  const isOnline = device.is_online !== undefined
    ? device.is_online
    : new Date(device.last_seen.endsWith("Z") ? device.last_seen : `${device.last_seen}Z`).getTime() > Date.now() - 8 * 1000; // 8s matches backend

  return (
    <div className={cn(
      "glass-card-hover rounded-xl border p-4 transition-all duration-300",
      device.blocked && "border-destructive/30 bg-destructive/5"
    )}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className={cn(
            "flex h-12 w-12 items-center justify-center rounded-lg",
            device.blocked
              ? "bg-destructive/10 text-destructive"
              : "bg-primary/10 text-primary"
          )}>
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-foreground">
                {device.label || device.hostname || device.mac}
              </h3>
              <span className={cn(
                "status-dot",
                device.blocked ? "status-blocked" : isOnline ? "status-online" : "status-offline"
              )} />
            </div>
            <p className="text-sm text-muted-foreground">{device.ip}</p>
            {device.group && (
              <span className="inline-flex items-center mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-secondary text-secondary-foreground">
                {device.group}
              </span>
            )}
            {device.child_safe && (
              <span className="inline-flex items-center mt-1 ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                Child Safe
              </span>
            )}
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={() => onEdit(device)}>
              Edit Device
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onViewActivity(device)}>
              View Activity
            </DropdownMenuItem>
            {onManageServices && (
              <DropdownMenuItem onClick={() => onManageServices(device)}>
                Manage Services
              </DropdownMenuItem>
            )}
            {device.blocked ? (
              <DropdownMenuItem onClick={() => onUnblock(device.id)}>
                <span className="text-success">Unblock</span>
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem onClick={() => onBlock(device.id)}>
                <span className="text-destructive">Block</span>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation();
              const newStatus = !device.child_safe;
              // Use onUpdate if available to avoid opening edit modal
              if (onUpdate) {
                onUpdate({ ...device, child_safe: newStatus });
              } else {
                onEdit({ ...device, child_safe: newStatus });
              }
            }}>
              <span className={device.child_safe ? "text-primary" : "text-muted-foreground"}>
                {device.child_safe ? "Disable Child Mode" : "Enable Child Mode"}
              </span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div >

      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
        <span>MAC: {device.mac}</span>
        <span>Last seen: {new Date(device.last_seen).toLocaleTimeString()}</span>
      </div>
    </div >
  );
}
