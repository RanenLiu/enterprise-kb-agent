import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { RefreshCw } from 'lucide-react'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { refresh } = useAuth()
  const from = (location.state as { from?: string })?.from || '/'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [captchaToken, setCaptchaToken] = useState('')
  const [captchaSvg, setCaptchaSvg] = useState('')
  const [captchaInput, setCaptchaInput] = useState('')
  const [needCaptcha, setNeedCaptcha] = useState(false)
  const [touched, setTouched] = useState<Record<string, boolean>>({})
  const [shaking, setShaking] = useState<Record<string, boolean>>({})
  const passwordRef = useRef<HTMLInputElement>(null)
  const captchaRef = useRef<HTMLInputElement>(null)

  const loadCaptcha = async () => {
    try {
      const res = await api.getCaptcha()
      setCaptchaToken(res.data.token)
      setCaptchaSvg(res.data.svg)
      setNeedCaptcha(true)
    } catch { /* captcha unavailable */ }
  }

  useEffect(() => { loadCaptcha() }, [])

  const handleBlur = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }))
    const val = field === 'username' ? username : password
    if (!val) {
      setShaking((prev) => ({ ...prev, [field]: true }))
      setTimeout(() => setShaking((prev) => ({ ...prev, [field]: false })), 300)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched({ username: true, password: true })
    if (!username || !password) return
    setLoading(true)
    setError('')
    try {
      const res = await api.login(
        username, password,
        needCaptcha ? captchaToken : undefined,
        needCaptcha ? captchaInput : undefined,
      )
      api.setToken(res.data.access_token)
      api.setRefreshToken(res.data.refresh_token)
      const prefs = res.data.theme_prefs
      if (prefs?.theme) localStorage.setItem('theme', prefs.theme)
      if (prefs?.accent) localStorage.setItem('accent', prefs.accent)
      if (prefs?.filledIcons !== undefined) localStorage.setItem('filledIcons', String(prefs.filledIcons))
      if (prefs) window.dispatchEvent(new CustomEvent('themechange', { detail: prefs }))
      await refresh()
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err.message || '登录失败')
      loadCaptcha()
      setCaptchaInput('')
      // 聚焦到验证码（如有）或密码输入框
      setTimeout(() => {
        if (needCaptcha) captchaRef.current?.focus()
        else passwordRef.current?.focus()
      }, 100)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">企业知识库</CardTitle>
          <CardDescription>智能问答系统登录</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input id="username" aria-invalid={touched.username && !username} placeholder={touched.username && !username ? '用户名不能为空' : '请输入用户名'} value={username} onChange={(e) => setUsername(e.target.value)} onBlur={() => handleBlur('username')} required className={`${shaking.username ? 'input-shake' : ''}${error ? ' border-destructive' : ''}`} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input id="password" type="password" ref={passwordRef} aria-invalid={touched.password && !password} placeholder={touched.password && !password ? '密码不能为空' : '请输入密码'} value={password} onChange={(e) => setPassword(e.target.value)} onBlur={() => handleBlur('password')} required className={`${shaking.password ? 'input-shake' : ''}${error ? ' border-destructive' : ''}`} />
            </div>
            {needCaptcha && captchaSvg && (
              <div className="space-y-2">
                <Label>验证码</Label>
                <div className="flex items-center gap-2">
                  <div className="border rounded overflow-hidden shrink-0" dangerouslySetInnerHTML={{ __html: captchaSvg }} />
                  <button type="button" className="p-1.5 rounded hover:bg-muted" onClick={loadCaptcha} title="刷新验证码">
                    <RefreshCw className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
                <Input ref={captchaRef} aria-invalid={touched.captcha && !captchaInput} placeholder={touched.captcha && !captchaInput ? '验证码不能为空' : '输入验证码'} value={captchaInput} onChange={(e) => setCaptchaInput(e.target.value)} onBlur={() => { setTouched((prev) => ({ ...prev, captcha: true })); if (!captchaInput) { setShaking((prev) => ({ ...prev, captcha: true })); setTimeout(() => setShaking((prev) => ({ ...prev, captcha: false })), 300) } }} required className={`${shaking.captcha ? 'input-shake' : ''}${error ? ' border-destructive' : ''}`} />
              </div>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '登录中...' : '登录'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
