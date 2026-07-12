import { useState, useEffect, useRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { AvatarCropDialog } from '@/components/AvatarCropDialog'
import { User, Lock, Camera } from 'lucide-react'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ProfileDialog({ open, onOpenChange }: Props) {
  const { user, refresh } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [cropFile, setCropFile] = useState<File | null>(null)
  const [uploading] = useState(false)
  const [cropOpen, setCropOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [profile, setProfile] = useState({
    display_name: user?.display_name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    avatar: user?.avatar || '',
  })
  const [password, setPassword] = useState({ old_password: '', new_password: '', confirm: '' })
  const [pwdErrors, setPwdErrors] = useState<Record<string, string>>({})

  // Sync profile state when dialog opens or user changes
  useEffect(() => {
    if (open) {
      setProfile({
        display_name: user?.display_name || '',
        email: user?.email || '',
        phone: user?.phone || '',
        avatar: user?.avatar || '',
      })
    }
  }, [open, user])

  const handleSelectFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCropFile(file)
    setCropOpen(true)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleCropComplete = (url: string) => {
    setProfile((p) => ({ ...p, avatar: url }))
  }

  const handleSaveProfile = async () => {
    setSaving(true)
    try {
      await api.updateProfile(profile)
      await refresh()
      toast.success('个人信息已更新')
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err.message || '更新失败')
    } finally {
      setSaving(false)
    }
  }

  const { logout } = useAuth()

  const handleChangePassword = async () => {
    const errs: Record<string, string> = {}
    if (!password.old_password) errs.old_password = '请输入当前密码'
    if (password.new_password.length < 6) errs.new_password = '密码至少 6 位'
    if (password.new_password !== password.confirm) errs.confirm = '两次密码输入不一致'
    setPwdErrors(errs)
    if (Object.keys(errs).length > 0) return

    setSaving(true)
    try {
      await api.changePassword({ old_password: password.old_password, new_password: password.new_password })
      toast.success('密码已修改，请重新登录')
      setPassword({ old_password: '', new_password: '', confirm: '' })
      setPwdErrors({})
      // Token is blacklisted — force re-login
      api.setToken(null)
      api.setRefreshToken(null)
      setTimeout(() => { window.location.href = '/login' }, 1500)
    } catch (err: any) {
      let msg = err.message || '修改失败'
      let key = 'old_password'
      // Parse Pydantic validation detail array: [{"loc":["body","old_password"],"msg":"..."}]
      try {
        const detail = typeof msg === 'string' && msg.startsWith('[') ? JSON.parse(msg) : null
        if (Array.isArray(detail)) {
          const first = detail[0]
          if (first?.loc?.includes('old_password')) key = 'old_password'
          else if (first?.loc?.includes('new_password')) key = 'new_password'
          msg = first?.msg || msg
        }
      } catch { /* not JSON */ }
      // Map backend messages to Chinese
      if (msg.includes('Old password')) { key = 'old_password'; msg = '当前密码不正确' }
      else if (msg.includes('old_password')) key = 'old_password'
      else if (msg.includes('new_password')) key = 'new_password'
      setPwdErrors({ [key]: msg })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg flex items-center gap-2">
            <User className="h-5 w-5 text-primary" />
            个人信息
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="profile" className="mt-2">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="profile" className="text-xs">基本信息</TabsTrigger>
            <TabsTrigger value="password" className="text-xs">修改密码</TabsTrigger>
          </TabsList>

          {/* Profile tab */}
          <TabsContent value="profile" className="space-y-4 pt-4">
            {/* Avatar */}
            <div className="flex items-center gap-4 pb-3 border-b">
              <div className="relative group">
                {profile.avatar ? (
                  <img src={profile.avatar} alt="" className="h-16 w-16 rounded-full object-cover border" />
                ) : (
                  <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border">
                    <User className="h-7 w-7 text-primary/40" />
                  </div>
                )}
                <label className="absolute inset-0 rounded-full bg-black/0 hover:bg-black/30 transition-colors flex items-center justify-center cursor-pointer">
                  <Camera className="h-5 w-5 text-white opacity-0 hover:opacity-100 transition-opacity" />
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleSelectFile}
                  />
                </label>
                {uploading && (
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
                    <span className="text-[10px] text-primary font-medium">上传中...</span>
                  </div>
                )}
              </div>
              <div className="text-sm">
                <p className="font-medium">{user?.display_name}</p>
                <p className="text-muted-foreground text-xs">@{user?.username}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">用户名</Label>
                <Input value={user?.username || ''} disabled className="text-sm bg-muted/50" />
                <p className="text-[10px] text-muted-foreground">用户名不可修改</p>
              </div>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">真实姓名</Label>
                <Input
                  value={profile.display_name}
                  onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
                  className="text-sm focus-visible:ring-1"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">邮箱</Label>
                <Input
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  className="text-sm focus-visible:ring-1"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">电话</Label>
                <Input
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  className="text-sm focus-visible:ring-1"
                />
              </div>
            </div>

            <Button onClick={handleSaveProfile} disabled={saving} className="w-full shadow-sm mt-2">
              {saving ? '保存中...' : '保存修改'}
            </Button>
          </TabsContent>

          {/* Password tab */}
          <TabsContent value="password" className="space-y-4 pt-4">
            <div className="flex items-center gap-3 pb-3 border-b">
              <Lock className="h-5 w-5 text-muted-foreground" />
              <div className="text-sm">
                <p className="font-medium">修改登录密码</p>
                <p className="text-xs text-muted-foreground">密码至少 6 位</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">当前密码</Label>
              <Input
                type="password"
                value={password.old_password}
                onChange={(e) => { setPassword({ ...password, old_password: e.target.value }); setPwdErrors({}) }}
                className={`text-sm focus-visible:ring-1${pwdErrors.old_password ? ' border-destructive' : ''}`}
              />
              {pwdErrors.old_password && <p className="text-xs text-destructive">{pwdErrors.old_password}</p>}
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">新密码</Label>
              <Input
                type="password"
                value={password.new_password}
                onChange={(e) => { setPassword({ ...password, new_password: e.target.value }); setPwdErrors({}) }}
                className={`text-sm focus-visible:ring-1${pwdErrors.new_password ? ' border-destructive' : ''}`}
              />
              {pwdErrors.new_password && <p className="text-xs text-destructive">{pwdErrors.new_password}</p>}
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">确认新密码</Label>
              <Input
                type="password"
                value={password.confirm}
                onChange={(e) => { setPassword({ ...password, confirm: e.target.value }); setPwdErrors({}) }}
                className={`text-sm focus-visible:ring-1${pwdErrors.confirm ? ' border-destructive' : ''}`}
              />
              {pwdErrors.confirm && <p className="text-xs text-destructive">{pwdErrors.confirm}</p>}
            </div>

            <Button onClick={handleChangePassword} disabled={saving} variant="default" className="w-full shadow-sm mt-2">
              {saving ? '修改中...' : '修改密码'}
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>

      <AvatarCropDialog
        open={cropOpen}
        onOpenChange={setCropOpen}
        file={cropFile}
        onComplete={handleCropComplete}
      />
    </Dialog>
  )
}
