import React, { useEffect, useRef, useState, ReactNode } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { Bridge } from './bridge';
import { FetchInterceptor } from './fetch-interceptor';

export interface BridgeRouterConfig {
  /** Pyodide packages to install */
  packages?: string[];
  /** Enable debug logging */
  debug?: boolean;
  /** Backend file list URL */
  backendFileListUrl?: string;
  /** Backend files base URL */
  backendFilesUrl?: string;
  /** API prefix for interceptor */
  apiPrefix?: string;
  /** Custom loading component */
  loadingComponent?: React.ComponentType<{ status: string }>;
  /** Custom error component */
  errorComponent?: React.ComponentType<{ error: string }>;
  /** React Query client options */
  queryClientOptions?: ConstructorParameters<typeof QueryClient>[0];
  /** Show React Query devtools */
  showDevtools?: boolean;
}

export interface BridgeRouterProps extends BridgeRouterConfig {
  children: ReactNode;
}

const DefaultLoadingComponent: React.FC<{ status: string }> = ({ status }) => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="text-center">
      <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">Initializing FastAPI Bridge</h2>
      <p className={`text-lg ${status.includes("❌") ? "text-red-600" : "text-gray-600"}`}>
        {status}
        {!status.includes("Ready") && !status.includes("❌") && (
          <span className="inline-block ml-2 animate-spin">⚪</span>
        )}
      </p>
    </div>
  </div>
);

const DefaultErrorComponent: React.FC<{ error: string }> = ({ error }) => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="text-center max-w-md">
      <div className="text-red-500 text-6xl mb-4">⚠️</div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">Bridge Initialization Failed</h2>
      <p className="text-red-600 text-sm bg-red-50 p-4 rounded border">
        {error}
      </p>
    </div>
  </div>
);

export const BridgeRouter: React.FC<BridgeRouterProps> = ({
  children,
  packages = ["fastapi", "pydantic", "sqlalchemy", "httpx"],
  debug = true,
  backendFileListUrl = "/backend/backend_filelist.json",
  backendFilesUrl = "/backend",
  apiPrefix = "/api/v1",
  loadingComponent: LoadingComponent = DefaultLoadingComponent,
  errorComponent: ErrorComponent = DefaultErrorComponent,
  queryClientOptions = {
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: 1,
        staleTime: 5 * 60 * 1000, // 5 minutes
      },
    },
  },
  showDevtools = false,
}) => {
  const [bridge] = useState(() => new Bridge({ debug, packages }));
  const [status, setStatus] = useState<string>("Initializing…");
  const [bridgeReady, setBridgeReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interceptor, setInterceptor] = useState<FetchInterceptor | null>(null);
  const [queryClient] = useState(() => new QueryClient(queryClientOptions));
  const initializationRef = useRef(false);

  useEffect(() => {
    const initializeBridge = async () => {
      if (initializationRef.current) {
        console.log("🔄 Skipping duplicate initialization");
        return;
      }
      initializationRef.current = true;

      try {
        console.log("🚀 Starting bridge initialization...");
        setStatus("Loading Pyodide…");
        await bridge.initialize();

        setStatus("Fetching backend sources…");
        const fileListResponse = await fetch(backendFileListUrl);
        if (!fileListResponse.ok) {
          throw new Error(`Failed to fetch file list: ${fileListResponse.statusText}`);
        }

        const fileList = await fileListResponse.json();
        setStatus("Loading backend files…");
        
        for (const file of fileList) {
          try {
            const response = await fetch(`${backendFilesUrl}/${file}`);
            if (response.ok) {
              const content = await response.text();
              await bridge.loadFile(`/${file}`, content);
            }
          } catch (e) {
            console.warn(`Failed to load file ${file}:`, e);
          }
        }

        setStatus("Starting FastAPI server…");
        await bridge.loadBackend("/backend", "directory");

        setStatus("Setting up API interceptor…");
        const fetchInterceptor = new FetchInterceptor(bridge, {
          apiPrefix,
          debug,
          routeMatcher: (url: string) => {
            return url.startsWith(apiPrefix) || url === "/docs" || url === "/openapi.json" || url === "/redoc";
          },
        });
        
        setInterceptor(fetchInterceptor);
        setBridgeReady(true);
        setStatus("Ready - API Client Active");
        console.log("✅ Bridge and client ready");
      } catch (e) {
        console.error("❌ Bridge initialization failed:", e);
        const errorMessage = (e as Error).message;
        setError(errorMessage);
        setStatus(`❌ ${errorMessage}`);
        initializationRef.current = false;
      }
    };

    if (!bridgeReady && !error && !initializationRef.current) {
      initializeBridge();
    }

    return () => {
      if (interceptor) {
        interceptor.restore();
      }
    };
  }, [bridge, backendFileListUrl, backendFilesUrl, apiPrefix, debug]);

  if (error) {
    return <ErrorComponent error={error} />;
  }

  if (!bridgeReady) {
    return <LoadingComponent status={status} />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        {children}
      </Router>
      {showDevtools && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
};

export default BridgeRouter; 