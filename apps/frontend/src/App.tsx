import './App.css';

import { Bridge } from 'pyodide-bridge-ts';
import { useEffect, useRef, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { OpenAPI } from './client';

// Auto-generated page imports
import { 
  AnalyticsPage,
  AsyncPage,
  DashboardPage,
  DashboardsPage,
  HealthPage,
  LivePage,
  PersistencePage,
  PostsPage,
  StreamPage,
  SystemPage,
  UsersPage
} from './pages';

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  const [bridge] = useState(
    () =>
      new Bridge({
        debug: true,
        packages: ["fastapi", "pydantic", "sqlalchemy", "httpx"],
      })
  );

  const [status, setStatus] = useState<string>("Initializing…");
  const [bridgeReady, setBridgeReady] = useState(false);
  const [interceptor, setInterceptor] = useState<any>(null);
  const initializationRef = useRef(false);

  // Initialize bridge and setup client
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
        const fileListResponse = await fetch("/backend/backend_filelist.json");
        if (!fileListResponse.ok) {
          throw new Error(`Failed to fetch file list: ${fileListResponse.statusText}`);
        }

        const fileList = await fileListResponse.json();
        setStatus("Loading backend files…");
        
        for (const file of fileList) {
          try {
            const response = await fetch(`/backend/${file}`);
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

        // Configure the generated client to use the bridge
        OpenAPI.BASE = ""; // Use relative URLs since we're on same origin
        
        // Set up request interceptor to route API calls through the bridge
        const { FetchInterceptor } = await import("pyodide-bridge-ts");
        const fetchInterceptor = new FetchInterceptor(bridge, {
          apiPrefix: "/api/v1",
          debug: true,
          routeMatcher: (url: string) => {
            // Route API calls and docs through the bridge
            return url.startsWith("/api/v1/") || url === "/docs" || url === "/openapi.json" || url === "/redoc";
          },
        });
        
        setInterceptor(fetchInterceptor);
        setBridgeReady(true);
        setStatus("Ready - API Client Active");
        console.log("✅ Bridge and client ready");
      } catch (e) {
        console.error("❌ Bridge initialization failed:", e);
        setStatus(`❌ ${(e as Error).message}`);
        initializationRef.current = false;
      }
    };

    if (!bridgeReady && !initializationRef.current) {
      initializeBridge();
    }

    return () => {
      if (interceptor) {
        interceptor.restore();
      }
    };
  }, [bridge]);

  if (!bridgeReady) {
    return (
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
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/async" element={<AsyncPage />} />
          <Route path="/dashboards" element={<DashboardsPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="/live" element={<LivePage />} />
          <Route path="/persistence" element={<PersistencePage />} />
          <Route path="/posts" element={<PostsPage />} />
          <Route path="/posts/:id" element={<PostsPage />} />
          <Route path="/stream" element={<StreamPage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/users/:id" element={<UsersPage />} />
        </Routes>
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;
