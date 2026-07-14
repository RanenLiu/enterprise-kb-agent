import { useState } from 'react'
import { ChevronDown, ChevronUp, FileText } from 'lucide-react'
import type { RetrievalChunk } from '@/types/chat'

interface SourceInfoProps {
  chunks: RetrievalChunk[]
}

function docName(chunk: RetrievalChunk): string {
  return (chunk.heading_path || '').split(' > ')[0] || (chunk.doc_id || '').slice(0, 8) || '来源'
}

export function SourceInfo({ chunks }: SourceInfoProps) {
  const [expandedDocs, setExpandedDocs] = useState<Record<string, boolean>>({})

  if (!chunks || chunks.length === 0) return null

  // Only show if at least one chunk has meaningful relevance score
  const maxScore = Math.max(...chunks.map(c => c.score || 0))
  if (maxScore < 0.2) return null

  // Group by document name
  const grouped = chunks.reduce(
    (acc, c) => {
      const key = docName(c)
      if (!acc[key]) acc[key] = []
      acc[key].push(c)
      return acc
    },
    {} as Record<string, RetrievalChunk[]>,
  )

  const toggleDoc = (name: string) => {
    setExpandedDocs(prev => ({ ...prev, [name]: !prev[name] }))
  }

  const docNames = Object.keys(grouped)

  return (
    <div className="mt-2 border-t pt-2 border-muted-foreground/10 space-y-1">
      <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wider mb-1">相关文档</p>
      {docNames.map(docName => {
        const docChunks = grouped[docName]
        const isExpanded = expandedDocs[docName]
        return (
          <div key={docName}>
            <button
              onClick={() => toggleDoc(docName)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground/70 hover:text-foreground transition-colors cursor-pointer w-full text-left py-0.5"
            >
              <FileText className="h-3 w-3 shrink-0 text-primary/60" />
              <span className="font-medium truncate flex-1">{docName}</span>
              <span className="text-muted-foreground/40 shrink-0">{docChunks.length} 项</span>
              {isExpanded ? <ChevronUp className="h-3 w-3 shrink-0" /> : <ChevronDown className="h-3 w-3 shrink-0" />}
            </button>
            {isExpanded && (
              <div className="ml-5 space-y-0.5 pb-1">
                {docChunks.map((chunk, i) => {
                  const heading = (chunk.heading_path || '').replace(/#/g, '').trim()
                  const parts = heading.split(' > ')
                  const section = parts.length > 1 ? parts.slice(1).join(' > ') : ''
                  const page = chunk.page_range ? `第${chunk.page_range}页` : ''
                  return (
                    <div key={i} className="flex items-start gap-2 py-0.5 text-xs text-muted-foreground/60">
                      <span className="text-primary/40 shrink-0">[{chunk.source}]</span>
                      <span className="flex-1">
                        {section && <span>{section}</span>}
                        {page && <span className="text-muted-foreground/40 ml-1">({page})</span>}
                        {!section && !page && (
                          <span className="italic">{chunk.content.slice(0, 100)}{chunk.content.length > 100 ? '…' : ''}</span>
                        )}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
