/**
 * TypeScript types for Pyodide Bridge
 */

// Pyodide interface types
export interface PyodideInterface {
  runPython: (code: string) => unknown;
  runPythonAsync: (code: string) => Promise<unknown>;
  globals: Map<string, unknown>;
  loadPackage: (packages: string[]) => Promise<void>;
  FS: {
    mkdirTree: (path: string) => void;
    mount: (filesystem: unknown, options: unknown, mountpoint: string) => void;
    syncfs: (populate: boolean, callback: (err?: Error) => void) => void;
    writeFile: (path: string, content: string) => void;
    filesystems: {
      IDBFS: unknown;
    };
  };
}

// Bridge configuration
export interface BridgeConfig {
  /** URL to Pyodide index (defaults to CDN) */
  pythonIndexUrl?: string;

  /** Python packages to install via micropip */
  packages?: string[];

  /** Path for persistent data (defaults to /persist) */
  persistPath?: string;

  /** Maximum chunk size for streaming (defaults to 16KB) */
  maxChunkSize?: number;

  /** Enable debug logging */
  debug?: boolean;

  /** Timeout for initialization in ms */
  initTimeout?: number;
}

// Endpoint definition
export interface Endpoint {
  operationId: string;
  path: string;
  method: string;
  summary?: string;
  tags?: string[];
  responseModel?: string;
  requestModel?: string;
}

// API call parameters
export interface CallParams {
  [key: string]: unknown;
}

// API response structure
export interface ApiResponse<T = unknown> {
  content: T;
  status_code: number;
}

// Streaming chunk structure
export interface StreamChunk<T = unknown> {
  type: "chunk" | "end" | "error";
  data: T;
  index: number;
  timestamp: string;
  warning?: string;
  error?: string;
}

// Storage information
export interface StorageInfo {
  supported: boolean;
  quota?: number;
  usage?: number;
  databases?: string[];
}

// React Router integration options
export interface RouterIntegrationOptions {
  /** API path prefix (e.g., '/api') */
  prefix?: string;

  /** Fallback route for unmatched API calls */
  fallback?: string;

  /** Custom route transformation function */
  transformRoute?: (endpoint: Endpoint) => string;
}

// Error types
export class BridgeError extends Error {
  constructor(message: string, public code?: string, public details?: unknown) {
    super(message);
    this.name = "BridgeError";
  }
}

export class InitializationError extends BridgeError {
  constructor(message: string, details?: unknown) {
    super(message, "INIT_ERROR", details);
    this.name = "InitializationError";
  }
}

export class CallError extends BridgeError {
  constructor(
    message: string,
    public operationId: string,
    public statusCode?: number,
    details?: unknown
  ) {
    super(message, "CALL_ERROR", details);
    this.name = "CallError";
  }
}

// Event types for bridge lifecycle
export interface BridgeEvents {
  initialized: () => void;
  "backend-loaded": (endpoints: Endpoint[]) => void;
  "call-start": (operationId: string, params: CallParams) => void;
  "call-end": (operationId: string, result: unknown) => void;
  "call-error": (operationId: string, error: Error) => void;
  "stream-chunk": (operationId: string, chunk: StreamChunk) => void;
  "persist-start": () => void;
  "persist-end": () => void;
  error: (error: Error) => void;
  [key: string]: (...args: unknown[]) => void;
}

// Type-safe event emitter interface
export interface EventEmitter<
  T extends Record<string, (...args: unknown[]) => void>
> {
  on<K extends keyof T>(event: K, listener: T[K]): void;
  off<K extends keyof T>(event: K, listener: T[K]): void;
  emit<K extends keyof T>(event: K, ...args: Parameters<T[K]>): void;
}

// Generic type for API calls with proper typing
export type TypedCall<
  TParams extends CallParams = CallParams,
  TResponse = unknown
> = (params: TParams) => Promise<TResponse>;

// Generic type for streaming calls
export type TypedStream<
  TParams extends CallParams = CallParams,
  TChunk = unknown
> = (params: TParams) => AsyncIterableIterator<StreamChunk<TChunk>>;

// Backend loading formats
export type BackendFormat = "eszip" | "directory" | "zip";

// Pyodide package installation status
export interface PackageStatus {
  name: string;
  installed: boolean;
  version?: string;
  error?: string;
}
