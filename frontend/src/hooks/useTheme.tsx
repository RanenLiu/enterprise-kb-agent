import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { api } from '@/api/client'

type Theme = 'light' | 'dark'
type Accent = 'blue' | 'violet' | 'emerald' | 'amber' | 'rose'

interface ThemeContextType {
  theme: Theme
  accent: Accent
  toggleTheme: () => void
  setAccent: (a: Accent) => void
  glass: boolean
  toggleGlass: () => void
  filledIcons: boolean
  toggleFilledIcons: () => void
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light', accent: 'blue',
  glass: false, filledIcons: false,
  toggleTheme: () => {}, setAccent: () => {}, toggleGlass: () => {}, toggleFilledIcons: () => {},
})

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    return (localStorage.getItem('theme') as Theme) || 'light'
  })
  const [accent, setAccentState] = useState<Accent>(() => {
    return (localStorage.getItem('accent') as Accent) || 'blue'
  })
  const [glass, setGlass] = useState(() => localStorage.getItem('glass') === 'true')
  const [filledIcons, setFilledIcons] = useState(() => localStorage.getItem('filledIcons') === 'true')
  const [synced, setSynced] = useState(false)

  // Listen for theme changes from LoginPage
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const prefs = e.detail
      if (prefs?.theme && ['light', 'dark'].includes(prefs.theme)) {
        setThemeState(prefs.theme)
      }
      if (prefs?.accent && ['blue','violet','emerald','amber','rose'].includes(prefs.accent)) {
        setAccentState(prefs.accent)
      }
      if (prefs?.filledIcons !== undefined) {
        localStorage.setItem('filledIcons', String(prefs.filledIcons))
        setFilledIcons(prefs.filledIcons)
      }
      setSynced(true)
    }
    window.addEventListener('themechange', handler as EventListener)
    return () => window.removeEventListener('themechange', handler as EventListener)
  }, [])

  // Load theme from server on mount
  useEffect(() => {
    if (!api.getToken()) {
      setSynced(true)
      return
    }
    api.getProfile().then((res) => {
      const prefs = res.data?.theme_prefs
      if (prefs?.theme && ['light', 'dark'].includes(prefs.theme)) {
        localStorage.setItem('theme', prefs.theme)
        setThemeState(prefs.theme)
      }
      if (prefs?.accent && ['blue','violet','emerald','amber','rose'].includes(prefs.accent)) {
        localStorage.setItem('accent', prefs.accent)
        setAccentState(prefs.accent)
      }
      if (prefs?.filledIcons !== undefined) {
        localStorage.setItem('filledIcons', String(prefs.filledIcons))
        setFilledIcons(prefs.filledIcons)
      }
    }).catch(() => {}).finally(() => setSynced(true))
  }, [api.getToken()])

  // Sync to server whenever theme/accent changes
  const syncToServer = useCallback(async (t: Theme, a: Accent, f?: boolean) => {
    if (!synced || !api.getToken()) return
    try {
      await api.updateProfile({ theme_prefs: { theme: t, accent: a, filledIcons: f ?? filledIcons } })
    } catch { /* ignore */ }
  }, [synced, filledIcons])

  const toggleTheme = useCallback(() => {
    setThemeState((t) => {
      const next = t === 'light' ? 'dark' : 'light'
      localStorage.setItem('theme', next)
      syncToServer(next, accent)
      return next
    })
  }, [accent, syncToServer])

  const setAccent = useCallback((a: Accent) => {
    setAccentState(a)
    localStorage.setItem('accent', a)
    syncToServer(theme, a)
  }, [theme, syncToServer])

  const toggleGlass = useCallback(() => {
    setGlass((g) => {
      const next = !g
      localStorage.setItem('glass', String(next))
      return next
    })
  }, [])

  const toggleFilledIcons = useCallback(() => {
    setFilledIcons((f) => {
      const next = !f
      localStorage.setItem('filledIcons', String(next))
      syncToServer(theme, accent, next)
      return next
    })
  }, [theme, accent, syncToServer])

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', theme === 'dark')
    root.classList.toggle('glass-mode', glass)
    root.classList.toggle('filled-icons', filledIcons)
    const ACCENT_COLORS: Record<Accent, { hue: string }> = {
      blue: { hue: '222' }, violet: { hue: '270' }, emerald: { hue: '158' },
      amber: { hue: '40' }, rose: { hue: '348' },
    }
    root.style.setProperty('--accent-hue', ACCENT_COLORS[accent].hue)
  }, [theme, accent, glass, filledIcons])

  return (
    <ThemeContext.Provider value={{ theme, accent, toggleTheme, setAccent, glass, toggleGlass, filledIcons, toggleFilledIcons }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)
export type { Accent }
