import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { Plus, Pencil, Trash2, Building2 } from 'lucide-react'

export function DepartmentPage() {
  const { user } = useAuth()
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const title = '部门管理'

  const [departments, setDepartments] = useState<any[]>([])
  const [myDept, setMyDept] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [deptPage, setDeptPage] = useState(1)
  const [deptPageSize, setDeptPageSize] = useState(20)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [tenants, setTenants] = useState<any[]>([])
  const [form, setForm] = useState({ name: '', code: '', description: '', tenant_id: '' })

  const fetchDepartments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.listDepartments()
      const data = res.data || []
      setDepartments(data)
      if (!isSuperAdmin && !isTenantAdmin && user?.dept_id) {
        setMyDept(data.find((d: any) => d.id === user.dept_id) || null)
      }
    } catch (err: any) {
      toast.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [isSuperAdmin, user?.dept_id])

  useEffect(() => {
    fetchDepartments()
    if (isSuperAdmin) {
      api.listTenants().then(r => setTenants(r.data || [])).catch(() => {})
    }
  }, [fetchDepartments, isSuperAdmin])

  const openCreate = () => {
    setEditing(null)
    setForm({ name: '', code: '', description: '', tenant_id: '' })
    setDialogOpen(true)
  }

  const openEdit = (d: any) => {
    setEditing(d)
    setForm({ name: d.name, code: d.code, description: d.description || '', tenant_id: '' })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('请输入部门名称'); return }
    if (!editing && !form.code.trim()) { toast.error('请输入部门编码'); return }
    if (isSuperAdmin && !editing && !form.tenant_id) { toast.error('请选择所属租户'); return }
    try {
      if (editing) {
        if (isSuperAdmin) {
          await api.updateDepartment(editing.id, form)
        } else {
          await api.updateMyDepartment(form)
        }
        toast.success('已更新')
      } else {
        await api.createDepartment(form)
        toast.success('已创建')
      }
      setDialogOpen(false)
      fetchDepartments()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDepartment(id)
      toast.success('已删除')
      fetchDepartments()
    } catch (err: any) {
      toast.error(err.message || '删除失败')
    }
  }

  // ── Dept admin view: single department card ──
  if (!isSuperAdmin && !isTenantAdmin)
    return (
      <div className="list-page animate-fade-in">
        <div className="page-section">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-balance">{title}</h1>
            <p className="text-sm text-muted-foreground mt-1">管理您所在部门的信息</p>
          </div>
        </div>

        <div className="page-section">
          <Card className="admin-table border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Building2 className="h-4 w-4 text-primary" />
                部门信息
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {loading ? (
                <p className="text-center py-8 text-muted-foreground animate-pulse">加载中…</p>
              ) : !myDept ? (
                <p className="text-center py-8 text-muted-foreground">未找到部门信息</p>
              ) : (
                <div className="flex items-start gap-6">
                  {/* Icon */}
                  <div className="flex-shrink-0">
                    <div className="h-20 w-20 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border">
                      <Building2 className="h-8 w-8 text-primary/40" />
                    </div>
                  </div>
                  {/* Info */}
                  <div className="flex-1 space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-xs text-muted-foreground">名称</Label>
                        <p className="text-sm text-foreground/80">{myDept.name}</p>
                      </div>
                      <div>
                        <Label className="text-xs text-muted-foreground">编码</Label>
                        <p className="text-sm text-foreground/80">{myDept.code}</p>
                      </div>
                    </div>
                    {myDept.description && (
                      <div>
                        <Label className="text-xs text-muted-foreground">描述</Label>
                        <p className="text-sm text-foreground/80">{myDept.description}</p>
                      </div>
                    )}
                    <Button variant="outline" size="sm" className="mt-2" onClick={() => openEdit(myDept)}>
                      <Pencil className="mr-1.5 h-3.5 w-3.5" />编辑信息
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Edit dialog */}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogContent className="sm:max-w-md">
              <DialogHeader><DialogTitle className="text-lg">编辑部门信息</DialogTitle></DialogHeader>
              <div className="space-y-4 py-2 max-md:overflow-y-auto max-md:flex-1" autoComplete="off"><div aria-hidden="true" style={{position:'absolute',left:-9999}}><input type="text" tabIndex={-1} autoComplete="username" /><input type="password" tabIndex={-1} autoComplete="current-password" /></div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">部门名称</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="focus-visible:ring-1" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">描述</Label>
                  <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} placeholder="可选" className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none" />
                </div>
              </div>
              <Button onClick={handleSave} className="w-full shadow-sm max-md:shrink-0">保存修改</Button>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    )



  // ── Super admin view: full CRUD table ──
  return (
    <div className="list-page animate-fade-in">
      <div className="list-header flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-balance">{title}</h1>
          <p className="text-sm text-muted-foreground/70 mt-0.5">管理系统中的部门组织架构</p>
        </div>
        <Button onClick={openCreate}><Plus className="mr-1 h-3 w-3" aria-hidden="true" aria-hidden="true" />新建部门</Button>
      </div>
      <div className="list-card">
        <Card className="admin-table border shadow-sm">
          <CardHeader className="bg-muted/30 border-b pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              部门列表
              
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 flex flex-col min-h-0">
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/20">
                    <TableHead className="font-medium">名称</TableHead>
                    <TableHead className="font-medium">编码</TableHead>
                    <TableHead className="font-medium hidden lg:table-cell">所属租户</TableHead>
                    <TableHead className="font-medium hidden sm:table-cell">分区</TableHead>
                    <TableHead className="font-medium">状态</TableHead>
                    <TableHead className="font-medium w-[100px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground animate-pulse">加载中…</TableCell></TableRow>
                  ) : departments.length === 0 ? (
                    <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground">暂无数据</TableCell></TableRow>
                  ) : departments.slice((deptPage - 1) * deptPageSize, deptPage * deptPageSize).map((d, idx) => (
                    <TableRow key={d.id} className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/10'}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2.5">
                          <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Building2 className="h-3.5 w-3.5 text-primary/50" />
                          </div>
                          {d.name}
                        </div>
                      </TableCell>
                      <TableCell><code className="text-xs px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">{d.code}</code></TableCell>
                      <TableCell className="hidden lg:table-cell text-muted-foreground text-sm">{d.tenant_name || '-'}</TableCell>
                      <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">{d.milvus_partition}</TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${d.status === 1 ? 'bg-success/15 text-success' : 'bg-muted/50 text-muted-foreground'}`}>
                          {d.status === 1 ? '启用' : '停用'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-0.5">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(d)}><Pencil className="h-3.5 w-3.5" aria-hidden="true" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive/70 hover:text-destructive" onClick={() => setDeleteTarget(d.id)}><Trash2 className="h-3.5 w-3.5" aria-hidden="true" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table></div>
            {departments.length > 0 && (
              <div className="flex items-center justify-end px-4 py-3 border-t bg-muted/10 gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">共 {departments.length} 条</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <select value={deptPageSize} onChange={(e) => { setDeptPageSize(Number(e.target.value)); setDeptPage(1) }}
                    className="h-7 text-xs border rounded px-1.5 bg-background text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring">
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <span className="text-xs text-muted-foreground">条/页</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={deptPage <= 1} onClick={() => setDeptPage((p) => p - 1)}>上一页</Button>
                  <span className="flex items-center px-2 text-xs text-muted-foreground">{deptPage} / {Math.ceil(departments.length / deptPageSize)}</span>
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={deptPage >= Math.ceil(departments.length / deptPageSize)} onClick={() => setDeptPage((p) => p + 1)}>下一页</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
          </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader><DialogTitle className="text-lg">{editing ? '编辑部门' : '新建部门'}</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2 max-md:overflow-y-auto max-md:flex-1" autoComplete="off"><div aria-hidden="true" style={{position:'absolute',left:-9999}}><input type="text" tabIndex={-1} autoComplete="username" /><input type="password" tabIndex={-1} autoComplete="current-password" /></div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">名称 <span className="text-destructive">*</span></Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：技术部" className="focus-visible:ring-1" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">编码 <span className="text-destructive">*</span></Label>
                  <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} disabled={!!editing} placeholder="如：tech" className="focus-visible:ring-1" />
                </div>
              {isSuperAdmin && !editing && tenants.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">所属租户 <span className="text-destructive">*</span></Label>
                  <Select value={form.tenant_id || ''} onValueChange={(val) => setForm({ ...form, tenant_id: val })}>
                    <SelectTrigger><SelectValue placeholder="选择租户" /></SelectTrigger>
                    <SelectContent>
                      {tenants.map((t) => (
                        <SelectItem key={t.id} value={t.id}>{t.name} ({t.code})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              {editing && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Milvus 分区</Label>
                  <Input value={editing.milvus_partition || 'default'} disabled className="focus-visible:ring-1 bg-muted/30" />
                  <p className="text-[10px] text-muted-foreground">创建时自动生成，不可修改</p>
                </div>
              )}
              <div className="space-y-2">
                <Label className="text-sm font-medium">描述</Label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} placeholder="可选" className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none" />
              </div>
            </div>
              <Button onClick={handleSave} className="w-full shadow-sm max-md:shrink-0">
                {editing ? '保存修改' : '创建部门'}
              </Button>
          </DialogContent>
        </Dialog>

        <ConfirmDialog
          open={!!deleteTarget}
          onOpenChange={(open) => !open && setDeleteTarget(null)}
          title="确认删除"
          description="确认删除此部门？"
          confirmText="删除"
          onConfirm={() => { if (deleteTarget) { handleDelete(deleteTarget); setDeleteTarget(null) } }}
        />
    </div>
  )
}
