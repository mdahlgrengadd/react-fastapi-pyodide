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
      for (const fileName of PYODIDE_CONFIG.API_FILES) {
        try {
          // Use the correct base path for the new modular structure
          const basePath = import.meta.env.BASE_URL || "/";
          const apiFileUrl = `${basePath}backend${fileName}`.replace(
            /\/+/g,
            "/"
          );
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
   * Load the FastAPI bridge from the modular API structure
   */
  async loadFastAPIBridge(): Promise<void> {
    console.log(" Loading FastAPI bridge from modular structure...");
    try {
      // Import the bridge from the persistent API directory using Python import
      await this.pyodide.runPythonAsync(`
# Import the FastAPI bridge from the persistent API directory
import sys
import os

# Ensure we're in the right directory and it's in the path
if "/persist/api" not in sys.path:
    sys.path.insert(0, "/persist/api")

# Change to the API directory if we're not already there
if not os.getcwd().endswith("/persist/api"):
    os.chdir("/persist/api")

# Try to import the bridge module properly
try:
    from app.core.bridge import EnhancedFastAPIBridge
    # Create a global bridge instance
    bridge = EnhancedFastAPIBridge()
    print("✅ Successfully imported and created bridge from modular structure!")
except ImportError as e:
    print(f"❌ Failed to import modular bridge: {e}")
    # Fall back to executing the file directly
    exec(open("/persist/api/app/core/bridge.py").read())
    # Create bridge instance after exec
    bridge = EnhancedFastAPIBridge()
    print("✅ Bridge loaded via exec fallback")
      `);
      console.log(" Enhanced FastAPI bridge loaded from modular structure!");
    } catch (error) {
      console.warn(
        " Could not load bridge from modular structure, falling back to fetch...",
        error
      );

      // Fallback: fetch from public directory
      const basePath = import.meta.env.BASE_URL || "/";
      const bridgeModuleUrl = `${basePath}backend/app/core/bridge.py`.replace(
        /\/+/g,
        "/"
      );

      const response = await fetch(bridgeModuleUrl);
      if (!response.ok) throw new Error(`Failed to load ${bridgeModuleUrl}`);
      const bridgeCode = await response.text();

      await this.pyodide.runPythonAsync(bridgeCode);
      console.log(" Enhanced FastAPI bridge loaded from fallback!");
    }
  }
  /**
   * Reset the FastAPI app and bridge for new code
   */
  async resetFastAPIBridge(): Promise<void> {
    // Reset the bridge for new code - but safely check if variables exist first
    await this.pyodide.runPythonAsync(`
# Reset the enhanced bridge for new code - clear app instance and registry safely
try:
    if '_app' in globals():
        _app = None
    if '_endpoints_registry' in globals():
        _endpoints_registry.clear()
    if 'bridge' in globals():
        bridge = EnhancedFastAPIBridge()
    else:
        # Bridge not loaded yet, that's fine
        pass
except NameError:
    # Variables don't exist yet, that's fine - first run
    pass
`);
  }
}
