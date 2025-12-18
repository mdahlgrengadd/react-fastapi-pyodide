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

print("📱 Loading FastAPI client app (with reactive sync)...")

# Clear cached session module to force reload with StaticPool fix
if 'app.db.session' in sys.modules:
    print("🔄 Clearing cached db.session module...")
    del sys.modules['app.db.session']
if 'app.db' in sys.modules:
    del sys.modules['app.db']

# Load CLIENT app with reactive sync support
from app.client_main import app
print("✅ FastAPI client app loaded successfully!")

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
from app.core.asgi_server import create_asgi_server

# Wrap the unmodified FastAPI app with ASGI server
asgi_server = create_asgi_server(app, streaming=True)
print("✅ ASGI server created - FastAPI running unmodified!")

# Helper function to get endpoints from FastAPI routes
def get_endpoints_from_app():
    """Extract endpoints from FastAPI OpenAPI schema (most reliable)."""
    # Force OpenAPI schema generation to ensure all routes are registered
    openapi_schema = app.openapi()
    endpoints = []
    
    # Extract from OpenAPI paths
    for path, path_item in openapi_schema.get('paths', {}).items():
        for method, operation in path_item.items():
            if method.upper() not in ['HEAD', 'OPTIONS']:
                operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")
                summary = operation.get('summary', f"{method.upper()} {path}")
                
                endpoints.append({
                    'operationId': operation_id,
                    'method': method.upper(),
                    'path': path,
                    'summary': summary,
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
    // Clear all app-related modules and reimport to pick up new endpoints
    await this.pyodide.runPythonAsync(`
import importlib
import sys

# IMPORTANT: Preserve reactive sync runtime before deleting modules
from app.reactive_sqlmodel.runtime import get_runtime
try:
    preserved_runtime = get_runtime()
    print("💾 Preserved reactive sync runtime")
except RuntimeError:
    preserved_runtime = None
    print("⚠️ No runtime to preserve")

# Step 1: Delete all domain router modules to force complete reimport
# BUT preserve models to avoid clearing reactive sync runtime
router_modules = [
    'app.domains.system.router',
    'app.domains.users.router',
    'app.domains.posts.router',
    'app.domains.dashboard.router',
]

for module_name in router_modules:
    if module_name in sys.modules:
        del sys.modules[module_name]
        print(f"🗑️ Deleted {module_name}")

# DO NOT delete domain.models or reactive_sqlmodel modules
# as they contain the reactive sync runtime

# Step 2: Delete API modules to force fresh imports
api_modules = ['app.api.v1', 'app.api']
for module_name in api_modules:
    if module_name in sys.modules:
        del sys.modules[module_name]
        print(f"🗑️ Deleted {module_name}")

# Step 3: DO NOT delete app.client_main - just reimport the routers
# This preserves the reactive sync runtime
print("♻️ Keeping app.client_main to preserve reactive sync runtime")

# Step 4: Force reimport of routers through importlib
import importlib
for module_name in ['app.api', 'app.api.v1']:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])

# Get the existing app instance (already has reactive sync)
from app.client_main import app
print("✅ Reusing app with reactive sync intact")

# Force OpenAPI schema generation to ensure all routes are registered
openapi_schema = app.openapi()
paths = openapi_schema.get('paths', {})
print(f"📋 App has {len(paths)} paths after fresh import")

# List all route paths for debugging
print("📍 Routes from OpenAPI:")
for path, path_item in paths.items():
    for method in path_item.keys():
        if method.upper() not in ['HEAD', 'OPTIONS']:
            print(f"  {method.upper()} {path}")

# Recreate ASGI server with fresh app
from app.core.asgi_server import create_asgi_server
asgi_server = create_asgi_server(app, streaming=True)
print("✅ ASGI server reset with fresh FastAPI app")
`);
  }
}
