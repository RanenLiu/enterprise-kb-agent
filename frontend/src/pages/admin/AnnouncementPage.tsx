import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { DateTimePicker } from '@/components/DateTimePicker'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { Megaphone, Plus, Pencil, Trash2, EyeOff, CheckCheck, ChevronDown, RotateCcw, Search } from 'lucide-react'

function canManageAnnouncement(userRoles: string[], scope: string, userDeptId?: string | null, annDeptId?: string | null): boolean {
  if (userRoles.includes('super_admin')) return true
  if (userRoles.includes('tenant_admin')) return scope === 'tenant' || scope === 'dept'
  if (scope === 'dept' && userDeptId && annDeptId) return userDeptId === annDeptId
  return false
}

export function AnnouncementPage() {
  const { user } = useAuth()
  const userRoles = user?.roles ?? []
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [annDialogOpen, setAnnDialogOpen] = useState(false)
  const [annEditing, setAnnEditing] = useState<any | null>(null)
  const [annForm, setAnnForm] = useState({ title: '', content: '' })
  const [annSaving, setAnnSaving] = useState(false)
  const [statsSheetOpen, setStatsSheetOpen] = useState(false)
  const [statsData, setStatsData] = useState<any>(null)
  const [statsOffset, setStatsOffset] = useState(0)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsAnnId, setStatsAnnId] = useState<string | null>(null)
  const [detail, setDetail] = useState<any>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const fetchAnnouncements = useCallback(async () => {
    try {
      const res = await api.listAnnouncements(true)
      setAnnouncements(res.data ?? [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { fetchAnnouncements() }, [fetchAnnouncements])

  useEffect(() => {
    let sse: EventSource | null = null
    let fallback: ReturnType<typeof setInterval> | null = null
    sse = new EventSource('/api/v1/admin/announcements/sse')
    sse.addEventListener('announcement', () => { fetchAnnouncements() })
    sse.addEventListener('error', () => {
      if (sse?.readyState === EventSource.CLOSED && !fallback) {
        fallback = setInterval(fetchAnnouncements, 15000)
      }
    })
    return () => { sse?.close(); if (fallback) clearInterval(fallback) }
  }, [fetchAnnouncements])

  useEffect(() => {
    const handler = () => fetchAnnouncements()
    window.addEventListener('announcement-read-changed', handler)
    return () => window.removeEventListener('announcement-read-changed', handler)
  }, [fetchAnnouncements])

  useEffect(() => {
    const handler = () => { if (!document.hidden) fetchAnnouncements() }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [fetchAnnouncements])

  const [filtered, setFiltered] = useState<any[]>([])

  const doFilter = useCallback(() => {
    let result = announcements
    if (startDate) result = result.filter((a) => new Date(a.created_at) >= new Date(startDate))
    if (endDate) {
      const end = new Date(endDate)
      end.setDate(end.getDate() + 1)
      result = result.filter((a) => new Date(a.created_at) < end)
    }
    setFiltered(result)
    setPage(1)
  }, [announcements, startDate, endDate])

  useEffect(() => { setFiltered(announcements) }, [announcements])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  useEffect(() => { if (page > totalPages) setPage(1) }, [filtered.length])

  const paged = filtered.slice((page - 1) * pageSize, page * pageSize)

  const handleMarkRead = async (id: string) => {
    try {
      await api.markAnnouncementRead(id)
      window.dispatchEvent(new CustomEvent('announcement-read-changed'))
      fetchAnnouncements()
    } catch { /* ignore */ }
  }

  const openReadStats = async (a: any) => {
    setStatsAnnId(a.id); setStatsOffset(0); setStatsLoading(true)
    try {
      const res = await api.getAnnouncementReadStats(a.id, { limit: 50, offset: 0 })
      setStatsData(res.data); setStatsSheetOpen(true)
    } catch (err: any) { toast.error(err.message || '加载失败') }
    finally { setStatsLoading(false) }
  }

  const loadMoreReaders = async () => {
    if (!statsAnnId) return
    const newOffset = statsOffset + 50; setStatsLoading(true)
    try {
      const res = await api.getAnnouncementReadStats(statsAnnId, { limit: 50, offset: newOffset })
      setStatsData((prev: any) => ({
        ...prev,
        readers: [...(prev?.readers ?? []), ...(res.data?.readers ?? [])],
        has_more: res.data?.has_more ?? false,
      }))
      setStatsOffset(newOffset)
    } catch (err: any) { toast.error(err.message || '加载失败') }
    finally { setStatsLoading(false) }
  }

  const openCreateAnn = () => { setAnnEditing(null); setAnnForm({ title: '', content: '' }); setAnnDialogOpen(true) }
  const openEditAnn = (a: any) => { setAnnEditing(a); setAnnForm({ title: a.title, content: a.content }); setAnnDialogOpen(true) }

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
      setAnnDialogOpen(false); fetchAnnouncements()
    } catch (err: any) { toast.error(err.message || '操作失败') }
    finally { setAnnSaving(false) }
  }

  const handleToggleAnnouncement = async (a: any) => {
    setAnnSaving(true)
    try {
      await api.updateAnnouncement(a.id, { is_active: !a.is_active })
      toast.success(a.is_active ? '公告已停用' : '公告已启用')
      fetchAnnouncements()
    } catch (err: any) { toast.error(err.message || '操作失败') }
    finally { setAnnSaving(false) }
  }

  const handleDeleteAnnouncement = async (a: any) => {
    if (!window.confirm(`确定删除公告「${a.title}」？`)) return
    setAnnSaving(true)
    try {
      await api.deleteAnnouncement(a.id)
      toast.success('公告已删除'); fetchAnnouncements()
    } catch (err: any) { toast.error(err.message || '操作失败') }
    finally { setAnnSaving(false) }
  }

  const handleReset = () => { setStartDate(''); setEndDate(''); setFiltered(announcements); setPage(1) }

  return (
    <div className="list-page animate-fade-in">
      <div className="list-header flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-balance">系统公告</h1>
          <p className="text-sm text-muted-foreground/70 mt-0.5">管理系统公告的发布与展示</p>
        </div>
        <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={openCreateAnn}>
          <Plus className="mr-1 h-3 w-3" aria-hidden="true" aria-hidden="true" />新建公告
        </Button>
      </div>
      <div className="list-card">
        <Card className="admin-table border shadow-sm">
          <CardHeader className="bg-muted/30 border-b pb-3">
            <div className="flex items-center gap-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Megaphone className="h-4 w-4 text-primary" />
                公告列表
              </CardTitle>
            </div>
            <div className="flex gap-3 flex-wrap mt-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground">时间</span>
                <DateTimePicker placeholder="开始时间" value={startDate} onChange={(v) => setStartDate(v)} />
                <span className="text-xs text-muted-foreground">~</span>
                <DateTimePicker placeholder="结束时间" value={endDate} onChange={(v) => setEndDate(v)} />
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={doFilter}><Search className="h-3 w-3 mr-1" aria-hidden="true" />搜索</Button>
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={handleReset}>
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
                  <TableHead className="font-medium w-[55%]">标题</TableHead>
                  <TableHead className="font-medium w-[25%]">发布时间</TableHead>
                  <TableHead className="font-medium w-[8%]">状态</TableHead>
                  {userRoles.some(r => ['super_admin', 'tenant_admin', 'dept_admin'].includes(r)) && <TableHead className="font-medium w-[12%]">操作</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-12 text-muted-foreground">暂无公告</TableCell></TableRow>
                ) : paged.map((a, idx) => (
                  <TableRow
                    key={a.id}
                    className={`${idx % 2 === 0 ? 'bg-background' : 'bg-muted/10'} cursor-pointer`}
                    onClick={() => { handleMarkRead(a.id); setDetail(a) }}
                  >
                    <TableCell>
                      <div className={`text-sm truncate ${!a.read ? 'text-primary' : ''} ${!a.is_active ? 'text-muted-foreground/50' : ''}`}>
                        {a.title}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(a.created_at).toLocaleString('zh-CN', { hour12: false })}
                    </TableCell>
                    <TableCell>
                      <span className={`text-xs ${a.is_active ? 'text-success' : 'text-muted-foreground'}`}>
                        {a.is_active ? '正常' : '已停用'}
                      </span>
                    </TableCell>
                    {canManageAnnouncement(userRoles, a.scope, user?.dept_id, a.dept_id) && (
                      <TableCell>
                        <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEditAnn(a)} title="编辑" disabled={annSaving}>
                            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground" onClick={() => handleToggleAnnouncement(a)} title={a.is_active ? '停用' : '启用'} disabled={annSaving}>
                            <EyeOff className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground/50 hover:text-foreground" onClick={() => openReadStats(a)} title="已读统计">
                            <CheckCheck className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive/70 hover:text-destructive" onClick={() => handleDeleteAnnouncement(a)} title="删除" disabled={annSaving}>
                            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table></div>
            {filtered.length > 0 && (
              <div className="flex items-center justify-end px-4 py-3 border-t bg-muted/10 gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">共 {filtered.length} 条</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <select
                    value={pageSize}
                    onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                    className="h-7 text-xs border rounded px-1.5 bg-background text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <span className="text-xs text-muted-foreground">条/页</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
                  <span className="flex items-center px-2 text-xs text-muted-foreground">{page} / {totalPages}</span>
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>下一页</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

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
            <Button onClick={handleSaveAnn} className="w-full mt-2 shadow-sm" disabled={annSaving}>
              {annEditing ? '保存修改' : '发布公告'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg">{detail?.title}</DialogTitle>
          </DialogHeader>
          {detail && (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                {new Date(detail.created_at).toLocaleString('zh-CN', { hour12: false })}
              </div>
              <div className="text-sm leading-relaxed whitespace-pre-wrap">{detail.content}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Sheet open={statsSheetOpen} onOpenChange={setStatsSheetOpen}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader className="px-6 pt-6">
            <SheetTitle className="text-lg flex items-center gap-2">
              <CheckCheck className="h-4 w-4 text-primary" />
              已读统计
            </SheetTitle>
          </SheetHeader>
          <div className="px-6 mt-4 space-y-4">
            {statsData && (
              <>
                <div className="text-sm text-muted-foreground border-b pb-3">
                  <span className="font-medium text-foreground">{statsData.announcement_title}</span>
                </div>
                <div className="text-sm flex items-center gap-2">
                  已读 <span className="font-semibold text-primary">{statsData.total_read}</span> 人
                </div>
                {statsData.readers.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">暂无已读记录</p>
                ) : (
                  <div className="divide-y max-h-[400px] overflow-y-auto border rounded-lg">
                    {statsData.readers.map((r: any) => (
                      <div key={r.user_id} className="flex items-center justify-between px-4 py-3 text-sm">
                        <div>
                          <span className="font-medium">{r.display_name}</span>
                          {r.dept_name && <span className="text-muted-foreground ml-2 text-xs">{r.dept_name}</span>}
                        </div>
                        <span className="text-xs text-muted-foreground">{new Date(r.read_at).toLocaleString('zh-CN', { hour12: false })}</span>
                      </div>
                    ))}
                    {statsData.has_more && (
                      <Button variant="ghost" className="w-full h-9 text-xs rounded-none text-muted-foreground" onClick={loadMoreReaders} disabled={statsLoading}>
                        <ChevronDown className="h-3 w-3 mr-1" />
                        {statsLoading ? '加载中…' : '加载更多'}
                      </Button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
