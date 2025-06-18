import { PYODIDE_CONFIG } from './constants';
import { PyodideAPIManager } from './PyodideAPIManager';
import { PyodideEndpointExecutor } from './PyodideEndpointExecutor';
import { PyodidePackageManager } from './PyodidePackageManager';
import { PyodidePersistence } from './PyodidePersistence';
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

    // Load the FastAPI bridge from the modular structure
    await this.apiManager.loadFastAPIBridge();

    // Set up JavaScript callback for manual persistence saves from Python
    this.pyodide.globals.set("_js_save_persistent_state", async () => {
      await this.persistence?.savePersistentState();
    });

    // Save state after installation
    await this.persistence.savePersistentState();

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

    // Reset the FastAPI app for new code
    await this.apiManager!.resetFastAPIBridge();

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
    body?: unknown
  ): Promise<unknown> {
    if (!this.isInitialized || !this.endpointExecutor) {
      throw new Error("PyodideEngine not properly initialized");
    }

    const result = await this.endpointExecutor.executeEndpoint(
      operationId,
      pathParams,
      queryParams,
      body
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

  // =============== STATUS METHODS ===============

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
