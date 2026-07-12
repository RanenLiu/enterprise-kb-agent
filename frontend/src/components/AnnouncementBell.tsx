import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { api } from '@/api/client'
import { Bell, Check, X } from 'lucide-react'

interface Announcement {
  id: string
  title: string
  content: string
  read: boolean
  created_at: string
}

export function AnnouncementBell() {
  const [unreadCount, setUnreadCount] = useState(0)
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<Announcement | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  const fetchUnread = async () => {
    if (!api.getToken()) return
    try {
      const res = await api.getUnreadAnnouncementCount()
      setUnreadCount(res.data ?? 0)
    } catch { /* ignore */ }
  }

  const fetchAll = async () => {
    try {
      const res = await api.listAnnouncements()
      setAnnouncements(res.data ?? [])
      // Also refresh unread count
      const unreadRes = await api.getUnreadAnnouncementCount()
      setUnreadCount(unreadRes.data ?? 0)
    } catch { /* ignore */ }
  }

  useEffect(() => {
    fetchUnread()

    let sse: EventSource | null = null
    let fallbackInterval: ReturnType<typeof setInterval> | null = null

    sse = new EventSource('/api/v1/admin/announcements/sse')
    sse.addEventListener('announcement', () => { fetchUnread() })
    sse.addEventListener('error', () => {
      if (sse?.readyState === EventSource.CLOSED && !fallbackInterval) {
        fallbackInterval = setInterval(fetchUnread, 15000)
      }
    })

    return () => {
      sse?.close()
      if (fallbackInterval) clearInterval(fallbackInterval)
    }
  }, [])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (detail) return
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open, detail])

  const handleToggle = () => {
    if (!open) fetchAll()
    setOpen(!open)
  }

  const handleMarkAllRead = async () => {
    try {
      await api.markAllAnnouncementsRead()
      setUnreadCount(0)
      setAnnouncements((prev) => prev.map((a) => ({ ...a, read: true })))
    } catch { /* ignore */ }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await api.markAnnouncementRead(id)
      setUnreadCount((c) => Math.max(0, c - 1))
      setAnnouncements((prev) => prev.map((a) => a.id === id ? { ...a, read: true } : a))
    } catch { /* ignore */ }
  }

  return (
    <>
      <div ref={ref} className="relative">
        <Button
          variant="ghost"
          size="icon"
          className={`h-9 w-9 rounded-full text-muted-foreground relative ${open ? 'text-primary ring-2 ring-primary/30 ring-offset-1' : ''}`}
          onClick={handleToggle}
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground px-1 leading-none">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </Button>

        {open && (
          <div className="absolute right-0 top-full mt-1.5 z-50 w-[360px] max-sm:w-[300px] rounded-xl border bg-popover shadow-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/20">
              <span className="text-sm font-semibold">系统公告</span>
              <div className="flex items-center gap-1">
                {announcements.length > 0 && (
                  <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground gap-1" onClick={handleMarkAllRead}>
                    <Check className="h-3 w-3" />全部已读
                  </Button>
                )}
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground" onClick={() => setOpen(false)}>
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            <div className="max-h-[400px] overflow-y-auto">
              {announcements.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-muted-foreground">暂无公告</div>
              ) : (
                announcements.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-start gap-3 px-4 py-3 border-b last:border-b-0 hover:bg-muted/20 cursor-pointer transition-colors group"
                    onClick={async () => {
                      await handleMarkRead(a.id)
                      setDetail(a)
                    }}
                  >
                    <div className="mt-1.5 flex-shrink-0">
                      <div className={`h-2 w-2 rounded-full ${a.read ? 'bg-transparent' : 'bg-primary'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{a.title}</div>
                      <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{a.content}</div>
                      <div className="text-[10px] text-muted-foreground/60 mt-1">
                        {new Date(a.created_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg">{detail?.title}</DialogTitle>
          </DialogHeader>
          {detail && (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                {new Date(detail.created_at).toLocaleString('zh-CN')}
              </div>
              <div className="text-sm leading-relaxed whitespace-pre-wrap">{detail.content}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
