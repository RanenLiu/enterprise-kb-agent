import { useCallback, useEffect, useState, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarHeader,
  useSidebar,
} from '@/components/ui/sidebar'
import {
  Home, MessageSquare, Database, Settings, LayoutDashboard, Building2, Building,
  Shield, Users, Menu, FileText, Activity, Cpu, ChevronRight, FolderKanban, Megaphone, type LucideIcon,
} from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/api/client'

const ICON_MAP: Record<string, LucideIcon> = {
  Home,
  MessageSquare, Database, Settings, LayoutDashboard, Building2, Building,
  Shield, Users, Menu, FileText, Activity, Cpu, FolderKanban, Megaphone,
}

type MenuNode = {
  id: string
  parent_id: string | null
  name: string
  path: string | null
  icon: string | null
  permission_code: string | null
  sort_order: number
  hidden: boolean
  children: MenuNode[]
}

function loadIcon(iconName: string | null): LucideIcon {
  if (iconName && ICON_MAP[iconName]) return ICON_MAP[iconName]
  return Settings
}

export function AppSidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, menus } = useAuth()
  const { glass } = useTheme()
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const visibleMenus = isSuperAdmin
    ? menus.filter((m) => !m.path?.startsWith('/admin/projects') && !m.children?.some((c: any) => c.path?.startsWith('/admin/projects')))
    : menus
  const { isMobile, setOpenMobile, state } = useSidebar()
  const [tenantInfo, setTenantInfo] = useState<{name:string;logo?:string}>({ name: '知识库客服' })
  const [flyoutMenu, setFlyoutMenu] = useState<string | null>(null)
  const [flyoutTop, setFlyoutTop] = useState(0)
  const flyoutRef = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('sidebarExpanded')
      return saved ? new Set(JSON.parse(saved)) : new Set()
    } catch { return new Set() }
  })

  useEffect(() => {
    if (menus.length === 0) return
    // Auto-expand parent of current route
    setExpanded((prev) => {
      const next = new Set(prev)
      const find = (nodes: MenuNode[], path: string): string | null => {
        for (const n of nodes) {
          if (n.path === '/' && path === '/') return n.parent_id
          if (n.path && n.path !== '/' && path.startsWith(n.path.replace(/\/$/, ''))) return n.parent_id
          if (n.children.length > 0) { const f = find(n.children, path); if (f) return f }
        }
        return null
      }
      const pid = find(menus, location.pathname)
      if (pid) next.add(pid)
      return next
    })
  }, [menus, location.pathname])

  const refreshTenant = useCallback(() => {
    api.getTenantInfo().then((r) => {
      if (r.data) setTenantInfo(r.data)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    refreshTenant()
    window.addEventListener('tenant-updated', refreshTenant)
    return () => window.removeEventListener('tenant-updated', refreshTenant)
  }, [refreshTenant])

  useEffect(() => {
    if (!flyoutMenu) return
    const close = (e: Event) => {
      if (flyoutRef.current && !flyoutRef.current.contains(e.target as Node)) setFlyoutMenu(null)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [flyoutMenu])

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      localStorage.setItem('sidebarExpanded', JSON.stringify([...next]))
      return next
    })
  }

  const hasExactMatch = (nodes: MenuNode[], target: string): boolean => {
    for (const n of nodes) {
      if (n.path && target === n.path.replace(/\/$/, '')) return true
      if (n.children.length > 0 && hasExactMatch(n.children, target)) return true
    }
    return false
  }

  const isActive = (path: string | null) => {
    if (!path) return false
    const a = location.pathname.replace(/\/$/, '')
    const b = path.replace(/\/$/, '')
    if (a === b) return true
    if (b === '') return false
    // Fall back to prefix match only when no exact match exists
    return a.startsWith(b + '/') && !hasExactMatch(menus, a)
  }

  const press = (el: HTMLElement | null) => { if (el) el.style.transform = 'scale(1.02)' }
const release = (el: HTMLElement | null) => { if (el) el.style.transform = '' }

const renderMenuItem = (node: MenuNode) => {
    if (node.path && node.children.length === 0) {
      const IC = loadIcon(node.icon)
      return (
        <SidebarMenuItem key={node.id}>
          <SidebarMenuButton
            isActive={isActive(node.path)}
            tooltip={node.name}
            onPointerDown={(e) => press(e.currentTarget)}
            onPointerUp={(e) => release(e.currentTarget)}
            onPointerLeave={(e) => release(e.currentTarget)}
            onClick={() => { navigate(node.path!); if (isMobile) setOpenMobile(false) }}
          >
            <IC className="h-4 w-4 shrink-0" />
            <span>{node.name}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      )
    }

    if (!node.path && node.children.length > 0) {
      const isExpanded = expanded.has(node.id)
      const IC = loadIcon(node.icon)
      const hasActiveChild = node.children.some(child => isActive(child.path))

      return (
        <SidebarMenuItem key={node.id}>
          <SidebarMenuButton isActive={hasActiveChild} onClick={(e: React.MouseEvent) => { if (state === "collapsed") { const rect = (e.currentTarget as HTMLElement).getBoundingClientRect(); setFlyoutTop(rect.bottom + 4); setFlyoutMenu(flyoutMenu === node.id ? null : node.id) } else toggleExpand(node.id) }}>
            <IC className="h-4 w-4 shrink-0" />
            <span className="font-medium">{node.name}</span>
            <ChevronRight className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
          </SidebarMenuButton>
          {isExpanded && (
            <SidebarMenuSub>
              {node.children.map((child) => {
                const CIC = loadIcon(child.icon)
                return (
                  <SidebarMenuSubItem key={child.id}>
                    <SidebarMenuSubButton
                      isActive={isActive(child.path)}
                      onPointerDown={(e) => press(e.currentTarget)}
                      onPointerUp={(e) => release(e.currentTarget)}
                      onPointerLeave={(e) => release(e.currentTarget)}
                      onClick={() => { if (child.path) { navigate(child.path); if (isMobile) setOpenMobile(false) } }}
                    >
                      <CIC className="h-4 w-4 shrink-0" />
                      <span>{child.name}</span>
                    </SidebarMenuSubButton>
                  </SidebarMenuSubItem>
                )
              })}
            </SidebarMenuSub>
          )}
          {state === "collapsed" && flyoutMenu === node.id && (
            <div ref={flyoutRef} className="fixed z-50 rounded-xl border-0 bg-popover py-2 shadow-2xl ring-1 ring-border/40" style={{ left: '4px', top: flyoutTop + 'px', width: '60px' }}>
              {node.children.map((child) => {
                const CIC = loadIcon(child.icon)
                const active = isActive(child.path)
                return (
                  <div key={child.id} onClick={() => { if (child.path) { navigate(child.path); setFlyoutMenu(null) } }} className={`flyout-item relative flex items-center justify-center py-2 mx-1 rounded-lg cursor-pointer transition-all duration-150 ${active ? 'bg-primary/8 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}>
                    <CIC className="h-4 w-4 shrink-0" />
                    <div className="flyout-tip absolute left-full ml-2 px-2 py-1 rounded bg-popover border text-xs whitespace-nowrap opacity-0 transition-opacity pointer-events-none shadow-sm">
                      {child.name}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </SidebarMenuItem>
      )
    }

    return null
  }

  return (
    <Sidebar collapsible="icon" className={glass ? 'glass-sidebar glass-edge-side' : ''}>
      <SidebarHeader>
        <div className="flex items-center gap-2.5 px-2 py-4">
          {tenantInfo.logo ? (
            <img src={tenantInfo.logo} alt="" className="h-9 w-9 rounded-xl object-cover border cursor-pointer" onClick={() => { navigate('/'); if (isMobile) setOpenMobile(false) }} />
          ) : (
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground text-sm font-bold shadow-sm shrink-0 cursor-pointer transition-transform hover:scale-105" onClick={() => { navigate('/'); if (isMobile) setOpenMobile(false) }}>
              {tenantInfo.name.charAt(0)}
            </div>
          )}
          <span className="text-sm font-semibold tracking-tight truncate text-foreground/80">{tenantInfo.name}</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {visibleMenus.map((node) => renderMenuItem(node))}
        </SidebarMenu>
      </SidebarContent>
    </Sidebar>
  )
}
