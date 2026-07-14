import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Settings, Info, Shield, Server, KeyRound, Building2, Upload, Megaphone, Plus, Pencil, Trash2, EyeOff } from 'lucide-react'

export function SettingsPage() {
  const { user } = useAuth()
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const isDeptAdmin = user?.roles?.includes('dept_admin')
  const [tenant, setTenant] = useState({ name: '', logo: '' })
  const [loading, setLoading] = useState(true)
  const [logoUploading, setLogoUploading] = useState(false)
  const logoInputRef = useRef<HTMLInputElement>(null)

  // Announcement management
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [annDialogOpen, setAnnDialogOpen] = useState(false)
  const [annEditing, setAnnEditing] = useState<any | null>(null)
  const [annForm, setAnnForm] = useState({ title: '', content: '' })
  const [annSaving, setAnnSaving] = useState(false)

  const fetchAnnouncements = useCallback(async () => {
    try {
      const res = await api.listAnnouncements(true)
      setAnnouncements(res.data ?? [])
    } catch { /* ignore */ }
  }, [])

  const openCreateAnn = () => {
    setAnnEditing(null)
    setAnnForm({ title: '', content: '' })
    setAnnDialogOpen(true)
  }

  const openEditAnn = (a: any) => {
    setAnnEditing(a)
    setAnnForm({ title: a.title, content: a.content })
    setAnnDialogOpen(true)
  }

  const handleSaveAnn = async () => {
    if (!annForm.title.trim()) { toast.error('请输入公告标题'); return }
    if (!annForm.content.trim()) { toast.error('请输入公告内容'); return }
    setAnnSaving(true)
    try {
      if (annEditing) {
        await api.updateAnnouncement(annEditing.id, annForm)
        toast.success('公告已更新')
      } else {
        await api.createAnnouncement(annForm)
        toast.success('公告已创建')
      }
      setAnnDialogOpen(false)
      fetchAnnouncements()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    } finally {
      setAnnSaving(false)
    }
  }

  const handleToggleAnnouncement = async (a: any) => {
    setAnnSaving(true)
    try {
      await api.updateAnnouncement(a.id, { is_active: !a.is_active })
      toast.success(a.is_active ? '公告已停用' : '公告已启用')
      fetchAnnouncements()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    } finally {
      setAnnSaving(false)
    }
  }

  const handleDeleteAnnouncement = async (a: any) => {
    setAnnSaving(true)
    try {
      await api.deleteAnnouncement(a.id)
      toast.success('公告已删除')
      fetchAnnouncements()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    } finally {
      setAnnSaving(false)
    }
  }

  const fetchTenant = useCallback(async () => {
    try {
      const res = await api.getTenantInfo()
      setTenant({ name: res.data?.name || '', logo: res.data?.logo || '' })
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchTenant() }, [fetchTenant])

  useEffect(() => {
    if (isSuperAdmin || isTenantAdmin || isDeptAdmin) fetchAnnouncements()
  }, [isSuperAdmin, isTenantAdmin, isDeptAdmin, fetchAnnouncements])

  const handleUploadLogo = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLogoUploading(true)
    try {
      const res = await api.uploadFile(file)
      setTenant((t) => ({ ...t, logo: res.data.url }))
      toast.success('图片已上传，点击保存生效')
    } catch (err: any) {
      toast.error(err.message || '上传失败')
    } finally {
      setLogoUploading(false)
      if (logoInputRef.current) logoInputRef.current.value = ''
    }
  }

  const handleSave = async () => {
    try {
      await api.updateTenantInfo(tenant)
      window.dispatchEvent(new CustomEvent('tenant-updated'))
      toast.success('已更新')
    } catch (err: any) {
      toast.error(err.message || '保存失败')
    }
  }

  const allItems = [
    { label: '应用名称', value: tenant.name || '企业知识库智能问答', icon: Info },
    { label: '版本', value: '0.4.0', icon: Server },
    { label: '技术栈', value: 'FastAPI + React + Milvus + Neo4j', icon: Shield },
    { label: 'API 前缀', value: '/api/v1', icon: KeyRound },
    { label: '认证方式', value: 'JWT Bearer + RBAC', icon: Shield },
  ]
  // Tenant admin only sees version
  const items = isSuperAdmin ? allItems : allItems.filter((i) => i.label === '版本')

  return (
    <div className="list-page animate-fade-in">
      <div className="page-section">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">系统设置</h1>
          <p className="text-sm text-muted-foreground mt-1">查看系统基本信息</p>
        </div>
      </div>

      {/* Tenant branding — for tenant_admin only */}
      {isTenantAdmin && (
        <div className="page-section">
          <Card className="border shadow-sm gap-0">
            <CardHeader className="border-b bg-muted/30 pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Building2 className="h-4 w-4 text-primary" />
                租户品牌
              </CardTitle>
            </CardHeader>
            <CardContent className="px-6 py-4 space-y-4">
              {loading ? (
                <p className="text-sm text-muted-foreground animate-pulse">加载中...</p>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">系统名称</Label>
                      <Input value={tenant.name} onChange={(e) => setTenant({ ...tenant, name: e.target.value })} className="focus-visible:ring-1" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Logo URL</Label>
                      <Input value={tenant.logo} onChange={(e) => setTenant({ ...tenant, logo: e.target.value })} placeholder="https://example.com/logo.png" className="focus-visible:ring-1" />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Button variant="outline" size="sm" onClick={() => logoInputRef.current?.click()} disabled={logoUploading} className="h-8 text-xs">
                      <Upload className="mr-1 h-3 w-3" />{logoUploading ? '上传中...' : '上传 Logo'}
                    </Button>
                    <input ref={logoInputRef} type="file" accept="image/*" className="hidden" onChange={handleUploadLogo} />
                    {tenant.logo && (
                      <img src={tenant.logo} alt="" className="h-8 w-8 rounded-lg object-cover border" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                    )}
                  </div>
                  <Button onClick={handleSave} className="shadow-sm">保存品牌设置</Button>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Announcement management — super admin / tenant admin */}
      {(isSuperAdmin || isTenantAdmin || isDeptAdmin) && (
        <div className="page-section">
          <Card className="border shadow-sm gap-0">
            <CardHeader className="border-b bg-muted/30">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Megaphone className="h-4 w-4 text-primary" />
                  系统公告
                </CardTitle>
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={openCreateAnn}>
                  <Plus className="mr-1 h-3 w-3" />新建公告
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {announcements.length === 0 ? (
                <div className="px-6 py-8 text-center text-sm text-muted-foreground">暂无公告</div>
              ) : (
                <div className="divide-y max-h-[300px] overflow-y-auto">
                  {announcements.map((a) => (
                    <div key={a.id} className="flex items-center gap-3 px-6 py-3 hover:bg-muted/10 transition-colors">
                      <div className={`h-2 w-2 rounded-full flex-shrink-0 ${a.read ? 'bg-transparent' : 'bg-primary'}`} />
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm truncate ${a.is_active ? '' : 'text-muted-foreground/50'}`}>
                          {a.title}
                          {!a.is_active && <span className="text-xs text-muted-foreground ml-2">(已停用)</span>}
                        </div>
                        <div className="text-xs text-muted-foreground/60 truncate">{a.content}</div>
                      </div>
                      <div className="flex gap-1 flex-shrink-0">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditAnn(a)} title="编辑" disabled={annSaving}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground" onClick={() => handleToggleAnnouncement(a)} title={a.is_active ? '停用' : '启用'} disabled={annSaving}>
                          <EyeOff className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive/70 hover:text-destructive" onClick={() => handleDeleteAnnouncement(a)} title="删除" disabled={annSaving}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-2 page-section">
        <Card className="border shadow-sm mb-6 gap-0">
          <CardHeader className="border-b bg-muted/30 pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Settings className="h-4 w-4 text-primary" />
              系统信息
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {items.map((item, i) => {
              const Icon = item.icon
              return (
                <div key={item.label} className={`flex items-center justify-between px-6 py-3.5 ${i < items.length - 1 ? 'border-b' : ''}`}>
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4 text-muted-foreground/60" />
                    <span className="text-sm text-muted-foreground">{item.label}</span>
                  </div>
                  <span className="text-sm font-medium text-right">{item.value}</span>
                </div>
              )
            })}
          </CardContent>
        </Card>
      </div>

      {/* Announcement edit/create dialog */}

      <Dialog open={annDialogOpen} onOpenChange={setAnnDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg">{annEditing ? '编辑公告' : '新建公告'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-sm font-medium">公告标题</Label>
              <Input value={annForm.title} onChange={(e) => setAnnForm({ ...annForm, title: e.target.value })} placeholder="如：系统升级通知" className="focus-visible:ring-1" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">公告内容</Label>
              <textarea
                value={annForm.content}
                onChange={(e) => setAnnForm({ ...annForm, content: e.target.value })}
                placeholder="输入公告内容..."
                rows={6}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
              />
            </div>
            <Button onClick={handleSaveAnn} className="w-full mt-2 shadow-sm" disabled={annSaving}>{annEditing ? '保存修改' : '发布公告'}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
