import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Pencil, Trash2, Star, Cpu } from 'lucide-react'

export function ModelPage() {
  const [configs, setConfigs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', provider: 'deepseek', api_key: '', base_url: '', model: '', max_tokens: 4096, temperature: 1.0, is_active: false, is_default: false })

  const fetchConfigs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.listLLMConfigs()
      setConfigs(res.data || [])
    } catch (err: any) {
      toast.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchConfigs() }, [fetchConfigs])

  const openCreate = () => {
    setEditing(null)
    setForm({ name: '', provider: 'deepseek', api_key: '', base_url: '', model: '', max_tokens: 4096, temperature: 1.0, is_active: false, is_default: false })
    setDialogOpen(true)
  }

  const openEdit = (c: any) => {
    setEditing(c)
    setForm({ name: c.name, provider: c.provider, api_key: '', base_url: c.base_url || '', model: c.model, max_tokens: c.max_tokens, temperature: c.temperature, is_active: c.is_active, is_default: c.is_default })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('请输入配置名称'); return }
    if (!form.model.trim()) { toast.error('请输入模型名'); return }
    if (!form.base_url.trim()) { toast.error('请输入 API Base URL'); return }
    try {
      const data = { ...form }
      if (!data.api_key && !editing) return toast.error('API Key 不能为空')
      if (editing) {
        const updateData: any = { name: data.name, provider: data.provider, model: data.model, max_tokens: data.max_tokens, temperature: data.temperature, is_active: data.is_active, is_default: data.is_default }
        if (data.base_url) updateData.base_url = data.base_url
        if (data.api_key) updateData.api_key = data.api_key
        await api.updateLLMConfig(editing.id, updateData)
        toast.success('已更新')
      } else {
        await api.createLLMConfig(data)
        toast.success('已创建')
      }
      setDialogOpen(false)
      fetchConfigs()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteLLMConfig(id)
      toast.success('已删除')
      fetchConfigs()
    } catch (err: any) {
      toast.error(err.message || '删除失败')
    }
  }

  const handleSetDefault = async (id: string) => {
    try {
      await api.setDefaultLLMConfig(id)
      toast.success('已设为默认')
      fetchConfigs()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    }
  }

  return (
    <div className="list-page animate-fade-in">
      <div className="flex items-center justify-between page-section">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">模型配置</h1>
          <p className="text-sm text-muted-foreground mt-1">管理 LLM 提供商和模型参数</p>
        </div>
        <Button onClick={openCreate}>+ 新建配置</Button>
      </div>
      <div className="list-card">
        <Card className="admin-table border shadow-sm overflow-hidden">
          <CardHeader className="bg-muted/30 border-b pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Cpu className="h-4 w-4 text-primary" />
              LLM 配置列表
              
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 flex flex-col min-h-0">
            <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20">
                  <TableHead className="font-medium">名称</TableHead>
                  <TableHead className="font-medium">提供商</TableHead>
                  <TableHead className="font-medium hidden md:table-cell">模型</TableHead>
                  <TableHead className="font-medium hidden sm:table-cell">Token 上限</TableHead>
                  <TableHead className="font-medium">状态</TableHead>
                  <TableHead className="font-medium w-[140px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground animate-pulse">加载中...</TableCell></TableRow>
                ) : configs.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground">暂无配置，点击"新建配置"添加</TableCell></TableRow>
                ) : configs.map((c, idx) => (
                  <TableRow key={c.id} className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/10'}>
                    <TableCell className="font-medium">
                      {c.name}
                      {c.is_default && <Star className="inline ml-1.5 h-3.5 w-3.5 text-amber-500 fill-amber-500" />}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs font-mono">{c.provider}</Badge>
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-sm font-mono text-muted-foreground">{c.model}</TableCell>
                    <TableCell className="hidden sm:table-cell text-sm">{c.max_tokens}</TableCell>
                    <TableCell>
                      {c.is_default ? (
                        <Badge className="text-xs bg-amber-500/10 text-amber-600 border-amber-200">默认</Badge>
                      ) : c.is_active ? (
                        <Badge variant="secondary" className="text-xs">活跃</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs text-muted-foreground">未启用</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-0.5">
                        {!c.is_default && (
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-amber-600/70 hover:text-amber-600" onClick={() => handleSetDefault(c.id)} title="设为默认">
                            <Star className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(c)}><Pencil className="h-3.5 w-3.5" /></Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive/70 hover:text-destructive" onClick={() => setDeleteTarget(c.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table></div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle className="text-lg">{editing ? '编辑配置' : '新建配置'}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2" autoComplete="off"><div aria-hidden="true" style={{ position: 'absolute', left: '-9999px' }}><input type="text" tabIndex={-1} autoComplete="username" /><input type="password" tabIndex={-1} autoComplete="current-password" /></div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">名称</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="focus-visible:ring-1" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">提供商 <span className="text-destructive">*</span></Label>
              <Select value={form.provider} onValueChange={(v) => setForm({ ...form, provider: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="deepseek">DeepSeek</SelectItem>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="qwen">通义千问</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">模型名 <span className="text-destructive">*</span></Label>
              <Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="如：deepseek-chat" className="focus-visible:ring-1" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">API Key <span className="text-destructive">*</span></Label>
              <Input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder={editing ? '留空则不修改' : ''} className="focus-visible:ring-1" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Base URL <span className="text-destructive">*</span></Label>
              <Input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="如：https://api.deepseek.com" className="focus-visible:ring-1" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Max Tokens</Label>
              <Input type="number" value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })} className="focus-visible:ring-1" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Temperature</Label>
              <Input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} className="focus-visible:ring-1" />
              <p className="text-[10px] text-muted-foreground">控制输出随机性：0 为确定输出，1 为高度随机。建议 0.7-1.0</p>
            </div>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2.5 cursor-pointer text-sm">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="h-4 w-4 rounded border-primary text-primary" />
                激活
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer text-sm">
                <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} className="h-4 w-4 rounded border-primary text-primary" />
                设为默认
              </label>
            </div>
            <Button onClick={handleSave} className="w-full mt-2 shadow-sm">
              {editing ? '保存修改' : '创建配置'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除"
        description="确认删除此配置？"
        confirmText="删除"
        onConfirm={() => { if (deleteTarget) { handleDelete(deleteTarget); setDeleteTarget(null) } }}
      />
    </div>
  )
}
