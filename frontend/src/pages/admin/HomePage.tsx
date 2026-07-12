import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/hooks/useAuth'
import { BookOpen, MessageSquare, Shield, Server, Database, Cpu, ArrowRight } from 'lucide-react'

export function HomePage() {
  const { user } = useAuth()
  const perms = user?.permissions ?? []

  const has = (code: string) => perms.includes(code)
  const isSuper = has('admin') // super_admin has all perms, but we check document for viewer

  const features = [
    { icon: MessageSquare, title: '智能问答', desc: '基于 RAG + GraphRAG 的精准问答，多路召回 + 精排，流式输出', color: 'from-violet-500/20 to-purple-500/10', iconColor: 'text-violet-600', perm: 'chat.access' },
    { icon: BookOpen, title: '知识库管理', desc: '多格式文档上传、解析、分块、索引，支持 PDF/Word/PPT/Excel', color: 'from-blue-500/20 to-cyan-500/10', iconColor: 'text-blue-600', perm: 'document.create' },
    { icon: Shield, title: '权限管控', desc: 'RBAC 五级角色体系，租户 Partition + 部门字段级数据隔离', color: 'from-amber-500/20 to-orange-500/10', iconColor: 'text-amber-600', perm: 'system.config' },
    { icon: Database, title: '多模型支持', desc: 'DeepSeek / OpenAI / Ollama vLLM 多 Provider 切换', color: 'from-rose-500/20 to-pink-500/10', iconColor: 'text-rose-600', perm: 'llm_config.read' },
    { icon: Cpu, title: '系统监控', desc: '实时服务状态监控，全链路 trace_id 追踪', color: 'from-indigo-500/20 to-blue-500/10', iconColor: 'text-indigo-600', perm: 'system.monitor' },
  ].filter((f) => has(f.perm))

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero */}
      <div className="page-section">
        <Card className="border-0 bg-gradient-to-br from-primary/5 via-primary/[0.02] to-background shadow-sm overflow-hidden relative">
          <div className="absolute top-0 right-0 w-1/3 h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent opacity-60" />
          <CardContent className="p-8 relative">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs font-mono border-primary/20 text-primary bg-primary/5">v0.4.0</Badge>
              <Badge variant="outline" className="text-xs border-emerald-500/20 text-emerald-600 bg-emerald-500/5">系统运行中</Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight mt-3">让知识流动起来，回答唾手可得</h1>
            <p className="text-muted-foreground mt-2 leading-relaxed">把文档交给它，它就变成了最懂你们业务的问答专家。团队成员只管提问，答案从知识库中来，准确实在。每个部门的数据天然隔离，安全可靠。</p>
            <div className="flex gap-3 mt-6">
              {has('chat.access') && (
                <a href="/chat"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm">
                  前往问答
                  <ArrowRight className="h-3.5 w-3.5" />
                </a>
              )}
              {has('document.create') && (
                <a href="/knowledge"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all bg-secondary text-secondary-foreground hover:bg-secondary/80 shadow-sm">
                  查看文档
                  <ArrowRight className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Feature cards */}
      {features.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 page-section">
          {features.map((f, i) => {
            const Icon = f.icon
            return (
              <Card key={f.title} className="card-hover border shadow-sm overflow-hidden" style={{ animationDelay: `${i * 0.05}s` }}>
                <div className={`h-1.5 bg-gradient-to-r ${f.color}`} />
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <div className={`p-1.5 rounded-lg bg-gradient-to-br ${f.color}`}>
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
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/30 pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Server className="h-4 w-4 text-primary" />
                技术栈
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <div className="flex flex-wrap gap-2">
                {[
                  'FastAPI', 'Python 3.11', 'React 19', 'PostgreSQL 16', 'Milvus 2.6',
                  'Neo4j 5', 'Redis 7', 'MinIO', 'LangChain', 'LlamaIndex',
                ].map((t) => (
                  <Badge key={t} variant="secondary" className="text-xs font-mono px-2.5 py-1">
                    {t}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
