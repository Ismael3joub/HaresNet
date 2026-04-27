import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { dnsFilterApi } from '@/lib/api';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Loader } from 'lucide-react';

const DNSTestFilter = () => {
  const [domain, setDomain] = useState('');
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleTest = async () => {
    if (!domain.trim()) {
      toast.error('Please enter a domain to test');
      return;
    }

    setTesting(true);
    try {
      const testResult = await dnsFilterApi.testFilter(domain);
      setResult({
        domain,
        is_blocked: testResult.is_blocked,
        matched_group: testResult.matched_group,
        matched_filter: testResult.matched_filter,
        matched_rule: testResult.matched_rule,
        reason: testResult.reason,
        timestamp: new Date(),
      });
      toast.success('Test completed');
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to test domain');
      setResult(null);
    } finally {
      setTesting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTest();
    }
  };

  return (
    <div className="space-y-6">
      {/* Test Input */}
      <Card>
        <CardHeader>
          <CardTitle>Test Domain Filtering</CardTitle>
          <CardDescription>
            Check if a domain would be blocked by your current filters
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="test-domain">Domain to Test</Label>
            <div className="flex gap-2 mt-2">
              <Input
                id="test-domain"
                placeholder="e.g., ads.example.com, tracking.service.net"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={testing}
                className="flex-1"
              />
              <Button
                onClick={handleTest}
                disabled={testing}
                className="gap-2"
              >
                {testing ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  'Test'
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Test Result */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {result.is_blocked ? (
                <>
                  <XCircle className="w-5 h-5 text-red-400" />
                  <span className="text-red-400">Domain Blocked</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <span className="text-green-400">Domain Allowed</span>
                </>
              )}
            </CardTitle>
            <CardDescription>
              {new Date(result.timestamp).toLocaleString()}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Domain */}
            <div>
              <Label className="text-xs text-gray-400">Domain</Label>
              <p className="font-mono text-sm mt-1 break-all">
                {result.domain}
              </p>
            </div>

            {/* Status */}
            <div>
              <Label className="text-xs text-gray-400">Status</Label>
              <p className={`text-sm font-medium mt-1 ${result.is_blocked ? 'text-red-400' : 'text-green-400'}`}>
                {result.is_blocked ? 'BLOCKED' : 'ALLOWED'}
              </p>
            </div>

            {/* Matched Group */}
            {result.matched_group && (
              <div>
                <Label className="text-xs text-gray-400">Matched Group</Label>
                <div className="mt-1 p-2 bg-gray-900/50 rounded border border-gray-800">
                  <p className="text-sm font-medium text-gray-300">{result.matched_group.name}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Type: {result.matched_group.group_type}
                  </p>
                </div>
              </div>
            )}

            {/* Matched Filter */}
            {result.matched_filter && (
              <div>
                <Label className="text-xs text-gray-400">Matched Filter Rule</Label>
                <div className="mt-1 p-2 bg-gray-900/50 rounded border border-gray-800">
                  <p className="text-sm font-mono break-all text-gray-300">
                    {result.matched_filter.domain}
                  </p>
                  <div className="grid grid-cols-2 gap-2 mt-2 text-xs text-gray-400">
                    <div>
                      <span className="text-gray-500">Type:</span> {result.matched_filter.pattern_type}
                    </div>
                    {result.matched_filter.reason && (
                      <div className="col-span-2">
                        <span className="text-gray-500">Reason:</span> {result.matched_filter.reason}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Source Blocklist */}
            {result.matched_rule?.blocklist && (
              <div>
                <Label className="text-xs text-gray-400">Source Blocklist</Label>
                <div className="mt-1 p-2 bg-gray-900/50 rounded border border-gray-800">
                  <p className="text-sm text-gray-300">{result.matched_rule.blocklist.name}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Category: {result.matched_rule.blocklist.category}
                  </p>
                </div>
              </div>
            )}

            {/* Reason */}
            {result.reason && (
              <div>
                <Label className="text-xs text-gray-400">Reason</Label>
                <p className="text-sm mt-1 text-gray-300">
                  {result.reason}
                </p>
              </div>
            )}

            {/* No Match Message */}
            {!result.is_blocked && !result.matched_group && (
              <div className="p-3 bg-green-900/20 border border-green-800 rounded">
                <p className="text-sm text-green-400">
                  This domain does not match any filter rules and will be allowed.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Help */}
      <Card className="bg-blue-900/10 border-blue-900/30">
        <CardHeader>
          <CardTitle>Examples to Try</CardTitle>
          <CardDescription>Test with these common domains</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p className="text-xs text-gray-400">Click a domain to test it:</p>
            <div className="flex flex-wrap gap-2">
              {['ads.google.com', 'analytics.google.com', 'facebook.com', 'google.com'].map((d) => (
                <button
                  key={d}
                  onClick={() => {
                    setDomain(d);
                  }}
                  className="px-3 py-1 bg-blue-900/30 hover:bg-blue-900/50 border border-blue-800 rounded text-sm text-blue-300 transition-colors"
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DNSTestFilter;
