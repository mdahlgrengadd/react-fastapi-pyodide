import './App.css';

import { useEffect, useState } from 'react';

// Types for Pyodide
interface PyodideInterface {
  runPython: (code: string) => any;
  runPythonAsync: (code: string) => Promise<any>;
  loadPackage: (packages: string[]) => Promise<void>;
  FS: any;
  globals: Map<string, any>;
}

declare global {
  interface Window {
    loadPyodide: (config?: any) => Promise<PyodideInterface>;
  }
}

function App() {
  const [pyodide, setPyodide] = useState<PyodideInterface | null>(null);
  const [status, setStatus] = useState("Loading Pyodide...");
  const [apiReady, setApiReady] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const initPyodide = async () => {
      try {
        setStatus("Loading Pyodide runtime...");

        // Load Pyodide from CDN
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js";
        script.onload = async () => {
          setStatus("Initializing Pyodide...");

          const pyodideInstance = await window.loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/",
          });

          setStatus("Installing Python packages...");

          // Install required packages
          await pyodideInstance.loadPackage(["micropip"]);

          // Install packages using runPythonAsync for async operations
          await pyodideInstance.runPythonAsync(`
            import micropip
            await micropip.install(['fastapi', 'pydantic', 'sqlalchemy', 'httpx'])
          `);

          setStatus("Loading FastAPI backend...");

          setStatus("Setting up Python environment...");

          // Set up the Python environment and load the actual FastAPIBridge middleware
          await pyodideInstance.runPythonAsync(`
import sys
import os
import asyncio
import inspect
import logging
import traceback
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

# Create virtual file system structure
sys.path.insert(0, '/backend')
sys.path.insert(0, '/backend/app')

# Load the pyodide-bridge-py package first
print("📦 Loading pyodide-bridge package...")

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.routing import APIRoute
    HAS_FASTAPI = True
except ImportError:
    FastAPI = object
    HTTPException = Exception
    APIRoute = object
    HAS_FASTAPI = False

logger = logging.getLogger(__name__)

# Global registry for routes
_global_route_registry = {}

def convert_to_serializable(obj):
    """Convert objects to JSON-serializable format."""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return convert_to_serializable(obj.__dict__)
    else:
        return str(obj)

def is_pyodide_environment():
    """Check if running in Pyodide."""
    return True  # We know we're in Pyodide

class FastAPIBridge(FastAPI if HAS_FASTAPI else object):
    """FastAPI extension that provides clean Pyodide integration."""

    def __init__(self, *args, **kwargs):
        if not HAS_FASTAPI:
            raise ImportError("FastAPI is required for PyodideBridge")
        super().__init__(*args, **kwargs)
        self._initialize_bridge()

    def _initialize_bridge(self):
        """Initialize bridge-specific functionality."""
        self._patch_route_methods()
        logger.info("FastAPIBridge initialized")

    def _patch_route_methods(self):
        """Override HTTP method decorators to capture route information."""
        for method in ("get", "post", "put", "patch", "delete", "options", "head"):
            original_method = getattr(super(), method)
            setattr(self, method, self._make_route_wrapper(original_method, method.upper()))

    def _make_route_wrapper(self, original_method, http_method):
        """Create a wrapper for route methods that captures route information."""
        def wrapper(path, **kwargs):
            def decorator(func):
                # Generate operation_id
                operation_id = kwargs.get('operation_id') or http_method.lower() + "_" + path.replace('/', '_').replace('{', '').replace('}', '').strip('_')
                if not operation_id or operation_id == http_method.lower() + "_":
                    operation_id = http_method.lower() + "_" + func.__name__

                # Store route information
                _global_route_registry[operation_id] = {
                    "handler": func,
                    "path": path,
                    "method": http_method,
                    "operation_id": operation_id,
                    "summary": kwargs.get('summary', ''),
                    "tags": kwargs.get('tags', []),
                    "response_model": kwargs.get('response_model'),
                }

                print("🔗 Registered endpoint: " + operation_id + " -> " + http_method + " " + path)
                
                # Call original FastAPI method
                result = original_method(path, **kwargs)(func)
                return result
            return decorator
        return wrapper

    async def invoke(
        self,
        operation_id,
        path_params=None,
        query_params=None,
        body=None,
        **kwargs
    ):
        """Invoke a registered endpoint by operation_id."""
        path_params = path_params or {}
        query_params = query_params or {}

        # Find handler in registry
        route_info = _global_route_registry.get(operation_id)
        if not route_info:
            available_ops = list(_global_route_registry.keys())
            return {
                "content": {
                    "detail": "Operation '" + operation_id + "' not found",
                    "available_operations": available_ops
                },
                "status_code": 404
            }

        handler = route_info["handler"]
        if not callable(handler):
            return {
                "content": {"detail": "Handler for '" + operation_id + "' is not callable"},
                "status_code": 500
            }

        try:
            # Execute handler
            if inspect.iscoroutinefunction(handler):
                result = await handler()
            else:
                result = handler()

            return {
                "content": convert_to_serializable(result),
                "status_code": 200
            }

        except HTTPException as e:
            return {
                "content": {"detail": str(e.detail)},
                "status_code": e.status_code
            }
        except Exception as e:
            logger.error("Error invoking " + operation_id + ": " + str(e), exc_info=True)
            return {
                "content": {
                    "detail": "Internal server error: " + str(e),
                    "traceback": traceback.format_exc() if is_pyodide_environment() else None
                },
                "status_code": 500
            }

    def get_endpoints(self):
        """Get list of registered endpoints."""
        endpoints = []
        for operation_id, route_info in _global_route_registry.items():
            endpoints.append({
                "operationId": operation_id,
                "path": route_info["path"],
                "method": route_info["method"],
                "summary": route_info["summary"],
                "tags": route_info["tags"],
            })
        return endpoints

print("✅ FastAPIBridge class created!")

# Now create the FastAPI app using the bridge
from fastapi import FastAPI

app = FastAPIBridge(title="Pyodide Demo API with Bridge")

@app.get("/", operation_id="get_root", summary="Get welcome message")
def read_root():
    return {"message": "Hello from FastAPI Bridge running in Pyodide!", "runtime": "browser", "middleware": "FastAPIBridge"}

@app.get("/api/v1/users", operation_id="get_users", summary="Get all users")
def get_users():
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ]

@app.get("/api/v1/health", operation_id="get_health", summary="Health check")
def health_check():
    return {
        "status": "healthy", 
        "runtime": "pyodide", 
        "backend": "fastapi",
        "middleware": "FastAPIBridge",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/endpoints", operation_id="get_endpoints", summary="List all available endpoints")
def list_endpoints():
    return app.get_endpoints()

# Set the bridge instance for testing
bridge_instance = app
print("✅ FastAPIBridge app created successfully!")

# Show registered endpoints
endpoints = app.get_endpoints()
print("📋 Registered " + str(len(endpoints)) + " endpoints:")
for endpoint in endpoints:
    print("  • " + endpoint['operationId'] + ": " + endpoint['method'] + " " + endpoint['path'])
          `);

          setPyodide(pyodideInstance);
          setStatus("FastAPIBridge loaded with middleware!");
          setApiReady(true);
        };
        document.head.appendChild(script);
      } catch (error) {
        console.error("Failed to initialize Pyodide:", error);
        setStatus(
          "Error: " + (error instanceof Error ? error.message : "Unknown error")
        );
      }
    };

    initPyodide();
  }, []);

  const callApi = async (endpoint: string, method: string = "GET") => {
    if (!pyodide || !apiReady) return;

    setLoading(true);
    try {
      setStatus("Calling " + method + " " + endpoint + "...");

      // Use the FastAPIBridge invoke method to call endpoints by operation_id
      const endpointMapping = {
        "/": "get_root",
        "/api/v1/users": "get_users",
        "/api/v1/health": "get_health",
        "/api/v1/endpoints": "get_endpoints",
      };

      const operationId = (endpointMapping as any)[endpoint];
      if (!operationId) {
        throw new Error("No operation_id found for endpoint: " + endpoint);
      }

      const pythonCode = `
import json

async def call_bridge():
    try:
        print("🚀 Calling bridge endpoint: ${operationId} for path: ${endpoint}")
        
        # Use the bridge's invoke method
        result = await bridge_instance.invoke(
            operation_id="${operationId}",
            path_params={},
            query_params={},
            body=None
        )
        
        print("✅ Bridge response: " + str(result))
        return result
        
    except Exception as e:
        print("❌ Bridge call failed: " + str(e))
        return {
            "content": {"error": str(e), "traceback": str(e.__class__.__name__)},
            "status_code": 500
        }

# Call the bridge endpoint
result = await call_bridge()

# Transform to match expected format (content -> data)
{
    "status_code": result.get("status_code", 500),
    "data": result.get("content", {"error": "No content returned"}),
    "headers": {"content-type": "application/json"}
}
      `
        .replace("${operationId}", operationId)
        .replace("${endpoint}", endpoint);

      const result = await pyodide.runPythonAsync(pythonCode);

      console.log("Raw Python result:", result);

      // Convert the result properly
      let finalResult;
      if (result && typeof result === "object") {
        // Convert Pyodide proxy object to JavaScript object
        // Use dict_converter to convert Python dicts to JS objects instead of Maps
        finalResult = result.toJs
          ? result.toJs({ dict_converter: Object.fromEntries })
          : result;
      } else {
        finalResult = {
          status_code: 500,
          data: { error: "Failed to get result from Python" },
          headers: {},
        };
      }

      console.log("Final result:", finalResult);

      setResponse(finalResult);
      setStatus(
        "✅ " +
          method +
          " " +
          endpoint +
          " - Status: " +
          finalResult.status_code
      );
    } catch (error) {
      console.error("API call failed:", error);
      setStatus("❌ Error calling " + endpoint + ": " + error);
      setResponse({
        error: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const testEndpoints = [
    { name: "Root", endpoint: "/", method: "GET" },
    { name: "Users", endpoint: "/api/v1/users", method: "GET" },
    { name: "Health", endpoint: "/api/v1/health", method: "GET" },
    { name: "Endpoints", endpoint: "/api/v1/endpoints", method: "GET" },
  ];

  return (
    <div className="App">
      <header className="App-header">
        <h1>🐍 React FastAPI Pyodide</h1>
        <h2>FastAPI + SQLite running entirely in your browser!</h2>

        <div className="status">
          <p>
            <strong>Status:</strong> {status}
          </p>
        </div>

        {!apiReady ? (
          <div className="loading">
            <p>Loading FastAPI backend into Pyodide...</p>
            <p>This may take 30-60 seconds on first load.</p>
            <div className="progress">
              <div className="progress-bar"></div>
            </div>
          </div>
        ) : (
          <div className="api-ready">
            <h3>🎉 FastAPI Backend Ready!</h3>
            <p>
              Your FastAPI server is running entirely in the browser via
              Pyodide.
            </p>

            <div className="controls">
              <h4>Test API Endpoints:</h4>
              {testEndpoints.map((endpoint) => (
                <button
                  key={endpoint.endpoint}
                  onClick={() => callApi(endpoint.endpoint, endpoint.method)}
                  disabled={loading}
                  className="endpoint-btn"
                >
                  {endpoint.method} {endpoint.name}
                </button>
              ))}
            </div>

            {response && (
              <div className="response">
                <h4>API Response:</h4>
                <pre>{JSON.stringify(response, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        <div className="architecture-info">
          <h3>🏗️ Architecture</h3>
          <div className="arch-grid">
            <div className="arch-item">
              <strong>Frontend:</strong> React + Vite
            </div>
            <div className="arch-item">
              <strong>Backend:</strong> FastAPI in Pyodide
            </div>
            <div className="arch-item">
              <strong>Database:</strong> SQLite in Browser
            </div>
            <div className="arch-item">
              <strong>Runtime:</strong> WebAssembly Python
            </div>
          </div>
        </div>
      </header>
    </div>
  );
}

export default App;
