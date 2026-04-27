import { useQuery, useMutation } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { Shield, CheckCircle, XCircle, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { firewallApi } from "@/lib/api";

const FirewallPage = () => {
  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['firewall-rules'],
    queryFn: () => firewallApi.getRules(),
  });

  const { data: statusData } = useQuery({
    queryKey: ['firewall-status'],
    queryFn: () => firewallApi.getStatus(),
    refetchInterval: 10000,
  });

  const applyMutation = useMutation({
    mutationFn: firewallApi.applyRules,
    onSuccess: () => {
      toast.success("Firewall rules applied successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || "Failed to apply rules");
    },
  });

  const rules = rulesData?.rules || [];

  if (isLoading) {
    return (
      <DashboardLayout title="Firewall" subtitle="Loading...">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout 
      title="Firewall" 
      subtitle="Manage network security rules"
    >
      <div className="space-y-6 animate-fade-in">
        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            title="Firewall Status"
            value={statusData?.active ? "Active" : "Inactive"}
            subtitle={statusData?.table || "nftables"}
            icon={Shield}
            variant={statusData?.active ? "success" : "danger"}
          />
          <StatCard
            title="Active Rules"
            value={rules.length}
            subtitle="Currently enforced"
            icon={CheckCircle}
            variant="default"
          />
          <StatCard
            title="Blocked Devices"
            value={statusData?.blocked_count || 0}
            subtitle="Access restricted"
            icon={XCircle}
            variant="danger"
          />
        </div>

        {/* Rules List */}
        <div className="glass-card rounded-xl border border-border p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-foreground">Firewall Rules</h3>
            <Button 
              onClick={() => applyMutation.mutate()} 
              disabled={applyMutation.isPending}
              className="gap-2"
            >
              {applyMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Shield className="h-4 w-4" />
              )}
              Apply Rules
            </Button>
          </div>

          {rules.length > 0 ? (
            <div className="space-y-3">
              {rules.map((rule: any, index: number) => (
                <div
                  key={index}
                  className="flex items-center justify-between rounded-lg border border-border bg-muted/30 p-4"
                >
                  <div className="flex items-center gap-4">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                      rule.type === "drop" || rule.type === "reject" 
                        ? "bg-destructive/10 text-destructive" 
                        : "bg-success/10 text-success"
                    }`}>
                      {rule.type === "drop" || rule.type === "reject" 
                        ? <XCircle className="h-5 w-5" /> 
                        : <CheckCircle className="h-5 w-5" />}
                    </div>
                    <div>
                      <p className="font-medium text-foreground">
                        {rule.chain || rule.type}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {rule.expr || rule.description || "Rule"}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Shield className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-muted-foreground">No firewall rules configured</p>
            </div>
          )}
        </div>

        {/* Warning */}
        <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4">
          <AlertTriangle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-warning">Caution</p>
            <p className="text-sm text-warning/80">
              Firewall changes take effect immediately. Incorrect rules may lock you out of the network.
            </p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default FirewallPage;
