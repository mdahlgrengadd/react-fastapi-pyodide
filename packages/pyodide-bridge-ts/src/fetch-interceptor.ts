/**
 * Fetch Interceptor for Pyodide Bridge
 * 
 * Automatically intercepts fetch calls to API endpoints and routes them
 * through the Pyodide bridge instead of making HTTP requests.
 */

import { Bridge } from './bridge';
import type { Endpoint, CallParams } from './types';

export interface FetchInterceptorConfig {
  /** API path prefix to intercept (e.g., '/api') */
  apiPrefix?: string;
  
  /** Base URL to intercept (e.g., 'http://localhost:8000') */
  baseUrl?: string;
  
  /** Whether to intercept relative URLs */
  interceptRelative?: boolean;
  
  /** Custom route matcher function */
  routeMatcher?: (url: string) => boolean;
  
  /** Enable debug logging */
  debug?: boolean;
}

export class FetchInterceptor {
  private bridge: Bridge;
  private config: Required<FetchInterceptorConfig>;
  private originalFetch: typeof fetch;
  private endpoints: Map<string, Endpoint> = new Map();
  private routePatterns: Map<string, { pattern: RegExp; operationId: string }> = new Map();

  constructor(bridge: Bridge, config: FetchInterceptorConfig = {}) {
    this.bridge = bridge;
    this.config = {
      apiPrefix: '/api',
      baseUrl: '',
      interceptRelative: true,
      routeMatcher: this.defaultRouteMatcher.bind(this),
      debug: false,
      ...config
    };
    
    this.originalFetch = globalThis.fetch;
    this.setupInterceptor();
  }

  private defaultRouteMatcher(url: string): boolean {
    // Intercept if URL starts with API prefix or base URL
    if (this.config.apiPrefix && url.startsWith(this.config.apiPrefix)) {
      return true;
    }
    
    if (this.config.baseUrl && url.startsWith(this.config.baseUrl)) {
      return true;
    }
    
    // Intercept relative URLs if configured
    if (this.config.interceptRelative && !url.startsWith('http')) {
      return true;
    }
    
    return false;
  }

  private setupInterceptor(): void {
    const self = this;
    
    globalThis.fetch = async function interceptedFetch(
      input: RequestInfo | URL,
      init?: RequestInit
    ): Promise<Response> {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      
      if (self.config.debug) {
        console.log('[FetchInterceptor] Checking URL:', url);
      }
      
      // Check if this URL should be intercepted
      if (self.config.routeMatcher(url)) {
        if (self.config.debug) {
          console.log('[FetchInterceptor] Intercepting:', url);
        }
        
        try {
          return await self.handleInterceptedRequest(url, init);
        } catch (error) {
          if (self.config.debug) {
            console.error('[FetchInterceptor] Bridge call failed, falling back to fetch:', error);
          }
          // Fallback to original fetch if bridge fails
          return self.originalFetch.call(globalThis, input, init);
        }
      }
      
      // Not intercepted, use original fetch with proper context
      return self.originalFetch.call(globalThis, input, init);
    };
  }

  private async handleInterceptedRequest(url: string, init?: RequestInit): Promise<Response> {
    // Parse the URL and method
    const method = init?.method?.toUpperCase() || 'GET';
    const cleanUrl = this.cleanUrl(url);
    
    // Find matching endpoint
    const match = this.findEndpointMatch(cleanUrl, method);
    
    if (!match) {
      throw new Error(`No endpoint found for ${method} ${cleanUrl}`);
    }
    
    // Extract parameters from URL and body
    const params = this.extractParameters(cleanUrl, match.endpoint, init);
    
    if (this.config.debug) {
      console.log('[FetchInterceptor] Calling bridge:', {
        operationId: match.endpoint.operationId,
        params
      });
    }
    
    // Call through bridge
    const result = await this.bridge.call(match.endpoint.operationId, params);
    
    // Convert bridge result to Response object
    return this.createResponse(result);
  }

  private cleanUrl(url: string): string {
    // Remove base URL if present
    if (this.config.baseUrl && url.startsWith(this.config.baseUrl)) {
      url = url.substring(this.config.baseUrl.length);
    }
    
    // Remove API prefix if present
    if (this.config.apiPrefix && url.startsWith(this.config.apiPrefix)) {
      url = url.substring(this.config.apiPrefix.length);
      // Ensure we have a leading slash, but handle root case
      if (!url.startsWith('/')) {
        url = '/' + url;
      }
      // If we end up with just '/', that's the root
      if (url === '/') {
        url = '/';
      }
    }
    
    // Remove query string for path matching
    const [path] = url.split('?');
    return path;
  }

  private findEndpointMatch(path: string, method: string): { endpoint: Endpoint; pathParams: Record<string, string> } | null {
    const endpoints = this.bridge.getEndpoints();
    
    if (this.config.debug) {
      console.log('[FetchInterceptor] Looking for:', method, path);
      console.log('[FetchInterceptor] Available endpoints:', endpoints.map(ep => `${ep.method} ${ep.path} (${ep.operationId})`));
      console.log('[FetchInterceptor] Cleaning endpoint paths with apiPrefix:', this.config.apiPrefix);
    }
    
    for (const endpoint of endpoints) {
      if (endpoint.method.toUpperCase() === method) {
        // Clean the endpoint path the same way we clean the request path
        const cleanEndpointPath = this.cleanUrl(endpoint.path);
        
        if (this.config.debug) {
          console.log(`[FetchInterceptor] Comparing "${path}" with "${cleanEndpointPath}" (from "${endpoint.path}")`);
        }
        
        const match = this.matchPath(path, cleanEndpointPath);
        if (match) {
          if (this.config.debug) {
            console.log(`[FetchInterceptor] ✅ Match found! Using endpoint:`, endpoint.operationId);
          }
          return { endpoint, pathParams: match };
        }
      }
    }
    
    if (this.config.debug) {
      console.log('[FetchInterceptor] ❌ No matches found');
    }
    
    return null;
  }

  private matchPath(requestPath: string, endpointPath: string): Record<string, string> | null {
    // Convert FastAPI path pattern to regex
    // e.g., "/users/{user_id}" -> "/users/([^/]+)"
    const pattern = endpointPath.replace(/\{([^}]+)\}/g, '([^/]+)');
    const regex = new RegExp(`^${pattern}$`);
    
    const match = requestPath.match(regex);
    if (!match) {
      return null;
    }
    
    // Extract parameter names and values
    const params: Record<string, string> = {};
    const paramNames = [...endpointPath.matchAll(/\{([^}]+)\}/g)].map(m => m[1]);
    
    for (let i = 0; i < paramNames.length; i++) {
      params[paramNames[i]] = match[i + 1];
    }
    
    return params;
  }

  private extractParameters(url: string, endpoint: Endpoint, init?: RequestInit): CallParams {
    const params: CallParams = {};
    
    // Extract path parameters (already handled in findEndpointMatch)
    const match = this.findEndpointMatch(this.cleanUrl(url), endpoint.method.toUpperCase());
    if (match?.pathParams) {
      Object.assign(params, match.pathParams);
    }
    
    // Extract query parameters
    const urlObj = new URL(url, 'http://localhost'); // Use dummy base for relative URLs
    const queryParams: Record<string, any> = {};
    for (const [key, value] of urlObj.searchParams.entries()) {
      queryParams[key] = value;
    }
    if (Object.keys(queryParams).length > 0) {
      params.queryParams = queryParams;
    }
    
    // Extract body for POST/PUT/PATCH requests
    if (init?.body && ['POST', 'PUT', 'PATCH'].includes(endpoint.method.toUpperCase())) {
      try {
        if (typeof init.body === 'string') {
          params.body = JSON.parse(init.body);
        } else {
          params.body = init.body;
        }
      } catch {
        params.body = init.body;
      }
    }
    
    return params;
  }

  private createResponse(data: any): Response {
    const responseBody = JSON.stringify(data);
    
    return new Response(responseBody, {
      status: 200,
      statusText: 'OK',
      headers: {
        'Content-Type': 'application/json',
        'X-Pyodide-Bridge': 'true'
      }
    });
  }

  /**
   * Restore original fetch behavior
   */
  public restore(): void {
    globalThis.fetch = this.originalFetch;
  }

  /**
   * Update endpoints cache (call when bridge loads new endpoints)
   */
  public updateEndpoints(): void {
    const endpoints = this.bridge.getEndpoints();
    this.endpoints.clear();
    this.routePatterns.clear();
    
    for (const endpoint of endpoints) {
      this.endpoints.set(endpoint.operationId, endpoint);
      
      // Pre-compile route patterns for better performance
      const pattern = endpoint.path.replace(/\{([^}]+)\}/g, '([^/]+)');
      this.routePatterns.set(endpoint.path, {
        pattern: new RegExp(`^${pattern}$`),
        operationId: endpoint.operationId
      });
    }
    
    if (this.config.debug) {
      console.log('[FetchInterceptor] Updated endpoints cache:', endpoints.length);
    }
  }
}

/**
 * React Hook for using fetch interceptor
 * Note: This should be used in a separate React-specific file
 */
export function createFetchInterceptorHook() {
  return function useFetchInterceptor(
    bridge: Bridge, 
    config?: FetchInterceptorConfig
  ): FetchInterceptor {
    // This would need proper React imports in the consuming application
    throw new Error('useFetchInterceptor hook should be implemented in your React app with proper React imports');
  };
} 