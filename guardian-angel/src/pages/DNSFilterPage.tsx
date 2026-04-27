import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { dnsFilterApi } from '@/lib/api';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import DNSFilterGroups from '@/components/dns-filter/DNSFilterGroups';
import DNSFilters from '@/components/dns-filter/DNSFilters';
import DNSBlocklists from '@/components/dns-filter/DNSBlocklists';
import DNSStatistics from '@/components/dns-filter/DNSStatistics';
import DNSLogs from '@/components/dns-filter/DNSLogs';
import DNSTestFilter from '@/components/dns-filter/DNSTestFilter';

const DNSFilterPage = () => {
  const [activeTab, setActiveTab] = useState('overview');

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dns-stats'],
    queryFn: () => dnsFilterApi.getStats(),
    refetchInterval: 30000,
  });

  return (
    <DashboardLayout
      title="DNS Filtering"
      subtitle="Pi-hole-like DNS domain filtering with regex support"
    >
      <div className="space-y-6">
        {/* Overview Cards */}
        {!statsLoading && stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Queries Today</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_queries_today?.toLocaleString() || 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Blocked Today</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-400">{stats.total_blocked_today?.toLocaleString() || 0}</div>
                {stats.total_queries_today && stats.total_blocked_today ? (
                  <p className="text-xs text-muted-foreground mt-1">
                    {((stats.total_blocked_today / stats.total_queries_today) * 100).toFixed(1)}% blocked
                  </p>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Active Filters</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_active_filters?.toLocaleString() || 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Blocklists</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_blocklists || 0}</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="blocklists">Blocklists</TabsTrigger>
            <TabsTrigger value="groups">Groups</TabsTrigger>
            <TabsTrigger value="filters">Filters</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
            <TabsTrigger value="test">Test</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <DNSStatistics stats={stats} />
          </TabsContent>

          {/* Blocklists Tab */}
          <TabsContent value="blocklists" className="space-y-4">
            <DNSBlocklists />
          </TabsContent>

          {/* Groups Tab */}
          <TabsContent value="groups" className="space-y-4">
            <DNSFilterGroups />
          </TabsContent>

          {/* Filters Tab */}
          <TabsContent value="filters" className="space-y-4">
            <DNSFilters />
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="space-y-4">
            <DNSLogs />
          </TabsContent>

          {/* Test Tab */}
          <TabsContent value="test" className="space-y-4">
            <DNSTestFilter />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default DNSFilterPage;
