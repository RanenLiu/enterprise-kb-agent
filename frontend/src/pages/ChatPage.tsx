import { useEffect, useState } from 'react'
import { useChat } from '@/pages/chat/hooks/useChat'
import { ChatSidebar } from '@/pages/chat/ChatSidebar'
import { ChatMessages } from '@/pages/chat/ChatMessages'
import { ChatInput } from '@/pages/chat/ChatInput'
import { Button } from '@/components/ui/button'
import { PanelLeftOpen, PanelLeftClose } from 'lucide-react'
import { useIsMobile } from '@/hooks/use-mobile'

export function ChatPage() {
  const {
    sessions, currentSessionId, messages, chunksByMsg, graphByMsg, streamingText, streamingReasoning, status, isLoading,
    deepThinking, toggleDeepThinking,
    editingMsgId, editContent,
    startEdit, setEditContent, submitEdit, cancelEdit,
    loadSessions, selectSession, createSession, deleteSession,
    sendMessage, abortStream,
  } = useChat()
  const isMobile = useIsMobile()
  const [showSessions, setShowSessions] = useState(false)

  // 初始化：加载列表后默认选中第一个会话
  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      selectSession(sessions[0].id)
    }
  }, [sessions, currentSessionId, selectSession])

  const handleCreateSession = async () => {
    const id = await createSession()
    await selectSession(id)
    if (isMobile) setShowSessions(false)
  }

  const handleSelectSession = (id: string) => {
    selectSession(id)
    if (isMobile) setShowSessions(false)
  }

  return (
    <div className="flex h-full min-h-0 chat-page">
      {/* Mobile overlay */}
      {isMobile && showSessions && (
        <div className="fixed inset-0 z-10 bg-black/20" onClick={() => setShowSessions(false)} />
      )}
      <div className={`${isMobile ? (showSessions ? 'fixed inset-y-0 left-0 z-20 w-4/5 max-w-[280px]' : 'hidden') : 'h-full min-h-0'}`}>
        <ChatSidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelect={handleSelectSession}
          onCreate={handleCreateSession}
          onDelete={deleteSession}
        />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header with session toggle */}
        {isMobile && (
          <div className="flex items-center gap-2 px-3 py-2 border-b shrink-0">
            <Button variant="ghost" size="icon" className="size-8 shrink-0" onClick={() => setShowSessions(!showSessions)}>
              {showSessions ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </Button>
            {currentSessionId && !showSessions && (
              <span className="text-sm font-medium truncate">
                {sessions.find(s => s.id === currentSessionId)?.title?.replace('New conversation', '新对话') || '智能问答'}
              </span>
            )}
          </div>
        )}
        <ChatMessages
          messages={messages}
          chunksByMsg={chunksByMsg}
          graphByMsg={graphByMsg}
          streamingText={streamingText}
          streamingReasoning={streamingReasoning}
          status={status}
          isLoading={isLoading}
          editingMsgId={editingMsgId}
          editContent={editContent}
          onEdit={startEdit}
          onEditContentChange={setEditContent}
          onEditSubmit={submitEdit}
          onEditCancel={cancelEdit}
        />
        <ChatInput
          onSend={sendMessage}
          onAbort={abortStream}
          isLoading={isLoading}
          disabled={!currentSessionId}
          deepThinking={deepThinking}
          onToggleDeepThinking={toggleDeepThinking}
        />
      </div>
    </div>
  )
}
