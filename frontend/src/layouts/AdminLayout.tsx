import { useState, useEffect, useRef } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { AnnouncementBell } from '@/components/AnnouncementBell'
import { AppSidebar } from '@/components/AppSidebar'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { useTheme, type Accent } from '@/hooks/useTheme'
import { ProfileDialog } from '@/components/ProfileDialog'
import { LogOut, Sun, Moon, Palette, ChevronRight, PaintBucket } from 'lucide-react'
import { api } from '@/api/client'

const ACCENTS: { key: Accent; color: string }[] = [
  { key: 'blue', color: 'bg-blue-500' },
  { key: 'violet', color: 'bg-violet-500' },
  { key: 'emerald', color: 'bg-emerald-500' },
  { key: 'amber', color: 'bg-amber-500' },
  { key: 'rose', color: 'bg-rose-500' },
]

const ROUTE_LABELS: Record<string, string> = {
  '/': '首页',
  '/dashboard': '仪表盘',
  '/chat': '智能问答',
  '/knowledge': '知识库',
  '/admin/tenants': '租户管理',
  '/admin/departments': '部门管理',
  '/admin/roles': '角色管理',
  '/admin/users': '用户管理',
  '/admin/menus': '菜单管理',
  '/admin/logs': '操作日志',
  '/admin/monitor': '系统监控',
  '/admin/models': '模型配置',
  '/admin/settings': '系统设置',
}

export function AdminLayout() {
  const navigate = useNavigate()
  const [narrow, setNarrow] = useState(window.innerWidth <= 768)
  useEffect(() => {
    const styleId = 'narrow-font-override'
    const apply = () => {
      const n = window.innerWidth <= 768
      setNarrow(n)
      let el = document.getElementById(styleId)
      if (n) {
        if (!el) {
          el = document.createElement('style')
          el.id = styleId
          el.textContent =
            `.admin-table td,.admin-table th,.text-xs,.list-page .text-xs{font-size:13px!important}` +
            `.list-page .admin-table td,.list-page .admin-table th{font-size:13px!important}` +
            `.list-page,.list-page .list-header,.list-page .list-header :not(h1){font-size:13px!important}` +
            `.list-page .list-header h1{font-size:18px!important}`
          document.head.appendChild(el)
        }
      } else if (el) {
        el.remove()
      }
    }
    apply()
    window.addEventListener('resize', apply)
    return () => {
      window.removeEventListener('resize', apply)
      document.getElementById('narrow-font-override')?.remove()
    }
  }, [])
  const location = useLocation()
  const { user } = useAuth()
  const { theme, accent, toggleTheme, setAccent, glass, toggleGlass, filledIcons, toggleFilledIcons } = useTheme()
  const [showAccents, setShowAccents] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const accentRef = useRef<HTMLDivElement>(null)

  // Close accent picker on outside click
  useEffect(() => {
    if (!showAccents) return
    const handler = (e: Event) => {
      if (accentRef.current && !accentRef.current.contains(e.target as Node)) {
        setShowAccents(false)
      }
    }
    document.addEventListener('pointerdown', handler)
    return () => document.removeEventListener('pointerdown', handler)
  }, [showAccents])

  const handleLogout = () => {
    api.setToken(null)
    navigate('/login')
  }

  // Build breadcrumb trail from path
  const pathParts = location.pathname.split('/').filter(Boolean)
  let breadcrumbs: { label: string; path: string }[] = []

  if (pathParts.length === 0) {
    breadcrumbs = [{ label: '首页', path: '/' }]
  } else if (location.pathname === '/dashboard') {
    breadcrumbs = [{ label: '仪表盘', path: '/dashboard' }]
  } else if (location.pathname === '/admin/logs') {
    breadcrumbs = [{ label: '操作日志', path: '/admin/logs' }]
  } else if (location.pathname === '/admin/projects') {
    breadcrumbs = [{ label: '项目管理', path: '/admin/projects' }]
  } else if (pathParts[0] === 'admin' && pathParts.length === 1) {
    breadcrumbs = [{ label: ROUTE_LABELS['/admin'], path: '/admin' }]
  } else if (pathParts[0] === 'admin' && pathParts.length >= 2) {
    breadcrumbs.push({ label: '系统管理', path: '/admin' })
    let accumulated = '/admin'
    for (let i = 1; i < pathParts.length; i++) {
      accumulated += `/${pathParts[i]}`
      breadcrumbs.push({ label: ROUTE_LABELS[accumulated] || pathParts[i], path: accumulated })
    }
  } else if (pathParts.length === 1) {
    breadcrumbs = [{ label: ROUTE_LABELS[`/${pathParts[0]}`] || pathParts[0], path: `/${pathParts[0]}` }]
  }

  const isChatPage = location.pathname === '/chat'

  return (
    <SidebarProvider className="h-dvh overflow-hidden">
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b glass px-4 sticky top-0 z-10">
          <SidebarTrigger className="-ml-1 text-muted-foreground hover:text-foreground" />
          <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.path} className="flex items-center gap-1.5">
                {i > 0 && <ChevronRight className="h-3.5 w-3.5" />}
                <span className={i === breadcrumbs.length - 1 ? 'text-foreground font-medium' : ''}>
                  {crumb.label}
                </span>
              </span>
            ))}
          </nav>
          <div className="flex-1" />

          {/* Accent color picker */}
          <div ref={accentRef} className="relative">
            <Button variant="ghost" size="icon" className={`h-9 w-9 rounded-full ${showAccents ? 'text-primary ring-2 ring-primary/30 ring-offset-1' : 'text-muted-foreground'}`} onClick={() => setShowAccents(!showAccents)}>
              <Palette className="h-4 w-4" />
            </Button>
            {showAccents && (
              <div className="absolute left-0 top-full mt-1.5 z-50 flex gap-3 p-2 rounded-xl border bg-popover shadow-xl">
                  {ACCENTS.map((a) => (
                    <button
                      key={a.key}
                      className={`h-7 w-7 rounded-full ${a.color} ${accent === a.key ? 'ring-2 ring-offset-2 ring-offset-popover ring-primary' : 'opacity-60 hover:opacity-100'} transition-all`}
                      onClick={() => { setAccent(a.key); setShowAccents(false) }}
                    />
                  ))}
                </div>
            )}
          </div>

          {/* Glass mode toggle */}
          <Button variant="ghost" size="icon" className={`h-9 w-9 rounded-full ${glass ? 'text-primary bg-primary/10' : 'text-muted-foreground'}`} onClick={toggleGlass} title="玻璃质感">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 20h16" />
              <rect x="6" y="4" width="12" height="12" rx="2" opacity="0.5" />
              <rect x="8" y="8" width="8" height="8" rx="1" opacity="0.3" />
            </svg>
          </Button>

          {/* Filled icons toggle */}
          <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-muted-foreground" onClick={toggleFilledIcons} title={filledIcons ? '实心图标' : '线条图标'}>
            <PaintBucket className={`h-4 w-4 ${filledIcons ? 'fill-primary text-primary' : ''}`} />
          </Button>

          {/* Theme toggle */}
          <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-muted-foreground" onClick={toggleTheme}>
            {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </Button>

          <AnnouncementBell />

          {user && (
            <button onClick={() => setShowProfile(true)} className="flex items-center gap-2 pl-2 border-l hover:bg-muted/30 rounded-lg py-1 pr-2 transition-colors cursor-pointer">
              {user.avatar ? (
                <img src={user.avatar} alt="" className="h-7 w-7 rounded-full object-cover border" />
              ) : (
                <div className="h-7 w-7 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
                  {user.display_name?.charAt(0) || 'U'}
                </div>
              )}
              <span className="text-sm font-medium text-foreground/80 hidden sm:inline">{user.display_name}</span>
            </button>
          )}

          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-destructive hover:bg-destructive/5 ml-1">
            <LogOut className="h-4 w-4" />
          </Button>
        </header>

        <ProfileDialog open={showProfile} onOpenChange={setShowProfile} />
        <main className={`flex-1 flex flex-col bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/[0.03] via-transparent to-transparent ${isChatPage ? 'overflow-hidden p-0' : 'overflow-y-auto p-6 text-sm'} ${narrow ? 'is-narrow' : ''}`}>
          <Outlet />
        </main>
        <footer className="h-8 shrink-0 flex items-center justify-center border-t text-xs text-muted-foreground/60">
          &copy; {new Date().getFullYear()} Enterprise Knowledge Base. All rights reserved.
        </footer>
      </SidebarInset>
    </SidebarProvider>
  )
}
