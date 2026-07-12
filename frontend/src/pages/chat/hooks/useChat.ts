import { useState, useCallback, useRef } from 'react'
import { api } from '@/api/client'
import type { ChatSession, ChatMessage, RetrievalChunk, GraphRelation, SSEEvent } from '@/types/chat'

export type ChatStatus = 'idle' | 'searching' | 'thinking' | 'streaming'

interface GraphData {
  entities: string[]
  relations: GraphRelation[]
}

interface UseChatReturn {
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: ChatMessage[]
  chunksByMsg: Record<string, RetrievalChunk[]>
  graphByMsg: Record<string, GraphData>
  streamingText: string
  streamingReasoning: string
  status: ChatStatus
  isLoading: boolean
  deepThinking: boolean
  editingMsgId: string | null
  editContent: string
  toggleDeepThinking: () => void
  startEdit: (msgId: string, content: string) => void
  setEditContent: (c: string) => void
  submitEdit: () => Promise<void>
  cancelEdit: () => void
  loadSessions: () => Promise<void>
  selectSession: (id: string) => Promise<void>
  createSession: () => Promise<string>
  deleteSession: (id: string) => Promise<void>
  sendMessage: (content: string) => Promise<void>
  abortStream: () => void
}

export function useChat(): UseChatReturn {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chunksByMsg, setChunksByMsg] = useState<Record<string, RetrievalChunk[]>>({})
  const [graphByMsg, setGraphByMsg] = useState<Record<string, GraphData>>({})
  const [streamingText, setStreamingText] = useState('')
  const [streamingReasoning, setStreamingReasoning] = useState('')
  const answerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [isLoading, setIsLoading] = useState(false)
  const [deepThinking, setDeepThinking] = useState(() => localStorage.getItem('deepThinking') === 'true')
  const [editingMsgId, setEditingMsgId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const lastChunksRef = useRef<RetrievalChunk[]>([])
  const lastGraphRef = useRef<GraphData | null>(null)

  const toggleDeepThinking = useCallback(() => {
    setDeepThinking(prev => {
      const next = !prev
      localStorage.setItem('deepThinking', String(next))
      return next
    })
  }, [])

  const loadSessions = useCallback(async () => {
    const res = await api.listSessions()
    setSessions(res.data)
  }, [])

  const selectSession = useCallback(async (id: string) => {
    setCurrentSessionId(id)
    setStreamingText('')
    const chunks: Record<string, RetrievalChunk[]> = {}
    const graphs: Record<string, GraphData> = {}
    const res = await api.listMessages(id)
    for (const msg of res.data) {
      if (msg.metadata?.search_chunks) {
        chunks[msg.id] = msg.metadata.search_chunks
      }
      if (msg.metadata?.graph_entities && msg.metadata?.graph_relations) {
        graphs[msg.id] = {
          entities: msg.metadata.graph_entities,
          relations: msg.metadata.graph_relations,
        }
      }
    }
    setChunksByMsg(chunks)
    setGraphByMsg(graphs)
    setMessages(res.data)
  }, [])

  const createSession = useCallback(async () => {
    const res = await api.createSession()
    await loadSessions()
    return res.data.id
  }, [loadSessions])

  const deleteSession = useCallback(async (id: string) => {
    await api.deleteSession(id)
    await loadSessions()
    if (currentSessionId === id) {
      setCurrentSessionId(null)
      setMessages([])
      setChunksByMsg({})
    }
  }, [loadSessions, currentSessionId])

  const sendMessage = useCallback(async (content: string) => {
    if (!currentSessionId) return
    setIsLoading(true)
    setStreamingText('')
    lastChunksRef.current = []

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])

    const abortController = new AbortController()
    abortRef.current = abortController

    let fullResponse = ''
    let thinkingContent = ''
    let hasStartedStreaming = false
    let msgId = ''
    setStatus('searching')
    setStreamingReasoning('')
    try {
      await api.sendMessageStream(
        currentSessionId,
        content,
        (event: SSEEvent) => {
          switch (event.event) {
            case 'intent':
              setStatus((event.data as any).intent === 'knowledge_query' ? 'searching' : 'thinking')
              break
            case 'retrieval':
              lastChunksRef.current = (event.data as any).chunks || []
              setStatus('thinking')
              break
            case 'graph':
              lastGraphRef.current = event.data
              break
            case 'thinking':
              thinkingContent += (event.data as any).text
              break
            case 'token':
              if (!hasStartedStreaming) {
                hasStartedStreaming = true
                setStatus('streaming')
                // 首个内容 token 到达，设置推理内容并延迟展示回答
                if (thinkingContent) {
                  setStreamingReasoning(thinkingContent)
                  setStreamingText(' ')
                  answerTimerRef.current = setTimeout(() => {
                    answerTimerRef.current = null
                    // 逐字回放缓冲的回答内容
                    const text = fullResponse || ''
                    if (!text) return
                    let k = 0
                    const playNext = () => {
                      k += 2
                      if (k >= text.length) {
                        setStreamingText(text)
                      } else {
                        setStreamingText(text.slice(0, k))
                        setTimeout(playNext, 12)
                      }
                    }
                    playNext()
                  }, thinkingContent.length * 15 + 300)
                  break
                }
              }
              fullResponse += (event.data as any).text
              if (!answerTimerRef.current) {
                setStreamingText(fullResponse)
              }
              break
            case 'done':
              if (answerTimerRef.current) {
                clearTimeout(answerTimerRef.current)
                answerTimerRef.current = null
              }
              setStreamingText('')
              setStreamingReasoning('')
              msgId = (event.data as any).message_id
              // 将图谱和检索数据写入 metadata
              const assistantMetadata: ChatMessage['metadata'] = {}
              if (lastChunksRef.current.length > 0) {
                assistantMetadata.search_chunks = lastChunksRef.current
              }
              if (lastGraphRef.current) {
                assistantMetadata.graph_entities = lastGraphRef.current.entities
                assistantMetadata.graph_relations = lastGraphRef.current.relations
              }
              const assistantMsg: ChatMessage = {
                id: msgId,
                role: 'assistant',
                content: fullResponse,
                reasoning_content: thinkingContent || undefined,
                created_at: new Date().toISOString(),
                metadata: Object.keys(assistantMetadata).length > 0 ? assistantMetadata : undefined,
              }
              setMessages(prev => [...prev, assistantMsg])
              if (lastChunksRef.current.length > 0) {
                setChunksByMsg(prev => ({ ...prev, [msgId]: lastChunksRef.current }))
              }
              if (lastGraphRef.current) {
                setGraphByMsg(prev => ({ ...prev, [msgId]: lastGraphRef.current! }))
                lastGraphRef.current = null
              }
              setStreamingText('')
              setStatus('idle')
              loadSessions()
              break
            case 'error':
              console.error('Stream error:', (event.data as any).message)
              setStatus('idle')
              break
          }
        },
        abortController.signal,
        deepThinking,
      )
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('sendMessage error:', err)
      }
    } finally {
      setIsLoading(false)
      setStatus('idle')
      abortRef.current = null
    }
  }, [currentSessionId, loadSessions, deepThinking])

  const abortStream = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsLoading(false)
  }, [])

  const startEdit = useCallback((msgId: string, content: string) => {
    setEditingMsgId(msgId)
    setEditContent(content)
  }, [])

  const cancelEdit = useCallback(() => {
    setEditingMsgId(null)
    setEditContent('')
  }, [])

  const submitEdit = useCallback(async () => {
    const content = editContent.trim()
    if (!content || !editingMsgId || !currentSessionId) return
    // 找到编辑的消息索引，截断后面的消息和元数据
    const idx = messages.findIndex(m => m.id === editingMsgId)
    if (idx < 0) return
    const truncated = messages.slice(0, idx)
    const oldIds = messages.slice(idx).map(m => m.id)
    setMessages(truncated)
    setChunksByMsg(prev => { const n = { ...prev }; oldIds.forEach(id => delete n[id]); return n })
    setGraphByMsg(prev => { const n = { ...prev }; oldIds.forEach(id => delete n[id]); return n })
    setEditingMsgId(null)
    setEditContent('')
    // 重新发送
    await sendMessage(content)
  }, [editContent, editingMsgId, currentSessionId, messages, sendMessage])

  return {
    sessions, currentSessionId, messages, chunksByMsg, graphByMsg, streamingText, streamingReasoning, status, isLoading,
    deepThinking, toggleDeepThinking,
    editingMsgId, editContent,
    startEdit, setEditContent, submitEdit, cancelEdit,
    loadSessions, selectSession, createSession, deleteSession, sendMessage, abortStream,
  }
}
