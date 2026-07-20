import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/hooks/useAuth'
import { BookOpen, MessageSquare, Shield, Server, Database, Cpu, ArrowRight } from 'lucide-react'

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  MessageSquare,
  BookOpen,
  Shield,
  Database,
  Cpu,
}

interface FeatureCard {
  icon: string
  title: string
  desc: string
  color: string
  iconColor: string
  perm: string
}

export function HomePage() {
  const { user } = useAuth()
  const perms = user?.permissions ?? []
  const has = (code: string) => perms.includes(code)
  const isSuper = has('admin')
  const [features, setFeatures] = useState<FeatureCard[]>([])

  useEffect(() => {
    fetch('/api/v1/config/features')
      .then(res => res.json())
      .then(json => setFeatures(json.data || []))
      .catch(() => setFeatures([]))
  }, [])

  const visibleFeatures = features.filter(f => has(f.perm))

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero */}
      <div className="page-section">
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-primary/[0.06] via-primary/[0.02] to-transparent border shadow-sm">
          <div className="absolute top-0 right-0 w-1/2 h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/[0.08] via-transparent to-transparent opacity-70" />
          <div className="absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-primary/[0.04] blur-3xl" />
          <div className="p-8 relative">
            <div className="flex items-center gap-2 mb-3">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border border-primary/20 text-primary bg-primary/5">v0.4.0</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border border-emerald-500/20 text-emerald-600 bg-emerald-500/5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                系统运行中
              </span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground text-balance">让知识流动起来，回答唾手可得</h1>
            <p className="text-muted-foreground mt-3 leading-relaxed">把文档交给它，它就变成了最懂你们业务的问答专家。团队成员只管提问，答案从知识库中来，准确实在。每个部门的数据天然隔离，安全可靠。</p>
            <div className="flex gap-3 mt-6">
              {has('chat.access') && (
                <a href="/chat"
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg text-sm font-medium transition-all bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/20">
                  前往问答
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              )}
              {has('document.create') && (
                <a href="/knowledge"
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg text-sm font-medium transition-all bg-secondary text-secondary-foreground hover:bg-secondary/80 shadow-sm">
                  查看文档
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Feature cards */}
      {visibleFeatures.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 page-section">
          {visibleFeatures.map((f, i) => {
            const Icon = ICON_MAP[f.icon]
            return (
              <Card key={f.title} className="card-modern overflow-hidden" style={{ animationDelay: `${i * 0.05}s` }}>
                <div className="h-1.5" style={{ background: f.color }} />
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <div className="p-1.5 rounded-lg" style={{ background: f.color?.replace('to right', 'to bottom right') }}>
                      <Icon className={`h-4 w-4 ${f.iconColor}`} />
                    </div>
                    {f.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Tech stack — super admin only */}
      {isSuper && (
        <div className="page-section">
          <div className="rounded-xl border shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 border-b bg-muted/20">
              <Server className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">技术栈</span>
            </div>
            <div className="p-4">
              <div className="flex flex-wrap gap-2">
                {[
                  'FastAPI', 'Python 3.11', 'React 19', 'PostgreSQL 16', 'Milvus 2.6',
                  'Neo4j 5', 'Redis 7', 'MinIO', 'LangChain', 'LlamaIndex',
                ].map((t) => (
                  <span key={t} className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono bg-muted/50 text-muted-foreground border">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
