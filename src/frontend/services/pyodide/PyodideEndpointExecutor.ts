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

    // Get endpoints directly from FastAPI app (no bridge!)
    const endpointsData = this.pyodide.runPython(
      "get_endpoints_from_app()"
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
      "get_openapi_from_app()"
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
    body?: unknown,
    headers?: Record<string, string>,
    contentType?: string
  ): Promise<unknown> {
    if (!this.isUserCodeLoaded) {
      throw new Error("User code not loaded");
    }

    // Properly handle undefined values - convert to null for Python
    const safePathParams = pathParams || null;
    const safeQueryParams = queryParams || null;
    const safeBody = body !== undefined ? body : null;
    const safeHeaders = headers || {};
    const safeContentType = contentType || null;

    console.log(` Executing endpoint: ${operationId}`, {
      pathParams: safePathParams,
      queryParams: safeQueryParams,
      body: safeBody,
      headers: safeHeaders,
      contentType: safeContentType,
    });

    // Prepare parameters for Python execution
    const pathParamsStr = safePathParams
      ? JSON.stringify(safePathParams)
      : "None";
    const queryParamsStr = safeQueryParams
      ? JSON.stringify(safeQueryParams)
      : "None";

    // Don't stringify the body - pass it as a Python object reference
    // Set the body, headers, and content type in Python globals
    if (safeBody !== null) {
      this.pyodide.globals.set("_request_body", safeBody);
    } else {
      this.pyodide.globals.set("_request_body", null);
    }

    // Pass headers as a dictionary
    this.pyodide.globals.set("_request_headers", safeHeaders);

    // Pass content type as a string
    if (safeContentType !== null) {
      this.pyodide.globals.set("_request_content_type", safeContentType);
    } else {
      this.pyodide.globals.set("_request_content_type", null);
    }

    const result = (await this.pyodide.runPythonAsync(`
import json
from urllib.parse import urlencode

# Get parameters from globals (already converted to Python objects by Pyodide)
request_body = globals().get('_request_body', None)
request_headers_proxy = globals().get('_request_headers', {})
request_content_type = globals().get('_request_content_type', None)

# Convert JavaScript proxy object to Python dict
request_headers = {}
if request_headers_proxy is not None:
    try:
        # Try to convert using to_py() if it's a JavaScript proxy
        request_headers = request_headers_proxy.to_py() if hasattr(request_headers_proxy, 'to_py') else dict(request_headers_proxy)
    except:
        request_headers = {}

# Debug: Print what we received
print(f"🔄 ASGI handling: ${operationId}")
print(" Path params:", ${pathParamsStr})
print(" Query params:", ${queryParamsStr})
print(f" Body: {request_body} (type: {type(request_body)})")
print(f" Headers: {request_headers}")

# Find the endpoint in the app routes
path_params = ${pathParamsStr} or {}
query_params = ${queryParamsStr} or {}

# Find matching route
target_route = None
for route in app.routes:
    if hasattr(route, 'name') and route.name == "${operationId}":
        target_route = route
        break
    if hasattr(route, 'methods'):
        for method in route.methods:
            path_normalized = route.path.replace('/', '_').replace('{', '').replace('}', '')
            if path_normalized.startswith('_'):
                path_normalized = path_normalized[1:]
            op_id = f"{method.lower()}{path_normalized}"
            if op_id == "${operationId}":
                target_route = route
                break
    if target_route:
        break

if not target_route:
    result = {"content": {"error": "Endpoint not found: ${operationId}"}, "status_code": 404}
else:
    # Build ASGI scope for this request
    path = target_route.path
    # Replace path parameters
    for key, value in path_params.items():
        path = path.replace(f'{{{key}}}', str(value))
    
    # Build query string
    query_string = urlencode(query_params) if query_params else ""
    
    # Determine HTTP method from route
    http_method = list(target_route.methods)[0] if hasattr(target_route, 'methods') else "GET"
    
    # Prepare request body
    body_bytes = b""
    if request_body is not None:
        if isinstance(request_body, str):
            body_bytes = request_body.encode('utf-8')
        elif isinstance(request_body, dict):
            # JSON encode dicts
            body_bytes = json.dumps(request_body).encode('utf-8')
            if 'content-type' not in {k.lower(): v for k, v in request_headers.items()}:
                request_headers['content-type'] = 'application/json'
        elif isinstance(request_body, bytes):
            body_bytes = request_body
    
    # Build headers list
    headers_list = [[k.lower().encode('latin-1'), str(v).encode('latin-1')] for k, v in request_headers.items()]
    
    # Build ASGI scope
    scope = {
        'type': 'http',
        'method': http_method.upper(),
        'path': path,
        'query_string': query_string,
        'headers': headers_list,
        'body': body_bytes,
        'scheme': 'https',
    }
    
    print(f"📡 Calling ASGI server: {http_method} {path}")
    
    # Call ASGI server
    asgi_response = await asgi_server.handle_request(scope)
    
    # Parse response
    status = asgi_response.get('status', 200)
    body_data = asgi_response.get('body', b'')
    
    # Decode body
    if isinstance(body_data, bytes):
        try:
            content = json.loads(body_data.decode('utf-8'))
        except:
            content = body_data.decode('utf-8', errors='ignore')
    else:
        content = body_data
    
    result = {
        'content': content,
        'status_code': status
    }
    
    print(f"✅ ASGI response: {status}")

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
