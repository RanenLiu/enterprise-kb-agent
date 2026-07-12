export interface Document {
  id: string
  dept_id: string
  title: string
  file_name: string
  file_type: string
  file_size: number
  md5: string | null
  visibility: 'private' | 'dept' | 'public'
  status: 'pending' | 'parsing' | 'chunking' | 'indexing' | 'ready' | 'failed'
  error_message: string | null
  file_path: string
  chunk_count: number
  uploaded_by: string | null
  created_at: string
  updated_at: string
}

export interface UploadResult {
  id: string
  file_name: string
  file_type: string
  file_size: number
  status: string
}

export interface PaginationMeta {
  total: number
  page: number
  page_size: number
}
