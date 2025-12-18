import { PYODIDE_CONFIG } from './constants';
import { PyodideAPIManager } from './PyodideAPIManager';
import { PyodideASGIBridge } from './PyodideASGIBridge';
import { PyodideEndpointExecutor } from './PyodideEndpointExecutor';
import { PyodidePackageManager } from './PyodidePackageManager';
import { PyodidePersistence } from './PyodidePersistence';
import { ReactiveTransport } from './ReactiveTransport';
import { ReactiveSyncManager } from './ReactiveSyncManager';
import { PyodideEndpoint, PyodideInterface, StorageInfo } from './types';
import { loadScript } from './utils';

export class PyodideEngine {
  private pyodide: PyodideInterface | null = null;
  private isInitialized = false;
  private initializationPromise: Promise<void> | null = null;

  // Component managers
  private persistence: PyodidePersistence | null = null;
  private packageManager: PyodidePackageManager | null = null;
  private apiManager: PyodideAPIManager | null = null;
  private endpointExecutor: PyodideEndpointExecutor | null = null;
  private asgiBridge: PyodideASGIBridge | null = null;

  // Reactive sync components
  private reactiveTransport: ReactiveTransport | null = null;
  private reactiveSyncManager: ReactiveSyncManager | null = null;

  /**
   * Initialize Pyodide and all its components
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    // If initialization is already in progress, wait for it
    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    this.initializationPromise = this._performInitialization();
    return this.initializationPromise;
  }

  private async _performInitialization(): Promise<void> {
    console.log("Initializing Pyodide (one-time setup)...");

    // Check and clear old cache first (before pyodide is loaded)
    const tempPersistence = new PyodidePersistence(null);
    await tempPersistence.checkAndClearOldCache();

    // Load Pyodide runtime
    console.log(" Loading Pyodide runtime...");
    const pyodideScriptUrl = `${PYODIDE_CONFIG.CDN_BASE_URL}/${PYODIDE_CONFIG.VERSION}/full/pyodide.js`;
    await loadScript(pyodideScriptUrl);

    // @ts-expect-error - loadPyodide is loaded from external script
    const pyodide = await loadPyodide({
      indexURL: `${PYODIDE_CONFIG.CDN_BASE_URL}/${PYODIDE_CONFIG.VERSION}/full/`,
    });
    this.pyodide = pyodide;

    // Initialize all component managers with the loaded pyodide instance
    this.persistence = new PyodidePersistence(this.pyodide);
    this.packageManager = new PyodidePackageManager(this.pyodide);
    this.apiManager = new PyodideAPIManager(this.pyodide);
    this.endpointExecutor = new PyodideEndpointExecutor(this.pyodide);

    // Set up persistent file system
    await this.persistence.setupPersistentFileSystem();

    // Load essential packages and install FastAPI
    await this.packageManager.loadEssentialPackages();
    console.log(" Installing FastAPI and dependencies...");
    await this.packageManager.installRealFastAPI();

    // Set up SQLite persistence after packages are installed
    await this.persistence.setupSQLitePersistence();

    // Set up API directory structure and load Python API files
    await this.apiManager.setupAPIDirectory();

    // Set up JavaScript callback for manual persistence saves from Python
    this.pyodide.globals.set("_js_save_persistent_state", async () => {
      await this.persistence?.savePersistentState();
    });

    // Initialize reactive sync transport BEFORE loading client_main.py
    console.log("🔄 Initializing reactive sync...");
    try {
      // Hardcode backend server URL for development
      // Backend is always on port 8000 in development
      const serverUrl = 'http://localhost:8000';
      console.log(`   Backend server URL: ${serverUrl}`);

      this.reactiveTransport = new ReactiveTransport(
        serverUrl,
        () => localStorage.getItem('access_token') || ''
      );

      // Expose transport to Python via window.REACTIVE_TRANSPORT
      // (Python's js module accesses window, not pyodide.globals)
      // Use setTimeout to defer request and avoid blocking browser
      (window as any).REACTIVE_TRANSPORT = {
        post_json_sync: (path: string, payload: string) => {
          const url = serverUrl + path;
          const data = JSON.parse(payload);
          
          console.log(`[REACTIVE_TRANSPORT] Sending POST to ${url}`, data);
          
          // Return a promise that resolves after a microtask
          // This prevents blocking the browser thread
          return new Promise((resolve, reject) => {
            // Use setTimeout(0) to defer to next event loop tick
            // This prevents blocking while still being relatively immediate
            setTimeout(() => {
              console.log(`[REACTIVE_TRANSPORT] Executing fetch to ${url}`);
              fetch(url, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                },
                body: JSON.stringify(data),
                credentials: 'include'
              })
              .then(response => {
                console.log(`[REACTIVE_TRANSPORT] Response status: ${response.status}`);
                if (!response.ok) {
                  return response.text().then(text => {
                    console.error(`[REACTIVE_TRANSPORT] Error: HTTP ${response.status}: ${text}`);
                    throw new Error(`HTTP ${response.status}: ${text}`);
                  });
                }
                return response.json();
              })
              .then(result => {
                console.log(`[REACTIVE_TRANSPORT] Success:`, result);
                
                // If this is a push response with accepted mutations, call back to Python
                if (path.includes('/push') && result.accepted && result.accepted.length > 0) {
                  try {
                    // Call Python callback to acknowledge mutations
                    const pyodide = this.pyodide;
                    if (pyodide && (window as any).__reactive_sync_ack) {
                      pyodide.runPython(`
try:
    __reactive_sync_ack(${JSON.stringify(result.accepted)})
except Exception as e:
    print(f"Error acknowledging mutations: {e}")
                      `);
                    }
                  } catch (error) {
                    console.warn(`[REACTIVE_TRANSPORT] Failed to acknowledge mutations:`, error);
                  }
                }
                
                resolve(JSON.stringify(result));
              })
              .catch(error => {
                console.error(`[REACTIVE_TRANSPORT] Fetch error:`, error);
                resolve(JSON.stringify({ accepted: [], error: error.message || String(error) }));
              });
            }, 0);
          });
        }
      };
      console.log("   Set window.REACTIVE_TRANSPORT for Python access");

      // Initialize sync manager for SSE poke subscriptions
      this.reactiveSyncManager = new ReactiveSyncManager(
        this.pyodide,
        serverUrl,
        () => localStorage.getItem('access_token') || ''
      );

      // Subscribe to default topics (can be customized later)
      // For now, we'll let the app decide which topics to subscribe to
      console.log("✅ Reactive sync transport initialized");
      console.log("   Use getReactiveSyncManager() to manage subscriptions");
    } catch (error) {
      console.warn("⚠️ Reactive sync initialization failed:", error);
      console.warn("App will work but changes won't sync in real-time");
    }

    // Load the ASGI server (clean architecture - no monkey-patching)
    // This MUST come after REACTIVE_TRANSPORT is set
    await this.apiManager.loadASGIServer();

    // Initialize ASGI bridge to connect service worker to Pyodide
    try {
      this.asgiBridge = new PyodideASGIBridge();
      await this.asgiBridge.initialize(this.pyodide);
      console.log("✅ ASGI Service Worker bridge connected");
    } catch (error) {
      console.warn("⚠️ ASGI bridge initialization failed (service worker may not be available):", error);
      // Continue without service worker - direct execution will still work
    }

    // Save state after installation
    await this.persistence.savePersistentState();

    // Expose pyodide and engine to window for console access
    (window as any).pyodide = this.pyodide;
    (window as any).pyodideEngine = this;
    console.log("💡 Available in console: pyodide, pyodideEngine");

    this.isInitialized = true;
    console.log(" Pyodide initialization complete!");
  }

  /**
   * Load and execute user Python code with FastAPI app
   */
  async loadUserCode(pythonCode: string): Promise<void> {
    if (!this.isInitialized) {
      throw new Error(
        "PyodideEngine not initialized. Call initialize() first."
      );
    }

    // SKIP RESET for client app - it breaks reactive sync runtime
    // The client app (client_main.py) is already loaded with all endpoints
    // and reactive sync configured during initialization.
    // await this.apiManager!.resetASGIServer();
    console.log("⏭️  Skipping ASGI reset to preserve reactive sync runtime");

    // Load user code through the endpoint executor
    await this.endpointExecutor!.loadUserCode(pythonCode);

    // Save the state after loading user code
    await this.persistence!.savePersistentState();
  }

  /**
   * Get OpenAPI schema from the real FastAPI app
   */
  getOpenAPISchema(): unknown {
    if (!this.isInitialized) {
      return null;
    }
    return this.endpointExecutor!.getOpenAPISchema();
  }

  /**
   * Get the list of registered endpoints
   */
  getEndpoints(): PyodideEndpoint[] {
    if (!this.endpointExecutor) return [];
    return this.endpointExecutor.getEndpoints();
  }

  /**
   * Execute a specific endpoint with given parameters
   */
  async executeEndpoint(
    operationId: string,
    pathParams?: Record<string, string>,
    queryParams?: Record<string, unknown>,
    body?: unknown,
    headers?: Record<string, string>,
    contentType?: string
  ): Promise<unknown> {
    if (!this.isInitialized || !this.endpointExecutor) {
      throw new Error("PyodideEngine not properly initialized");
    }

    const result = await this.endpointExecutor.executeEndpoint(
      operationId,
      pathParams,
      queryParams,
      body,
      headers,
      contentType
    );

    // Auto-save state after data-modifying operations
    if (this.endpointExecutor.shouldAutoSave(operationId)) {
      const endpoint = this.endpointExecutor
        .getEndpoints()
        .find((ep) => ep.operationId === operationId);
      if (endpoint) {
        console.log(
          ` Auto-saving state after ${endpoint.method} ${endpoint.path}...`
        );
        await this.persistence!.savePersistentState();
      }
    }

    return result;
  }

  // =============== PERSISTENCE METHODS ===============

  /**
   * Trigger manual save of current state
   */
  async saveState(): Promise<void> {
    if (!this.isInitialized) {
      console.warn(" Cannot save state: Pyodide not initialized");
      return;
    }
    await this.persistence!.savePersistentState();
  }

  /**
   * Clear all persistent data (useful for debugging or reset)
   */
  async clearPersistentData(): Promise<void> {
    if (this.persistence) {
      await this.persistence.clearPersistentData();
    }
  }

  /**
   * Get information about persistent storage usage
   */
  async getStorageInfo(): Promise<StorageInfo> {
    if (!this.persistence) {
      return { supported: false };
    }
    return this.persistence.getStorageInfo();
  }

  // =============== REACTIVE SYNC METHODS ===============

  /**
   * Get the reactive sync manager for managing topic subscriptions
   */
  getReactiveSyncManager(): ReactiveSyncManager | null {
    return this.reactiveSyncManager;
  }

  /**
   * Subscribe to topics for reactive sync
   */
  subscribeToTopics(topics: string[]): void {
    if (this.reactiveSyncManager) {
      this.reactiveSyncManager.subscribe(topics);
    } else {
      console.warn("⚠️ Reactive sync not initialized, cannot subscribe to topics");
    }
  }

  /**
   * Unsubscribe from topics
   */
  unsubscribeFromTopics(topics: string[]): void {
    if (this.reactiveSyncManager) {
      this.reactiveSyncManager.unsubscribe(topics);
    }
  }

  // =============== STATUS METHODS ===============

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    // Clean up reactive sync
    if (this.reactiveSyncManager) {
      this.reactiveSyncManager.disconnect();
      this.reactiveSyncManager = null;
    }
    this.reactiveTransport = null;

    // Clean up ASGI bridge
    if (this.asgiBridge) {
      await this.asgiBridge.cleanup();
      this.asgiBridge = null;
    }

    this.isInitialized = false;
    this.pyodide = null;
    this.persistence = null;
    this.packageManager = null;
    this.apiManager = null;
    this.endpointExecutor = null;
  }

  /**
   * Check if Pyodide is initialized
   */
  isEngineInitialized(): boolean {
    return this.isInitialized;
  }

  /**
   * Check if user code is loaded
   */
  isUserCodeLoaded(): boolean {
    return this.endpointExecutor?.isCodeLoaded() || false;
  }

  /**
   * Get the hash of the currently loaded code
   */
  getCurrentCodeHash(): string {
    return this.endpointExecutor?.getCurrentCodeHash() || "";
  }
}

// Singleton instance
export const pyodideEngine = new PyodideEngine();
