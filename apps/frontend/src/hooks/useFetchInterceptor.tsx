import { useEffect, useRef, useState } from 'react';

export interface UseFetchInterceptorOptions {
  /** API path prefix to intercept (e.g., '/api') */
  apiPrefix?: string;
  
  /** Base URL to intercept (e.g., 'http://localhost:8000') */
  baseUrl?: string;
  
  /** Whether to intercept relative URLs */
  interceptRelative?: boolean;
  
  /** Enable debug logging */
  debug?: boolean;
}

/**
 * React hook that sets up fetch interception
 */
export function useFetchInterceptor(
  bridge: any | null,
  options: UseFetchInterceptorOptions = {}
) {
  const interceptorRef = useRef<any>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  
  const {
    apiPrefix = '/api',
    debug = true,
    ...restOptions
  } = options;

  useEffect(() => {
    if (!bridge) return;

    // Dynamically import and create the interceptor
    const setupInterceptor = async () => {
      try {
        const { FetchInterceptor } = await import('pyodide-bridge-ts');
        
        if (!interceptorRef.current) {
          const config = {
            apiPrefix,
            debug,
            ...restOptions,
            
            // Custom route matcher
            routeMatcher: (url: string) => {
              // Default API interception
              if (apiPrefix && url.startsWith(apiPrefix)) {
                return true;
              }
              
              // Default behavior for relative URLs
              return !url.startsWith('http') && !url.startsWith('//');
            }
          };
          
          interceptorRef.current = new FetchInterceptor(bridge, config);
          setIsLoaded(true);
          console.log('[useFetchInterceptor] Interceptor created');
        }
      } catch (error) {
        console.error('[useFetchInterceptor] Failed to load FetchInterceptor:', error);
      }
    };

    setupInterceptor();

    // Update endpoints when bridge loads
    const handleBackendLoaded = () => {
      console.log('[useFetchInterceptor] Backend loaded, updating endpoints');
      interceptorRef.current?.updateEndpoints();
    };

    bridge.on('backend-loaded', handleBackendLoaded);

    return () => {
      bridge.off('backend-loaded', handleBackendLoaded);
    };
  }, [bridge, apiPrefix, debug]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (interceptorRef.current) {
        console.log('[useFetchInterceptor] Restoring original fetch');
        interceptorRef.current.restore();
      }
    };
  }, []);

  return {
    interceptor: interceptorRef.current,
    isActive: !!interceptorRef.current,
    isLoaded
  };
} 