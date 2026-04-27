import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { dnsFilterApi } from '@/lib/api';
import { toast } from 'sonner';
import { Plus, Trash2, Edit2, Filter, Search } from 'lucide-react';

const DNSFilters = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [formData, setFormData] = useState({
    group_id: 0,
    domain: '',
    pattern_type: 'exact',
    regex_pattern: '',
    enabled: true,
    blocking_enabled: true,
    reason: '',
  });

  const queryClient = useQueryClient();

  const { data: { groups = [] } = {} } = useQuery({
    queryKey: ['dns-groups'],
    queryFn: () => dnsFilterApi.getGroups(),
  });

  const { data: filtersData = {}, isLoading } = useQuery({
    queryKey: ['dns-filters', selectedGroupId, page],
    queryFn: () => dnsFilterApi.getFilters({
      group_id: selectedGroupId || undefined,
      page,
      per_page: 50,
    }),
  });

  const createFilterMutation = useMutation({
    mutationFn: (data: any) => dnsFilterApi.createFilter(data),
    onSuccess: () => {
      toast.success('Filter created successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-filters'] });
      setIsDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => toast.error(error.response?.data?.error || 'Failed to create filter'),
  });

  const updateFilterMutation = useMutation({
    mutationFn: ({ id, data }: any) => dnsFilterApi.updateFilter(id, data),
    onSuccess: () => {
      toast.success('Filter updated successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-filters'] });
      setIsDialogOpen(false);
      setEditingId(null);
      resetForm();
    },
    onError: () => toast.error('Failed to update filter'),
  });

  const deleteFilterMutation = useMutation({
    mutationFn: (id: number) => dnsFilterApi.deleteFilter(id),
    onSuccess: () => {
      toast.success('Filter deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-filters'] });
    },
    onError: () => toast.error('Failed to delete filter'),
  });

  const resetForm = () => {
    setFormData({
      group_id: selectedGroupId || (groups.length > 0 ? groups[0].id : 0),
      domain: '',
      pattern_type: 'exact',
      regex_pattern: '',
      enabled: true,
      blocking_enabled: true,
      reason: '',
    });
  };

  const handleSave = () => {
    if (!formData.group_id || !formData.domain) {
      toast.error('Group and domain are required');
      return;
    }

    if (formData.pattern_type === 'regex' && !formData.regex_pattern) {
      toast.error('Regex pattern is required for regex type');
      return;
    }

    if (editingId) {
      updateFilterMutation.mutate({ id: editingId, data: formData });
    } else {
      createFilterMutation.mutate(formData);
    }
  };

  const handleEdit = (filter: any) => {
    setFormData(filter);
    setEditingId(filter.id);
    setIsDialogOpen(true);
  };

  const handleNew = () => {
    resetForm();
    setEditingId(null);
    setIsDialogOpen(true);
  };

  return (
    <div className="space-y-4">
      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2" onClick={handleNew}>
              <Plus className="w-4 h-4" />
              Add Filter
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingId ? 'Edit' : 'Create'} Filter</DialogTitle>
              <DialogDescription>
                {editingId ? 'Modify existing filter rule' : 'Add a new filter rule to a group'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Group *</Label>
                  <Select
                    value={String(formData.group_id)}
                    onValueChange={(v) => setFormData({ ...formData, group_id: parseInt(v) })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a group" />
                    </SelectTrigger>
                    <SelectContent>
                      {groups.map((g: any) => (
                        <SelectItem key={g.id} value={String(g.id)}>
                          {g.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Pattern Type</Label>
                  <Select
                    value={formData.pattern_type}
                    onValueChange={(v) => setFormData({ ...formData, pattern_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="exact">Exact Match</SelectItem>
                      <SelectItem value="wildcard">Wildcard (*.domain.com)</SelectItem>
                      <SelectItem value="regex">Regular Expression</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Domain *</Label>
                <Input
                  value={formData.domain}
                  onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  placeholder="e.g., ads.example.com"
                  className="font-mono"
                />
              </div>

              {formData.pattern_type === 'regex' && (
                <div className="space-y-2">
                  <Label>Regex Pattern *</Label>
                  <Input
                    value={formData.regex_pattern}
                    onChange={(e) => setFormData({ ...formData, regex_pattern: e.target.value })}
                    placeholder="e.g., ^tracker[0-9]+\.example\.com$"
                    className="font-mono"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label>Reason</Label>
                <Input
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  placeholder="e.g., Advertisement server"
                />
              </div>

              <div className="flex gap-6 pt-2">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="filter-enabled"
                    checked={formData.enabled}
                    onCheckedChange={(v) => setFormData({ ...formData, enabled: v as boolean })}
                  />
                  <Label htmlFor="filter-enabled" className="cursor-pointer">Enabled</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="blocking-enabled"
                    checked={formData.blocking_enabled}
                    onCheckedChange={(v) => setFormData({ ...formData, blocking_enabled: v as boolean })}
                  />
                  <Label htmlFor="blocking-enabled" className="cursor-pointer">Blocking Active</Label>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleSave} disabled={createFilterMutation.isPending || updateFilterMutation.isPending}>
                {editingId ? 'Update' : 'Create'} Filter
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <div className="flex gap-2 w-full sm:w-auto">
          {groups.length > 0 && (
            <div className="relative w-full sm:w-64">
              <Select
                value={selectedGroupId ? String(selectedGroupId) : 'all'}
                onValueChange={(v) => {
                  setSelectedGroupId(v === 'all' ? null : parseInt(v));
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Filter className="w-4 h-4" />
                    <SelectValue placeholder="Filter by group..." />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  {groups.map((g: any) => (
                    <SelectItem key={g.id} value={String(g.id)}>
                      {g.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </div>

      {/* Filters Table */}
      <Card>
        <CardHeader>
          <CardTitle>Domain Filters</CardTitle>
          <CardDescription>Individual domain filtering rules</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading filters...</div>
          ) : !filtersData.filters || filtersData.filters.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <Search className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">No filters found</p>
              <p className="text-sm">Try adjusting your search or add a new filter.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 border-b">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground">Domain</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground">Type</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground">Hits</th>
                      <th className="text-left py-3 px-4 font-medium text-muted-foreground">Status</th>
                      <th className="text-right py-3 px-4 font-medium text-muted-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtersData.filters.map((filter: any) => (
                      <tr key={filter.id} className="border-b last:border-0 hover:bg-muted/50 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-mono text-xs">{filter.domain}</div>
                          {filter.reason && <div className="text-xs text-muted-foreground mt-0.5">{filter.reason}</div>}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="secondary" className="font-normal text-xs">{filter.pattern_type}</Badge>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs">{filter.hit_count}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-1.5">
                            <div className={`w-2 h-2 rounded-full ${filter.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />
                            <span className={filter.enabled ? 'text-green-500 font-medium' : 'text-muted-foreground'}>
                              {filter.enabled ? 'Active' : 'Disabled'}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleEdit(filter)}
                              title="Edit filter"
                            >
                              <Edit2 className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => deleteFilterMutation.mutate(filter.id)}
                              className="text-red-400 hover:text-red-300 hover:bg-red-950/20"
                              title="Delete filter"
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

              {/* Pagination */}
              {filtersData.pagination && filtersData.pagination.pages > 1 && (
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
                    Page {page} of {filtersData.pagination.pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= filtersData.pagination.pages}
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

export default DNSFilters;
