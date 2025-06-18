import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { createBrowserRouter, RouteObject } from 'react-router-dom';

import { EndpointList, PyodideEndpoint, pyodideEngine, SmartEndpoint } from './index';
import { PyodideSwaggerUI } from './PyodideSwaggerUI';

interface PyodideContextType {
  isInitialized: boolean;
  isLoading: boolean;
  error: Error | null;
  endpoints: PyodideEndpoint[];
  router: ReturnType<typeof createBrowserRouter> | null;
  reinitialize: (pythonCode: string) => Promise<void>;
}

const PyodideContext = createContext<PyodideContextType | null>(null);

export const usePyodide = () => {
  const context = useContext(PyodideContext);
  if (!context) {
    throw new Error("usePyodide must be used within a PyodideProvider");
  }
  return context;
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      cacheTime: 1000 * 60 * 10,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Global flag to prevent double initialization in React Strict Mode (development)
let globalInitializationGuard = false;

interface PyodideProviderProps {
  children: React.ReactNode;
  pythonCode: string;
  enableDevTools?: boolean;
  onError?: (error: Error) => void;
}

export const PyodideProvider: React.FC<PyodideProviderProps> = ({
  children,
  pythonCode,
  enableDevTools = process.env.NODE_ENV === "development",
  onError,
}) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [endpoints, setEndpoints] = useState<PyodideEndpoint[]>([]);
  const [router, setRouter] = useState<ReturnType<
    typeof createBrowserRouter
  > | null>(null);

  // Use refs to track initialization state and prevent re-runs
  const initializationPromiseRef = useRef<Promise<void> | null>(null);
  const isInitializingRef = useRef(false);
  const lastPythonCodeRef = useRef<string>("");

  const handleError = useCallback(
    (err: Error) => {
      console.error(" Pyodide Context Error:", err);
      setError(err);
      if (onError) {
        onError(err);
      }
    },
    [onError]
  );

  const createRoutes = useCallback(
    (endpoints: PyodideEndpoint[]) => {
      // Components are imported at the top of the file

      const convertOpenAPIPathToReactRouter = (openAPIPath: string): string => {
        return openAPIPath.replace(/{([^}]+)}/g, ":$1");
      };

      // Create individual routes for each endpoint using query parameters
      const generatedRoutes: RouteObject[] = endpoints.map((endpoint) => ({
        path: convertOpenAPIPathToReactRouter(endpoint.path),
        element: (
          <React.Suspense fallback={<div>Loading endpoint...</div>}>
            <SmartEndpoint
              endpoints={endpoints.filter(
                (ep) =>
                  convertOpenAPIPathToReactRouter(ep.path) ===
                  convertOpenAPIPathToReactRouter(endpoint.path)
              )}
              onError={handleError}
            />
          </React.Suspense>
        ),
      }));

      // Remove duplicates by path
      const uniqueRoutes = generatedRoutes.filter(
        (route, index, self) =>
          index === self.findIndex((r) => r.path === route.path)
      );

      const homeRoute: RouteObject = {
        path: "/",
        element: (
          <React.Suspense fallback={<div>Loading...</div>}>
            <EndpointList endpoints={endpoints} />
          </React.Suspense>
        ),
      };

      // Add Swagger UI docs route
      const docsRoute: RouteObject = {
        path: "/docs",
        element: (
          <React.Suspense fallback={<div>Loading API documentation...</div>}>
            <PyodideSwaggerUI onError={handleError} />
          </React.Suspense>
        ),
      };

      return [homeRoute, docsRoute, ...uniqueRoutes];
    },
    [handleError]
  );

  const initializePyodide = useCallback(
    async (code: string, force = false) => {
      // Global guard for React Strict Mode (development)
      if (globalInitializationGuard && !force) {
        console.log(
          " Global initialization guard active - preventing duplicate init"
        );
        return;
      }

      // Prevent multiple simultaneous initializations
      if (isInitializingRef.current && !force) {
        console.log(" Pyodide initialization already in progress, waiting...");
        if (initializationPromiseRef.current) {
          return initializationPromiseRef.current;
        }
        return;
      }

      // Check if we've already initialized with the same code
      if (isInitialized && lastPythonCodeRef.current === code && !force) {
        console.log(" Pyodide already initialized with this code, skipping...");
        return;
      }

      // Set global guard
      globalInitializationGuard = true;
      isInitializingRef.current = true;

      const initPromise = (async () => {
        try {
          setIsLoading(true);
          setError(null);

          console.log(" Initializing Pyodide Context (app-level)...");

          // Initialize Pyodide (cached after first call)
          await pyodideEngine.initialize();

          // Load Python code (cached if same)
          await pyodideEngine.loadUserCode(code);

          // Get endpoints
          const loadedEndpoints = pyodideEngine.getEndpoints();
          console.log(
            ` Pyodide Context: Loaded ${loadedEndpoints.length} endpoints`
          );

          // Create routes
          const routes = createRoutes(loadedEndpoints);
          const newRouter = createBrowserRouter(routes, {
            basename: import.meta.env.BASE_URL,
          });

          // Update state
          setEndpoints(loadedEndpoints);
          setRouter(newRouter);
          setIsInitialized(true);
          lastPythonCodeRef.current = code;

          console.log(" Pyodide Context: Initialization complete!");
        } catch (err) {
          globalInitializationGuard = false; // Reset on error
          handleError(err as Error);
        } finally {
          setIsLoading(false);
          isInitializingRef.current = false;
          initializationPromiseRef.current = null;
        }
      })();

      initializationPromiseRef.current = initPromise;
      return initPromise;
    },
    [createRoutes, handleError, isInitialized]
  );

  const reinitialize = useCallback(
    async (code: string) => {
      console.log(" Reinitializing Pyodide with new code...");
      await initializePyodide(code, true);
    },
    [initializePyodide]
  );

  // Initialize only once on mount or when Python code actually changes
  useEffect(() => {
    const shouldInitialize =
      !isInitialized || lastPythonCodeRef.current !== pythonCode;

    if (shouldInitialize && !isInitializingRef.current) {
      console.log(" PyodideProvider useEffect triggered - initializing...");
      // Add a small delay to ensure DOM is ready and avoid preload conflicts
      const timeoutId = setTimeout(() => {
        initializePyodide(pythonCode);
      }, 100);

      return () => clearTimeout(timeoutId);
    } else {
      console.log(
        " PyodideProvider useEffect - skipping (already initialized or in progress)"
      );
    }
  }, [pythonCode]); // Only depend on pythonCode, not the function

  const contextValue: PyodideContextType = {
    isInitialized,
    isLoading,
    error,
    endpoints,
    router,
    reinitialize,
  };

  return (
    <PyodideContext.Provider value={contextValue}>
      <QueryClientProvider client={queryClient}>
        {children}
        {enableDevTools && isInitialized && (
          <PyodideDevTools
            isInitialized={isInitialized}
            endpointCount={endpoints.length}
          />
        )}
      </QueryClientProvider>
    </PyodideContext.Provider>
  );
};

// Dev tools component
const PyodideDevTools: React.FC<{
  isInitialized: boolean;
  endpointCount: number;
}> = ({ isInitialized, endpointCount }) => {
  if (process.env.NODE_ENV !== "development") return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "20px",
        right: "20px",
        background: "#1a1a1a",
        color: "white",
        padding: "12px",
        borderRadius: "8px",
        fontSize: "11px",
        zIndex: 9999,
        border: `2px solid ${isInitialized ? "#4CAF50" : "#FFC107"}`,
        minWidth: "200px",
      }}
    >
      <div style={{ fontWeight: "bold", marginBottom: "6px" }}>
        Pyodide Context (Persistent)
      </div>

      <div style={{ fontSize: "10px", opacity: 0.9, marginBottom: "4px" }}>
        Status: {isInitialized ? " Ready" : " Loading..."}
      </div>

      {isInitialized && (
        <>
          <div style={{ fontSize: "10px", opacity: 0.7, marginBottom: "2px" }}>
            {endpointCount} endpoints loaded
          </div>
          <div style={{ fontSize: "10px", opacity: 0.7, marginBottom: "2px" }}>
            Global guard: {globalInitializationGuard ? "Active" : "Inactive"}
          </div>
          <div style={{ fontSize: "10px", opacity: 0.7 }}>
            Navigation: Instant (no reinit)
          </div>
        </>
      )}

      {!isInitialized && (
        <div style={{ fontSize: "10px", opacity: 0.7 }}>
          First-time setup in progress...
        </div>
      )}
    </div>
  );
};
