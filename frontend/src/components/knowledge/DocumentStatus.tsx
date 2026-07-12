import { Badge } from '@/components/ui/badge'
import type { Document } from '@/types/knowledge'

const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending:  { label: '等待中', variant: 'outline' },
  parsing:  { label: '解析中', variant: 'secondary' },
  chunking: { label: '分块中', variant: 'secondary' },
  indexing: { label: '索引中', variant: 'secondary' },
  ready:    { label: '已完成', variant: 'default' },
  failed:   { label: '失败',   variant: 'destructive' },
}

export function DocumentStatus({ status }: { status: Document['status'] }) {
  const config = statusConfig[status] || { label: status, variant: 'outline' as const }
  return <Badge variant={config.variant}>{config.label}</Badge>
}
