import './App.css';

import { Bridge, FetchInterceptor } from 'pyodide-bridge-ts';
import { useEffect, useRef, useState } from 'react';
import { FastAPIRouter } from 'react-router-fastapi';

// Import page components
import { DashboardPage, PostsPage, SystemPage, UsersPage } from './pages';

import type { RouteConfig } from "react-router-fastapi";

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
  const [interceptor, setInterceptor] = useState<InstanceType<
    typeof FetchInterceptor
  > | null>(null);
  const initializationRef = useRef(false);

  // Initialize bridge and setup interceptor
  useEffect(() => {
    const initializeBridge = async () => {
      // Prevent multiple initializations
      if (initializationRef.current) {
        console.log("🔄 Skipping duplicate initialization");
        return;
      }
      initializationRef.current = true;

      try {
        console.log("🚀 Starting bridge initialization...");
        setStatus("Loading Pyodide…");
        await bridge.initialize();

        // Mount backend Python sources into Pyodide FS
        setStatus("Fetching backend sources…");
        const fileListResponse = await fetch("/backend/backend_filelist.json");
        if (!fileListResponse.ok) {
          throw new Error(
            `Failed to fetch file list: ${fileListResponse.statusText}`
          );
        }
        const fileList: string[] = await fileListResponse.json();

        const pyodide = (bridge as any).pyodide;

        for (const relPath of fileList) {
          const fileUrl = `/backend/${relPath}`;
          const fileResponse = await fetch(fileUrl);
          if (!fileResponse.ok) {
            console.warn(
              `Failed to fetch ${fileUrl}: ${fileResponse.statusText}`
            );
            continue;
          }
          const content = await fileResponse.text();
          const dirName = `/backend/${relPath.substring(
            0,
            relPath.lastIndexOf("/")
          )}`;
          if (dirName) {
            try {
              pyodide.FS.mkdirTree(dirName);
            } catch {
              // ignore if exists
            }
          }
          pyodide.FS.writeFile(`/backend/${relPath}`, content);
        }

        setStatus("Loading backend…");
        await bridge.loadBackend("/backend/app", "directory");

        // Setup fetch interceptor - only after backend is loaded
        setStatus("Setting up API interceptor…");

        const fetchInterceptor = new FetchInterceptor(bridge, {
          apiPrefix: "/api/v1",
          baseUrl: "http://localhost:8000", // Will be intercepted
          debug: false, // Reduce logging now that it's working
          routeMatcher: (url: string) => {
            // More specific matching - only intercept actual API calls
            // Don't intercept:
            // - Static files (contain file extensions)
            // - Backend source files
            // - Non-API URLs

            // Exclude backend files
            if (url.startsWith("/backend/")) {
              return false;
            }

            // Exclude static files (contain extensions)
            if (url.match(/\.[a-zA-Z0-9]+(\?|$)/)) {
              return false;
            }

            // Handle absolute URLs - check if they match our base URL
            if (url.startsWith("http://localhost:8000/")) {
              // Extract the path from absolute URL
              const path = url.replace("http://localhost:8000", "");
              // Check if it's an API path
              const shouldIntercept =
                path.startsWith("/api/v1/") ||
                path === "/docs" ||
                path === "/openapi.json" ||
                path === "/redoc";
              return shouldIntercept;
            }

            // Handle relative URLs
            if (
              !url.startsWith("http://") &&
              !url.startsWith("https://") &&
              !url.startsWith("//")
            ) {
              // Only intercept specific API patterns
              const shouldIntercept =
                url.startsWith("/api/v1/") ||
                url === "/docs" ||
                url === "/openapi.json" ||
                url === "/redoc";
              return shouldIntercept;
            }

            // Don't intercept anything else
            return false;
          },
        });

        setInterceptor(fetchInterceptor);

        // Now create the API client AFTER the interceptor is set up
        console.log("🔧 Creating API client...");
        const { createAPIClient } = await import("react-router-fastapi");
        createAPIClient({
          baseURL: "http://localhost:8000",
          tokenKey: "access_token",
          refreshTokenKey: "refresh_token",
          retryAttempts: 3,
          retryDelay: 1000,
        });

        setBridgeReady(true);
        setStatus("Ready - FastAPI Router Active");

        console.log("✅ Bridge and interceptor ready");
      } catch (e) {
        console.error("❌ Bridge initialization failed:", e);
        setStatus(`❌ ${(e as Error).message}`);
        initializationRef.current = false; // Reset on error
      }
    };

    // Only run once
    if (!bridgeReady && !initializationRef.current) {
      initializeBridge();
    }

    // Cleanup
    return () => {
      if (interceptor) {
        interceptor.restore();
      }
    };
  }, [bridge]); // Remove interceptor from dependency array

  // Route definitions - these will be handled by FastAPIRouter
  const routes: RouteConfig[] = [
    {
      path: "/",
      element: <DashboardPage />,
      requiresAuth: false, // Set to true if you want to enable auth
    },
    {
      path: "/system",
      element: <SystemPage />,
    },
    {
      path: "/users",
      element: <UsersPage />,
    },
    {
      path: "/users/:id",
      element: <UsersPage />, // Will show user detail based on ID
    },
    {
      path: "/posts",
      element: <PostsPage />,
    },
    {
      path: "/posts/:id",
      element: <PostsPage />, // Will show post detail based on ID
    },
  ];

  // Show loading screen while bridge initializes
  if (!bridgeReady) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            Initializing FastAPI Bridge
          </h2>
          <p
            className={`text-lg ${
              status.includes("❌") ? "text-red-600" : "text-gray-600"
            }`}
          >
            {status}
            {!status.includes("Ready") && !status.includes("❌") && (
              <span className="inline-block ml-2 animate-spin">⚪</span>
            )}
          </p>
        </div>
      </div>
    );
  }

  // Render FastAPIRouter once bridge is ready
  return (
    <FastAPIRouter
      routes={routes}
      apiBaseURL="http://localhost:8000" // This will be intercepted by FetchInterceptor
      enableDevTools={true}
      onError={(error: Error) => {
        console.error("FastAPI Router Error:", error);
        setStatus(`❌ Router Error: ${error.message}`);
      }}
      loadingComponent={() => (
        <div className="flex justify-center items-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      )}
      errorComponent={({ error }: { error: Error }) => (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded m-4">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error.message}</span>
        </div>
      )}
    />
  );
}

export default App;
