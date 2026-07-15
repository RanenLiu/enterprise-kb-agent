import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Plus, Pencil, Trash2, Users, KeyRound, RotateCcw, Search } from 'lucide-react'

export function UserPage() {
  const [users, setUsers] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [statusFilter, setStatusFilter] = useState('active')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [userPage, setUserPage] = useState(1)
  const [userPageSize, setUserPageSize] = useState(20)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [resetPwdOpen, setResetPwdOpen] = useState(false)
  const [resetPwdUser, setResetPwdUser] = useState<any | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [form, setForm] = useState({ username: '', password: '', display_name: '', email: '', phone: '', dept_id: '' })
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [deptError, setDeptError] = useState(false)

  const { user } = useAuth()
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const isDeptAdmin = user?.roles?.includes('dept_admin')
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [u, d] = await Promise.all([api.listUsers(), api.listDepartments()])
      setUsers(u.data || [])
      setDepartments(d.data || [])
    } catch (err: any) {
      toast.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
    // Roles — only load for users with role.read permission
    if (user?.permissions?.includes('role.read')) {
      try {
        const r = await api.listRoles()
        setRoles(r.data || [])
      } catch {
        setRoles([])
      }
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const openCreate = async () => {
    setEditing(null)
    setForm({ username: '', password: '', display_name: '', email: '', phone: '', dept_id: user?.dept_id || '' })
    setSelectedRoles([])
    try {
      const res = await api.getNextEpNumber()
      setForm((prev) => ({ ...prev, username: res.data }))
    } catch {
      toast.error('获取编号失败，请重试')
    }
    setDialogOpen(true)
  }

  const openEdit = (u: any) => {
    setEditing(u)
    setForm({ username: u.username, password: '', display_name: u.display_name, email: u.email || '', phone: u.phone || '', dept_id: u.dept_id || '' })
    setSelectedRoles(u.role_ids || [])
    setDialogOpen(true)
  }

  const handleSave = async () => {
    try {
      if (!form.dept_id) {
        setDeptError(true)
        return
      }
      setDeptError(false)
      let roleIds = selectedRoles
      if (!editing && roleIds.length === 0) {
        // Default to dept_viewer if no role selected
        const viewerRole = roles.find((r: any) => r.code === 'dept_viewer')
        if (viewerRole) roleIds = [viewerRole.id]
      }
      const data = { ...form, role_ids: roleIds }
      if (!editing) data.password = data.password || 'admin123'
      if (editing) {
        await api.updateUser(editing.id, { display_name: data.display_name, email: data.email, phone: data.phone, dept_id: data.dept_id || null, role_ids: roleIds })
        toast.success('已更新')
      } else {
        await api.createUser(data)
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
      await api.deleteUser(id)
      toast.success('已删除')
      fetchData()
    } catch (err: any) {
      toast.error(err.message || '删除失败')
    }
  }

  // Compute visible roles based on current user's role
  const allowedRoleCodes = isSuperAdmin
    ? ['tenant_admin', 'dept_admin', 'dept_editor', 'dept_viewer']
    : isTenantAdmin
      ? ['dept_admin', 'dept_editor', 'dept_viewer']
      : isDeptAdmin
        ? ['dept_editor', 'dept_viewer']
        : []

  const filteredUsers = users
    .filter((u) => {
      if (statusFilter === 'active') return u.status === 1
      if (statusFilter === 'disabled') return u.status === 0
      return true
    }).filter((u) => {
      if (!searchKeyword) return true
      const kw = searchKeyword.toLowerCase()
      return u.username.toLowerCase().includes(kw) || (u.display_name || '').includes(kw)
    }).filter((u) => {
      if (!roleFilter) return true
      return (u.role_ids || []).includes(roleFilter)
    }).sort((a, b) => {
      if (a.id === user?.id) return -1
      if (b.id === user?.id) return 1
      return 0
    })

  const userTotalPages = Math.ceil(filteredUsers.length / userPageSize)
  const pagedUsers = filteredUsers.slice((userPage - 1) * userPageSize, userPage * userPageSize)

  const handleSearch = () => { setUserPage(1) }
  const handleUserReset = () => { setSearchKeyword(''); setRoleFilter(''); setStatusFilter('active'); setUserPage(1) }

  const handleResetPassword = async () => {
    if (!resetPwdUser || newPassword.length < 6) return toast.error('密码至少 6 位')
    try {
      await api.resetPassword(resetPwdUser.id, newPassword)
      toast.success('密码已重置')
      setResetPwdOpen(false)
      setNewPassword('')
    } catch (err: any) {
      toast.error(err.message || '重置失败')
    }
  }

  const toggleRole = (roleId: string) => {
    setSelectedRoles((r) => r.includes(roleId) ? r.filter((x) => x !== roleId) : [...r, roleId])
  }


  return (
    <div className="list-page animate-fade-in">
      <div className="list-header flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">用户管理</h1>
          <p className="text-sm text-muted-foreground mt-1">管理系统中的用户账号</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={openCreate}><Plus className="mr-1 h-3 w-3" />新建用户</Button>
        </div>
      </div>
      <div className="list-card">
        <Card className="admin-table border shadow-sm">
          <CardHeader className="bg-muted/30 border-b pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4 text-primary" />
                用户列表
                
              </CardTitle>
            </div>
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <Input
                placeholder="搜索用户名/姓名..."
                className="h-8 w-48 text-xs"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
              />
              {roles.length > 0 && (
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                  <SelectTrigger size="sm" className="w-28 text-xs">
                    <SelectValue placeholder="全部角色" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="" className="text-xs">全部角色</SelectItem>
                    {roles.map((r: any) => (
                      <SelectItem key={r.id} value={r.id} className="text-xs">{r.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger size="sm" className="w-24 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active" className="text-xs">启用</SelectItem>
                  <SelectItem value="disabled" className="text-xs">停用</SelectItem>
                  <SelectItem value="all" className="text-xs">全部</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2">
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={handleSearch}><Search className="h-3 w-3 mr-1" />搜索</Button>
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={handleUserReset}>
                  <RotateCcw className="mr-1 h-3 w-3" />重置
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 flex-1 flex flex-col min-h-0">
            <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20">
                  <TableHead className="font-medium w-[12%]">用户名</TableHead>
                  <TableHead className="font-medium w-[12%]">真实姓名</TableHead>
                  <TableHead className="font-medium hidden md:table-cell w-[18%]">邮箱</TableHead>
                  <TableHead className="font-medium hidden sm:table-cell w-[12%]">部门</TableHead>
                  <TableHead className="font-medium hidden md:table-cell w-[18%]">角色</TableHead>
                  <TableHead className="font-medium w-[8%]">状态</TableHead>
                  <TableHead className="font-medium w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={7} className="text-center py-12 text-muted-foreground animate-pulse">加载中...</TableCell></TableRow>
                ) : filteredUsers.length === 0 ? (
                  <TableRow><TableCell colSpan={7} className="text-center py-12 text-muted-foreground">暂无用户数据</TableCell></TableRow>
                ) : pagedUsers.map((u, idx) => (
                  <TableRow key={u.id} className={`${u.id === user?.id ? 'bg-primary/5 ring-1 ring-primary/20' : idx % 2 === 0 ? 'bg-background' : 'bg-muted/10'}`}>
                    <TableCell className="font-medium">{u.username}</TableCell>
                    <TableCell>{u.display_name}</TableCell>
                    <TableCell className="hidden md:table-cell text-muted-foreground text-sm">{u.email || '-'}</TableCell>
                    <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">{departments.find((d: any) => d.id === u.dept_id)?.name || '-'}</TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {(u.role_names || []).map((r: string) => (
                          <span key={r} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-primary/5 text-primary border border-primary/10">
                            {r}
                          </span>
                        ))}
                        {(!u.role_names || u.role_names.length === 0) && <span className="text-xs text-muted-foreground">-</span>}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.status === 1 ? 'bg-success/15 text-success' : 'bg-muted/50 text-muted-foreground'
                      }`}>
                        {u.status === 1 ? '启用' : '停用'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-0.5">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(u)}><Pencil className="h-3.5 w-3.5" /></Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { setResetPwdUser(u); setNewPassword(''); setResetPwdOpen(true) }} title="重置密码"><KeyRound className="h-3.5 w-3.5" /></Button>
                        {u.id !== user?.id && <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive/70 hover:text-destructive" onClick={() => setDeleteTarget(u.id)}><Trash2 className="h-3.5 w-3.5" /></Button>}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table></div>
            {filteredUsers.length > 0 && (
              <div className="flex items-center justify-end px-4 py-3 border-t bg-muted/10 gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">共 {filteredUsers.length} 条</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <select
                    value={userPageSize}
                    onChange={(e) => { setUserPageSize(Number(e.target.value)); setUserPage(1) }}
                    className="h-7 text-xs border rounded px-1.5 bg-background text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <span className="text-xs text-muted-foreground">条/页</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={userPage <= 1} onClick={() => setUserPage((p) => p - 1)}>上一页</Button>
                  <span className="flex items-center px-2 text-xs text-muted-foreground">{userPage} / {userTotalPages}</span>
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={userPage >= userTotalPages} onClick={() => setUserPage((p) => p + 1)}>下一页</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent key={String(dialogOpen)} className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg">{editing ? '编辑用户' : '新建用户'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium">用户名</Label>
                <Input value={form.username} disabled className="focus-visible:ring-1 bg-muted/30" />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">真实姓名 <span className="text-destructive">*</span></Label>
                <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} autoComplete="name" className="focus-visible:ring-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {!editing && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">密码 <span className="text-xs text-muted-foreground font-normal">（留空默认 admin123）</span></Label>
                  <Input type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="可选" className="focus-visible:ring-1" />
                </div>
              )}
              <div className="space-y-2">
                <Label className="text-sm font-medium">邮箱</Label>
                <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="focus-visible:ring-1" />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">电话</Label>
                <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="focus-visible:ring-1" />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">部门 <span className="text-destructive">*</span></Label>
              <Select value={form.dept_id} onValueChange={(v) => { setForm({ ...form, dept_id: v }); setDeptError(false) }}>
                <SelectTrigger className={deptError ? 'border-destructive ring-destructive/30' : ''}><SelectValue placeholder="选择部门" /></SelectTrigger>
                <SelectContent>
                  {departments.filter((d: any) => d.id !== '00000000-0000-0000-0000-000000000000').map((d: any) => (
                    <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {deptError && <p className="text-xs text-destructive">请选择部门</p>}
            </div>
            {(() => {
              const allowedRoleCodes = isSuperAdmin
                ? ['tenant_admin', 'dept_admin', 'dept_editor', 'dept_viewer']
                : isTenantAdmin
                  ? ['dept_admin', 'dept_editor', 'dept_viewer']
                  : isDeptAdmin
                    ? ['dept_editor', 'dept_viewer']
                    : []
              const visibleRoles = roles.filter((r: any) =>
                allowedRoleCodes.includes(r.code) ||
                (editing && editing.role_ids?.includes(r.id))
              )
              const isSelf = editing && user && editing.id === user.id
              return visibleRoles.length > 0 ? (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">角色 <span className="text-xs text-muted-foreground font-normal">（未选默认 dept_viewer）</span></Label>
                  <div className="border rounded-lg p-3 space-y-1.5 bg-muted/20">
                    {isSelf && <p className="text-xs text-muted-foreground mb-1">不能修改自己的角色</p>}
                    {visibleRoles.map((r: any) => (
                      <label key={r.id} className={`flex items-center gap-2.5 py-1 px-1 text-sm rounded transition-colors ${isSelf ? '' : 'hover:bg-background cursor-pointer'}`}>
                        <Checkbox checked={selectedRoles.includes(r.id)} onCheckedChange={() => toggleRole(r.id)} disabled={isSelf} />
                        {r.name}
                      </label>
                    ))}
                  </div>
                </div>
              ) : null
            })()}
            <Button onClick={handleSave} className="w-full mt-2 shadow-sm">
              {editing ? '保存修改' : '创建用户'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={resetPwdOpen} onOpenChange={setResetPwdOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-lg">重置密码</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground">
              为 <strong>{resetPwdUser?.display_name}</strong> 设置新密码
            </p>
            <div className="space-y-2">
              <Label className="text-sm font-medium">新密码</Label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="至少 6 位"
                className="focus-visible:ring-1"
              />
            </div>
            <Button onClick={handleResetPassword} className="w-full shadow-sm">
              确认重置
            </Button>
          </div>
        </DialogContent>
      </Dialog>


      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除"
        description="确认删除此用户？"
        confirmText="删除"
        onConfirm={() => { if (deleteTarget) { handleDelete(deleteTarget); setDeleteTarget(null) } }}
      />
    </div>
  )
}
