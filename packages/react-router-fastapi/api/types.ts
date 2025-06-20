export interface APIClientConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
  tokenKey?: string;
  refreshTokenKey?: string;
  onUnauthorized?: () => void;
  retryAttempts?: number;
  retryDelay?: number;
  onConnectionError?: (error: Error, baseURL: string) => void;
}

export interface APIResponse<T = unknown> {
  data: T;
  status: number;
  headers: Record<string, string>;
  timestamp?: string;
}

export interface APIError {
  message: string;
  status?: number;
  data?: unknown;
  code?: string;
  details?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface APIQueryOptions {
  page?: number;
  pageSize?: number;
  sort?: string;
  order?: "asc" | "desc";
  search?: string;
  filters?: Record<string, unknown>;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
