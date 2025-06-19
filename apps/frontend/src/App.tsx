import './App.css';

import { Bridge } from 'pyodide-bridge-ts';
import { useEffect, useState } from 'react';

interface ApiEndpoint {
  operationId: string;
  path: string;
  method: string;
  summary?: string;
  tags?: string[];
}

function App() {
  // Create one Bridge instance for the lifetime of the component
  const [bridge] = useState(
    () =>
      new Bridge({
        debug: true,
        // Install our own bridge package plus common deps
        packages: ["fastapi", "pydantic", "sqlalchemy", "httpx"],
      })
  );
  const [status, setStatus] = useState<string>("Initializing…");
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([]);
  const [result, setResult] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false); // One-time startup
  useEffect(() => {
    (async () => {
      try {
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
        const loadedEndpoints = await bridge.loadBackend(
          "/backend/app",
          "directory"
        );

        let finalEndpoints = loadedEndpoints;
        if (finalEndpoints.length === 0) {
          try {
            const endpointsStr = pyodide.runPython(
              `import json, builtins; json.dumps(get_bridge().get_endpoints())`
            );
            finalEndpoints = JSON.parse(
              endpointsStr as string
            ) as ApiEndpoint[];
          } catch (err) {
            console.warn("Could not retrieve endpoints via direct Python", err);
          }
        }

        setEndpoints(finalEndpoints);
        setStatus("Ready");
      } catch (e) {
        console.error(e);
        setStatus(`❌ ${(e as Error).message}`);
      }
    })();
    // The bridge instance never changes, so empty deps are fine
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Helper to invoke an endpoint
  const invoke = async (operationId: string) => {
    try {
      setIsLoading(true);
      setStatus(`Calling ${operationId}…`);
      const data = await bridge.call(operationId);
      setResult(data);
      setStatus("Ready");
    } catch (e) {
      console.error(e);
      setStatus(`❌ ${(e as Error).message}`);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <div className="App min-h-screen bg-gray-50" style={{ padding: "2rem" }}>
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 text-gray-800">
            React × FastAPI × Pyodide
          </h1>{" "}
          <p
            className={`text-lg ${
              status.includes("❌") ? "text-red-600" : "text-gray-600"
            }`}
          >
            Status: {status}
            {!status.includes("Ready") && !status.includes("❌") && (
              <span className="inline-block ml-2 animate-spin">⚪</span>
            )}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">
            Available Endpoints
          </h2>
          {endpoints.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {endpoints.map((ep) => (
                <button
                  key={ep.operationId}
                  className={`p-3 rounded-lg text-left transition-colors ${
                    isLoading
                      ? "bg-gray-100 cursor-not-allowed border-gray-200"
                      : "bg-blue-50 hover:bg-blue-100 border-blue-200"
                  } border`}
                  onClick={() => invoke(ep.operationId)}
                  disabled={isLoading}
                >
                  <div className="font-medium text-blue-800">
                    {isLoading ? "Loading..." : ep.operationId}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    {ep.method} {ep.path}
                  </div>
                  {ep.summary && (
                    <div className="text-xs text-gray-500 mt-1">
                      {ep.summary}
                    </div>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-gray-500">
              {status.includes("❌")
                ? "Failed to load endpoints"
                : "Loading endpoints..."}
            </p>
          )}
        </div>

        {result !== null && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-gray-800">
                API Response
              </h3>
              <button
                onClick={() => setResult(null)}
                className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors"
              >
                Clear
              </button>
            </div>
            <pre className="bg-gray-50 p-4 rounded border overflow-auto max-h-96 text-sm">
              {typeof result === "string"
                ? result
                : JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
