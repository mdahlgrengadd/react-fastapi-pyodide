/**
 * Pyodide Bridge TypeScript Package
 *
 * A clean TypeScript interface for integrating FastAPI with Pyodide.
 */

// Re-export types
export type {
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
  TypedCall,
  TypedStream,
  PackageStatus,
} from "./types.js";

// Re-export error classes
export { BridgeError, InitializationError, CallError } from "./types.js";

// Export Bridge class
export { Bridge } from "./bridge.js";

// Export Fetch Interceptor
export { FetchInterceptor, type FetchInterceptorConfig } from "./fetch-interceptor.js";

// Export BridgeRouter
export { BridgeRouter, type BridgeRouterConfig, type BridgeRouterProps } from "./BridgeRouter.js";

// Version info
export const version = "0.1.0";
