export interface PyodideInterface {
  runPython: (code: string) => unknown;
  globals: Map<string, unknown>;
  loadPackage: (packages: string[]) => Promise<void>;
  runPythonAsync: (code: string) => Promise<unknown>;
  FS: {
    mkdirTree: (path: string) => void;
    mount: (filesystem: unknown, options: unknown, mountpoint: string) => void;
    syncfs: (populate: boolean, callback: (err?: Error) => void) => void;
    filesystems: {
      IDBFS: unknown;
    };
  };
}

export interface PyodideObject {
  toJs: (options?: {
    dict_converter?: (entries: [string, unknown][]) => Record<string, unknown>;
  }) => unknown;
}

export interface PyodideEndpoint {
  path: string;
  method: string;
  operationId: string;
  summary?: string;
  handler: string;
  responseModel?: string;
  requestModel?: string;
}

export interface StorageInfo {
  supported: boolean;
  quota?: number;
  usage?: number;
  databases?: string[];
}

declare global {
  interface Window {
    pyodide: PyodideInterface;
  }
}
