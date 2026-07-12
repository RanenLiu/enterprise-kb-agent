import { type ChatStatus } from './hooks/useChat'

const STATUS_LABELS: Record<ChatStatus, string | null> = {
  idle: null,
  searching: '正在搜索知识库',
  thinking: '正在思考',
  streaming: null,
}

export function ThinkingIndicator({ status }: { status: ChatStatus }) {
  const label = STATUS_LABELS[status]
  if (!label) return null

  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3 bg-muted">
        <div className="flex items-center gap-2.5">
          <span className="text-sm text-muted-foreground">{label}</span>
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:300ms]" />
          </span>
        </div>
      </div>
    </div>
  )
}
