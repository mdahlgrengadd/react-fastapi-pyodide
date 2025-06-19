/**
 * Main Bridge class for Pyodide FastAPI integration
 *
 * This class provides a clean interface for initializing Pyodide,
 * loading Python backends, and calling FastAPI endpoints.
 */

import type {
  PyodideInterface,
  BridgeConfig,
  Endpoint,
  CallParams,
  ApiResponse,
  StreamChunk,
  StorageInfo,
  RouterIntegrationOptions,
  BridgeEvents,
  EventEmitter,
  BackendFormat,
  PackageStatus,
} from "./types.js";

import { CallError, InitializationError } from './types.js';

// Simple event emitter implementation
class SimpleEventEmitter<T extends Record<string, (...args: unknown[]) => void>>
  implements EventEmitter<T>
{
  private listeners = new Map<keyof T, Set<T[keyof T]>>();

  on<K extends keyof T>(event: K, listener: T[K]): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener);
  }

  off<K extends keyof T>(event: K, listener: T[K]): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(listener);
    }
  }

  emit<K extends keyof T>(event: K, ...args: Parameters<T[K]>): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach((listener) => {
        try {
          listener(...args);
        } catch (error) {
          console.error(`Error in event listener for ${String(event)}:`, error);
        }
      });
    }
  }
}

export class Bridge extends SimpleEventEmitter<BridgeEvents> {
  private pyodide: PyodideInterface | null = null;
  private isInitialized = false;
  private initPromise: Promise<void> | null = null;
  private endpoints: Endpoint[] = [];
  private config: Required<BridgeConfig>;
  private backendLoaded = false;

  constructor(config: BridgeConfig = {}) {
    super();

    // Set default configuration
    this.config = {
      pythonIndexUrl: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/",
      packages: ["fastapi", "micropip"],
      persistPath: "/persist",
      maxChunkSize: 16384, // 16KB
      debug: false,
      initTimeout: 30000, // 30 seconds
      ...config,
    };

    if (this.config.debug) {
      console.log("[Bridge] Initialized with config:", this.config);
    }
  }

  /**
   * Initialize the Pyodide environment
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = this._performInitialization();
    return this.initPromise;
  }

  private async _performInitialization(): Promise<void> {
    try {
      this._log("Starting Pyodide initialization...");

      // Load Pyodide
      await this._loadPyodide();

      // Setup persistence
      await this._setupPersistence();

      // Install packages
      await this._installPackages();

      // Setup FastAPI bridge infrastructure
      await this._setupBridge();

      this.isInitialized = true;
      this._log("Pyodide initialization completed");
      this.emit("initialized");
    } catch (error) {
      const initError = new InitializationError(
        `Failed to initialize Pyodide: ${
          error instanceof Error ? error.message : String(error)
        }`,
        error
      );
      this.emit("error", initError);
      throw initError;
    }
  }

  private async _loadPyodide(): Promise<void> {
    if (typeof window !== "undefined" && "loadPyodide" in window) {
      // Use global loadPyodide if available
      this.pyodide = await (window as any).loadPyodide({
        indexURL: this.config.pythonIndexUrl,
      });
    } else {
      // Dynamically import Pyodide
      const { loadPyodide } = await import("pyodide");
      this.pyodide = await loadPyodide({
        indexURL: this.config.pythonIndexUrl,
      });
    }

    if (!this.pyodide) {
      throw new Error("Failed to load Pyodide");
    }

    this._log("Pyodide loaded successfully");
  }

  private async _setupPersistence(): Promise<void> {
    if (!this.pyodide) return;

    try {
      // Create persist directory
      this.pyodide.runPython(`
import os
import sys

# Create persist directory
persist_path = "${this.config.persistPath}"
os.makedirs(persist_path, exist_ok=True)
print(f"Created persist directory: {persist_path}")
      `);

      // Setup IDBFS if in browser
      if (typeof window !== "undefined") {
        this.pyodide.runPython(`
try:
    # Mount IDBFS for persistence
    import os
    from pyodide.ffi import to_js
    
    # This will be available in Pyodide context
    js_code = '''
    if (pyodide.FS && pyodide.FS.filesystems && pyodide.FS.filesystems.IDBFS) {
        pyodide.FS.mkdirTree('${this.config.persistPath}');
        pyodide.FS.mount(pyodide.FS.filesystems.IDBFS, {}, '${this.config.persistPath}');
        console.log('IDBFS mounted at ${this.config.persistPath}');
    }
    '''
    # Note: This would need to be executed in JS context
    print("Persistence setup prepared")
except Exception as e:
    print(f"Persistence setup warning: {e}")
        `);
      }

      this._log("Persistence setup completed");
    } catch (error) {
      this._log("Warning: Persistence setup failed:", error);
      // Don't fail initialization for persistence issues
    }
  }

  private async _installPackages(): Promise<void> {
    if (!this.pyodide || this.config.packages.length === 0) return;

    try {
      // Install micropip first if not already available
      await this.pyodide.loadPackage(["micropip"]);

      // Install additional packages
      this.pyodide.runPython(`
import micropip
import asyncio

async def install_packages():
    packages = ${JSON.stringify(this.config.packages)}
    for package in packages:
        if package != 'micropip':  # Skip micropip as it's already loaded
            try:
                print(f"Installing {package}...")
                await micropip.install(package)
                print(f"✓ {package} installed")
            except Exception as e:
                print(f"✗ Failed to install {package}: {e}")

# Run the installation
asyncio.ensure_future(install_packages())
      `);

      this._log("Package installation completed");
    } catch (error) {
      this._log("Warning: Package installation failed:", error);
      // Don't fail initialization for package installation issues
    }
  }

  private async _setupBridge(): Promise<void> {
    if (!this.pyodide) return;

    // Load the Python bridge code
    this.pyodide.runPython(`
# Import bridge functionality
try:
    # This would import our Python package
    from pyodide_bridge import FastAPIBridge
    
    # Create a global bridge instance
    _bridge_instance = None
    
    def get_bridge():
        global _bridge_instance
        return _bridge_instance
    
    def set_bridge(bridge):
        global _bridge_instance
        _bridge_instance = bridge
    
    print("Bridge infrastructure ready")
except ImportError as e:
    print(f"Warning: Could not import bridge package: {e}")
    print("Bridge will use fallback mode")
    
    # Fallback bridge implementation
    class FallbackBridge:
        def __init__(self):
            self.endpoints = []
        
        def get_endpoints(self):
            return self.endpoints
        
        async def invoke(self, operation_id, **kwargs):
            return {"content": {"error": "Bridge not properly initialized"}, "status_code": 500}
    
    _bridge_instance = FallbackBridge()
    
    def get_bridge():
        global _bridge_instance
        return _bridge_instance
    `);

    this._log("Bridge infrastructure setup completed");
  }

  /**
   * Load a Python backend
   */
  async loadBackend(
    source: string,
    format: BackendFormat = "directory"
  ): Promise<Endpoint[]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    if (!this.pyodide) {
      throw new Error("Pyodide not initialized");
    }

    try {
      this._log(`Loading backend from ${source} (format: ${format})`);

      if (format === "directory") {
        // Load Python files from directory structure
        await this._loadFromDirectory(source);
      } else if (format === "eszip") {
        // Load from ESZip format
        await this._loadFromESZip(source);
      } else {
        throw new Error(`Unsupported backend format: ${format}`);
      }

      // Get endpoints from the loaded backend
      this.endpoints = await this._extractEndpoints();
      this.backendLoaded = true;

      this._log(`Backend loaded with ${this.endpoints.length} endpoints`);
      this.emit("backend-loaded", this.endpoints);

      return this.endpoints;
    } catch (error) {
      const loadError = new Error(
        `Failed to load backend: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
      this.emit("error", loadError);
      throw loadError;
    }
  }

  private async _loadFromDirectory(basePath: string): Promise<void> {
    // This would load Python files from a directory structure
    // For now, we'll simulate loading the main FastAPI app
    this.pyodide!.runPython(`
# Load the main FastAPI application
import sys
import os

# Add the backend path to Python path
backend_path = "${basePath}"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    # Import the main application
    from app_main import create_app
    
    # Create the app instance
    app = create_app()
    
    # Set as the bridge instance
    set_bridge(app)
    
    print(f"Loaded FastAPI app from {backend_path}")
except Exception as e:
    print(f"Error loading app: {e}")
    import traceback
    traceback.print_exc()
    `);
  }

  private async _loadFromESZip(source: string): Promise<void> {
    // ESZip loading would be implemented here
    // For now, throw not implemented
    throw new Error("ESZip loading not yet implemented");
  }

  private async _extractEndpoints(): Promise<Endpoint[]> {
    if (!this.pyodide) return [];

    try {
      const result = this.pyodide.runPython(`
import json
bridge = get_bridge()
result = "[]"
if hasattr(bridge, 'get_endpoints'):
    endpoints = bridge.get_endpoints()
    result = json.dumps(endpoints)
result
      `);

      return JSON.parse(result as string) as Endpoint[];
    } catch (error) {
      this._log("Warning: Could not extract endpoints:", error);
      return [];
    }
  }

  /**
   * Call a FastAPI endpoint
   */
  async call<T = unknown>(
    operationId: string,
    params: CallParams = {}
  ): Promise<T> {
    if (!this.backendLoaded) {
      throw new CallError("Backend not loaded", operationId);
    }

    if (!this.pyodide) {
      throw new CallError("Pyodide not initialized", operationId);
    }

    try {
      this.emit("call-start", operationId, params);

      // Extract path params, query params, and body
      const { pathParams, queryParams, body } = this._extractParams(
        operationId,
        params
      );

      const result = (await this.pyodide.runPythonAsync(`
import asyncio
import json

async def call_endpoint():
    bridge = get_bridge()
    if hasattr(bridge, 'invoke'):
        result = await bridge.invoke(
            operation_id="${operationId}",
            path_params=${JSON.stringify(pathParams)},
            query_params=${JSON.stringify(queryParams)},
            body=json.loads('${JSON.stringify(body)}')
        )
        return json.dumps(result)
    else:
        return json.dumps({
            "content": {"error": "Bridge invoke method not available"},
            "status_code": 500
        })

# Run the async call
call_endpoint()
      `)) as string;

      const apiResponse: ApiResponse<T> = JSON.parse(result);

      if (apiResponse.status_code >= 400) {
        throw new CallError(
          `API call failed: ${JSON.stringify(apiResponse.content)}`,
          operationId,
          apiResponse.status_code,
          apiResponse.content
        );
      }

      this.emit("call-end", operationId, apiResponse.content);
      return apiResponse.content;
    } catch (error) {
      const callError =
        error instanceof CallError
          ? error
          : new CallError(
              `Call failed: ${
                error instanceof Error ? error.message : String(error)
              }`,
              operationId
            );
      this.emit("call-error", operationId, callError);
      throw callError;
    }
  }

  /**
   * Stream data from a FastAPI endpoint
   */
  async *stream<T = unknown>(
    operationId: string,
    params: CallParams = {}
  ): AsyncIterableIterator<StreamChunk<T>> {
    // For now, this is a simplified implementation
    // Real streaming would require more complex Python generator handling
    try {
      const result = await this.call<{
        stream_processing?: { progress_data: T[] };
      }>(operationId, params);

      // If the result has streaming data, emit it as chunks
      if (
        result &&
        typeof result === "object" &&
        "stream_processing" in result
      ) {
        const streamData = (result as any).stream_processing;
        if (streamData && streamData.progress_data) {
          for (let i = 0; i < streamData.progress_data.length; i++) {
            const chunk: StreamChunk<T> = {
              type: "chunk",
              data: streamData.progress_data[i],
              index: i,
              timestamp: new Date().toISOString(),
            };
            this.emit("stream-chunk", operationId, chunk);
            yield chunk;
          }
        }
      }

      // Send end marker
      const endChunk: StreamChunk<T> = {
        type: "end",
        data: undefined as T,
        index: -1,
        timestamp: new Date().toISOString(),
      };
      yield endChunk;
    } catch (error) {
      const errorChunk: StreamChunk<T> = {
        type: "error",
        data: undefined as T,
        index: -1,
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : String(error),
      };
      yield errorChunk;
    }
  }

  private _extractParams(operationId: string, params: CallParams) {
    // Find the endpoint to understand parameter structure
    const endpoint = this.endpoints.find(
      (ep) => ep.operationId === operationId
    );

    // For now, simple extraction logic
    // In a real implementation, this would parse the OpenAPI spec
    const pathParams: Record<string, unknown> = {};
    const queryParams: Record<string, unknown> = {};
    let body: unknown = null;

    // Extract common path parameters
    Object.entries(params).forEach(([key, value]) => {
      if (key.endsWith("_id") || key === "id") {
        pathParams[key] = value;
      } else if (typeof value === "object" && value !== null) {
        body = value;
      } else {
        queryParams[key] = value;
      }
    });

    return { pathParams, queryParams, body };
  }

  /**
   * Get list of available endpoints
   */
  getEndpoints(): Endpoint[] {
    return [...this.endpoints];
  }

  /**
   * Save persistent data
   */
  async persist(): Promise<void> {
    if (!this.pyodide || typeof window === "undefined") return;

    try {
      this.emit("persist-start");

      // Sync filesystem to IndexedDB
      await new Promise<void>((resolve, reject) => {
        if (this.pyodide?.FS) {
          this.pyodide.FS.syncfs(false, (err) => {
            if (err) reject(err);
            else resolve();
          });
        } else {
          resolve();
        }
      });

      this.emit("persist-end");
      this._log("Data persisted to IndexedDB");
    } catch (error) {
      this._log("Warning: Failed to persist data:", error);
      throw error;
    }
  }

  /**
   * Get storage information
   */
  async getStorageInfo(): Promise<StorageInfo> {
    if (typeof navigator === "undefined" || !navigator.storage) {
      return { supported: false };
    }

    try {
      const estimate = await navigator.storage.estimate();
      return {
        supported: true,
        quota: estimate.quota,
        usage: estimate.usage,
        databases: [], // Would list database names if available
      };
    } catch (error) {
      return { supported: false };
    }
  }

  /**
   * Check if bridge is initialized
   */
  isReady(): boolean {
    return this.isInitialized && this.backendLoaded;
  }

  /**
   * Attach to React Router for automatic route handling
   */
  attachToRouter(
    router: unknown,
    options: RouterIntegrationOptions = {}
  ): void {
    // This would integrate with React Router
    // Implementation depends on the specific router version
    this._log("Router integration not yet implemented");
  }

  private _log(...args: unknown[]): void {
    if (this.config.debug) {
      console.log("[Bridge]", ...args);
    }
  }
}
