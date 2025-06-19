import './App.css';

import { Bridge } from 'pyodide-bridge-ts';
import { useEffect, useState } from 'react';

// Local fallback types (can be removed when library typings are resolved)
interface BridgeEndpoint {
  operationId: string;
  path: string;
  method: string;
  summary?: string;
  tags?: string[];
}

interface BridgePyodideInterface {
  runPython: (code: string) => unknown;
  runPythonAsync: (code: string) => Promise<unknown>;
  globals: Map<string, unknown>;
  loadPackage: (packages: string[]) => Promise<void>;
  FS: {
    writeFile: (path: string, data: string) => void;
    mkdirTree: (path: string) => void;
  };
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
  const [endpoints, setEndpoints] = useState<BridgeEndpoint[]>([]);
  const [result, setResult] = useState<unknown>(null);

  // One-time startup
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading Pyodide…");
        await bridge.initialize();

        // Mount backend Python sources into Pyodide FS
        setStatus("Fetching backend sources…");

        const fileList: string[] = await fetch(
          "/backend/backend_filelist.json"
        ).then((r) => r.json());

        const pyodide = (
          bridge as unknown as { pyodide: BridgePyodideInterface }
        ).pyodide;

        for (const relPath of fileList) {
          const fileUrl = `/backend/${relPath}`;
          const content = await fetch(fileUrl).then((r) => r.text());
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

        // Ensure Python can import top-level packages we placed under /backend
        await pyodide.runPythonAsync(`
import sys, importlib
p = '/backend'
if p not in sys.path:
    sys.path.insert(0, p)
try:
    import pyodide_bridge  # noqa: F401
except ModuleNotFoundError:
    pass

# Ensure set_bridge / get_bridge exist (they may be missing if the initial bridge setup fell back)
if 'set_bridge' not in globals():
    _bridge_instance = None

    def set_bridge(bridge):
        global _bridge_instance
        _bridge_instance = bridge

    def get_bridge():
        global _bridge_instance
        return _bridge_instance
`);

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
            ) as BridgeEndpoint[];
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
      setStatus(`Calling ${operationId}…`);
      const data = await bridge.call(operationId);
      setResult(data);
      setStatus("Ready");
    } catch (e) {
      console.error(e);
      setStatus(`❌ ${(e as Error).message}`);
    }
  };

  return (
    <div className="App" style={{ padding: "2rem", textAlign: "center" }}>
      <h1 className="text-2xl font-bold mb-4">React × FastAPI × Pyodide</h1>
      <p className="mb-2">Status: {status}</p>

      {endpoints.length > 0 ? (
        <ul className="space-y-2 mb-6">
          {endpoints.map((ep) => (
            <li key={ep.operationId}>
              <button
                className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded"
                onClick={() => invoke(ep.operationId)}
              >
                {ep.operationId} ({ep.method} {ep.path})
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="italic">No endpoints loaded yet.</p>
      )}

      {result !== null && (
        <pre className="text-left bg-gray-100 p-4 rounded border border-gray-200 overflow-auto">
          {typeof result === "string"
            ? result
            : JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default App;
