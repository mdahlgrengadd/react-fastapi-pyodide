import { RouteObject } from "react-router-dom";

export interface APIEndpoint {
  path: string;
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  operationId?: string;
  summary?: string;
  tags?: string[];
  parameters?: Array<{
    name: string;
    in: "path" | "query" | "header";
    required?: boolean;
    schema: any;
  }>;
  requestBody?: {
    content: Record<string, any>;
  };
  responses: Record<string, any>;
}

export interface RouteConfig extends Omit<RouteObject, "path"> {
  path: string;
  apiEndpoint?: APIEndpoint;
  requiresAuth?: boolean;
  roles?: string[];
  loadingComponent?: React.ComponentType;
  errorComponent?: React.ComponentType<{ error: Error }>;
}

export interface AuthConfig {
  loginPath?: string;
  tokenKey?: string;
  refreshTokenKey?: string;
  checkAuth?: () => Promise<boolean>;
  getUser?: () => Promise<any>;
  onUnauthorized?: () => void;
}

export interface FastAPIRouterProps {
  routes: RouteConfig[];
  apiBaseURL: string;
  authConfig?: AuthConfig;
  schemaURL?: string;
  enableDevTools?: boolean;
  onError?: (error: Error) => void;
  loadingComponent?: React.ComponentType;
  errorComponent?: React.ComponentType<{ error: Error }>;
}

export interface APIResponse<T = any> {
  data: T;
  status: number;
  headers: Record<string, string>;
}

export interface APIError {
  message: string;
  status?: number;
  data?: any;
}
