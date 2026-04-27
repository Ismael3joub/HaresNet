import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

interface DNSStatisticsProps {
  stats: any;
}

const DNSStatistics = ({ stats }: DNSStatisticsProps) => {
  if (!stats) {
    return <div className="text-center text-muted-foreground p-8">Loading statistics...</div>;
  }

  const blockPercentage = stats.total_queries_today
    ? ((stats.total_blocked_today / stats.total_queries_today) * 100).toFixed(1)
    : 0;

  const pieData = [
    { name: 'Blocked', value: stats.total_blocked_today || 0 },
    { name: 'Allowed', value: (stats.total_queries_today || 0) - (stats.total_blocked_today || 0) },
  ];

  const COLORS = ['#ef4444', '#10b981'];

  return (
    <div className="space-y-6">
      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Filtering Summary</CardTitle>
          <CardDescription>Today's DNS filtering statistics</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="text-sm font-medium text-muted-foreground mb-1">Total Queries</div>
              <div className="text-2xl font-bold">{stats.total_queries_today?.toLocaleString() || 0}</div>
            </div>
            <div className="p-4 rounded-lg bg-red-950/10 border border-red-900/20">
              <div className="text-sm font-medium text-red-400 mb-1">Blocked</div>
              <div className="text-2xl font-bold text-red-500">{stats.total_blocked_today?.toLocaleString() || 0}</div>
            </div>
            <div className="p-4 rounded-lg bg-green-950/10 border border-green-900/20">
              <div className="text-sm font-medium text-green-400 mb-1">Allowed</div>
              <div className="text-2xl font-bold text-green-500">
                {(stats.total_queries_today - stats.total_blocked_today || 0).toLocaleString()}
              </div>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="text-sm font-medium text-muted-foreground mb-1">Block Rate</div>
              <div className="text-2xl font-bold">{blockPercentage}%</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Query Status</CardTitle>
            <CardDescription>Distribution of blocked vs allowed queries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--popover))', borderColor: 'hsl(var(--border))', borderRadius: 'var(--radius)' }}
                    itemStyle={{ color: 'hsl(var(--popover-foreground))' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-6 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-sm text-muted-foreground">Blocked</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-sm text-muted-foreground">Allowed</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Top Blocked Domains */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Top Blocked Domains</CardTitle>
            <CardDescription>Most frequently blocked domains today</CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            <div className="space-y-4">
              {stats.top_blocked_domains && stats.top_blocked_domains.length > 0 ? (
                stats.top_blocked_domains.map((domain: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center">
                    <div className="text-sm font-mono truncate max-w-[70%] text-muted-foreground" title={domain.domain}>
                      {domain.domain}
                    </div>
                    <div className="text-sm font-semibold text-red-400 bg-red-950/30 px-2 py-0.5 rounded">
                      {domain.blocked_count.toLocaleString()}
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                  No blocked domains recorded yet
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Clients */}
      <Card>
        <CardHeader>
          <CardTitle>Top DNS Clients</CardTitle>
          <CardDescription>Devices making the most DNS queries</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {stats.top_clients && stats.top_clients.length > 0 ? (
              stats.top_clients.map((client: any, idx: number) => (
                <div key={idx} className="flex justify-between items-center p-2 rounded hover:bg-muted/50 transition-colors">
                  <div className="font-mono text-sm">{client.client_ip}</div>
                  <div className="text-sm font-semibold">{client.query_count.toLocaleString()} queries</div>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground text-sm text-center py-4">No client activity recorded yet</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DNSStatistics;
