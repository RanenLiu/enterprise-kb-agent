import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '@/api/client'

export interface MenuNode {
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

interface UserProfile {
  id: string
  username: string
  display_name: string
  avatar: string | null
  dept_id: string | null
  dept_name: string | null
  roles: string[]
  permissions: string[]
}

interface AuthContextType {
  user: UserProfile | null
  menus: MenuNode[]
  loading: boolean
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  menus: [],
  loading: true,
  refresh: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [menus, setMenus] = useState<MenuNode[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    try {
      const [profileRes, menusRes] = await Promise.allSettled([
        api.getProfile(),
        api.getUserMenus(),
      ])
      if (profileRes.status === 'fulfilled') {
        setUser(profileRes.value.data)
      } else {
        setUser(null)
        const err = profileRes.reason
        if (err?.code === 4001 || err?.code === 4004) {
          api.setToken(null)
          if (!window.location.pathname.startsWith('/login')) {
            window.location.href = '/login'
          }
        }
      }
      if (menusRes.status === 'fulfilled' && menusRes.value.data?.length > 0) {
        localStorage.setItem('sidebarMenuTree', JSON.stringify(menusRes.value.data))
        setMenus(menusRes.value.data)
      }
      // Fallback: if API returned empty, use cached (already set from localStorage)
    } catch (err: any) {
      setUser(null)
      // Fallback: use cached or basic static menus
      if (menus.length === 0) {
        const fallback = [
          { id: '0', parent_id: null, name: '首页', path: '/', icon: 'Home', permission_code: null, sort_order: 0, hidden: false, children: [] },
          { id: '1', parent_id: null, name: '智能问答', path: '/chat', icon: 'MessageSquare', permission_code: null, sort_order: 1, hidden: false, children: [] },
        ]
        setMenus(fallback)
        localStorage.setItem('sidebarMenuTree', JSON.stringify(fallback))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Load cached menus immediately
    try {
      const cached = localStorage.getItem('sidebarMenuTree')
      if (cached) setMenus(JSON.parse(cached))
    } catch {}

    if (api.getToken()) {
      refresh()
    } else {
      setLoading(false)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, menus, loading, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
