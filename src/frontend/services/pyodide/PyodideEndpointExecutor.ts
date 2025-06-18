import { PyodideEndpoint, PyodideInterface, PyodideObject } from './types';
import { computeHash, isMutatingMethod } from './utils';

export class PyodideEndpointExecutor {
  private endpoints: PyodideEndpoint[] = [];
  private isUserCodeLoaded = false;
  private loadedUserCodeHash = "";

  constructor(private pyodide: PyodideInterface) {}

  /**
   * Load and execute user Python code with FastAPI app
   */
  async loadUserCode(pythonCode: string): Promise<void> {
    const codeHash = await computeHash(pythonCode);
    if (this.isUserCodeLoaded && this.loadedUserCodeHash === codeHash) {
      console.log(" User code already loaded (cached)");
      return;
    }

    console.log(" Loading user Python code...");

    // Clear previous endpoints
    this.endpoints = [];

    // Execute user code
    await this.pyodide.runPythonAsync(pythonCode);

    // Get endpoints from the FastAPI bridge
    const endpointsData = this.pyodide.runPython(
      "bridge.get_endpoints()"
    ) as PyodideObject;

    // Type assertion is safe here as we know the Python function returns a list of endpoint dictionaries
    this.endpoints = endpointsData.toJs({
      dict_converter: Object.fromEntries,
    }) as PyodideEndpoint[];

    console.log(
      ` Registered ${this.endpoints.length} endpoints:`,
      this.endpoints
    );

    this.isUserCodeLoaded = true;
    this.loadedUserCodeHash = codeHash;
  }

  /**
   * Get OpenAPI schema from the real FastAPI app
   */
  getOpenAPISchema(): unknown {
    if (!this.isUserCodeLoaded) {
      return null;
    }

    const schema = this.pyodide.runPython(
      "bridge.get_openapi_schema()"
    ) as PyodideObject;

    // Type assertion is safe here as we know the Python function returns a dictionary
    return schema.toJs({ dict_converter: Object.fromEntries });
  }

  /**
   * Get the list of registered endpoints
   */
  getEndpoints(): PyodideEndpoint[] {
    return this.endpoints;
  }

  /**
   * Execute a specific endpoint with given parameters
   */
  async executeEndpoint(
    operationId: string,
    pathParams?: Record<string, string>,
    queryParams?: Record<string, unknown>,
    body?: unknown
  ): Promise<unknown> {
    if (!this.isUserCodeLoaded) {
      throw new Error("User code not loaded");
    }

    // Properly handle undefined values - convert to null for Python
    const safePathParams = pathParams || null;
    const safeQueryParams = queryParams || null;
    const safeBody = body !== undefined ? body : null;

    console.log(` Executing endpoint: ${operationId}`, {
      pathParams: safePathParams,
      queryParams: safeQueryParams,
      body: safeBody,
    });

    // Prepare parameters for Python execution
    const pathParamsStr = safePathParams
      ? JSON.stringify(safePathParams)
      : "None";
    const queryParamsStr = safeQueryParams
      ? JSON.stringify(safeQueryParams)
      : "None";

    // Don't stringify the body - pass it as a Python object reference
    // Set the body in Python globals so it can be accessed properly
    if (safeBody !== null) {
      this.pyodide.globals.set("_request_body", safeBody);
    } else {
      this.pyodide.globals.set("_request_body", null);
    }

    const result = (await this.pyodide.runPythonAsync(`
import json

# Get the body from globals (already converted to Python object by Pyodide)
request_body = globals().get('_request_body', None)

# Debug: Print what we received
print(f" Python received operationId: ${operationId}")
print(" Python received pathParams:", ${pathParamsStr})
print(" Python received queryParams:", ${queryParamsStr})
print(f" Python received body: {request_body} (type: {type(request_body)})")

# Call the endpoint executor
result = await execute_endpoint(
    "${operationId}",
    ${pathParamsStr},
    ${queryParamsStr},
    request_body
)
result
`)) as PyodideObject;

    // Type assertion is safe here as we know the Python function returns a result dictionary
    const jsResult = result.toJs({ dict_converter: Object.fromEntries });
    console.log(` Endpoint result:`, jsResult);

    return jsResult;
  }

  /**
   * Check if the endpoint should trigger auto-save
   */
  shouldAutoSave(operationId: string): boolean {
    const endpoint = this.endpoints.find(
      (ep) => ep.operationId === operationId
    );
    return endpoint ? isMutatingMethod(endpoint.method) : false;
  }

  /**
   * Check if user code is loaded
   */
  isCodeLoaded(): boolean {
    return this.isUserCodeLoaded;
  }

  /**
   * Get the hash of the currently loaded code
   */
  getCurrentCodeHash(): string {
    return this.loadedUserCodeHash;
  }

  /**
   * Clear loaded user code
   */
  clearUserCode(): void {
    this.endpoints = [];
    this.isUserCodeLoaded = false;
    this.loadedUserCodeHash = "";
  }
}
