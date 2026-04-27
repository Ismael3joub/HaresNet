import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Calendar, Plus, Clock, Trash2, Loader2, ShieldAlert, ShieldCheck, Laptop, Check } from "lucide-react";
import { toast } from "sonner";
import { schedulesApi, devicesApi } from "@/lib/api";
import { Schedule, Device } from "@/types";
import { cn } from "@/lib/utils";

const daysOfWeek = [
  { short: "Mon", full: "monday" },
  { short: "Tue", full: "tuesday" },
  { short: "Wed", full: "wednesday" },
  { short: "Thu", full: "thursday" },
  { short: "Fri", full: "friday" },
  { short: "Sat", full: "saturday" },
  { short: "Sun", full: "sunday" },
];

const SchedulesPage = () => {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
    device_id: "",
    name: "",
    days: [] as string[],
    start_time: "21:00",
    end_time: "07:00",
    action: "block" as "block" | "allow",
  });

  const { data: schedulesData, isLoading } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => schedulesApi.getAll(),
  });

  const { data: devicesData } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: schedulesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success("Schedule created successfully");
      setIsDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to create schedule");
    },
  });

  const toggleMutation = useMutation({
    mutationFn: schedulesApi.toggle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to toggle schedule");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: schedulesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success("Schedule deleted");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to delete schedule");
    },
  });

  const schedules: Schedule[] = schedulesData?.schedules || [];
  const devices: Device[] = devicesData?.devices || [];

  const resetForm = () => {
    setNewSchedule({
      device_id: "",
      name: "",
      days: [],
      start_time: "21:00",
      end_time: "07:00",
      action: "block",
    });
  };

  const toggleDay = (day: string) => {
    setNewSchedule(prev => ({
      ...prev,
      days: prev.days.includes(day)
        ? prev.days.filter(d => d !== day)
        : [...prev.days, day]
    }));
  };

  const selectDays = (type: 'all' | 'weekdays' | 'weekends') => {
    let days: string[] = [];
    if (type === 'all') days = daysOfWeek.map(d => d.full);
    if (type === 'weekdays') days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
    if (type === 'weekends') days = ['saturday', 'sunday'];
    setNewSchedule(prev => ({ ...prev, days }));
  };

  const getDayLabel = () => {
    if (newSchedule.days.length === 0) return "Select days";
    if (newSchedule.days.length === 7) return "Every day";
    if (newSchedule.days.length === 5 && !newSchedule.days.includes('saturday') && !newSchedule.days.includes('sunday')) return "Weekdays";
    if (newSchedule.days.length === 2 && newSchedule.days.includes('saturday') && newSchedule.days.includes('sunday')) return "Weekends";
    return `${newSchedule.days.length} days selected`;
  };

  const getSummary = () => {
    if (!newSchedule.device_id) return "Select a device to see summary";

    const device = devices.find(d => d.id.toString() === newSchedule.device_id);
    const deviceName = device?.label || device?.mac || "Device";
    const actionText = newSchedule.action === "block" ? "blocking internet for" : "allowing internet for";
    const timeText = `from ${formatTime(newSchedule.start_time)} to ${formatTime(newSchedule.end_time)}`;
    const dayText = getDayLabel();

    return `This rule will vary be ${actionText} ${deviceName} ${timeText} on ${dayText}.`;
  };

  const formatTime = (time: string) => {
    // Simple 24h to 12h conversion for display
    const [h, m] = time.split(':');
    const hour = parseInt(h);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${m} ${ampm}`;
  };

  const handleCreateSchedule = () => {
    if (!newSchedule.name || !newSchedule.device_id || newSchedule.days.length === 0) {
      toast.error("Please fill in all required fields");
      return;
    }

    createMutation.mutate({
      device_id: parseInt(newSchedule.device_id),
      name: newSchedule.name,
      days: newSchedule.days,
      start_time: newSchedule.start_time,
      end_time: newSchedule.end_time,
      action: newSchedule.action,
    });
  };

  const getDeviceLabel = (deviceId: number) => {
    const device = devices.find(d => d.id === deviceId);
    return device?.label || device?.mac || `Device ${deviceId}`;
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Schedules" subtitle="Loading...">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Schedules"
      subtitle="Automate device access rules"
    >
      <div className="space-y-6 animate-fade-in max-w-7xl mx-auto">
        {/* Header Actions */}
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground">
            {schedules.length} schedule{schedules.length !== 1 ? "s" : ""} active
          </p>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button size="lg" className="gap-2 shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all">
                <Plus className="h-5 w-5" />
                Create New Rule
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-2xl p-0 overflow-hidden gap-0 border-0 shadow-2xl">
              <div className="bg-gradient-to-br from-background to-muted/30 p-6 md:p-8 space-y-8">
                <DialogHeader className="mb-6">
                  <DialogTitle className="text-2xl font-bold">Create Access Rule</DialogTitle>
                  <DialogDescription className="text-base">
                    Configure when devices can access the internet.
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-8">
                  {/* Step 1: Who & What */}
                  <div className="grid md:grid-cols-2 gap-8">
                    <div className="space-y-3">
                      <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">1. Select Device</Label>
                      <Select
                        value={newSchedule.device_id}
                        onValueChange={(v) => setNewSchedule(prev => ({ ...prev, device_id: v }))}
                      >
                        <SelectTrigger className="h-12 border-primary/20 bg-background/50 focus:ring-primary/20">
                          <SelectValue placeholder="Identify device..." />
                        </SelectTrigger>
                        <SelectContent>
                          {devices.map((device) => (
                            <SelectItem key={device.id} value={device.id.toString()}>
                              <div className="flex items-center gap-2">
                                <Laptop className="h-4 w-4 text-muted-foreground" />
                                <span className="font-medium">{device.label || device.mac}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        value={newSchedule.name}
                        onChange={(e) => setNewSchedule(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Name this rule (e.g. Bedtime)"
                        className="h-12 border-primary/20 bg-background/50 focus:ring-primary/20"
                      />
                    </div>

                    <div className="space-y-3">
                      <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">2. Choose Action</Label>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          type="button"
                          onClick={() => setNewSchedule(prev => ({ ...prev, action: "block" }))}
                          className={cn(
                            "relative flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all duration-200",
                            newSchedule.action === "block"
                              ? "border-destructive bg-destructive/5 text-destructive shadow-md shadow-destructive/10"
                              : "border-border bg-background/50 text-muted-foreground hover:bg-muted/50 hover:border-muted-foreground/30"
                          )}
                        >
                          {newSchedule.action === "block" && (
                            <div className="absolute top-2 right-2">
                              <Check className="h-4 w-4" />
                            </div>
                          )}
                          <ShieldAlert className="h-8 w-8" />
                          <span className="font-bold">Block Internet</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setNewSchedule(prev => ({ ...prev, action: "allow" }))}
                          className={cn(
                            "relative flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all duration-200",
                            newSchedule.action === "allow"
                              ? "border-green-500 bg-green-500/5 text-green-600 shadow-md shadow-green-500/10"
                              : "border-border bg-background/50 text-muted-foreground hover:bg-muted/50 hover:border-muted-foreground/30"
                          )}
                        >
                          {newSchedule.action === "allow" && (
                            <div className="absolute top-2 right-2">
                              <Check className="h-4 w-4" />
                            </div>
                          )}
                          <ShieldCheck className="h-8 w-8" />
                          <span className="font-bold">Allow Internet</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Step 2: When */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">3. Schedule Time</Label>
                      <div className="flex gap-2">
                        <button onClick={() => selectDays('weekdays')} type="button" className="text-xs font-medium px-2 py-1 rounded bg-secondary hover:bg-secondary/80 transition-colors">Weekdays</button>
                        <button onClick={() => selectDays('weekends')} type="button" className="text-xs font-medium px-2 py-1 rounded bg-secondary hover:bg-secondary/80 transition-colors">Weekends</button>
                        <button onClick={() => selectDays('all')} type="button" className="text-xs font-medium px-2 py-1 rounded bg-secondary hover:bg-secondary/80 transition-colors">Every day</button>
                      </div>
                    </div>

                    <div className="flex justify-between gap-2 overflow-x-auto pb-2">
                      {daysOfWeek.map((day) => (
                        <button
                          key={day.full}
                          type="button"
                          onClick={() => toggleDay(day.full)}
                          className={cn(
                            "flex-1 min-w-[3rem] h-12 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-200 border",
                            newSchedule.days.includes(day.full)
                              ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/25 scale-105"
                              : "bg-background border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
                          )}
                        >
                          {day.short}
                        </button>
                      ))}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <Label className="text-xs text-muted-foreground">Start Time</Label>
                        <div className="relative">
                          <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            type="time"
                            value={newSchedule.start_time}
                            onChange={(e) => setNewSchedule(prev => ({ ...prev, start_time: e.target.value }))}
                            className="pl-9 h-12 bg-background/50 border-primary/20"
                          />
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs text-muted-foreground">End Time</Label>
                        <div className="relative">
                          <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            type="time"
                            value={newSchedule.end_time}
                            onChange={(e) => setNewSchedule(prev => ({ ...prev, end_time: e.target.value }))}
                            className="pl-9 h-12 bg-background/50 border-primary/20"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Summary Box */}
                  <div className="bg-muted/50 rounded-lg p-4 border border-border/50">
                    <div className="flex gap-3">
                      <div className="mt-1">
                        {newSchedule.action === 'block'
                          ? <ShieldAlert className="h-5 w-5 text-destructive" />
                          : <ShieldCheck className="h-5 w-5 text-green-600" />
                        }
                      </div>
                      <div>
                        <h4 className="font-semibold text-sm mb-1">Rule Summary</h4>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {getSummary()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <DialogFooter className="gap-2">
                  <Button variant="ghost" onClick={() => setIsDialogOpen(false)} className="h-11">
                    Cancel
                  </Button>
                  <Button
                    onClick={handleCreateSchedule}
                    disabled={createMutation.isPending}
                    className="h-11 px-8 gap-2 bg-primary hover:bg-primary/90"
                  >
                    {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Create Rule
                  </Button>
                </DialogFooter>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Schedules List */}
        {schedules.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {schedules.map((schedule) => (
              <div
                key={schedule.id}
                className="group relative overflow-hidden glass-card rounded-xl border border-border/50 bg-gradient-to-br from-background to-muted/20 hover:shadow-lg transition-all duration-300"
              >
                {/* Status Indicator Line */}
                <div className={cn(
                  "absolute top-0 left-0 w-1 h-full",
                  schedule.action === "block" ? "bg-destructive" : "bg-green-500"
                )} />

                <div className="p-5 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-lg text-foreground truncate max-w-[150px]">{schedule.name}</h3>
                      <div className="flex items-center gap-1.5 text-sm text-muted-foreground mt-1">
                        <Laptop className="h-3.5 w-3.5" />
                        <span className="truncate max-w-[150px]">{getDeviceLabel(schedule.device_id)}</span>
                      </div>
                    </div>
                    <Switch
                      checked={schedule.enabled}
                      onCheckedChange={() => toggleMutation.mutate(schedule.id)}
                      className="data-[state=checked]:bg-primary"
                    />
                  </div>

                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/40 border border-border/50">
                    <div className={cn(
                      "p-2 rounded-md",
                      schedule.action === "block" ? "bg-destructive/10 text-destructive" : "bg-green-500/10 text-green-600"
                    )}>
                      {schedule.action === "block" ? <ShieldAlert className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
                    </div>
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        {schedule.action === "block" ? "Access Blocked" : "Access Allowed"}
                      </div>
                      <div className="text-sm font-medium flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-primary" />
                        {schedule.start_time} - {schedule.end_time}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {schedule.days.length === 7 ? (
                      <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                        Every day
                      </span>
                    ) : (
                      schedule.days.map((day) => (
                        <span
                          key={day}
                          className="px-2 py-1 rounded-md text-xs font-medium bg-secondary text-secondary-foreground border border-border"
                        >
                          {day.substring(0, 3)}
                        </span>
                      ))
                    )}
                  </div>
                </div>

                <div className="absolute top-4 right-14 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteMutation.mutate(schedule.id)}
                    className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 bg-muted/10 rounded-3xl border-2 border-dashed border-border/50">
            <div className="p-4 bg-primary/10 rounded-full mb-4">
              <Calendar className="h-10 w-10 text-primary" />
            </div>
            <h3 className="text-xl font-bold text-foreground">No schedules configured</h3>
            <p className="text-muted-foreground max-w-sm text-center mt-2 mb-8">
              Create automated rules to manage internet access for devices on your network.
            </p>
            <Button onClick={() => setIsDialogOpen(true)} size="lg" className="gap-2">
              <Plus className="h-5 w-5" />
              Create First Rule
            </Button>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default SchedulesPage;
