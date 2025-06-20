import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

import { APIClientConfig, TokenResponse } from './types';

interface ExtendedAxiosRequestConfig extends AxiosRequestConfig {
  _retry?: boolean;
  _retryCount?: number;
  headers: Record<string, string>;
}

export class APIError extends Error {
  constructor(
    message: string,
    public code: "NETWORK_ERROR" | "AUTHENTICATION_ERROR" | "UNKNOWN_ERROR",
    public status?: number,
    public data?: unknown
  ) {
    super(message);
    this.name = "APIError";
  }
}

class APIClient {
  private client: AxiosInstance;
  private tokenKey: string;
  private refreshTokenKey: string;
  private retryAttempts: number;
  private retryDelay: number;
  private config: APIClientConfig;

  constructor(config: APIClientConfig) {
    this.config = config;
    this.tokenKey = config.tokenKey || "token";
    this.refreshTokenKey = config.refreshTokenKey || "refresh_token";
    this.retryAttempts = config.retryAttempts || 3;
    this.retryDelay = config.retryDelay || 1000;

    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 10000,
      headers: {
        "Content-Type": "application/json",
        ...config.headers,
      },
      // Force axios to use fetch instead of XMLHttpRequest
      adapter: 'fetch',
    });

    this.setupInterceptors(config);
  }

  // Method to update the base URL dynamically
  updateBaseURL(newBaseURL: string) {
    this.config.baseURL = newBaseURL;
    this.client.defaults.baseURL = newBaseURL;
  }

  // Method to test server connection
  async testConnection(): Promise<boolean> {
    try {
      const response = await this.client.get("/health", { timeout: 5000 });
      return response.status === 200;
    } catch {
      return false;
    }
  }
  private setupInterceptors(config: APIClientConfig) {
    // Request interceptor to add auth token
    this.client.interceptors.request.use((requestConfig) => {
      const token = localStorage.getItem(this.tokenKey);
      if (token && requestConfig.headers) {
        requestConfig.headers["Authorization"] = `Bearer ${token}`;
      }
      return requestConfig;
    });

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as ExtendedAxiosRequestConfig;

        // Handle connection errors
        if (
          !error.response &&
          (error.code === "ECONNREFUSED" || error.code === "ERR_NETWORK")
        ) {
          if (config.onConnectionError) {
            config.onConnectionError(error as Error, this.config.baseURL);
          }
          return Promise.reject(error);
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          const refreshToken = localStorage.getItem(this.refreshTokenKey);
          if (refreshToken) {
            try {
              const response = await this.refreshAccessToken(refreshToken);
              localStorage.setItem(this.tokenKey, response.access_token);
              originalRequest.headers.Authorization = `Bearer ${response.access_token}`;
              return this.client.request(originalRequest);
            } catch {
              const apiError = new APIError(
                "Authentication failed: Unable to refresh token",
                "AUTHENTICATION_ERROR",
                401
              );
              this.handleUnauthorized(config);
              return Promise.reject(apiError);
            }
          } else {
            const apiError = new APIError(
              "Authentication failed: No refresh token available",
              "AUTHENTICATION_ERROR",
              401
            );
            this.handleUnauthorized(config);
            return Promise.reject(apiError);
          }
        }

        // Retry logic for network errors
        if (
          (error.code === "NETWORK_ERROR" || error.code === "ECONNREFUSED") &&
          (originalRequest._retryCount || 0) < this.retryAttempts
        ) {
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

          await this.delay(this.retryDelay * originalRequest._retryCount);
          return this.client.request(originalRequest);
        }

        return Promise.reject(error);
      }
    );
  }

  private handleUnauthorized(config: APIClientConfig) {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshTokenKey);

    if (config.onUnauthorized) {
      config.onUnauthorized();
    } else {
      window.location.href = "/login";
    }
  }

  private async refreshAccessToken(
    refreshToken: string
  ): Promise<TokenResponse> {
    const response = await axios.post("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  async patch<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async upload<T>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<T> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await this.client.post<T>(url, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });

    return response.data;
  }
}

let apiClient: APIClient;

export const createAPIClient = (config: APIClientConfig): APIClient => {
  apiClient = new APIClient(config);
  return apiClient;
};

export const getAPIClient = (): APIClient => {
  if (!apiClient) {
    throw new Error("API client not initialized. Call createAPIClient first.");
  }
  return apiClient;
};

export const isAPIClientInitialized = (): boolean => {
  return !!apiClient;
};

export const updateAPIClientBaseURL = (newBaseURL: string): void => {
  const client = getAPIClient();
  client.updateBaseURL(newBaseURL);
};
