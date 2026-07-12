import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Download, RotateCw, Share2, Trash2 } from 'lucide-react'
import { DocumentStatus } from './DocumentStatus'
import { useAuth } from '@/hooks/useAuth'
import type { Document } from '@/types/knowledge'

const VIS_CLASSES: Record<string, string> = {
  private: 'bg-muted text-muted-foreground border-muted-foreground/20',
  dept: 'bg-success/10 text-success-foreground border-success/30',
  public: 'bg-primary/10 text-primary border-primary/30',
}

interface DocumentTableProps {
  documents: Document[]
  onPreview?: (doc: Document) => void
  onDelete: (id: string) => void
  onReindex: (id: string) => void
  onVisibilityChange: (id: string, visibility: string) => void
  onGraph?: (id: string) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export function DocumentTable({ documents, onPreview, onDelete, onReindex, onVisibilityChange, onGraph }: DocumentTableProps) {
  const { user } = useAuth()
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const isAdmin = isSuperAdmin || isTenantAdmin
  const hasDept = !!user?.dept_id

  const canChangeVisibility = (doc: Document): boolean => {
    if (isAdmin) return true
    if (doc.visibility === 'public') return false
    return true
  }

  if (documents.length === 0) {
    return <p className="text-center text-muted-foreground py-8">暂无文档，点击上方按钮上传</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[15%] min-w-[120px]">文件名</TableHead>
          <TableHead className="w-[5%]">类型</TableHead>
          <TableHead className="w-[5%]">大小</TableHead>
          <TableHead className="w-[5%]">状态</TableHead>
          <TableHead className="w-[5%]">可见范围</TableHead>
          <TableHead className="w-[5%]">Chunk 数</TableHead>
          <TableHead className="w-[6%]">上传时间</TableHead>
          <TableHead className="w-[8%]">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map(doc => {
          const canChange = canChangeVisibility(doc)
          const isAdminDoc = doc.visibility === 'public' && !isAdmin
          return (
          <TableRow key={doc.id} className={isAdminDoc ? 'bg-muted/30' : doc.visibility === 'private' ? 'opacity-60' : ''}>
            <TableCell>
              <button className="font-medium text-left hover:text-primary hover:underline cursor-pointer transition-colors bg-transparent border-none p-0" onClick={() => onPreview?.(doc)} title="预览">
                {doc.file_name}
              </button>
            </TableCell>
            <TableCell>{doc.file_type.toUpperCase()}</TableCell>
            <TableCell>{formatSize(doc.file_size)}</TableCell>
            <TableCell><DocumentStatus status={doc.status} /></TableCell>
            <TableCell>
              {doc.status === 'ready' ? (
                canChange ? (
                  <Select value={doc.visibility} onValueChange={(v) => onVisibilityChange(doc.id, v)}>
                    <SelectTrigger className={`h-7 w-28 text-xs border ${VIS_CLASSES[doc.visibility] || ''}`}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="private" className="text-xs">仅自己</SelectItem>
                      {hasDept && <SelectItem value="dept" className="text-xs">部门可见</SelectItem>}
                      {isAdmin && <SelectItem value="public" className="text-xs">全局公有</SelectItem>}
                    </SelectContent>
                  </Select>
                ) : (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${VIS_CLASSES[doc.visibility] || ''}`}>
                    {doc.visibility === 'public' ? '全局公有' : doc.visibility === 'dept' ? '部门可见' : '仅自己'}
                  </span>
                )
              ) : (
                <span className="text-xs text-muted-foreground">-</span>
              )}
            </TableCell>
            <TableCell>{doc.chunk_count}</TableCell>
            <TableCell>{formatDate(doc.created_at)}</TableCell>
            <TableCell className="space-x-1 whitespace-nowrap">
              {doc.status === 'ready' && doc.file_path && (
                <Button variant="outline" size="icon" className="h-8 w-8" asChild title="下载">
                  <a href={'/api/v1/admin/files/' + doc.file_path.split('/').map(encodeURIComponent).join('/')} download target="_blank" rel="noopener noreferrer">
                    <Download className="h-3.5 w-3.5" />
                  </a>
                </Button>
              )}
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => onReindex(doc.id)} disabled={['parsing', 'chunking', 'indexing'].includes(doc.status)} title="重索引">
                <RotateCw className="h-3.5 w-3.5" />
              </Button>
              {onGraph && (
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => onGraph(doc.id)} title="图谱">
                  <Share2 className="h-3.5 w-3.5" />
                </Button>
              )}
              <Button variant="destructive" size="icon" className="h-8 w-8" onClick={() => onDelete(doc.id)} title="删除">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </TableCell>
          </TableRow>
        )})}
      </TableBody>
    </Table>
  )
}
