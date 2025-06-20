import React, { useCallback, useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { createBrowserRouter, RouteObject, RouterProvider } from 'react-router-dom';

import { createAPIClient } from '../api/client';
import { isAPIClientInitialized } from '../api/client';
import { generateRoutesFromSchema } from '../utils/schema';
import { FastAPIRouterContext } from './context';
import { DefaultError, DefaultLoading } from './DefaultComponents';
import { RouteGuard } from './RouteGuard';
import { FastAPIRouterProps, RouteConfig } from './types';

// Define global interface for connection error callback on window
interface WindowWithOnConnection {
  __onConnectionError?: (error: Error, baseURL: string) => void;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 10, // 10 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

export const FastAPIRouter: React.FC<FastAPIRouterProps> = ({
  routes,
  apiBaseURL,
  authConfig,
  schemaURL,
  enableDevTools = process.env.NODE_ENV === "development",
  onError,
  loadingComponent = DefaultLoading,
  errorComponent = DefaultError,
}) => {
  const [generatedRoutes, setGeneratedRoutes] = useState<RouteConfig[]>([]);
  const [loading, setLoading] = useState(true);


  const handleError = useCallback(
    (error: Error) => {
      console.error("FastAPI Router error:", error);
      if (onError) {
        onError(error);
      }
    },
    [onError]
  );
  const handleUnauthorized = useCallback(() => {
    if (authConfig?.onUnauthorized) {
      authConfig.onUnauthorized();
    }
  }, [authConfig]);

  const tokenKey = authConfig?.tokenKey || "access_token";

  useEffect(() => {
    const initializeRouter = async () => {
      try {
        setLoading(true); 
        
        // Only initialize API client if it hasn't been created already
        if (!isAPIClientInitialized()) {
          console.log('🔧 FastAPIRouter creating API client...');
          createAPIClient({
            baseURL: apiBaseURL,
            tokenKey,
            refreshTokenKey: "refresh_token",
            onUnauthorized: handleUnauthorized,
            onConnectionError: (error: Error, baseURL: string): void => {
              const w = window as WindowWithOnConnection;
              if (w.__onConnectionError) {
                w.__onConnectionError(error, baseURL);
              }
            },
            retryAttempts: 3,
            retryDelay: 1000,
          });
        } else {
          console.log('🔧 API client already initialized, skipping...');
        }

        // Generate routes from OpenAPI schema if provided
        if (schemaURL) {
          try {
            const autoRoutes = await generateRoutesFromSchema(schemaURL);
            setGeneratedRoutes([...routes, ...autoRoutes]);
          } catch (error) {
            // Network failure loading schema
            const w = window as WindowWithOnConnection;
            if (w.__onConnectionError) {
              w.__onConnectionError(error as Error, apiBaseURL);
            }
            setGeneratedRoutes(routes);
          }
        } else {
          setGeneratedRoutes(routes);
        }
      } catch (err) {
        const error = err as Error;
        setGeneratedRoutes(routes);
        handleError(error);
      } finally {
        setLoading(false);
      }
    };

    initializeRouter();
  }, [
    routes,
    apiBaseURL,
    schemaURL,
    handleError,
    handleUnauthorized,
    tokenKey,
  ]);
  const processRoutes = (routeConfigs: RouteConfig[]): RouteObject[] => {
    return routeConfigs.map((config) => {
      const {
        requiresAuth,
        roles,
        loadingComponent: routeLoadingComponent,
        errorComponent: routeErrorComponent,
        apiEndpoint,
        ...routeObject
      } = config;

      // Store API endpoint info for potential use in components
      if (apiEndpoint) {
        // TODO: Store endpoint metadata for component use
      }

      if (requiresAuth || roles) {
        return {
          ...routeObject,
          element: (
            <RouteGuard
              requiresAuth={requiresAuth}
              roles={roles}
              authConfig={authConfig}
              loadingComponent={routeLoadingComponent || loadingComponent}
              errorComponent={routeErrorComponent || errorComponent}
            >
              {routeObject.element}
            </RouteGuard>
          ),
        } as RouteObject;
      }

      return routeObject as RouteObject;
    });
  };
  if (loading) {
    return React.createElement(loadingComponent);
  }

  // Use BrowserRouter with 404.html fallback for clean URLs on GitHub Pages
  const router = createBrowserRouter(processRoutes(generatedRoutes), {
    basename: (import.meta as any).env?.BASE_URL || '/'
  });

  const contextValue = {
    apiBaseURL,
    authConfig,
    isDevMode: enableDevTools,
  };

  return (
    <FastAPIRouterContext.Provider value={contextValue}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        {enableDevTools && <DevTools />}
      </QueryClientProvider>
    </FastAPIRouterContext.Provider>
  );
};

// Development tools component
const DevTools: React.FC = () => {
  if (process.env.NODE_ENV !== "development") return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "20px",
        right: "20px",
        background: "#1a1a1a",
        color: "white",
        padding: "10px",
        borderRadius: "5px",
        fontSize: "12px",
        zIndex: 9999,
      }}
    >
      🚀 FastAPI Router DevTools
    </div>
  );
};
