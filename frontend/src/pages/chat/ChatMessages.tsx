import { useEffect, useRef } from 'react'
import type { ChatMessage, RetrievalChunk } from '@/types/chat'
import { MessageBubble } from './MessageBubble'
import { ThinkingIndicator } from './ThinkingIndicator'
import type { ChatStatus } from './hooks/useChat'

interface ChatMessagesProps {
  messages: ChatMessage[]
  chunksByMsg: Record<string, RetrievalChunk[]>
  graphByMsg: Record<string, { entities: string[]; relations: { source: string; relation: string; target: string; doc_id: string }[] }>
  streamingText: string
  streamingReasoning?: string
  status: ChatStatus
  isLoading: boolean
  editingMsgId?: string | null
  editContent?: string
  onEdit?: (msgId: string, content: string) => void
  onEditContentChange?: (c: string) => void
  onEditSubmit?: () => void
  onEditCancel?: () => void
}

export function ChatMessages({ messages, chunksByMsg, graphByMsg, streamingText, streamingReasoning, status, isLoading, editingMsgId, editContent, onEdit, onEditContentChange, onEditSubmit, onEditCancel }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ block: 'end' })
    })
  }, [messages, streamingText, status])

  const showStatus = status === 'searching' || status === 'thinking'

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 && !isLoading && (
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>开始你的第一个问题</p>
        </div>
      )}
      {messages.map((m, i) => {
        // 最后一条用户消息才显示编辑按钮
        const lastUserIdx = [...messages].reverse().findIndex(x => x.role === 'user')
        const isLastUser = lastUserIdx >= 0 && i === messages.length - 1 - lastUserIdx
        return (
          <MessageBubble
            key={m.id} message={m} chunks={chunksByMsg[m.id]} graphData={graphByMsg[m.id]}
            isLastUser={isLastUser} onEdit={onEdit}
            isEditing={editingMsgId === m.id}
            editContent={editingMsgId === m.id ? editContent : undefined}
            onEditContentChange={onEditContentChange}
            onEditSubmit={onEditSubmit}
            onEditCancel={onEditCancel}
          />
        )
      })}
      {streamingText && (
        <MessageBubble
          message={{
            id: 'streaming',
            role: 'assistant',
            content: streamingText,
            reasoning_content: streamingReasoning,
            created_at: '',
          }}
          isStreaming
        />
      )}
      {showStatus && <ThinkingIndicator status={status} />}
      <div ref={bottomRef} />
    </div>
  )
}
