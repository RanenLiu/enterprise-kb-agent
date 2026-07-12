import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, Square, Brain } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  onSend: (content: string) => void
  onAbort: () => void
  isLoading: boolean
  disabled: boolean
  deepThinking: boolean
  onToggleDeepThinking: () => void
}

export function ChatInput({ onSend, onAbort, isLoading, disabled, deepThinking, onToggleDeepThinking }: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    setInput('')
    onSend(trimmed)
  }, [input, isLoading, onSend])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  if (isLoading) {
    return (
      <div className="border-t p-4">
        <Button onClick={onAbort} variant="outline" className="w-full bg-muted/20 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-colors">
          <Square className="mr-2 h-4 w-4" /> 停止生成
        </Button>
      </div>
    )
  }

  return (
    <div className="border-t p-4 space-y-2">
      <div className="flex items-center gap-3 px-1">
        <button
          onClick={onToggleDeepThinking}
          className={cn(
            'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-colors cursor-pointer',
            deepThinking
              ? 'border-primary/40 bg-primary/5 text-primary'
              : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground hover:border-muted-foreground/20',
          )}
        >
          <Brain className="h-3.5 w-3.5" />
          深度思考
        </button>
      </div>
      <div className="flex gap-2">
        <Textarea
          placeholder="输入你的问题..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="min-h-[80px] max-h-[200px]"
          rows={3}
        />
        <Button
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          className="self-end"
          size="icon"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
