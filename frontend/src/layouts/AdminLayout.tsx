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

const ACCENTS: { key: Accent; className: string }[] = [
  { key: 'blue', className: 'bg-blue-500' },
  { key: 'violet', className: 'bg-violet-500' },
  { key: 'emerald', className: 'bg-emerald-500' },
  { key: 'amber', className: 'bg-amber-600' },
  { key: 'rose', className: 'bg-rose-600' },
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
  '/admin/announcements': '系统公告',
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
            `.list-page .list-header h1{font-size:18px!important}` +
            `[data-slot="sidebar-trigger"]{background:transparent!important}` +
            `input:focus-visible,textarea:focus-visible,select:focus-visible{border-color:var(--ring)!important;box-shadow:none!important;outline:none!important}`
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
      <SidebarInset className="min-w-0">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:z-50 focus:top-4 focus:left-4 focus:px-4 focus:py-2 focus:rounded-lg focus:bg-background focus:text-foreground focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-ring">
          跳转到主内容
        </a>
        <header className={`flex h-14 shrink-0 items-center gap-2 px-4 sticky top-0 z-10 bg-background backdrop-blur-xl ${glass ? 'glass-header glass-edge-light' : ''}`}>
          <SidebarTrigger className="-ml-1.5 text-muted-foreground hover:text-foreground transition-colors" />
          <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.path} className="flex items-center gap-1.5">
                {i > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground/40" aria-hidden="true" />}
                <span className={i === breadcrumbs.length - 1 ? 'text-foreground font-medium' : ''}>
                  {crumb.label}
                </span>
              </span>
            ))}
          </nav>
          <div className="flex-1" />

          {/* Accent color picker */}
          <div ref={accentRef} className="relative">
            <Button variant="ghost" size="icon" className={`h-9 w-9 rounded-full ${showAccents ? 'text-primary ring-2 ring-primary/30 ring-offset-1' : 'text-muted-foreground'}`} onClick={() => setShowAccents(!showAccents)} aria-label="主题色">
              <Palette className="h-4 w-4" aria-hidden="true" />
            </Button>
            {showAccents && (
              <div className="absolute left-0 top-full mt-1.5 z-50 flex gap-3 p-2 rounded-xl border bg-popover shadow-xl">
                  {ACCENTS.map((a) => (
                    <button
                      key={a.key}
                      className={`h-7 w-7 rounded-full ${a.className} ${accent === a.key ? 'ring-2 ring-offset-2 ring-offset-popover ring-primary' : 'opacity-60 hover:opacity-100'} transition-all`}
                      onClick={() => { setAccent(a.key); setShowAccents(false) }}
                    />
                  ))}
                </div>
            )}
          </div>

          {/* Glass mode toggle */}
          <Button variant="ghost" size="icon" className={`h-9 w-9 rounded-full ${glass ? 'text-primary bg-primary/10' : 'text-muted-foreground'}`} onClick={toggleGlass} aria-label="玻璃质感" title="玻璃质感">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 20h16" />
              <rect x="6" y="4" width="12" height="12" rx="2" opacity="0.5" />
              <rect x="8" y="8" width="8" height="8" rx="1" opacity="0.3" />
            </svg>
          </Button>

          {/* Filled icons toggle */}
          <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-muted-foreground" onClick={toggleFilledIcons} aria-label={filledIcons ? '实心图标' : '线条图标'} title={filledIcons ? '实心图标' : '线条图标'}>
            <PaintBucket className={`h-4 w-4 ${filledIcons ? 'fill-primary text-primary' : ''}`} />
          </Button>

          {/* Theme toggle */}
          <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-muted-foreground" onClick={toggleTheme} aria-label={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}>
            {theme === 'light' ? <Moon className="h-4 w-4" aria-hidden="true" /> : <Sun className="h-4 w-4" aria-hidden="true" />}
          </Button>

          <AnnouncementBell />

          {user && (
            <button onClick={() => setShowProfile(true)} className="flex items-center gap-2 pl-3 border-l hover:bg-muted/40 rounded-lg py-1 pr-2 transition-colors cursor-pointer" aria-label="用户信息">
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

          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-destructive hover:bg-destructive/5 ml-1" aria-label="退出登录">
            <LogOut className="h-4 w-4" aria-hidden="true" />
          </Button>
        </header>

        <ProfileDialog open={showProfile} onOpenChange={setShowProfile} />
        <main id="main-content" className={`flex-1 flex flex-col bg-muted/60 ${isChatPage ? 'overflow-hidden p-0' : 'p-6'} ${narrow ? 'is-narrow' : ''}`} style={{ overflow: 'hidden auto', maxWidth: '100%' }}>
          <Outlet />
        </main>
        <footer className="h-7 shrink-0 flex items-center justify-center bg-background text-[10px] text-muted-foreground/40 select-none">
          &copy; {new Date().getFullYear()} Enterprise Knowledge Base
        </footer>
      </SidebarInset>
    </SidebarProvider>
  )
}
