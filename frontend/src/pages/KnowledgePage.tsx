import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Plus, Download } from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '@/api/client'
import { DocumentTable } from '@/components/knowledge/DocumentTable'
import { UploadDialog } from '@/components/knowledge/UploadDialog'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import type { Document } from '@/types/knowledge'
import { toast } from 'sonner'

export function KnowledgePage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [fileTypeFilter, setFileTypeFilter] = useState<string>('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [, setLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null)
  const [previewContent, setPreviewContent] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)

  const TEXT_EXTENSIONS = new Set(['txt', 'md', 'csv'])
  const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'tif'])
  const MARKDOWN_EXTENSIONS = new Set(['md', 'mdx'])
  const OFFICE_EXTENSIONS = new Set(['docx', 'pptx', 'ppt', 'xlsx', 'xls'])

  const getFileExt = (name: string) => name.split('.').pop()?.toLowerCase() || ''
  const fileUrl = (path: string) => '/api/v1/admin/files/' + path.split('/').map(s => encodeURIComponent(s)).join('/')

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.listDocuments({
        page, page_size: pageSize,
        status: statusFilter || undefined,
        file_type: fileTypeFilter || undefined,
        keyword: keyword || undefined,
      })
      setDocuments(res.data || [])
      setTotal(res.meta?.total || 0)
    } catch (err: any) {
      toast.error(err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter, fileTypeFilter, keyword])

  useEffect(() => { fetchDocuments() }, [fetchDocuments])

  // SSE — live document status updates from worker
  useEffect(() => {
    const es = new EventSource('/api/v1/knowledge/status/events')
    es.addEventListener('status_change', () => fetchDocuments())
    return () => es.close()
  }, [fetchDocuments])

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDocument(id)
      toast.success('文档已删除')
      fetchDocuments()
    } catch (err: any) {
      toast.error(err.message || '删除失败')
    }
  }

  const handleReindex = async (id: string) => {
    try {
      await api.reindexDocument(id)
      toast.success('已加入重索引队列')
      fetchDocuments()
    } catch (err: any) {
      toast.error(err.message || '重索引失败')
    }
  }

  const handlePreview = async (doc: Document) => {
    if (!doc.file_path) return
    setPreviewDoc(doc)
    setPreviewContent('')
    setPreviewLoading(true)
    const ext = getFileExt(doc.file_name)
    try {
      if (IMAGE_EXTENSIONS.has(ext)) {
        setPreviewContent(`__IMAGE__:${doc.file_path}`)
      } else if (TEXT_EXTENSIONS.has(ext)) {
        const resp = await fetch(fileUrl(doc.file_path))
        setPreviewContent(await resp.text())
      } else if (ext === 'pdf') {
        setPreviewContent(`__PDF__:${doc.file_path}`)
      } else if (OFFICE_EXTENSIONS.has(ext) || ext === 'eml' || ext === 'msg') {
        const token = api.getToken()
        const resp = await fetch(`/api/v1/knowledge/preview-text/${doc.id}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        })
        if (resp.ok) {
          const json = await resp.json()
          const content: string = json.data || ''
          // HTML preview (starts with __HTML__: marker)
          if (content.startsWith('__HTML__:')) {
            setPreviewContent(content)  // Keep marker for rendering
          } else {
            setPreviewContent(content)
          }
        } else {
          const errBody = await resp.json().catch(() => null)
          const errMsg = errBody?.message || resp.statusText
          setPreviewContent(`__OFFICE_FAIL__:${doc.file_path}`)
          console.warn('Office preview failed:', resp.status, errMsg)
        }
      } else {
        setPreviewContent(`__DOWNLOAD__:${doc.file_path}`)
      }
    } catch {
      setPreviewContent(`__DOWNLOAD__:${doc.file_path}`)
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleVisibilityChange = async (id: string, visibility: string) => {
    const labels: Record<string, string> = { private: '仅自己', dept: '部门可见', public: '全局公有' }
    try {
      await api.updateDocumentVisibility(id, visibility)
      toast.success(`可见范围已改为「${labels[visibility] || visibility}」`)
      fetchDocuments()
    } catch (err: any) {
      toast.error(err.message || '操作失败')
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="list-page animate-fade-in">
      <div className="list-header flex items-center justify-between shrink-0">
        <h1 className="text-2xl font-bold">知识库管理</h1>
        <Button onClick={() => setUploadOpen(true)}><Plus className="mr-1 h-3 w-3" />上传文档</Button>
      </div>
      <div className="list-card">

      <Card className="admin-table border shadow-sm">
        <CardHeader>
          <div className="flex items-center gap-4">
            <Input
              placeholder="搜索文件名..."
              className="max-w-xs"
              value={keyword}
              onChange={e => { setKeyword(e.target.value); setPage(1) }}
            />
            <Select value={fileTypeFilter} onValueChange={v => { setFileTypeFilter(v); setPage(1) }}>
              <SelectTrigger className="w-28">
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全部类型</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem><SelectItem value="docx">DOCX</SelectItem>
                <SelectItem value="xlsx">XLSX</SelectItem><SelectItem value="pptx">PPTX</SelectItem>
                <SelectItem value="md">Markdown</SelectItem><SelectItem value="txt">TXT</SelectItem>
                <SelectItem value="csv">CSV</SelectItem><SelectItem value="jpg">JPEG</SelectItem>
                <SelectItem value="png">PNG</SelectItem><SelectItem value="bmp">BMP</SelectItem>
                <SelectItem value="msg">MSG</SelectItem><SelectItem value="eml">EML</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={v => { setStatusFilter(v); setPage(1) }}>
              <SelectTrigger className="w-28">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全部状态</SelectItem>
                <SelectItem value="pending">等待中</SelectItem>
                <SelectItem value="parsing">解析中</SelectItem>
                <SelectItem value="chunking">分块中</SelectItem>
                <SelectItem value="indexing">索引中</SelectItem>
                <SelectItem value="ready">已完成</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0 flex-1 flex flex-col min-h-0">
          <div className="table-scroll">
          <DocumentTable
            documents={documents}
            onPreview={handlePreview}
            onDelete={(id) => setDeleteTarget(id)}
            onReindex={handleReindex}
            onVisibilityChange={handleVisibilityChange}
          />
          </div>
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
                <Button variant="outline" size="sm" className="h-7 text-xs" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</Button>
                <span className="flex items-center px-2 text-xs text-muted-foreground">{page} / {totalPages}</span>
                <Button variant="outline" size="sm" className="h-7 text-xs" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card></div>

      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} onSuccess={fetchDocuments} />

      <Dialog open={!!previewDoc} onOpenChange={(open) => { if (!open) setPreviewDoc(null) }}>
        <DialogContent className="sm:max-w-4xl max-h-[85vh]">
          <DialogHeader><DialogTitle className="text-lg">{previewDoc?.file_name}</DialogTitle></DialogHeader>
          {previewLoading ? (
            <p className="text-muted-foreground animate-pulse text-center py-8">加载中...</p>
          ) : (<div className="flex flex-col min-h-0">
            {previewDoc?.file_path && !previewContent.startsWith('__OFFICE_FAIL__:') && !previewContent.startsWith('__DOWNLOAD__:') && !previewContent.startsWith('__HTML__:') && (
              <div className="bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 px-4 py-2 text-xs text-center border-b shrink-0 flex items-center justify-center gap-1">
                预览效果可能与实际文档有差异，
                <a href={fileUrl(previewDoc.file_path)} download className="font-semibold underline underline-offset-2">下载</a>
                查看原文件
              </div>
            )}
            {previewContent.startsWith('__PDF__:') ? (
            <iframe src={fileUrl(previewContent.slice(8))} className="w-full h-[70vh] border rounded" />
          ) : previewContent.startsWith('__IMAGE__:') ? (
            <div className="flex justify-center p-4">
              <img src={fileUrl(previewContent.slice(11))} alt={previewDoc?.file_name} className="max-w-full max-h-[70vh] object-contain rounded" />
            </div>
          ) : previewContent.startsWith('__HTML__:') ? (
            <iframe srcDoc={previewContent.slice(9)} className="w-full h-[75vh] border rounded bg-white" title="文档预览" />
          ) : previewContent.startsWith('__OFFICE_FAIL__:') ? (
            <div className="text-center py-8 space-y-4">
              <p className="text-muted-foreground">该 Office 文档暂不支持在线预览</p>
              <Button variant="outline" asChild>
                <a href={fileUrl(previewContent.slice(16))} download target="_blank" rel="noopener noreferrer">
                  <Download className="mr-1.5 h-4 w-4" />下载文件
                </a>
              </Button>
            </div>
          ) : previewContent.startsWith('__DOWNLOAD__:') ? (
            <div className="text-center py-8 space-y-4">
              <p className="text-muted-foreground">该格式暂不支持在线预览</p>
              <Button variant="outline" asChild>
                <a href={fileUrl(previewContent.slice(13))} download target="_blank" rel="noopener noreferrer">
                  <Download className="mr-1.5 h-4 w-4" />下载文件
                </a>
              </Button>
            </div>
          ) : previewContent ? (
            <ScrollArea className="max-h-[70vh]">
              <div className="prose prose-sm dark:prose-invert max-w-none p-1 [&_pre]:whitespace-pre-wrap [&_pre]:break-all [&_code]:whitespace-pre-wrap [&_code]:break-all" style={{ overflowWrap: 'break-word' }}>
                {MARKDOWN_EXTENSIONS.has(getFileExt(previewDoc?.file_name || '')) ? (
                  <Markdown remarkPlugins={[remarkGfm]}>{previewContent}</Markdown>
                ) : (
                  <pre className="text-sm whitespace-pre-wrap break-all font-mono">{previewContent}</pre>
                )}
              </div>
            </ScrollArea>
          ) : (
            <p className="text-muted-foreground text-center py-8">（无内容）</p>
          )}
          </div>)}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除"
        description="确认删除此文档？"
        confirmText="删除"
        onConfirm={() => { if (deleteTarget) { handleDelete(deleteTarget); setDeleteTarget(null) } }}
      />
    </div>
  )
}
