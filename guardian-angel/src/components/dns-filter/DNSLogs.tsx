import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { dnsFilterApi } from '@/lib/api';
import { RefreshCw, Download, Search, Filter, ShieldAlert, ShieldCheck } from 'lucide-react';

const DNSLogs = () => {
  const [page, setPage] = useState(1);
  const [domainFilter, setDomainFilter] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [blockedOnly, setBlockedOnly] = useState(false);
  const [hoursBack, setHoursBack] = useState('24');

  const [isLive, setIsLive] = useState(false);

  const { data: logsData = {}, isLoading, refetch } = useQuery({
    queryKey: ['dns-logs', page, domainFilter, clientFilter, blockedOnly, hoursBack],
    queryFn: () => dnsFilterApi.getLogs({
      domain: domainFilter || undefined,
      client_ip: clientFilter || undefined,
      blocked_only: blockedOnly || undefined,
      hours_back: parseInt(hoursBack),
      page,
      per_page: 100,
    }),
    refetchInterval: isLive ? 2000 : 30000,
  });

  const logs = logsData.logs || [];
  const pagination = logsData.pagination || {};

  const handleDownloadCSV = () => {
    if (logs.length === 0) return;

    const headers = ['Timestamp', 'Domain', 'Client IP', 'Response', 'Blocked', 'Filter Group', 'Response Type'];
    const rows = logs.map((log: any) => [
      new Date(log.timestamp).toLocaleString(),
      log.domain,
      log.client_ip,
      log.response || '-',
      log.is_blocked ? 'Yes' : 'No',
      log.matched_group?.name || '-',
      log.response_type || '-',
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dns-logs-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const getStatusColor = (blocked: boolean) => {
    return blocked ? 'text-red-400' : 'text-green-400';
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div className="space-y-2">
            <Label htmlFor="domain-filter">Domain</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="domain-filter"
                placeholder="Filter by domain..."
                value={domainFilter}
                onChange={(e) => {
                  setDomainFilter(e.target.value);
                  setPage(1);
                }}
                className="pl-9"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="client-filter">Client IP</Label>
            <Input
              id="client-filter"
              placeholder="Filter by IP..."
              value={clientFilter}
              onChange={(e) => {
                setClientFilter(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hours-back">Time Range</Label>
            <Select value={hoursBack} onValueChange={(v) => { setHoursBack(v); setPage(1); }}>
              <SelectTrigger id="hours-back">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Last 1 hour</SelectItem>
                <SelectItem value="6">Last 6 hours</SelectItem>
                <SelectItem value="24">Last 24 hours</SelectItem>
                <SelectItem value="168">Last 7 days</SelectItem>
                <SelectItem value="720">Last 30 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Checkbox
                id="blocked-only"
                checked={blockedOnly}
                onCheckedChange={(v) => {
                  setBlockedOnly(v as boolean);
                  setPage(1);
                }}
              />
              <Label htmlFor="blocked-only" className="cursor-pointer text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Show Blocked Only
              </Label>
            </div>
            <div className="flex gap-2">
              <Button
                variant={isLive ? "default" : "outline"}
                size="sm"
                onClick={() => setIsLive(!isLive)}
                className="gap-2 flex-1"
              >
                <RefreshCw className={`w-4 h-4 ${isLive ? 'animate-spin' : ''}`} />
                {isLive ? 'Live' : 'Refresh'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadCSV}
                disabled={logs.length === 0}
                className="gap-2 flex-1"
              >
                <Download className="w-4 h-4" />
                CSV
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>DNS Query Logs</CardTitle>
          <CardDescription>
            Recent DNS queries and blocking activity ({pagination.total ? pagination.total.toLocaleString() : logs.length} logs)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading logs...</div>
          ) : logs.length === 0 ? (
            <div className="text-center text-muted-foreground py-12">No logs found matching your criteria</div>
          ) : (
            <div className="space-y-4">
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 border-b">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground w-40">Timestamp</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground flex-1">Domain</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground w-32">Client IP</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground w-24">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground w-24">Type</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground w-32">Group</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log: any) => (
                      <tr key={log.id} className="border-b last:border-0 hover:bg-muted/50 transition-colors">
                        <td className="py-2.5 px-4 text-xs text-muted-foreground whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-xs break-all">
                          <span className={log.is_blocked ? 'text-red-400' : ''}>{log.domain}</span>
                        </td>
                        <td className="py-2.5 px-4 font-mono text-xs">
                          {log.client_ip}
                        </td>
                        <td className={`py-2.5 px-4 font-medium`}>
                          <div className={`flex items-center gap-1.5 ${getStatusColor(log.is_blocked)}`}>
                            {log.is_blocked ? <ShieldAlert className="w-3 h-3" /> : <ShieldCheck className="w-3 h-3" />}
                            <span className="text-xs uppercase">{log.is_blocked ? 'BLOCKED' : 'ALLOWED'}</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-xs text-muted-foreground w-24">
                          {log.response_type || 'A'}
                        </td>
                        <td className="py-2.5 px-4 text-xs w-32">
                          {log.matched_group?.name ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] h-5 font-normal border"
                              style={{
                                borderColor: log.matched_group.color || '#e2e8f0',
                                backgroundColor: log.matched_group.color ? `${log.matched_group.color}10` : 'transparent',
                                color: log.matched_group.color || 'inherit'
                              }}
                            >
                              {log.matched_group.name}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {pagination.pages && pagination.pages > 1 && (
                <div className="flex justify-center gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="py-2 px-4 text-sm text-muted-foreground">
                    Page {page} of {pagination.pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= pagination.pages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DNSLogs;
