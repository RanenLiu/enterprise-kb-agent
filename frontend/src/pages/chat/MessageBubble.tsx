import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { Pencil, Check, X, Copy, Brain, ChevronDown, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'
import type { ChatMessage, RetrievalChunk } from '@/types/chat'
import { SourceInfo } from './SourceInfo'

function ReasoningBlock({ content, initiallyExpanded }: { content: string; initiallyExpanded?: boolean }) {
  const [collapsed, setCollapsed] = useState(!initiallyExpanded)
  const [displayed, setDisplayed] = useState('')
  const textRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!initiallyExpanded || !content || displayed) return
    let i = 0
    const typeNext = () => {
      i++
      if (textRef.current) textRef.current.textContent = content.slice(0, i)
      if (i < content.length) timerRef.current = setTimeout(typeNext, 15)
      else setDisplayed(content)
    }
    typeNext()
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [content, initiallyExpanded])

  const handleToggle = () => {
    if (collapsed) {
      setCollapsed(false)
      setDisplayed(content)
    } else {
      setCollapsed(true)
    }
  }

  return (
    <div className="mb-3 rounded-lg border border-primary/10 bg-primary/[0.02] overflow-hidden">
      <button
        className="flex items-center gap-1.5 w-full px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        onClick={handleToggle}
      >
        <Brain className="h-3.5 w-3.5 text-primary/60" />
        <span className="font-medium">思考过程</span>
        {collapsed ? <ChevronRight className="h-3 w-3 ml-auto text-muted-foreground/40" /> : <ChevronDown className="h-3 w-3 ml-auto text-muted-foreground/40" />}
      </button>
      {!collapsed && (
        <div className="px-3 pb-2 text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap border-t border-primary/5 pt-2">
          {displayed ? content : <div ref={textRef} />}
        </div>
      )}
    </div>
  )
}

interface MessageBubbleProps {
  message: ChatMessage
  chunks?: RetrievalChunk[]
  isStreaming?: boolean
  isLastUser?: boolean
  onEdit?: (msgId: string, content: string) => void
  isEditing?: boolean
  editContent?: string
  onEditContentChange?: (c: string) => void
  onEditSubmit?: () => void
  onEditCancel?: () => void
}

export function MessageBubble({ message, chunks, isStreaming, isLastUser, onEdit, isEditing, editContent, onEditContentChange, onEditSubmit, onEditCancel }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const [showActions, setShowActions] = useState(false)

  if (isUser && isEditing) {
    // 编辑模式
    return (
      <div className="flex justify-end">
        <div className="w-full max-w-lg rounded-2xl rounded-br-sm bg-gradient-to-br from-primary to-primary/90 text-primary-foreground p-3 space-y-2 shadow-md">
          <textarea
            className="w-full bg-transparent text-sm resize-none outline-none border-b border-primary-foreground/20 pb-1 placeholder:text-primary-foreground/40"
            rows={3}
            value={editContent || ''}
            onChange={e => onEditContentChange?.(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onEditSubmit?.() } }}
            autoFocus
          />
          <div className="flex gap-2 justify-end">
            <button onClick={onEditCancel} className="p-1.5 rounded-lg hover:bg-primary-foreground/10 transition-colors"><X className="h-3.5 w-3.5" /></button>
            <button onClick={onEditSubmit} className="p-1.5 rounded-lg hover:bg-primary-foreground/10 transition-colors"><Check className="h-3.5 w-3.5" /></button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
    <div
      className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div
        className={cn(
          'w-fit max-w-full max-w-[60%] max-md:max-w-[75%] rounded-2xl px-4 py-3 relative break-words',
          isUser
            ? 'bg-gradient-to-br from-primary to-primary/85 text-primary-foreground rounded-br-sm'
            : 'bg-card border border-border/40 text-foreground rounded-bl-sm',
        )}
      >
        {isUser ? (
          <>
            <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
            {isLastUser && showActions && onEdit && (
              <button
                onClick={() => onEdit(message.id, message.content)}
                className="absolute -left-8 top-1/2 -translate-y-1/2 p-1 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-muted transition-colors"
                title="编辑" aria-label="编辑"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            )}
          </>
        ) : (
          <>
            {message.reasoning_content && (
              <ReasoningBlock content={message.reasoning_content} initiallyExpanded={!!isStreaming} />
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none break-words w-full prose-headings:font-bold prose-h3:text-base prose-h4:text-sm prose-strong:text-foreground prose-strong:font-semibold">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  pre: ({ children }) => <pre style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', wordBreak: 'break-word', overflow: 'hidden'}}>{children}</pre>,
                  code: ({ children }) => <code style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', wordBreak: 'break-word'}}>{children}</code>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
            {chunks && chunks.length > 0 && <SourceInfo chunks={chunks} />}
          </>
        )}
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-current animate-pulse ml-0.5" />
        )}
      </div>
      {message.created_at && !isStreaming && (
        <div className={cn('flex items-center gap-2 mt-1', isUser ? 'justify-end' : 'justify-start')}>
          <p className="text-[10px] text-foreground/40">{new Date(message.created_at).toLocaleString("zh-CN", { hour12: false })}</p>
          <button onClick={() => { navigator.clipboard.writeText(message.content); toast.success('已复制') }}
            className="text-[10px] text-foreground/30 hover:text-foreground/60 transition-colors cursor-pointer"
            title="复制内容" aria-label="复制内容">
            <Copy className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
    </>
  )
}
