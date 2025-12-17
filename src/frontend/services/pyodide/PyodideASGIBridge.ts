/**
 * Pyodide ASGI Bridge
 *
 * Connects the Service Worker to Pyodide's ASGI server,
 * enabling clean FastAPI execution without monkey-patching.
 */

import { PyodideInterface } from "./types";

export class PyodideASGIBridge {
  private pyodide: PyodideInterface | null = null;
  private asgiServer: any = null;
  private messageChannel: MessageChannel | null = null;
  private serviceWorker: ServiceWorker | null = null;

  /**
   * Initialize the ASGI bridge
   */
  async initialize(pyodide: PyodideInterface): Promise<void> {
    this.pyodide = pyodide;

    console.log("🌉 Initializing Pyodide ASGI Bridge...");

    // Load ASGI server module
    await this.loadASGIServer();

    // Wait for Service Worker to be ready (it should be registered in main.tsx)
    await this.waitForServiceWorker();

    // Connect Service Worker to Pyodide
    await this.connectServiceWorker();

    console.log("✅ Pyodide ASGI Bridge initialized");
  }

  /**
   * Load the ASGI server Python module
   */
  private async loadASGIServer(): Promise<void> {
    console.log("📦 Loading ASGI server module...");

    // The asgi_server.py module should be in the API files
    await this.pyodide!.runPythonAsync(`
# Import the ASGI server
from app.core.asgi_server import PyodideASGIServer

# Import the FastAPI app
from app.app_main import app

# Create ASGI server instance
asgi_server = PyodideASGIServer(app)

print("✅ ASGI server initialized")
    `);

    // Get reference to the server
    this.asgiServer = this.pyodide!.globals.get("asgi_server");

    console.log("✅ ASGI server loaded");
  }

  /**
   * Wait for Service Worker to be ready
   */
  private async waitForServiceWorker(): Promise<void> {
    if (!("serviceWorker" in navigator)) {
      throw new Error("Service Workers not supported in this browser");
    }

    console.log("⏳ Waiting for Service Worker to be ready...");

    try {
      // Wait for the service worker to be ready
      const registration = await navigator.serviceWorker.ready;

      this.serviceWorker =
        registration.active || registration.installing || registration.waiting;

      if (!this.serviceWorker) {
        throw new Error("Service Worker not available");
      }

      console.log("✅ Service Worker ready");
    } catch (error) {
      console.error("❌ Service Worker not available:", error);
      throw error;
    }
  }

  /**
   * Connect Service Worker to Pyodide via MessageChannel
   */
  private async connectServiceWorker(): Promise<void> {
    if (!this.serviceWorker) {
      console.warn("⚠️ No Service Worker available");
      return;
    }

    console.log("🔗 Connecting Service Worker to Pyodide...");

    // Create a MessageChannel for bidirectional communication
    this.messageChannel = new MessageChannel();

    // Listen for requests from Service Worker
    this.messageChannel.port1.onmessage = async (event) => {
      await this.handleASGIRequest(event.data);
    };

    // Send port to Service Worker
    this.serviceWorker.postMessage(
      {
        type: "PYODIDE_READY",
      },
      [this.messageChannel.port2]
    );

    console.log("✅ Service Worker connected to Pyodide");
  }

  /**
   * Handle ASGI request from Service Worker
   */
  private async handleASGIRequest(data: any): Promise<void> {
    const { requestId, scope } = data;

    try {
      console.log(`🔄 Handling ASGI request: ${scope.method} ${scope.path}`);

      // Call Python ASGI server
      const response = await this.asgiServer.handle_request(scope);

      // Convert Python response to JavaScript
      const jsResponse = response.toJs({
        dict_converter: Object.fromEntries,
      });

      // Convert body to proper format
      let body = jsResponse.body;
      if (body && typeof body === "object" && body.constructor.name === "Uint8Array") {
        // Keep as Uint8Array
      } else if (body && typeof body === "string") {
        // Keep as string
      } else if (body) {
        // Try to decode as UTF-8
        try {
          body = new TextDecoder().decode(body);
        } catch {
          // Keep as-is
        }
      }

      // Send response back to Service Worker
      this.messageChannel!.port1.postMessage({
        requestId,
        response: {
          status: jsResponse.status,
          headers: jsResponse.headers,
          body: body,
        },
      });

      console.log(`✅ ASGI response sent: ${jsResponse.status}`);
    } catch (error) {
      console.error("❌ ASGI request failed:", error);

      // Send error response
      this.messageChannel!.port1.postMessage({
        requestId,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Check if the bridge is ready
   */
  isReady(): boolean {
    return (
      this.pyodide !== null &&
      this.asgiServer !== null &&
      this.messageChannel !== null
    );
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    // Close message channel
    if (this.messageChannel) {
      this.messageChannel.port1.close();
      this.messageChannel = null;
    }

    // Note: We don't unregister the service worker as it may be used by other parts of the app
    // The service worker will continue to cache resources and can be reused

    this.serviceWorker = null;
    this.asgiServer = null;
    this.pyodide = null;

    console.log("🧹 Pyodide ASGI Bridge cleaned up");
  }
}

/**
 * Create and initialize ASGI bridge
 */
export async function createASGIBridge(
  pyodide: PyodideInterface
): Promise<PyodideASGIBridge> {
  const bridge = new PyodideASGIBridge();
  await bridge.initialize(pyodide);
  return bridge;
}
