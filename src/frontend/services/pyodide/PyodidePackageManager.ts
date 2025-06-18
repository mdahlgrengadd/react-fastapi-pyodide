import { PYODIDE_CONFIG } from './constants';
import { PyodideInterface } from './types';
import { analyzePythonDependencies } from './utils';

export class PyodidePackageManager {
  constructor(private pyodide: PyodideInterface | null) {}

  /**
   * Install FastAPI and core dependencies
   */
  async installRealFastAPI(): Promise<void> {
    // Check if packages are already installed (from persistence)
    const packagesAlreadyInstalled = await this.checkPackagesInstalled();

    if (packagesAlreadyInstalled) {
      console.log(" FastAPI packages already installed (from cache)");
    } else {
      console.log(" Installing FastAPI, Pydantic, and related packages...");

      // Install FastAPI and dependencies via micropip
      // Note: ssl and sqlite3 are part of Pyodide stdlib, removed from install list
      // Avoid ujson dependency by installing core FastAPI instead of [all]
      await this.pyodide.runPythonAsync(`
import micropip
try:
    # Install typing_extensions first to avoid version conflicts
    await micropip.install("typing_extensions>=4.12.0")
    # Install FastAPI core without ujson dependency (which lacks pure Python wheels)
    await micropip.install("fastapi")
    # Install essential dependencies manually to avoid ujson
    await micropip.install([
        "python-multipart",   # For form data parsing
        "pydantic-settings",  # For settings management
        "sqlalchemy",         # Commonly needed for database work
    ])
    print(" FastAPI and dependencies installed successfully")
except Exception as e:
    print(f" Package installation error: {e}")
    # Try minimal installation as fallback
    try:
        await micropip.install("typing_extensions>=4.12.0")
        await micropip.install("fastapi")
        print(" Minimal FastAPI installation successful")
    except Exception as e2:
        print(f" Minimal installation also failed: {e2}")
        raise e2
      `);
    }
  }

  /**
   * Check if required packages are already installed
   */
  async checkPackagesInstalled(): Promise<boolean> {
    try {
      const result = this.pyodide.runPython(`
import importlib.util, ssl, sqlite3

def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None

required = ${JSON.stringify(PYODIDE_CONFIG.REQUIRED_PACKAGES)}
installed = all(has_module(pkg) for pkg in required)

# Ensure mandatory stdlib modules exist (they always do in Pyodide)
_ = ssl, sqlite3

installed
`) as boolean;

      return result;
    } catch (error) {
      console.warn(" Could not check installed packages:", error);
      return false;
    }
  }

  /**
   * Install packages on demand based on code requirements
   */
  async installPackagesOnDemand(packages: string[]): Promise<void> {
    if (packages.length === 0) return;

    console.log(` Installing required packages: ${packages.join(", ")}`);

    await this.pyodide.runPythonAsync(`
import micropip
await micropip.install([${packages.map((pkg) => `"${pkg}"`).join(", ")}])
    `);
  }

  /**
   * Analyze Python code and install required dependencies
   */
  async installDependenciesForCode(pythonCode: string): Promise<void> {
    const requiredPackages = analyzePythonDependencies(pythonCode);
    if (requiredPackages.length > 0) {
      await this.installPackagesOnDemand(requiredPackages);
    }
  }

  /**
   * Load essential packages required for the system
   */
  async loadEssentialPackages(): Promise<void> {
    console.log(" Loading essential packages...");
    await this.pyodide.loadPackage(["micropip"]);
  }
}
