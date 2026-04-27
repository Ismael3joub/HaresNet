import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { dnsFilterApi } from '@/lib/api';
import { toast } from 'sonner';
import { Plus, RefreshCw, Trash2, Download, ExternalLink, ShieldAlert } from 'lucide-react';

const DNSBlocklists = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    category: 'custom',
    description: '',
  });

  const queryClient = useQueryClient();

  const { data: { blocklists = [] } = {}, isLoading } = useQuery({
    queryKey: ['dns-blocklists'],
    queryFn: () => dnsFilterApi.getBlocklists(),
  });

  const addDefaultMutation = useMutation({
    mutationFn: () => dnsFilterApi.addDefaultBlocklists(),
    onSuccess: () => {
      toast.success('Default blocklists added successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-blocklists'] });
    },
    onError: () => toast.error('Failed to add default blocklists'),
  });

  const addBlocklistMutation = useMutation({
    mutationFn: (data: any) => dnsFilterApi.addBlocklist(data),
    onSuccess: () => {
      toast.success('Blocklist added successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-blocklists'] });
      setIsDialogOpen(false);
      setFormData({ name: '', url: '', category: 'custom', description: '' });
    },
    onError: () => toast.error('Failed to add blocklist'),
  });

  const fetchBlocklistMutation = useMutation({
    mutationFn: (id: number) => dnsFilterApi.fetchBlocklist(id),
    onSuccess: (data) => {
      toast.success(`Loaded ${data.domains_added} domains from blocklist`);
      queryClient.invalidateQueries({ queryKey: ['dns-blocklists'] });
    },
    onError: () => toast.error('Failed to fetch blocklist'),
  });

  const deleteBlocklistMutation = useMutation({
    mutationFn: (id: number) => dnsFilterApi.deleteBlocklist(id),
    onSuccess: () => {
      toast.success('Blocklist deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-blocklists'] });
    },
    onError: () => toast.error('Failed to delete blocklist'),
  });

  const handleAddBlocklist = () => {
    if (!formData.name || !formData.url) {
      toast.error('Name and URL are required');
      return;
    }
    addBlocklistMutation.mutate(formData);
  };

  return (
    <div className="space-y-4">
      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <div className="flex gap-2">
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="w-4 h-4" />
                Add Custom Blocklist
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Add Custom Blocklist</DialogTitle>
                <DialogDescription>Add a custom blocklist from a URL</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., My Custom List"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="url">URL *</Label>
                  <Input
                    id="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    placeholder="https://example.com/blocklist.txt"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Input
                    id="category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    placeholder="custom"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Optional description"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleAddBlocklist} disabled={addBlocklistMutation.isPending}>
                  {addBlocklistMutation.isPending ? 'Adding...' : 'Add Blocklist'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Button variant="outline" onClick={() => addDefaultMutation.mutate()} disabled={addDefaultMutation.isPending}>
            <Download className="w-4 h-4 mr-2" />
            Add Default Lists
          </Button>
        </div>

        <div className="text-sm text-muted-foreground">
          {blocklists.length} List{blocklists.length !== 1 && 's'} Configured
        </div>
      </div>

      {/* Blocklists Table */}
      <Card>
        <CardHeader>
          <CardTitle>Blocklists</CardTitle>
          <CardDescription>Manage external blocklist sources</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading blocklists...</div>
          ) : blocklists.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <ShieldAlert className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">No blocklists configured</p>
              <p className="text-sm">Add a blocklist to start filtering bad domains.</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Name</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Category</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Domains</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Last Updated</th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {blocklists.map((bl: any) => (
                    <tr key={bl.id} className="border-b last:border-0 hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-medium">{bl.name}</div>
                        <div className="text-xs text-muted-foreground truncate max-w-[200px]" title={bl.url}>{bl.url}</div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary" className="font-normal capitalize">{bl.category}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="font-mono">
                          {bl.domain_count?.toLocaleString() || 0}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {bl.last_updated ? new Date(bl.last_updated).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => fetchBlocklistMutation.mutate(bl.id)}
                            disabled={fetchBlocklistMutation.isPending}
                            title="Update list"
                          >
                            <RefreshCw className={`w-4 h-4 ${fetchBlocklistMutation.isPending ? 'animate-spin' : ''}`} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-red-400 hover:text-red-300 hover:bg-red-950/20"
                            onClick={() => deleteBlocklistMutation.mutate(bl.id)}
                            disabled={deleteBlocklistMutation.isPending}
                            title="Delete list"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DNSBlocklists;
