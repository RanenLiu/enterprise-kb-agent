import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus, Trash2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import type { ChatSession } from '@/types/chat'

interface ChatSidebarProps {
  sessions: ChatSession[]
  currentSessionId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
}

export function ChatSidebar({ sessions, currentSessionId, onSelect, onCreate, onDelete }: ChatSidebarProps) {
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  return (
    <div className="w-64 border-r flex flex-col h-full" style={{ backgroundColor: 'var(--sidebar-background)' }}>
      <div className="p-3 border-b">
        <Button onClick={onCreate} className="w-full" size="sm">
          <Plus className="mr-2 h-4 w-4" /> 新建对话
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-1 chat-sidebar-items">
          {sessions.map(s => (
            <div
              key={s.id}
              className={`group flex items-center justify-between rounded-lg px-3 py-2 cursor-pointer text-sm transition-colors ${s.id === currentSessionId
                ? 'bg-primary/10 text-primary'
                : 'hover:bg-muted/60'
                }`}
              onClick={() => onSelect(s.id)}
            >
              <span className="truncate flex-1">{s.title === 'New conversation' ? '新对话' : s.title}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100"
                onClick={e => { e.stopPropagation(); setDeleteTarget(s.id) }}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      </div>

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
    </div>
  )
}
