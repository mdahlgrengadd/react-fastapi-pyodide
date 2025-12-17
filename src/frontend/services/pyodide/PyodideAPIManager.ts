import { PYODIDE_CONFIG } from "./constants";
import { PyodideInterface } from "./types";

export class PyodideAPIManager {
  constructor(private pyodide: PyodideInterface) {}

  /**
   * Set up API directory structure and load Python API files
   */
  async setupAPIDirectory(): Promise<void> {
    console.log(" Setting up API directory structure...");

    try {
      // Create API directory structure in IDBFS
      for (const path of PYODIDE_CONFIG.API_PATHS) {
        this.pyodide.FS.mkdirTree(path);
      } // Load and write Python API files from public/backend/app
      console.log("🔧 BASE_URL:", import.meta.env.BASE_URL);
      for (const fileName of PYODIDE_CONFIG.API_FILES) {
        try {
          // Use the correct base path for the new modular structure
          const basePath = import.meta.env.BASE_URL || "/";
          const apiFileUrl = `${basePath}backend${fileName}`.replace(
            /\/+/g,
            "/"
          );
          console.log(`🔗 Loading: ${apiFileUrl}`);
          const response = await fetch(apiFileUrl);
          if (response.ok) {
            const content = await response.text();
            this.pyodide.runPython(`
with open("/persist/api${fileName}", "w") as f:
    f.write(${JSON.stringify(content)})
`);
            console.log(` Loaded API file: ${fileName}`);
          } else {
            console.warn(
              ` Could not load API file: ${fileName} (${response.status})`
            );
          }
        } catch (error) {
          console.warn(` Error loading API file ${fileName}:`, error);
        }
      }

      // Add the API directory to Python path
      await this.pyodide.runPythonAsync(`
import sys
import os
api_path = "/persist/api"
if api_path not in sys.path:
    sys.path.insert(0, api_path)
    print(f" Added {api_path} to Python path")

# Also change working directory to API directory
os.chdir("/persist/api")
print(f" Changed working directory to {os.getcwd()}")
`);

      console.log(" API directory structure setup complete");
    } catch (error) {
      console.warn(" Could not setup API directory:", error);
      // Continue without API structure
    }
  }
  /**
   * Load the ASGI server for clean FastAPI execution (no monkey-patching)
   */
  async loadASGIServer(): Promise<void> {
    console.log("🚀 Loading ASGI server (clean architecture - no monkey-patching)...");
    try {
      // Import the ASGI server and FastAPI app
      await this.pyodide.runPythonAsync(`
import sys
import os

# Ensure we're in the right directory and it's in the path
if "/persist/api" not in sys.path:
    sys.path.insert(0, "/persist/api")

# Change to the API directory if we're not already there
if not os.getcwd().endswith("/persist/api"):
    os.chdir("/persist/api")

print("📱 Loading FastAPI app (unmodified)...")

# Clear cached session module to force reload with StaticPool fix
if 'app.db.session' in sys.modules:
    print("🔄 Clearing cached db.session module...")
    del sys.modules['app.db.session']
if 'app.db' in sys.modules:
    del sys.modules['app.db']

from app.app_main import app
print("✅ FastAPI app loaded successfully!")

# Initialize the database
try:
    from app.db.init_db import init_db_sync
    print("🗄️ Initializing database...")
    init_db_sync()
    print("✅ Database initialized successfully!")
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}")
    print(f"🔍 Error details: {type(e).__name__}: {str(e)}")

# Import and create ASGI server (NO monkey-patching!)
print("🔧 Creating ASGI server...")
from app.core.asgi_server import PyodideASGIServer

# Wrap the unmodified FastAPI app with ASGI server
asgi_server = PyodideASGIServer(app)
print("✅ ASGI server created - FastAPI running unmodified!")

# Helper function to get endpoints from FastAPI routes
def get_endpoints_from_app():
    """Extract endpoints directly from FastAPI app routes."""
    endpoints = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            for method in route.methods:
                if method.upper() not in ('HEAD', 'OPTIONS'):
                    # Generate operation ID
                    path_normalized = route.path.replace('/', '_').replace('{', '').replace('}', '')
                    if path_normalized.startswith('_'):
                        path_normalized = path_normalized[1:]
                    operation_id = route.name or f"{method.lower()}{path_normalized}"
                    
                    endpoints.append({
                        'operationId': operation_id,
                        'method': method.upper(),
                        'path': route.path,
                        'summary': getattr(route.endpoint, '__doc__', '') or f"{method.upper()} {route.path}",
                    })
    return endpoints

# Helper function to get OpenAPI schema from FastAPI
def get_openapi_from_app():
    """Get OpenAPI schema directly from FastAPI app."""
    return app.openapi()

print(f"📋 Registered {len(get_endpoints_from_app())} endpoints")
      `);
      console.log("✅ ASGI server initialized - using pure FastAPI!");
    } catch (error) {
      console.error("❌ Failed to load ASGI server:", error);
      throw error;
    }
  }
  /**
   * Reset the ASGI server for new code (recreate FastAPI app)
   */
  async resetASGIServer(): Promise<void> {
    console.log("🔄 Resetting ASGI server for new code...");
    // With ASGI, we just need to reload the app module
    // No global state to clear since we don't monkey-patch!
    await this.pyodide.runPythonAsync(`
import importlib
import sys

# Reload the app module to get a fresh FastAPI instance
if 'app.app_main' in sys.modules:
    importlib.reload(sys.modules['app.app_main'])
    from app.app_main import app
    
    # Recreate ASGI server with fresh app
    from app.core.asgi_server import PyodideASGIServer
    asgi_server = PyodideASGIServer(app)
    print("✅ ASGI server reset with fresh FastAPI app")
`);
  }
}
