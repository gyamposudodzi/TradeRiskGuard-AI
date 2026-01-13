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

class APIClient {
  private baseURL: string
  private getAuthToken: (() => string | null) | null = null

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  setAuthTokenGetter(getter: () => string | null) {
    this.getAuthToken = getter
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    // Add auth token if available
    if (this.getAuthToken) {
      const token = this.getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      const data = await response.json()

      if (!response.ok) {
        // Handle error responses from FastAPI (may have 'detail' field) or custom APIResponse
        const errorMessage = data.detail || data.error || data.message || 'An error occurred'
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

  // Auth endpoints
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
}

export const apiClient = new APIClient(API_BASE_URL)
