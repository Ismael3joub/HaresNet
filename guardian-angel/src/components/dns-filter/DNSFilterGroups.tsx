import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { dnsFilterApi } from '@/lib/api';
import { toast } from 'sonner';
import { Plus, Trash2, Edit2, Shield, ShieldCheck, ShieldAlert, Layers } from 'lucide-react';

const DNSFilterGroups = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    list_type: 'blocklist',
    enabled: true,
    color: '#64748b',
  });

  const queryClient = useQueryClient();

  const { data: { groups = [] } = {}, isLoading } = useQuery({
    queryKey: ['dns-groups'],
    queryFn: () => dnsFilterApi.getGroups(),
  });

  const createGroupMutation = useMutation({
    mutationFn: (data: any) => dnsFilterApi.createGroup(data),
    onSuccess: () => {
      toast.success('Group created successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-groups'] });
      setIsDialogOpen(false);
      resetForm();
    },
    onError: () => toast.error('Failed to create group'),
  });

  const updateGroupMutation = useMutation({
    mutationFn: ({ id, data }: any) => dnsFilterApi.updateGroup(id, data),
    onSuccess: () => {
      toast.success('Group updated successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-groups'] });
      setIsDialogOpen(false);
      setEditingId(null);
      resetForm();
    },
    onError: () => toast.error('Failed to update group'),
  });

  const deleteGroupMutation = useMutation({
    mutationFn: (id: number) => dnsFilterApi.deleteGroup(id),
    onSuccess: () => {
      toast.success('Group deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-groups'] });
    },
    onError: () => toast.error('Failed to delete group'),
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      list_type: 'blocklist',
      enabled: true,
      color: '#64748b',
    });
  };

  const handleSave = () => {
    if (!formData.name) {
      toast.error('Name is required');
      return;
    }

    if (editingId) {
      updateGroupMutation.mutate({ id: editingId, data: formData });
    } else {
      createGroupMutation.mutate(formData);
    }
  };

  const handleEdit = (group: any) => {
    setFormData(group);
    setEditingId(group.id);
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
      <div className="flex justify-between items-center">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2" onClick={handleNew}>
              <Plus className="w-4 h-4" />
              New Filter Group
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>{editingId ? 'Edit' : 'Create'} Filter Group</DialogTitle>
              <DialogDescription>
                {editingId ? 'Edit this filter group' : 'Create a new filter group to organize your domains'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., My Blocklist"
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
              <div className="space-y-2">
                <Label>Type</Label>
                <div className="flex gap-4 mt-2">
                  <label className="flex items-center gap-2 cursor-pointer p-2 rounded hover:bg-muted">
                    <input
                      type="radio"
                      name="list_type"
                      value="blocklist"
                      checked={formData.list_type === 'blocklist'}
                      onChange={(e) => setFormData({ ...formData, list_type: e.target.value })}
                      className="accent-primary"
                    />
                    <div className="flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-red-400" />
                      <span>Blocklist</span>
                    </div>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer p-2 rounded hover:bg-muted">
                    <input
                      type="radio"
                      name="list_type"
                      value="allowlist"
                      checked={formData.list_type === 'allowlist'}
                      onChange={(e) => setFormData({ ...formData, list_type: e.target.value })}
                      className="accent-primary"
                    />
                    <div className="flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-green-400" />
                      <span>Allowlist</span>
                    </div>
                  </label>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="color">Color</Label>
                <div className="flex gap-2 items-center">
                  <Input
                    id="color"
                    type="color"
                    value={formData.color}
                    onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    className="w-12 h-10 p-1 cursor-pointer"
                  />
                  <Input
                    value={formData.color}
                    onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    placeholder="#000000"
                    className="flex-1 font-mono"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2 py-2">
                <Checkbox
                  id="enabled"
                  checked={formData.enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, enabled: checked as boolean })}
                />
                <Label htmlFor="enabled" className="cursor-pointer">Enabled</Label>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleSave} disabled={createGroupMutation.isPending || updateGroupMutation.isPending}>
                {editingId ? 'Update' : 'Create'} Group
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <div className="text-sm text-muted-foreground">
          {groups.length} Group{groups.length !== 1 && 's'} Configured
        </div>
      </div>

      {/* Groups Table */}
      <Card>
        <CardHeader>
          <CardTitle>Filter Groups</CardTitle>
          <CardDescription>Organized collections of domain filters</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading groups...</div>
          ) : groups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <Layers className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">No filter groups</p>
              <p className="text-sm">Create a group to start adding domain filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground w-[30%]">Name</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Filters</th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Status</th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((group: any) => (
                    <tr key={group.id} className="border-b last:border-0 hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full border shadow-sm"
                            style={{ backgroundColor: group.color || '#64748b' }}
                            title="Group Color"
                          />
                          <div>
                            <div className="font-medium">{group.name}</div>
                            {group.description && (
                              <div className="text-xs text-muted-foreground">{group.description}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={group.list_type === 'blocklist' ? 'destructive' : 'default'} className="capitalize">
                          {group.list_type}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="font-mono">
                          {group.filter_count?.toLocaleString() || 0}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <div className={`w-2 h-2 rounded-full ${group.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />
                          <span className={group.enabled ? 'text-green-500 font-medium' : 'text-muted-foreground'}>
                            {group.enabled ? 'Active' : 'Disabled'}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(group)}
                            title="Edit group"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => deleteGroupMutation.mutate(group.id)}
                            className="text-red-400 hover:text-red-300 hover:bg-red-950/20"
                            title="Delete group"
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

export default DNSFilterGroups;
