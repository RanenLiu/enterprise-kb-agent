import { lazy, Suspense } from 'react'
import { Route } from 'react-router-dom'
import { AdminLayout } from '@/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Loader2 } from 'lucide-react'

const HomePage = lazy(() => import('@/pages/admin/HomePage').then(m => ({ default: m.HomePage })))
const ChatPage = lazy(() => import('@/pages/ChatPage').then(m => ({ default: m.ChatPage })))
const KnowledgePage = lazy(() => import('@/pages/KnowledgePage').then(m => ({ default: m.KnowledgePage })))
const DepartmentPage = lazy(() => import('@/pages/admin/DepartmentPage').then(m => ({ default: m.DepartmentPage })))
const RolePage = lazy(() => import('@/pages/admin/RolePage').then(m => ({ default: m.RolePage })))
const UserPage = lazy(() => import('@/pages/admin/UserPage').then(m => ({ default: m.UserPage })))
const LogPage = lazy(() => import('@/pages/admin/LogPage').then(m => ({ default: m.LogPage })))
const ModelPage = lazy(() => import('@/pages/admin/ModelPage').then(m => ({ default: m.ModelPage })))
const SettingsPage = lazy(() => import('@/pages/admin/SettingsPage').then(m => ({ default: m.SettingsPage })))

const LazyLoad = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<div className="flex flex-1 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}>
    {children}
  </Suspense>
)

const wrap = (Element: React.ComponentType) => (
  <LazyLoad><Element /></LazyLoad>
)

export const protectedRoutes = (
  <Route element={<ProtectedRoute />}>
    <Route element={<AdminLayout />}>
      <Route path="/" element={wrap(HomePage)} />
      <Route path="/chat" element={wrap(ChatPage)} />
      <Route path="/knowledge" element={wrap(KnowledgePage)} />
      <Route path="/admin/departments" element={wrap(DepartmentPage)} />
      <Route path="/admin/roles" element={wrap(RolePage)} />
      <Route path="/admin/users" element={wrap(UserPage)} />
      <Route path="/admin/logs" element={wrap(LogPage)} />
      <Route path="/admin/models" element={wrap(ModelPage)} />
      <Route path="/admin/settings" element={wrap(SettingsPage)} />
    </Route>
  </Route>
)
