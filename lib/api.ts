/**
 * API client for backend communication
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface APIResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export interface AuthResponse {
  user: {
    id: string
    email: string
    username: string
    created_at: string
  }
  access_token: string
  token_type: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

// ---- Analysis types ----

export interface AnalyzeTradesResult {
  analysis_id: string
  metrics: any
  risk_results: any
  score_result: any
  ai_explanations: any
}

export interface AnalysisSummaryItem {
  id: string
  filename: string
  trade_count: number
  score?: number
  grade?: string
  created_at: string
  status: string
}

export interface AnalysisListResponse {
  analyses: AnalysisSummaryItem[]
  total: number
  skip: number
  limit: number
}

// ---- Risk types ----
export interface RiskTypes {
  [key: string]: {
    name: string
    description: string
    threshold?: string
    weight?: number
  }
}

export interface RiskSimulationPayload {
  current_score: number
  improvements: Record<string, number>
}

// ---- Reports ----
export type ReportFormat = "markdown" | "html" | "pdf"

export interface GenerateReportPayload {
  analysis_id: string
  format?: ReportFormat
  include_sections?: string[]
}

export interface ReportInfo {
  id: string
  analysis_id: string
  report_type: string
  generated_at: string
  download_url?: string
}

// ---- User Settings types ----
export interface UserSettings {
  max_position_size_pct: number
  min_win_rate: number
  max_drawdown_pct: number
  min_rr_ratio: number
  min_sl_usage_rate: number
  ai_enabled: boolean
  preferred_model: string
  openai_api_key?: string
  openai_api_key_configured?: boolean
}

export interface AlertSettings {
  enabled: boolean
  min_confidence: number
  in_app_alerts: boolean
  email_alerts: boolean
  push_notifications: boolean
  show_pattern_alerts: boolean
  show_behavioral_alerts: boolean
  show_time_based_alerts: boolean
  show_market_alerts: boolean
  real_time_alerts: boolean
  daily_summary: boolean
  weekly_report: boolean
  default_snooze_hours: number
}

export interface SnoozeAlertPayload {
  duration_hours: number
  reason?: string
}

// ---- Dashboard types ----
export interface DashboardSummary {
  total_trades: number
  win_rate: number
  total_profit: number
  risk_score: number
  grade: string
  [key: string]: any
}

export interface DashboardMetrics {
  period: string
  data: Array<{
    date: string
    [key: string]: any
  }>
}

export interface DashboardInsight {
  id: string
  type: string
  title: string
  description: string
  confidence: number
  [key: string]: any
}

class APIClient {
  private baseURL: string
  private getAuthToken: (() => string | null) | null = null
  private onUnauthorized: (() => void) | null = null

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  setAuthTokenGetter(getter: () => string | null) {
    this.getAuthToken = getter
  }

  setOnUnauthorized(callback: () => void) {
    this.onUnauthorized = callback
  }

  private getAuthHeaders(base: HeadersInit = {}): HeadersInit {
    const headers: any = { ...base }
    if (this.getAuthToken) {
      const token = this.getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }
    return headers
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`

    const headers: HeadersInit = this.getAuthHeaders({
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    })

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      const data = await response.json()

      if (!response.ok) {
        // Handle 401 Unauthorized globally
        if (response.status === 401) {
          if (this.onUnauthorized) {
            this.onUnauthorized()
          }
        }

        let errorMessage = data.detail || data.error || data.message || 'An error occurred'

        // Handle Pydantic validation errors (array of objects)
        if (typeof errorMessage !== 'string') {
          errorMessage = typeof errorMessage === 'object'
            ? JSON.stringify(errorMessage)
            : String(errorMessage)
        }

        return {
          success: false,
          error: errorMessage,
          message: errorMessage,
        }
      }

      return data
    } catch (error) {
      console.error('API request failed:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error occurred',
        message: 'Failed to connect to the server',
      }
    }
  }

  // ---- Auth endpoints ----

  async register(data: RegisterRequest): Promise<APIResponse<AuthResponse>> {
    return this.request<AuthResponse>('/api/users/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async login(data: LoginRequest): Promise<APIResponse<AuthResponse>> {
    return this.request<AuthResponse>('/api/users/login', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getProfile(): Promise<APIResponse<any>> {
    return this.request('/api/users/profile', {
      method: 'GET',
    })
  }

  // ---- Analysis endpoints ----

  /**
   * Analyze trades from CSV upload or sample data.
   * When file is provided, it uploads the CSV.
   * When useSample is true, backend uses built-in sample data.
   */
  async analyzeTrades(params: {
    file?: File
    useSample?: boolean
  }): Promise<APIResponse<AnalyzeTradesResult>> {
    const url = new URL('/api/analyze/trades', this.baseURL)
    if (params.useSample) {
      url.searchParams.set('use_sample', 'true')
    }

    const formData = new FormData()
    if (params.file) {
      formData.append('file', params.file)
    }

    try {
      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: this.getAuthHeaders(), // do NOT set Content-Type here; browser will set multipart boundary
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        const errorMessage = data.detail || data.error || data.message || 'An error occurred during analysis'
        return {
          success: false,
          error: errorMessage,
          message: errorMessage,
        }
      }

      return data
    } catch (error) {
      console.error('Analyze trades request failed:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error occurred',
        message: 'Failed to connect to the analysis service',
      }
    }
  }

  async getAnalysis(analysisId: string): Promise<APIResponse<any>> {
    return this.request<any>(`/api/analyze/${analysisId}`, {
      method: 'GET',
    })
  }

  async listAnalyses(params: { skip?: number; limit?: number } = {}): Promise<APIResponse<AnalysisListResponse>> {
    const search = new URLSearchParams()
    if (params.skip != null) search.set('skip', String(params.skip))
    if (params.limit != null) search.set('limit', String(params.limit))

    const qs = search.toString()
    const path = qs ? `/api/analyze/?${qs}` : '/api/analyze/'

    return this.request<AnalysisListResponse>(path, {
      method: 'GET',
    })
  }

  async quickAnalyze(payload: any): Promise<APIResponse<AnalyzeTradesResult>> {
    return this.request<AnalyzeTradesResult>('/api/analyze/quick', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  // ---- Risk endpoints ----
  async riskCalculate(riskDetails: Record<string, any>): Promise<APIResponse<any>> {
    return this.request<any>('/api/risk/calculate', {
      method: 'POST',
      body: JSON.stringify(riskDetails),
    })
  }

  async riskExplanations(payload: {
    metrics?: any
    risk_results?: any
    score_result?: any
    format_for_display?: boolean
  }): Promise<APIResponse<any>> {
    return this.request<any>('/api/risk/explanations', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async riskSimulate(simulation: RiskSimulationPayload): Promise<APIResponse<any>> {
    return this.request<any>('/api/risk/simulate', {
      method: 'POST',
      body: JSON.stringify(simulation),
    })
  }

  async riskTypes(): Promise<APIResponse<RiskTypes>> {
    return this.request<RiskTypes>('/api/risk/types', {
      method: 'GET',
    })
  }

  // ---- Report endpoints ----
  async generateReport(payload: GenerateReportPayload): Promise<APIResponse<any>> {
    return this.request<any>('/api/reports/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async listReports(analysisId: string): Promise<APIResponse<ReportInfo[]>> {
    return this.request<ReportInfo[]>(`/api/reports/${analysisId}`, {
      method: 'GET',
    })
  }

  async downloadReport(reportId: string, format?: string): Promise<Blob | null> {
    try {
      const url = new URL(`/api/reports/download/${reportId}`, this.baseURL)
      if (format) url.searchParams.set('format', format)

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: this.getAuthHeaders(),
      })

      if (!response.ok) {
        console.error('Failed to download report')
        return null
      }

      return await response.blob()
    } catch (error) {
      console.error('Download report error:', error)
      return null
    }
  }

  // ---- User Profile & Settings endpoints ----
  async getUserSettings(): Promise<APIResponse<UserSettings>> {
    return this.request<UserSettings>('/api/users/settings', {
      method: 'GET',
    })
  }

  async updateUserSettings(settings: Partial<UserSettings>): Promise<APIResponse<UserSettings>> {
    return this.request<UserSettings>('/api/users/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }

  // ---- Alert Settings endpoints ----
  async getAlertSettings(): Promise<APIResponse<AlertSettings>> {
    return this.request<AlertSettings>('/api/alerts/settings', {
      method: 'GET',
    })
  }

  async updateAlertSettings(settings: Partial<AlertSettings>): Promise<APIResponse<AlertSettings>> {
    return this.request<AlertSettings>('/api/alerts/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }

  async snoozeAlert(alertId: string, payload: SnoozeAlertPayload): Promise<APIResponse<any>> {
    return this.request<any>(`/api/alerts/${alertId}/snooze`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  // ---- Dashboard endpoints ----
  async getDashboardSummary(): Promise<APIResponse<DashboardSummary>> {
    return this.request<DashboardSummary>('/api/dashboard/summary', {
      method: 'GET',
    })
  }

  async getDashboardMetrics(period: string = 'month'): Promise<APIResponse<DashboardMetrics>> {
    return this.request<DashboardMetrics>(`/api/dashboard/metrics?period=${encodeURIComponent(period)}`, {
      method: 'GET',
    })
  }

  async getDashboardInsights(limit: number = 3): Promise<APIResponse<DashboardInsight[]>> {
    return this.request<DashboardInsight[]>(`/api/dashboard/insights?limit=${limit}`, {
      method: 'GET',
    })
  }

  // ---- Deriv Integration endpoints ----
  async connectDeriv(payload: {
    api_token: string
    connection_name: string
    app_id?: string
    account_id?: string
    auto_sync?: boolean
    sync_frequency?: string
    sync_days_back?: number
  }): Promise<APIResponse<any>> {
    return this.request<any>('/api/integrations/deriv/connect', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async listDerivConnections(): Promise<APIResponse<{ connections: any[]; total: number }>> {
    return this.request<{ connections: any[]; total: number }>('/api/integrations/deriv/connections', {
      method: 'GET',
    })
  }

  async syncDeriv(payload: {
    connection_id?: string
    days_back?: number
    force_full_sync?: boolean
    analyze_after_sync?: boolean
  }): Promise<APIResponse<any>> {
    return this.request<any>('/api/integrations/deriv/sync', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async disconnectDeriv(connectionId: string): Promise<APIResponse<any>> {
    return this.request<any>(`/api/integrations/deriv/connections/${connectionId}`, {
      method: 'DELETE',
    })
  }
}

export const apiClient = new APIClient(API_BASE_URL)
