import type { Document, UploadResult } from '@/types/knowledge'
import type { ChatSession, ChatMessage, SSEEvent } from '@/types/chat'

const BASE_URL = '/api/v1'

class ApiClient {
  private token: string | null = null
  private _refreshing: Promise<void> | null = null

  constructor() {
    this.token = localStorage.getItem('access_token')
  }

  getToken(): string | null {
    return this.token
  }

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('access_token', token)
    } else {
      localStorage.removeItem('access_token')
    }
  }

  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token')
  }

  setRefreshToken(token: string | null) {
    if (token) {
      localStorage.setItem('refresh_token', token)
    } else {
      localStorage.removeItem('refresh_token')
    }
  }

  private async tryRefresh(): Promise<boolean> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) return false
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      const json = await res.json()
      if (json.code === 0 && json.data?.access_token) {
        this.setToken(json.data.access_token)
        this.setRefreshToken(json.data.refresh_token || refreshToken)
        return true
      }
    } catch {}
    return false
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })

    const json = await response.json()
    if (!response.ok) {
      if (response.status === 401) {
        const refreshed = this.getRefreshToken() ? await this.tryRefresh() : false
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.token}`
          const retryRes = await fetch(`${BASE_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
          const retryJson = await retryRes.json()
          if (retryRes.ok) return retryJson
        }
        this.setToken(null)
        this.setRefreshToken(null)
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      const errMsg = json.message
        || (Array.isArray(json.detail) ? json.detail.map((d: any) => d.msg || '').join('; ') : json.detail)
        || (typeof json === 'string' ? json : '请求失败')
      throw new ApiError(json.code || response.status, errMsg)
    }
    return json
  }

  // Auth
  login(username: string, password: string, captcha_token?: string, captcha_code?: string, tenant_code?: string) {
    return this.request<ApiResponse<{ access_token: string; refresh_token: string }>>(
      'POST', '/auth/login', { username, password, captcha_token, captcha_code, tenant_code }
    )
  }

  getCaptcha() {
    return this.request<ApiResponse<{ token: string; svg: string }>>('GET', '/auth/captcha')
  }


  getProfile() {
    return this.request<ApiResponse<any>>('GET', '/auth/profile')
  }

  updateProfile(data: any) {
    return this.request<ApiResponse<any>>('PUT', '/auth/profile', data)
  }

  changePassword(data: { old_password: string; new_password: string }) {
    return this.request<ApiResponse<null>>('PUT', '/auth/password', data)
  }

  // Auth - User Menus
  getUserMenus() {
    return this.request<ApiResponse<any[]>>('GET', '/auth/menus')
  }

  // Admin - Departments
  listDepartments() {
    return this.request<ApiResponse<any[]>>('GET', '/admin/departments')
  }

  getDepartment(id: string) {
    return this.request<ApiResponse<any>>('GET', `/admin/departments/${id}`)
  }

  createDepartment(data: any) {
    return this.request<ApiResponse<any>>('POST', '/admin/departments', data)
  }

  updateDepartment(id: string, data: any) {
    return this.request<ApiResponse<any>>('PUT', `/admin/departments/${id}`, data)
  }

  updateMyDepartment(data: any) {
    return this.request<ApiResponse<any>>('PUT', '/admin/departments/my', data)
  }

  deleteDepartment(id: string) {
    return this.request<ApiResponse<null>>('DELETE', `/admin/departments/${id}`)
  }

  // Admin - Roles
  listRoles() {
    return this.request<ApiResponse<any[]>>('GET', '/admin/roles')
  }

  getRole(id: string) {
    return this.request<ApiResponse<any>>('GET', `/admin/roles/${id}`)
  }

  createRole(data: any) {
    return this.request<ApiResponse<any>>('POST', '/admin/roles', data)
  }

  updateRole(id: string, data: any) {
    return this.request<ApiResponse<any>>('PUT', `/admin/roles/${id}`, data)
  }

  deleteRole(id: string) {
    return this.request<ApiResponse<null>>('DELETE', `/admin/roles/${id}`)
  }

  // Admin - Users
  listUsers(params?: { scope?: string }) {
    const qs = params?.scope ? `?scope=${params.scope}` : ''
    return this.request<ApiResponse<any[]>>('GET', `/admin/users${qs}`)
  }

  getNextEpNumber() {
    return this.request<ApiResponse<string>>('GET', '/admin/users/next-ep')
  }

  createUser(data: any) {
    return this.request<ApiResponse<any>>('POST', '/admin/users', data)
  }

  updateUser(id: string, data: any) {
    return this.request<ApiResponse<any>>('PUT', `/admin/users/${id}`, data)
  }

  deleteUser(id: string) {
    return this.request<ApiResponse<null>>('DELETE', `/admin/users/${id}`)
  }



  resetPassword(id: string, newPassword: string) {
    return this.request<ApiResponse<null>>('PUT', `/admin/users/${id}/reset-password`, { new_password: newPassword })
  }

  // Admin - Permissions
  listPermissions() {
    return this.request<ApiResponse<any[]>>('GET', '/admin/permissions')
  }

// Admin - Logs
  listOperationLogs(params: {
    page?: number; page_size?: number; user_id?: string;
    action_type?: string; resource_type?: string; result?: string;
    keyword?: string; dept_id?: string; tenant_id?: string;
    start_time?: string; end_time?: string
  }) {
    const qs = new URLSearchParams()
    if (params.page) qs.set('page', String(params.page))
    if (params.page_size) qs.set('page_size', String(params.page_size))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.action_type) qs.set('action_type', params.action_type)
    if (params.resource_type) qs.set('resource_type', params.resource_type)
    if (params.result) qs.set('result', params.result)
    if (params.keyword) qs.set('keyword', params.keyword)
    if (params.dept_id) qs.set('dept_id', params.dept_id)
    if (params.tenant_id) qs.set('tenant_id', params.tenant_id)
    if (params.start_time) qs.set('start_time', params.start_time)
    if (params.end_time) qs.set('end_time', params.end_time)
    return this.request<ApiResponse<any[]>>('GET', `/admin/operation-logs?${qs}`)
  }

  listLoginLogs(params: {
    page?: number; page_size?: number; username?: string;
    operator?: string; result?: string; tenant_id?: string;
    dept_id?: string; start_time?: string; end_time?: string
  }) {
    const qs = new URLSearchParams()
    if (params.page) qs.set('page', String(params.page))
    if (params.page_size) qs.set('page_size', String(params.page_size))
    if (params.username) qs.set('username', params.username)
    if (params.operator) qs.set('operator', params.operator)
    if (params.result) qs.set('result', params.result)
    if (params.tenant_id) qs.set('tenant_id', params.tenant_id)
    if (params.dept_id) qs.set('dept_id', params.dept_id)
    if (params.start_time) qs.set('start_time', params.start_time)
    if (params.end_time) qs.set('end_time', params.end_time)
    return this.request<ApiResponse<any[]>>('GET', `/admin/login-logs?${qs}`)
  }


  // System / Tenant Info
  getTenantInfo() {
    return this.request<ApiResponse<{name:string;logo?:string}>>('GET', '/admin/tenant')
  }

  listTenants(params?: URLSearchParams) {
    const qs = params?.toString()
    return this.request<ApiResponse<any[]>>('GET', `/admin/tenants${qs ? '?' + qs : ''}`)
  }

  updateTenantInfo(data: {name?:string;logo?:string}) {
    return this.request<ApiResponse<{name:string;logo?:string}>>('PUT', '/admin/tenant', data)
  }


  listLLMConfigs() {
    return this.request<ApiResponse<any[]>>('GET', '/admin/llm-configs')
  }

  createLLMConfig(data: any) {
    return this.request<ApiResponse<any>>('POST', '/admin/llm-configs', data)
  }

  updateLLMConfig(id: string, data: any) {
    return this.request<ApiResponse<any>>('PUT', `/admin/llm-configs/${id}`, data)
  }

  deleteLLMConfig(id: string) {
    return this.request<ApiResponse<null>>('DELETE', `/admin/llm-configs/${id}`)
  }

  setDefaultLLMConfig(id: string) {
    return this.request<ApiResponse<any>>('PUT', `/admin/llm-configs/${id}/default`)
  }

  // Announcements
  listAnnouncements(all?: boolean) {
    const qs = all ? '?all=true' : ''
    return this.request<ApiResponse<any[]>>('GET', `/admin/announcements${qs}`)
  }

  getUnreadAnnouncementCount() {
    return this.request<ApiResponse<number>>('GET', '/admin/announcements/unread-count')
  }

  markAnnouncementRead(id: string) {
    return this.request<ApiResponse<null>>('PUT', `/admin/announcements/${id}/read`)
  }

  markAllAnnouncementsRead() {
    return this.request<ApiResponse<null>>('PUT', '/admin/announcements/read-all')
  }

  createAnnouncement(data: { title: string; content: string; expires_at?: string }) {
    return this.request<ApiResponse<any>>('POST', '/admin/announcements', data)
  }

  updateAnnouncement(id: string, data: any) {
    return this.request<ApiResponse<any>>('PUT', `/admin/announcements/${id}`, data)
  }

  deleteAnnouncement(id: string) {
    return this.request<ApiResponse<null>>('DELETE', `/admin/announcements/${id}`)
  }

  // Health
  async health() {
    const response = await fetch('/health')
  }

  // Knowledge
  async listDocuments(params?: {
    page?: number
    page_size?: number
    status?: string
    file_type?: string
    keyword?: string
    project_id?: string
  }): Promise<ApiResponse<Document[]>> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    if (params?.status) searchParams.set('status', params.status)
    if (params?.file_type) searchParams.set('file_type', params.file_type)
    if (params?.keyword) searchParams.set('keyword', params.keyword)
    if (params?.project_id) searchParams.set('project_id', params.project_id)
    const qs = searchParams.toString()
    return this.request('GET', `/knowledge/documents${qs ? '?' + qs : ''}`)
  }

  async uploadFile(file: File): Promise<ApiResponse<{url:string}>> {
    const formData = new FormData()
    formData.append('file', file)
    const headers: Record<string, string> = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    const response = await fetch(`${BASE_URL}/admin/upload`, {
      method: 'POST',
      headers,
      body: formData,
    })
    const json = await response.json()
    if (!response.ok) {
      throw new ApiError(json.code || response.status, json.message || 'Upload failed')
    }
    return json
  }

  async uploadDocument(file: File): Promise<ApiResponse<UploadResult>> {
    const formData = new FormData()
    formData.append('file', file)
    const headers: Record<string, string> = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    const response = await fetch(`${BASE_URL}/knowledge/upload`, {
      method: 'POST',
      headers,
      body: formData,
    })
    const json = await response.json()
    if (!response.ok) {
      throw new ApiError(json.code || response.status, json.message || 'Upload failed')
    }
    return json
  }

  async getDocument(id: string): Promise<ApiResponse<Document>> {
    return this.request('GET', `/knowledge/documents/${id}`)
  }

  async deleteDocument(id: string): Promise<ApiResponse<null>> {
    return this.request('DELETE', `/knowledge/documents/${id}`)
  }


  async reindexDocument(id: string): Promise<ApiResponse<{ id: string; status: string }>> {
    return this.request('POST', `/knowledge/documents/${id}/reindex`)
  }

  async updateDocumentVisibility(id: string, visibility: string): Promise<ApiResponse<Document>> {
    return this.request('PUT', `/knowledge/documents/${id}/visibility`, { visibility })
  }

  // Chat
  async listSessions(): Promise<ApiResponse<ChatSession[]>> {
    return this.request('GET', '/chat/sessions')
  }

  async createSession(): Promise<ApiResponse<{ id: string; title: string }>> {
    return this.request('POST', '/chat/sessions')
  }

  async deleteSession(sessionId: string): Promise<ApiResponse<null>> {
    return this.request('DELETE', `/chat/sessions/${sessionId}`)
  }

  async batchDeleteSessions(sessionIds: string[]): Promise<ApiResponse<null>> {
    return this.request('POST', '/chat/sessions/batch-delete', { session_ids: sessionIds })
  }

  async listMessages(sessionId: string): Promise<ApiResponse<ChatMessage[]>> {
    return this.request('GET', `/chat/sessions/${sessionId}/messages`)
  }

  async sendMessageStream(
    sessionId: string,
    content: string,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal,
    deepThinking?: boolean,
  ): Promise<void> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    const body: Record<string, unknown> = { session_id: sessionId, content }
    if (deepThinking) body.deep_thinking = true
    // 从浏览器获取时区偏移
    const tzOffset = -new Date().getTimezoneOffset()
    const tzSign = tzOffset >= 0 ? '+' : '-'
    const tzHours = String(Math.floor(Math.abs(tzOffset) / 60)).padStart(2, '0')
    const tzMins = String(Math.abs(tzOffset) % 60).padStart(2, '0')
    body.timezone = `${tzSign}${tzHours}:${tzMins}`
    const response = await fetch(`${BASE_URL}/chat/message`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    })
    if (!response.ok) {
      throw new ApiError(response.status, 'Chat request failed')
    }
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    const { createParser } = await import('eventsource-parser')
    const parser = createParser({
      onEvent: event => {
        try {
          const data = JSON.parse(event.data)
          onEvent({ event: event.event as SSEEvent['event'], data } as SSEEvent)
        } catch { /* skip malformed events */ }
      },
    })
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      parser.feed(decoder.decode(value))
    }
  }
}

interface ApiResponse<T> {
  code: number
  message: string
  data: T
  meta?: Record<string, unknown>
}

class ApiError extends Error {
  code: number
  constructor(code: number, message: string) {
    super(message)
    this.code = code
    this.name = 'ApiError'
  }
}

export const api = new ApiClient()
export { ApiError }
export type { ApiResponse }
