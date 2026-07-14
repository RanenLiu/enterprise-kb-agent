import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Plus, Trash2, CheckSquare, Square } from 'lucide-react'
import type { ChatSession } from '@/types/chat'

interface ChatSidebarProps {
  sessions: ChatSession[]
  currentSessionId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
  onBatchDelete: (ids: string[]) => void
}

export function ChatSidebar({ sessions, currentSessionId, onSelect, onCreate, onDelete, onBatchDelete }: ChatSidebarProps) {
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showBatchConfirm, setShowBatchConfirm] = useState(false)

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === sessions.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(sessions.map(s => s.id)))
    }
  }

  const handleBatchDelete = () => {
    setShowBatchConfirm(false)
    onBatchDelete(Array.from(selectedIds))
    setSelectedIds(new Set())
    setSelectMode(false)
  }

  const exitSelectMode = () => {
    setSelectMode(false)
    setSelectedIds(new Set())
  }

  return (
    <div className="w-64 border-r flex flex-col h-full" style={{ backgroundColor: 'var(--sidebar-background)' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b shrink-0 min-h-[53px]">
        {selectMode ? (
          <>
            <div className="flex items-center gap-2">
              <button onClick={toggleSelectAll} className="text-muted-foreground hover:text-foreground transition-colors p-0.5">
                {selectedIds.size === sessions.length
                  ? <CheckSquare className="h-4 w-4" />
                  : <Square className="h-4 w-4" />
                }
              </button>
              <span className="text-xs text-muted-foreground">{selectedIds.size}/{sessions.length}</span>
            </div>
            <div className="flex items-center gap-1">
              {selectedIds.size > 0 && (
                <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive/70 hover:text-destructive"
                  onClick={() => setShowBatchConfirm(true)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
              <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={exitSelectMode}>完成</Button>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-sm font-semibold tracking-tight">会话</h2>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground"
                onClick={() => setSelectMode(true)} title="批量选择">
                <CheckSquare className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onCreate} title="新建会话">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5 chat-sidebar-items">
        {sessions.map(s => (
          <div
            key={s.id}
            className={`group flex items-center gap-2 rounded-lg px-2 py-2 cursor-pointer text-sm transition-colors
              ${selectMode ? 'hover:bg-muted/40' : s.id === currentSessionId ? 'bg-primary/10 text-primary' : 'hover:bg-muted/60'}`}
            onClick={() => selectMode ? toggleSelect(s.id) : onSelect(s.id)}
          >
            {selectMode && (
              <Checkbox
                checked={selectedIds.has(s.id)}
                className="shrink-0 pointer-events-none"
              />
            )}
            <span className="truncate flex-1">{s.title === 'New conversation' ? '新对话' : s.title}</span>
            {!selectMode && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
                onClick={e => { e.stopPropagation(); setDeleteTarget(s.id) }}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            )}
          </div>
        ))}
      </div>

      {/* Single delete confirm */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>删除后无法恢复，确定要删除此对话吗？</DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={() => { if (deleteTarget) onDelete(deleteTarget); setDeleteTarget(null) }}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Batch delete confirm */}
      <Dialog open={showBatchConfirm} onOpenChange={setShowBatchConfirm}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>批量删除</DialogTitle>
            <DialogDescription>确定要删除选中的 {selectedIds.size} 个会话吗？删除后无法恢复。</DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowBatchConfirm(false)}>取消</Button>
            <Button variant="destructive" onClick={handleBatchDelete}>删除 {selectedIds.size} 个</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
