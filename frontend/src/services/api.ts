/**
 * API Service Layer — Frontend-Backend Connectivity
 * Handles all HTTP communication with the FastAPI backend
 */

import { API_BASE_URL } from './config';
import {
  AuthToken,
  UserProfile,
  LoginCredentials,
  ExtractedField,
  ExtractionResponse,
  MappingSuggestion,
  MappingConfirmRequest,
  AnalyticalReport,
  HistoricalTrendData,
  EfficiencyResponse
} from './types';

// ─── Token Management ───
class TokenManager {
  private static readonly ACCESS_TOKEN_KEY = 'dss_access_token';
  private static readonly REFRESH_TOKEN_KEY = 'dss_refresh_token';

  static getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  static getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  static setTokens(access: string, refresh: string): void {
    localStorage.setItem(this.ACCESS_TOKEN_KEY, access);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refresh);
  }

  static clearTokens(): void {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
  }

  static isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}

// ─── HTTP Client ───
class HttpClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    _isRetry: boolean = false,  // F-08: prevent infinite 401 loop
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    // Default headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    // Add auth token if available
    const token = TokenManager.getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        throw new ApiError(
          'Rate limit exceeded. Please try again later.',
          429,
          { retryAfter }
        );
      }

      // Handle unauthorized — retry ONCE with refreshed token (F-08)
      if (response.status === 401 && !_isRetry) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          return this.request<T>(endpoint, options, true);  // single retry
        } else {
          TokenManager.clearTokens();
          window.location.href = '/login';
          throw new ApiError('Session expired. Please log in again.', 401);
        }
      }

      // Handle other errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

      // Parse JSON response
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error instanceof Error ? error.message : 'Network error',
        0
      );
    }
  }

  private async refreshAccessToken(): Promise<boolean> {
    const refreshToken = TokenManager.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      TokenManager.setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  // HTTP methods
  get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  post<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  put<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // File upload with FormData
  upload<T>(endpoint: string, formData: FormData): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type with boundary
    });
  }
}

// ─── API Error Class ───
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public data?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }

  isRateLimit(): boolean {
    return this.statusCode === 429;
  }

  isAuthError(): boolean {
    return this.statusCode === 401 || this.statusCode === 403;
  }
}

// ─── Initialize HTTP Client ───
const httpClient = new HttpClient(API_BASE_URL);

// ─── API Services ───

/**
 * Authentication Service
 */
export const AuthService = {
  async login(credentials: LoginCredentials): Promise<AuthToken> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(error.detail || 'Login failed', response.status);
    }

    const data = await response.json();
    if (!data.success || !data.token) {
      throw new ApiError(data.message || 'Login failed', 401);
    }

    TokenManager.setTokens(data.token.access_token, data.token.refresh_token);
    return data.token;
  },

  async logout(): Promise<void> {
    try {
      await httpClient.post('/auth/logout', {});
    } finally {
      TokenManager.clearTokens();
    }
  },

  async getProfile(): Promise<UserProfile> {
    return httpClient.get<UserProfile>('/auth/me');
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return httpClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  isAuthenticated(): boolean {
    return TokenManager.isAuthenticated();
  },

  getToken(): string | null {
    return TokenManager.getAccessToken();
  },
};

/**
 * Extraction Service — PDF document processing
 */
export const ExtractionService = {
  async uploadPDF(file: File): Promise<ExtractionResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return httpClient.upload<ExtractionResponse>('/extract/upload', formData);
  },

  async getExtractions(): Promise<ExtractedField[]> {
    return httpClient.get<ExtractedField[]>('/extract/fields');
  },
};

/**
 * Mapping Service — Human-in-the-loop verification
 */
export const MappingService = {
  async getPendingMappings(): Promise<MappingSuggestion[]> {
    return httpClient.get<MappingSuggestion[]>('/mapping/pending');
  },

  async confirmMapping(request: MappingConfirmRequest): Promise<MappingSuggestion> {
    return httpClient.post<MappingSuggestion>('/mapping/confirm', request);
  },

  async overrideMapping(
    mappingId: number,
    newHead: string,
    newCategory: string,
    comment: string
  ): Promise<MappingSuggestion> {
    return httpClient.post<MappingSuggestion>('/mapping/confirm', {
      mapping_id: mappingId,
      decision: 'Overridden',
      override_head: newHead,
      override_category: newCategory,
      comment,
      officer_name: 'Current User', // TODO(F-07): Replace with user.full_name from AuthContext
    });
  },

  async rejectMapping(mappingId: number, comment: string): Promise<MappingSuggestion> {
    return httpClient.post<MappingSuggestion>('/mapping/confirm', {
      mapping_id: mappingId,
      decision: 'Rejected',
      comment,
      officer_name: 'Current User',
    });
  },
};

/**
 * Reports Service — Analytical reports and audit trails
 */
export const ReportsService = {
  async generateAnalyticalReport(
    financialYear: string,
    sbuCode?: string
  ): Promise<AnalyticalReport> {
    const params = new URLSearchParams();
    params.append('financial_year', financialYear);
    if (sbuCode) params.append('sbu_code', sbuCode);

    return httpClient.get<AnalyticalReport>(`/reports/analytical?${params}`);
  },

  async getSBUSummary(financialYear: string): Promise<Array<{
    sbu_code: string;
    total_approved: number;
    total_actual: number;
    net_variance: number;
    compliance_status: string;
  }>> {
    return httpClient.get(`/reports/sbu-summary?financial_year=${financialYear}`);
  },

  async downloadAnnexure(financialYear: string): Promise<Blob> {
    const response = await fetch(
      `${API_BASE_URL}/reports/annexure?financial_year=${financialYear}`,
      {
        headers: {
          Authorization: `Bearer ${TokenManager.getAccessToken() || ''}`,
        },
      }
    );
    return response.blob();
  },
};

/**
 * Health Check Service
 */
export const HealthService = {
  async checkHealth(): Promise<{ status: string; engine: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  },

  async checkSecurityStatus(): Promise<{
    security_features: Record<string, string>;
    environment: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/security/status`);
    return response.json();
  },
};

/**
 * Tariff Generation Service
 */
export const TariffService = {
  async generateDraft(data: {
    financial_year: string;
    net_revenue_gap: number;
    total_approved_arr: number;
    total_actual_arr: number;
    controllable_gap: number;
    uncontrollable_gap: number;
    anomaly_flags_count: number;
  }): Promise<{
    draft_id: string;
    financial_year: string;
    generated_at: string;
    llm_model: string;
    draft_narrative: string;
    human_review_required: boolean;
  }> {
    return httpClient.post('/tariff/generate-draft', data);
  },
};

/**
 * Historical Data Service
 */
export const HistoryService = {
  async getTrends(): Promise<HistoricalTrendData[]> {
    return httpClient.get<HistoricalTrendData[]>('/history/trends');
  },
};

/**
 * Efficiency Analysis Service
 */
export const EfficiencyService = {
  async evaluateLineLoss(financialYear: string, actualLineLossPercent: number): Promise<EfficiencyResponse> {
    return httpClient.post<EfficiencyResponse>('/efficiency/line-loss', {
      financial_year: financialYear,
      actual_line_loss_percent: actualLineLossPercent
    });
  },
};

// ─── Export TokenManager for direct access ───
export { TokenManager };
export { httpClient };
