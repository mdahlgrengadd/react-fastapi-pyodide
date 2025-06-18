import { PYODIDE_CONFIG } from './constants';
import { PyodideInterface, StorageInfo } from './types';

export class PyodidePersistence {
  constructor(private pyodide: PyodideInterface | null) {}

  /**
   * Check and clear old cache if version has changed
   */
  async checkAndClearOldCache(): Promise<void> {
    const storedVersion = localStorage.getItem(
      PYODIDE_CONFIG.STORAGE_VERSION_KEY
    );

    if (storedVersion !== PYODIDE_CONFIG.CURRENT_STORAGE_VERSION) {
      console.log(
        ` Clearing old cache (${storedVersion} -> ${PYODIDE_CONFIG.CURRENT_STORAGE_VERSION})`
      );

      // Clear IndexedDB storage by deleting and recreating
      try {
        const databases = await indexedDB.databases();
        for (const db of databases) {
          if (db.name?.includes("emscripten") || db.name?.includes("pyodide")) {
            console.log(` Deleting old database: ${db.name}`);
            indexedDB.deleteDatabase(db.name);
          }
        }
      } catch (error) {
        console.warn(" Could not clear old databases:", error);
      }

      // Update version
      localStorage.setItem(
        PYODIDE_CONFIG.STORAGE_VERSION_KEY,
        PYODIDE_CONFIG.CURRENT_STORAGE_VERSION
      );
    }
  }

  /**
   * Set up persistent file system using IDBFS
   */
  async setupPersistentFileSystem(): Promise<void> {
    if (!this.pyodide) {
      console.warn(
        " Cannot setup persistent file system: Pyodide not initialized"
      );
      return;
    }

    console.log(" Setting up persistent file system...");

    try {
      // Create and mount persistent directory
      this.pyodide.FS.mkdirTree(PYODIDE_CONFIG.PERSIST_ROOT);
      this.pyodide.FS.mount(
        this.pyodide.FS.filesystems.IDBFS,
        {},
        PYODIDE_CONFIG.PERSIST_ROOT
      );

      // Load previous state from IndexedDB
      await new Promise<void>((resolve) => {
        this.pyodide!.FS.syncfs(true, (err?: Error) => {
          if (err) {
            console.warn(" Could not load previous state:", err);
            resolve(); // Continue even if loading fails
          } else {
            console.log(" Loaded previous state from IndexedDB");
            resolve();
          }
        });
      });
    } catch (error) {
      console.warn(" Could not set up persistent file system:", error);
      // Continue without persistence
    }
  }

  /**
   * Set up SQLite persistence by creating the persistent database functions
   */
  async setupSQLitePersistence(): Promise<void> {
    if (!this.pyodide) {
      console.warn(" Cannot setup SQLite persistence: Pyodide not initialized");
      return;
    }

    try {
      console.log(" Setting up SQLite persistence...");

      await this.pyodide.runPythonAsync(`
# Set up persistent SQLite database
import os
import sqlite3

# Create persistent directory for databases if it doesn't exist
db_dir = "/persist/databases"
os.makedirs(db_dir, exist_ok=True)

# Set default SQLite database path
DEFAULT_DB_PATH = "/persist/databases/app.db"

# Create a helper function to get persistent database URL
def get_persistent_db_url():
    return f"sqlite:///{DEFAULT_DB_PATH}"

# Store in globals for easy access
import builtins
builtins.DEFAULT_DB_PATH = DEFAULT_DB_PATH
builtins.get_persistent_db_url = get_persistent_db_url

# Add a function to manually save persistence state from Python
def save_persistent_state():
    """Save the current state to persistent storage (IndexedDB)"""
    # This will call the JavaScript method through a global callback
    try:
        # The JavaScript callback will be set up by the engine
        if hasattr(builtins, '_js_save_persistent_state'):
            builtins._js_save_persistent_state()
            print(" Manually saved state to persistent storage")
        else:
            print(" Persistence save callback not available")
    except Exception as e:
        print(f" Error saving persistent state: {e}")

builtins.save_persistent_state = save_persistent_state

print(f" SQLite persistence enabled - database: {DEFAULT_DB_PATH}")
`);

      console.log(" SQLite persistence setup complete");
    } catch (error) {
      console.warn(" Could not set up SQLite persistence:", error);

      // Set up fallback functions
      try {
        await this.pyodide!.runPythonAsync(`
# Fallback: Create stub functions that indicate persistence is not available
def get_persistent_db_url():
    print(" SQLite persistence not available, using fallback")
    return "sqlite:///:memory:"

def save_persistent_state():
    print(" Persistence not available - save_persistent_state() has no effect")

import builtins
builtins.get_persistent_db_url = get_persistent_db_url
builtins.save_persistent_state = save_persistent_state
builtins.DEFAULT_DB_PATH = ":memory:"

print(" SQLite persistence disabled - using in-memory database")
`);
      } catch (fallbackError) {
        console.warn(
          " Could not even set up fallback persistence functions:",
          fallbackError
        );
      }
    }
  }

  /**
   * Save current state to persistent storage
   */
  async savePersistentState(): Promise<void> {
    if (!this.pyodide) {
      console.warn(" Cannot save persistent state: Pyodide not initialized");
      return;
    }

    try {
      console.log(" Saving state to persistent storage...");

      await new Promise<void>((resolve) => {
        this.pyodide!.FS.syncfs(false, (err?: Error) => {
          if (err) {
            console.warn(" Could not save state:", err);
            resolve(); // Continue even if saving fails
          } else {
            console.log(" State saved to IndexedDB");
            resolve();
          }
        });
      });
    } catch (error) {
      console.warn(" Could not save persistent state:", error);
    }
  }

  /**
   * Clear all persistent data (useful for debugging or reset)
   */
  async clearPersistentData(): Promise<void> {
    console.log(" Clearing all persistent data...");

    try {
      // Clear localStorage
      localStorage.removeItem(PYODIDE_CONFIG.STORAGE_VERSION_KEY);

      // Clear IndexedDB databases
      const databases = await indexedDB.databases();
      for (const db of databases) {
        if (db.name?.includes("emscripten") || db.name?.includes("pyodide")) {
          console.log(` Deleting database: ${db.name}`);
          indexedDB.deleteDatabase(db.name);
        }
      }

      console.log(" Persistent data cleared");
    } catch (error) {
      console.warn(" Could not clear persistent data:", error);
    }
  }

  /**
   * Get information about persistent storage usage
   */
  async getStorageInfo(): Promise<StorageInfo> {
    try {
      const info: StorageInfo = { supported: true };

      // Get storage quota if available
      if ("storage" in navigator && "estimate" in navigator.storage) {
        const estimate = await navigator.storage.estimate();
        info.quota = estimate.quota;
        info.usage = estimate.usage;
      }

      // List databases
      const databases = await indexedDB.databases();
      info.databases = databases
        .filter(
          (db) =>
            db.name?.includes("emscripten") || db.name?.includes("pyodide")
        )
        .map((db) => db.name || "unknown");

      return info;
    } catch (error) {
      console.warn(" Could not get storage info:", error);
      return { supported: false };
    }
  }
}
