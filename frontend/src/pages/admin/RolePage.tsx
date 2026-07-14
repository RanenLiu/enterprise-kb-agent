import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Pencil, Trash2, Shield } from 'lucide-react'

export function RolePage() {
  const [roles, setRoles] = useState<any[]>([])
  const [permissions, setPermissions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [rolePage, setRolePage] = useState(1)
  const [rolePageSize, setRolePageSize] = useState(20)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', code: '', description: '', sort_order: 0 })
  const [selectedPerms, setSelectedPerms] = useState<string[]>([])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [r, p] = await Promise.all([api.listRoles(), api.listPermissions()])
      setRoles(r.data || [])
      setPermissions(p.data || [])
    } catch (err: any) {
      toast.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const openCreate = () => {
    setEditing(null)
    setForm({ name: '', code: '', description: '', sort_order: 0 })
    setSelectedPerms([])
    setDialogOpen(true)
  }

  const openEdit = async (r: any) => {
    setEditing(r)
    setForm({ name: r.name, code: r.code, description: r.description || '', sort_order: r.sort_order })
    try {
      const res = await api.getRole(r.id)
      setSelectedPerms(res.data?.permission_ids || [])
    } catch {
      setSelectedPerms([])
    }
    setDialogOpen(true)
  }

  const togglePerm = (permId: string) => {
    setSelectedPerms((p) => p.includes(permId) ? p.filter((x) => x !== permId) : [...p, permId])
  }

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('请输入角色名称'); return }
    if (!editing && !form.code.trim()) { toast.error('请输入角色编码'); return }
    try {
      const data = { ...form, permission_ids: selectedPerms }
      if (editing) {
        await api.updateRole(editing.id, data)
        toast.success('已更新')
      } else {
        await api.createRole(data)
        toast.success('已创建')
      }
      setDialogOpen(false)
      fetchData()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteRole(id)
      toast.success('已删除')
      fetchData()
    } catch (err: any) {
      toast.error(err.message || '删除失败')
    }
  }

  const groupedPerms = permissions.reduce((acc: any, p: any) => {
    if (!acc[p.group]) acc[p.group] = []
    acc[p.group].push(p)
    return acc
  }, {} as Record<string, any[]>)

  return (
    <div className="list-page animate-fade-in">
      <div className="list-header flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">角色管理</h1>
          <p className="text-sm text-muted-foreground mt-1">定义角色及其权限范围</p>
        </div>
        <Button onClick={openCreate}>+ 新建角色</Button>
      </div>
      <div className="list-card">
        <Card className="admin-table border shadow-sm overflow-hidden">
          <CardHeader className="bg-muted/30 border-b pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              角色列表
              
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 flex flex-col min-h-0">
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/20">
                    <TableHead className="font-medium w-[20%]">名称</TableHead>
                    <TableHead className="font-medium w-[12%]">编码</TableHead>
                    <TableHead className="font-medium hidden md:table-cell w-[35%]">描述</TableHead>
                    <TableHead className="font-medium w-[8%]">内置</TableHead>
                    <TableHead className="font-medium hidden sm:table-cell w-[8%]">排序</TableHead>
                    <TableHead className="font-medium w-[12%]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground animate-pulse">加载中...</TableCell></TableRow>
                  ) : roles.length === 0 ? (
                    <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground">暂无角色数据</TableCell></TableRow>
                  ) : roles.slice((rolePage - 1) * rolePageSize, rolePage * rolePageSize).map((r, idx) => (
                    <TableRow key={r.id} className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/10'}>
                      <TableCell className="font-medium">{r.name}</TableCell>
                      <TableCell><code className="text-xs px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">{r.code}</code></TableCell>
                      <TableCell className="hidden md:table-cell text-muted-foreground text-sm">{r.description || '-'}</TableCell>
                      <TableCell>{r.is_system ? <Badge variant="secondary" className="text-xs">系统</Badge> : <Badge variant="outline" className="text-xs">自定义</Badge>}</TableCell>
                      <TableCell className="hidden sm:table-cell text-sm">{r.sort_order}</TableCell>
                      <TableCell>
                        <div className="flex gap-0.5">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(r)}><Pencil className="h-3.5 w-3.5" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive/70 hover:text-destructive" onClick={() => setDeleteTarget(r.id)} disabled={r.is_system}><Trash2 className="h-3.5 w-3.5" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table></div>
            {roles.length > 0 && (
              <div className="flex items-center justify-end px-4 py-3 border-t bg-muted/10 gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">共 {roles.length} 条</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <select value={rolePageSize} onChange={(e) => { setRolePageSize(Number(e.target.value)); setRolePage(1) }}
                    className="h-7 text-xs border rounded px-1.5 bg-background text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring">
                    <option value={10}>10</option><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option>
                  </select>
                  <span className="text-xs text-muted-foreground">条/页</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={rolePage <= 1} onClick={() => setRolePage((p) => p - 1)}>上一页</Button>
                  <span className="flex items-center px-2 text-xs text-muted-foreground">{rolePage} / {Math.ceil(roles.length / rolePageSize) || 1}</span>
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={rolePage >= Math.ceil(roles.length / rolePageSize)} onClick={() => setRolePage((p) => p + 1)}>下一页</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

          </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="text-lg">{editing ? '编辑角色' : '新建角色'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2" autoComplete="off"><div aria-hidden="true" style={{position:'absolute',left:-9999}}><input type="text" tabIndex={-1} autoComplete="username" /><input type="password" tabIndex={-1} autoComplete="current-password" /></div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">名称 <span className="text-destructive">*</span></Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：部门管理员" className="focus-visible:ring-1" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">编码 <span className="text-destructive">*</span></Label>
                  <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="dept_admin" disabled={!!editing} className="focus-visible:ring-1" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">排序</Label>
                  <Input type="number" value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) })} className="focus-visible:ring-1" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">描述</Label>
                  <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} placeholder="可选" className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none" />
                </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">权限</Label>
                <div className="max-h-52 overflow-y-auto border rounded-lg p-3 space-y-3 bg-muted/20">
                  {Object.entries(groupedPerms).map(([group, perms]: [string, any]) => (
                    <div key={group}>
                      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">{group}</p>
                      <div className="grid grid-cols-2 gap-1">
                        {perms.map((p: any) => (
                          <label key={p.id} className="flex items-center gap-2 py-1 px-1 text-sm rounded hover:bg-background cursor-pointer transition-colors">
                            <Checkbox checked={selectedPerms.includes(p.id)} onCheckedChange={() => togglePerm(p.id)} />
                            <span className="truncate">{p.name}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <Button onClick={handleSave} className="w-full mt-2 shadow-sm">
                {editing ? '保存修改' : '创建角色'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        <ConfirmDialog
          open={!!deleteTarget}
          onOpenChange={(open) => !open && setDeleteTarget(null)}
          title="确认删除"
          description="确认删除此角色？"
          confirmText="删除"
          onConfirm={() => { if (deleteTarget) { handleDelete(deleteTarget); setDeleteTarget(null) } }}
        />
    </div>
  )
}
