import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Settings, Info, Shield, Server, KeyRound, Building2, Upload, Mail } from 'lucide-react'

export function SettingsPage() {
  const { user } = useAuth()
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const [tenant, setTenant] = useState({ name: '', logo: '' })
  const [loading, setLoading] = useState(true)
  const [logoUploading, setLogoUploading] = useState(false)
  const logoInputRef = useRef<HTMLInputElement>(null)

  const fetchTenant = useCallback(async () => {
    try {
      const res = await api.getTenantInfo()
      setTenant({ name: res.data?.name || '', logo: res.data?.logo || '' })
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchTenant() }, [fetchTenant])

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
      <div className="list-header flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">系统设置</h1>
          <p className="text-sm text-muted-foreground mt-1">查看系统基本信息</p>
        </div>
      </div>
      <div className="list-card space-y-4">

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

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-2 page-section min-w-0">
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
        <Card className="border shadow-sm mb-6 gap-0">
          <CardHeader className="border-b bg-muted/30 pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Mail className="h-4 w-4 text-primary" />
              联系我们
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="px-6 py-5 text-sm text-muted-foreground space-y-3">
              <p>如有问题、建议或商业合作意向，欢迎发送邮件：</p>
              <a href="mailto:xiao_boy@sohu.com" className="inline-flex items-center gap-2 text-primary hover:underline font-medium">
                <Mail className="h-4 w-4" />
                xiao_boy@sohu.com
              </a>
              <p className="text-xs text-muted-foreground/60">我们会在 1-2 个工作日内回复</p>
            </div>
          </CardContent>
        </Card>
      </div>
      </div>
    </div>
  )
}
