export interface ChatSession {
  id: string
  title: string
  message_count: number
  last_message_at: string | null
  created_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  reasoning_content?: string
  metadata?: {
    search_chunks?: RetrievalChunk[]
    graph_entities?: string[]
    graph_relations?: Array<{ source: string; relation: string; target: string }>
  }
  created_at: string
}

export interface ChatRequest {
  session_id: string
  content: string
}

export interface SSEIntentData {
  intent: string
  reasoning: string
}

export interface RetrievalChunk {
  doc_id: string
  content: string
  heading_path: string
  page_range: string
  score: number
  source: string
}

export interface SSERetrievalData {
  chunks: RetrievalChunk[]
}

export interface SSETokenData {
  text: string
}

export interface SSEDoneData {
  message_id: string
  session_id: string
  usage: { prompt_tokens: number; completion_tokens: number }
}

export interface SSEErrorData {
  code: number
  message: string
}

export interface GraphRelation {
  source: string
  relation: string
  target: string
  doc_id: string
}

export interface SSEThinkingData {
  text: string
}

export interface SSEGraphData {
  entities: string[]
  relations: GraphRelation[]
}

export type SSEEvent =
  | { event: 'intent'; data: SSEIntentData }
  | { event: 'retrieval'; data: SSERetrievalData }
  | { event: 'graph'; data: SSEGraphData }
  | { event: 'thinking'; data: SSEThinkingData }
  | { event: 'token'; data: SSETokenData }
  | { event: 'done'; data: SSEDoneData }
  | { event: 'error'; data: SSEErrorData }
