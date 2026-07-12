import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { FileText, LogIn, RotateCcw } from 'lucide-react'
import { DateTimePicker } from '@/components/DateTimePicker'

const ACTION_LABELS: Record<string, string> = {
  create: '创建', update: '修改', delete: '删除', read: '查看',
  upload: '上传', download: '下载', login: '登录', logout: '登出',
  publish: '上线', unpublish: '下线', reindex: '重索引',
}

const RESOURCE_LABELS: Record<string, string> = {
  document: '文档', department: '部门', role: '角色', user: '用户',
  menu: '菜单', llm_config: '模型', system: '系统', session: '会话',
  auth: '认证', profile: '个人信息', password: '密码',
}

export function LogPage() {
  const { user } = useAuth()
  const roles = user?.roles ?? []
  const isSuper = roles.includes('super_admin')
  const isTenantAdmin = roles.includes('tenant_admin')

  const [searchParams, setSearchParams] = useSearchParams()

  const initFromParams = () => ({
    action_type: searchParams.get('action_type') || '_all',
    resource_type: searchParams.get('resource_type') || '_all',
    result: searchParams.get('result') || '_all',
    keyword: searchParams.get('keyword') || '',
    user: searchParams.get('user') || '',
    operator: searchParams.get('operator') || '',
    dept_id: searchParams.get('dept_id') || '_all',
    tenant_id: searchParams.get('tenant_id') || '_all',
    start_time: searchParams.get('start_time') || '',
    end_time: searchParams.get('end_time') || '',
  })

  const [tab, setTab] = useState<'operation' | 'login'>(searchParams.get('tab') === 'login' ? 'login' : 'operation')
  const [logs, setLogs] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10))
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [departments, setDepartments] = useState<any[]>([])
  const [tenants, setTenants] = useState<any[]>([])
  const [filters, setFilters] = useState(initFromParams)
  const [searchTrigger, setSearchTrigger] = useState(0)
  const filtersRef = useRef(filters)

  const showDeptSelect = isTenantAdmin || (isSuper && filters.tenant_id !== '_all')
  const deptOptions = isSuper && filters.tenant_id !== '_all'
    ? departments.filter((d) => d.tenant_id === filters.tenant_id)
    : departments
  useEffect(() => { filtersRef.current = filters }, [filters])

  // Load departments and tenants for filter
  useEffect(() => {
    if (isSuper || isTenantAdmin) {
      api.listDepartments().then((r) => setDepartments(r.data || [])).catch(() => { })
    }
    if (isSuper) {
      api.listTenants().then((r) => setTenants(r.data || [])).catch(() => { })
    }
  }, [])

  // Sync filters to URL search params
  useEffect(() => {
    const sp = new URLSearchParams()
    if (tab !== 'operation') sp.set('tab', tab)
    if (page > 1) sp.set('page', String(page))
    if (filters.action_type !== '_all') sp.set('action_type', filters.action_type)
    if (filters.resource_type !== '_all') sp.set('resource_type', filters.resource_type)
    if (filters.result !== '_all') sp.set('result', filters.result)
    if (filters.keyword) sp.set('keyword', filters.keyword)
    if (filters.user) sp.set('user', filters.user)
    if (filters.operator) sp.set('operator', filters.operator)
    if (filters.dept_id !== '_all') sp.set('dept_id', filters.dept_id)
    if (filters.tenant_id !== '_all') sp.set('tenant_id', filters.tenant_id)
    if (filters.start_time) sp.set('start_time', filters.start_time)
    if (filters.end_time) sp.set('end_time', filters.end_time)
    setSearchParams(sp, { replace: true })
  }, [tab, page, filters])

  const fetchLogs = useCallback(async () => {
    const f = filtersRef.current
    setLoading(true)
    try {
      const params: any = { page, page_size: pageSize }
      if (f.result && f.result !== '_all') params.result = f.result
      if (f.keyword) {
        if (tab === 'operation') params.keyword = f.keyword
        else params.username = f.keyword
      }
      if (tab === 'operation' && f.user) params.user = f.user
      if (tab === 'login' && f.operator) params.operator = f.operator
      if (f.dept_id && f.dept_id !== '_all' && (isSuper || isTenantAdmin)) {
        params.dept_id = f.dept_id
      }
      if (f.tenant_id && f.tenant_id !== '_all' && isSuper) {
        params.tenant_id = f.tenant_id
      }
      if (f.start_time) params.start_time = f.start_time
      if (f.end_time) params.end_time = f.end_time
      if (tab === 'operation') {
        if (f.action_type && f.action_type !== '_all') params.action_type = f.action_type
        if (f.resource_type && f.resource_type !== '_all') params.resource_type = f.resource_type
        const res = await api.listOperationLogs(params)
        setLogs(res.data || [])
        setTotal((res.meta?.total as number) || 0)
      } else {
        const res = await api.listLoginLogs(params)
        setLogs(res.data || [])
        setTotal((res.meta?.total as number) || 0)
      }
    } catch (err: any) {
      toast.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [tab, page, pageSize, searchTrigger])

  useEffect(() => { fetchLogs() }, [fetchLogs])

  const doSearch = () => { setSearchTrigger((n) => n + 1); setPage(1) }

  const totalPages = Math.ceil(total / pageSize)

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="list-page animate-fade-in">
      <div className="list-header shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">操作日志</h1>
          <p className="text-sm text-muted-foreground mt-1">查看系统操作和登录记录</p>
        </div>
      </div>
      <div className="list-card">
        <Card className="admin-table border shadow-sm">
          <CardHeader className="bg-muted/30 border-b pb-3">
            <div className="flex items-center gap-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                {tab === 'operation' ? <FileText className="h-4 w-4 text-primary" /> : <LogIn className="h-4 w-4 text-primary" />}
                {tab === 'operation' ? '操作日志' : '登录日志'}
              </CardTitle>
              <div className="flex ml-auto gap-1">
                <Button variant={tab === 'operation' ? 'default' : 'ghost'} size="sm" className="h-8 text-xs" onClick={() => { setTab('operation'); setPage(1); setFilters((prev) => ({ ...prev, start_time: '', end_time: '', tenant_id: '_all', dept_id: '_all' })) }}>
                  操作日志
                </Button>
                <Button variant={tab === 'login' ? 'default' : 'ghost'} size="sm" className="h-8 text-xs" onClick={() => { setTab('login'); setPage(1); setFilters((prev) => ({ ...prev, start_time: '', end_time: '', tenant_id: '_all', dept_id: '_all' })) }}>
                  登录日志
                </Button>
              </div>
            </div>
            <div className="flex gap-3 flex-wrap mt-3">
              {tab === 'operation' ? (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">资源</span>
                    <Select value={filters.resource_type} onValueChange={(v) => handleFilterChange('resource_type', v)}>
                      <SelectTrigger size="sm" className="w-28 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_all">全部</SelectItem>
                        <SelectItem value="document">文档</SelectItem>
                        <SelectItem value="department">部门</SelectItem>
                        <SelectItem value="role">角色</SelectItem>
                        <SelectItem value="user">用户</SelectItem>
                        <SelectItem value="menu">菜单</SelectItem>
                        <SelectItem value="llm_config">LLM 配置</SelectItem>
                        <SelectItem value="password">密码</SelectItem>
                        <SelectItem value="auth">认证</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">操作类型</span>
                    <Select value={filters.action_type} onValueChange={(v) => handleFilterChange('action_type', v)}>
                      <SelectTrigger size="sm" className="w-28 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_all">全部</SelectItem>
                        <SelectItem value="create">创建</SelectItem>
                        <SelectItem value="update">修改</SelectItem>
                        <SelectItem value="delete">删除</SelectItem>
                        <SelectItem value="upload">上传</SelectItem>
                        <SelectItem value="publish">发布</SelectItem>
                        <SelectItem value="unpublish">取消发布</SelectItem>
                        <SelectItem value="reindex">重新索引</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">用户</span>
                    <Input placeholder="用户" className="h-8 w-36 text-xs" value={filters.user} onChange={(e) => setFilters((prev) => ({ ...prev, user: e.target.value }))} />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">操作人</span>
                    <Input placeholder="操作人" className="h-8 w-36 text-xs" value={filters.keyword} onChange={(e) => setFilters((prev) => ({ ...prev, keyword: e.target.value }))} />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">时间</span>
                    <DateTimePicker placeholder="开始时间" value={filters.start_time} onChange={(v) => setFilters((prev) => ({ ...prev, start_time: v }))} />
                    <span className="text-xs text-muted-foreground">~</span>
                    <DateTimePicker placeholder="结束时间" value={filters.end_time} onChange={(v) => setFilters((prev) => ({ ...prev, end_time: v }))} />
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">用户</span>
                    <Input placeholder="用户名" className="h-8 w-36 text-xs" value={filters.keyword} onChange={(e) => setFilters((prev) => ({ ...prev, keyword: e.target.value }))} />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">操作人</span>
                    <Input placeholder="操作人" className="h-8 w-36 text-xs" value={filters.operator} onChange={(e) => setFilters((prev) => ({ ...prev, operator: e.target.value }))} />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">时间</span>
                    <DateTimePicker placeholder="开始时间" value={filters.start_time} onChange={(v) => setFilters((prev) => ({ ...prev, start_time: v }))} />
                    <span className="text-xs text-muted-foreground">~</span>
                    <DateTimePicker placeholder="结束时间" value={filters.end_time} onChange={(v) => setFilters((prev) => ({ ...prev, end_time: v }))} />
                  </div>
                </>
              )}
              {isSuper && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">租户</span>
                  <Select value={filters.tenant_id} onValueChange={(v) => {
                    setFilters((prev) => ({ ...prev, tenant_id: v, dept_id: '_all' }))
                  }}>
                    <SelectTrigger size="sm" className="w-28 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_all">全部</SelectItem>
                      {tenants.map((t: any) => (
                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              {showDeptSelect && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">部门</span>
                  <Select value={filters.dept_id} onValueChange={(v) => setFilters((prev) => ({ ...prev, dept_id: v }))}>
                    <SelectTrigger size="sm" className="w-28 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_all">全部</SelectItem>
                      {deptOptions.map((d: any) => (
                        <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground">结果</span>
                <Select value={filters.result} onValueChange={(v) => setFilters((prev) => ({ ...prev, result: v }))}>
                  <SelectTrigger size="sm" className="w-24 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all">全部</SelectItem>
                    <SelectItem value="success">成功</SelectItem>
                    <SelectItem value="failure">失败</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={doSearch}>搜索</Button>
                <Button variant="default" size="sm" className="h-8 text-xs shadow-sm" onClick={() => { setFilters({ action_type: '_all', resource_type: '_all', result: '_all', keyword: '', user: '', operator: '', dept_id: '_all', tenant_id: '_all', start_time: '', end_time: '' }); doSearch() }}>
                  <RotateCcw className="mr-1 h-3 w-3" />重置
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 flex-1 flex flex-col min-h-0">
            <div className="table-scroll">
              <Table className="min-w-[900px]">
                <TableHeader>
                  <TableRow className="bg-muted/20">
                    {tab === 'operation' ? (
                      <>
                        <TableHead className="font-medium w-[22%]">资源</TableHead>
                        <TableHead className="font-medium w-[8%]">操作类型</TableHead>
                        <TableHead className="font-medium w-[10%]">部门</TableHead>
                        <TableHead className="font-medium w-[10%]">用户</TableHead>
                        <TableHead className="font-medium w-[12%]">操作人</TableHead>
                        <TableHead className="font-medium w-[8%]">IP</TableHead>
                        <TableHead className="font-medium w-[8%]">结果</TableHead>
                        <TableHead className="font-medium w-[14%]">时间</TableHead></>
                    ) : (
                      <>
                        <TableHead className="font-medium w-[12%]">用户名</TableHead>
                        <TableHead className="font-medium w-[12%]">操作人</TableHead>
                        <TableHead className="font-medium w-[10%]">部门</TableHead>
                        <TableHead className="font-medium hidden md:table-cell w-[12%]">登录方式</TableHead>
                        <TableHead className="font-medium hidden sm:table-cell w-[12%]">IP</TableHead>
                        <TableHead className="font-medium w-[10%]">结果</TableHead>
                        <TableHead className="font-medium w-[18%]">失败原因</TableHead>
                        <TableHead className="font-medium w-[14%]">时间</TableHead>
                      </>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow><TableCell colSpan={8} className="text-center py-12 text-muted-foreground animate-pulse">加载中...</TableCell></TableRow>
                  ) : logs.length === 0 ? (
                    <TableRow><TableCell colSpan={8} className="text-center py-12 text-muted-foreground">暂无日志记录</TableCell></TableRow>
                  ) : logs.map((l: any, idx: number) => (
                    <TableRow key={l.id} className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/10'}>
                      {tab === 'operation' ? (
                        <>
                          <TableCell>
                            <span className="inline-flex items-center gap-1.5">
                              <Badge variant="secondary" className="text-xs font-normal px-1.5 py-0">{RESOURCE_LABELS[l.resource_type] || l.resource_type}</Badge>
                              {l.detail?.changes?.length > 0 && (
                                <span className="text-xs text-muted-foreground/70">{l.detail.changes.join('; ')}</span>
                              )}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs font-normal font-mono">{ACTION_LABELS[l.action_type] || l.action_type}</Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">{l.dept_name || '-'}</TableCell>
                          <TableCell className="text-sm">{l.user_name || '-'}</TableCell>
                          <TableCell className="text-sm">{l.display_name || '-'}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{l.ip_address || '-'}</TableCell>
                          <TableCell>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-normal ${l.result === 'success' ? 'bg-success/15 text-success' : 'bg-destructive/15 text-destructive'
                              }`}>{l.result === 'success' ? '成功' : '失败'}</span>
                          </TableCell>
                          <TableCell className="text-sm whitespace-nowrap text-muted-foreground">{new Date(l.created_at).toLocaleString()}</TableCell></>
                      ) : (
                        <>
                          <TableCell className="text-sm">{l.username}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{l.display_name || '-'}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{l.dept_name || "-"}</TableCell>
                          <TableCell className="hidden md:table-cell text-sm text-muted-foreground">{l.login_type}</TableCell>
                          <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">{l.ip_address || '-'}</TableCell>
                          <TableCell>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-normal ${l.result === 'success' ? 'bg-success/15 text-success' : 'bg-destructive/15 text-destructive'
                              }`}>{l.result === 'success' ? '成功' : '失败'}</span>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">{l.failure_reason || '-'}</TableCell>
                          <TableCell className="text-sm whitespace-nowrap">{new Date(l.created_at).toLocaleString()}</TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table></div>
            {total > 0 && (
              <div className="flex items-center justify-end px-4 py-3 border-t bg-muted/10 gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">共 {total} 条</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <select
                    value={pageSize}
                    onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                    className="h-7 text-xs border rounded px-1.5 bg-background text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <span className="text-xs text-muted-foreground">条/页</span>
                  <div className="w-px h-4 bg-border mx-1" />
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
                  <span className="flex items-center px-2 text-xs text-muted-foreground">{page} / {totalPages}</span>
                  <Button variant="outline" size="sm" className="h-7 text-xs" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
