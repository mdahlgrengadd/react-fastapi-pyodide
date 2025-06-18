import { PYODIDE_CONFIG } from './constants';
import { PyodideInterface } from './types';

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
      }

      // Load and write Python API files from public/pyodide
      for (const fileName of PYODIDE_CONFIG.API_FILES) {
        try {
          // Use the correct base path for GitHub Pages deployment
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
      // Load the bridge from the persistent API directory
      await this.pyodide.runPythonAsync(`
# Load the FastAPI bridge from the persistent API directory
exec(open("/persist/api/bridge.py").read())
      `);
      console.log(" Enhanced FastAPI bridge loaded from modular structure!");
    } catch (error) {
      console.warn(
        " Could not load bridge from modular structure, falling back to fetch...",
        error
      );

      // Fallback: fetch from public directory
      const basePath = import.meta.env.BASE_URL || "/";
      const bridgeModuleUrl = `${basePath}backend/bridge.py`.replace(
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
    // Reset the bridge for new code
    await this.pyodide.runPythonAsync(`
# Reset the enhanced bridge for new code - clear app instance and registry
_app = None
_endpoints_registry.clear()
bridge = EnhancedFastAPIBridge()
`);
  }
}
