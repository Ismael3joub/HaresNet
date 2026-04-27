import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Loader2, Globe, Save, UserCircle, Wifi, Eye, EyeOff, ShieldCheck, Mail } from "lucide-react";
import { toast } from "sonner";
import { settingsApi, authApi } from "@/lib/api";
import { Input } from "@/components/ui/input";

const SettingsPage = () => {
    const queryClient = useQueryClient();
    const [selectedTimezone, setSelectedTimezone] = useState("");

    const { data: settingsData, isLoading } = useQuery({
        queryKey: ['settings'],
        queryFn: () => settingsApi.getSettings(),
    });

    const { data: timezonesData } = useQuery({
        queryKey: ['timezones'],
        queryFn: () => settingsApi.getTimezones(),
    });

    const updateMutation = useMutation({
        mutationFn: settingsApi.updateSettings,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings'] });
            toast.success("Settings updated successfully");
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || "Failed to update settings");
        },
    });
    const [adminForm, setAdminForm] = useState({
        username: "",
        current_password: "",
        new_password: "",
        confirm_password: ""
    });

    const { data: userData } = useQuery({
        queryKey: ['auth-status'],
        queryFn: () => authApi.status(),
    });

    useEffect(() => {
        if (userData?.user?.username) {
            setAdminForm(prev => ({ ...prev, username: userData.user.username }));
        }
    }, [userData]);

    const profileMutation = useMutation({
        mutationFn: authApi.updateProfile,
        onSuccess: () => {
            toast.success("Profile updated successfully. Please log in again with your new credentials.");
            setTimeout(() => {
                authApi.logout();
                window.location.href = '/login';
            }, 2000);
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || "Failed to update profile");
        },
    });

    const handleAdminSave = () => {
        if (!adminForm.current_password) {
            toast.error("Current password is required to save changes");
            return;
        }

        if (adminForm.new_password && adminForm.new_password !== adminForm.confirm_password) {
            toast.error("New passwords do not match");
            return;
        }

        if (adminForm.new_password && adminForm.new_password.length < 8) {
            toast.error("New password must be at least 8 characters");
            return;
        }

        profileMutation.mutate({
            username: adminForm.username,
            current_password: adminForm.current_password,
            new_password: adminForm.new_password || undefined
        });
    };

    useEffect(() => {
        if (settingsData?.timezone) {
            setSelectedTimezone(settingsData.timezone);
        }
    }, [settingsData]);

    const handleSave = () => {
        if (!selectedTimezone) {
            toast.error("Please select a timezone");
            return;
        }

        updateMutation.mutate({ timezone: selectedTimezone });
    };



    const timezones = timezonesData?.timezones || [];

    if (isLoading) {
        return (
            <DashboardLayout title="Settings" subtitle="Loading...">
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout
            title="Settings"
            subtitle="Configure your router settings"
        >
            <div className="space-y-6 animate-fade-in">
                {/* Blynk / 2FA Settings */}
                {/* Notifications & Security Settings */}
                <div className="glass-card rounded-xl border border-border p-6">
                    <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <ShieldCheck className="h-6 w-6" />
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center gap-3">
                                <h3 className="font-semibold text-foreground">Notifications & Security</h3>
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                                Configure notification delivery via NTFY and secure your account with 2FA
                            </p>

                            <div className="mt-6 space-y-6 max-w-md">
                                {/* NTFY Settings */}
                                <div className="space-y-3">
                                    <Label htmlFor="ntfy_topic">NTFY Topic</Label>
                                    <div className="flex gap-2">
                                        <Input
                                            id="ntfy_topic"
                                            value={settingsData?.ntfy_topic || ""}
                                            onChange={(e) => updateMutation.mutate({ ntfy_topic: e.target.value })}
                                            placeholder="e.g. haresnet_admin"
                                        />
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="shrink-0"
                                            onClick={() => window.open(`https://ntfy.sh/${settingsData?.ntfy_topic || 'haresnet_admin'}`, '_blank')}
                                            title="Open NTFY Feed"
                                        >
                                            <Globe className="h-4 w-4" />
                                        </Button>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Use a unique topic name to receive notifications. <br />
                                        Subscribe at: <a href={`https://ntfy.sh/${settingsData?.ntfy_topic || 'haresnet_admin'}`} target="_blank" rel="noreferrer" className="text-primary hover:underline">ntfy.sh/{settingsData?.ntfy_topic || 'haresnet_admin'}</a>
                                    </p>

                                </div>

                                {/* Email Settings */}
                                <div className="space-y-3">
                                    <Label htmlFor="admin_email">Admin Email (for 2FA)</Label>
                                    <div className="flex gap-2">
                                        <div className="relative flex-1">
                                            <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                            <Input
                                                id="admin_email"
                                                className="pl-9"
                                                value={settingsData?.admin_email || ""}
                                                onChange={(e) => updateMutation.mutate({ admin_email: e.target.value })}
                                                placeholder="admin@example.com"
                                            />
                                        </div>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="shrink-0"
                                            onClick={() => updateMutation.mutate({ admin_email: settingsData?.admin_email })}
                                            disabled={updateMutation.isPending}
                                            title="Save Email"
                                        >
                                            <Save className="h-4 w-4" />
                                        </Button>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Receive OTP codes via email. Requires Docker mail-server to be running.
                                    </p>
                                </div>

                                {/* 2FA Toggle */}
                                <div className="flex items-center justify-between rounded-lg border border-border p-3">
                                    <div>
                                        <Label className="font-medium">Two-Factor Authentication</Label>
                                        <p className="text-xs text-muted-foreground mt-0.5">
                                            Require OTP verification via Email for admin login
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        role="switch"
                                        aria-checked={settingsData?.two_factor_enabled}
                                        onClick={() => updateMutation.mutate({ two_factor_enabled: !settingsData?.two_factor_enabled })}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${settingsData?.two_factor_enabled ? 'bg-primary' : 'bg-muted'}`}
                                        disabled={updateMutation.isPending}
                                    >
                                        <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${settingsData?.two_factor_enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                                    </button>
                                </div>

                                {updateMutation.isPending && (
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        <Loader2 className="h-4 w-4 animate-spin" /> Saving changes...
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Timezone Settings */}
                <div className="glass-card rounded-xl border border-border p-6">
                    <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <Globe className="h-6 w-6" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-foreground">Timezone</h3>
                            <p className="text-sm text-muted-foreground mt-1">
                                Set your router's timezone for accurate schedule activation
                            </p>

                            <div className="mt-4 space-y-4 max-w-md">
                                <div className="space-y-2">
                                    <Label htmlFor="timezone">Select Timezone</Label>
                                    <Select value={selectedTimezone} onValueChange={setSelectedTimezone}>
                                        <SelectTrigger id="timezone">
                                            <SelectValue placeholder="Select timezone" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {timezones.map((tz: string) => (
                                                <SelectItem key={tz} value={tz}>
                                                    {tz}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {settingsData?.timezone !== selectedTimezone && (
                                    <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 p-3">
                                        <p className="text-sm text-amber-600 dark:text-amber-400">
                                            Current timezone: <strong>{settingsData?.timezone}</strong>
                                            <br />
                                            Changing to: <strong>{selectedTimezone}</strong>
                                        </p>
                                    </div>
                                )}

                                <Button
                                    onClick={handleSave}
                                    disabled={updateMutation.isPending || settingsData?.timezone === selectedTimezone}
                                    className="gap-2"
                                >
                                    {updateMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                                    <Save className="h-4 w-4" />
                                    Save Changes
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Admin Account Settings */}
                <div className="glass-card rounded-xl border border-border p-6">
                    <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <UserCircle className="h-6 w-6" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-foreground">Admin Account</h3>
                            <p className="text-sm text-muted-foreground mt-1">
                                Update your administrative credentials
                            </p>

                            <div className="mt-6 space-y-6 max-w-md">
                                <div className="space-y-2">
                                    <Label htmlFor="username">Username</Label>
                                    <Input
                                        id="username"
                                        value={adminForm.username}
                                        onChange={(e) => setAdminForm({ ...adminForm, username: e.target.value })}
                                        placeholder="Admin username"
                                    />
                                </div>

                                <div className="space-y-4 pt-2 border-t border-border">
                                    <h4 className="text-sm font-medium text-foreground">Change Password</h4>

                                    <div className="space-y-2">
                                        <Label htmlFor="current_password">Current Password</Label>
                                        <Input
                                            id="current_password"
                                            type="password"
                                            value={adminForm.current_password}
                                            onChange={(e) => setAdminForm({ ...adminForm, current_password: e.target.value })}
                                            placeholder="Required to save changes"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="new_password">New Password (optional)</Label>
                                        <Input
                                            id="new_password"
                                            type="password"
                                            value={adminForm.new_password}
                                            onChange={(e) => setAdminForm({ ...adminForm, new_password: e.target.value })}
                                            placeholder="Leave blank to keep current"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="confirm_password">Confirm New Password</Label>
                                        <Input
                                            id="confirm_password"
                                            type="password"
                                            value={adminForm.confirm_password}
                                            onChange={(e) => setAdminForm({ ...adminForm, confirm_password: e.target.value })}
                                            placeholder="Repeat new password"
                                        />
                                    </div>
                                </div>

                                <Button
                                    onClick={handleAdminSave}
                                    disabled={profileMutation.isPending}
                                    className="gap-2 w-full sm:w-auto"
                                >
                                    {profileMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                                    <Save className="h-4 w-4" />
                                    Update Admin Profile
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </DashboardLayout >
    );
};

export default SettingsPage;

