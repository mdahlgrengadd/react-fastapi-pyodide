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
   * Execute a streaming endpoint with REAL interleaved updates
   * 
   * GENERIC APPROACH: Works with any FastAPI streaming endpoint!
   * Automatically detects StreamingResponse and manually iterates it.
   */
  async executeEndpointStreaming(
    operationId: string,
    onChunk: (data: Uint8Array) => Promise<void>,
    pathParams?: Record<string, string>,
    queryParams?: Record<string, unknown>,
    body?: unknown,
    headers?: Record<string, string>
  ): Promise<void> {
    if (!this.isUserCodeLoaded) {
      throw new Error('User code not loaded');
    }

    console.log(`🌊 Starting TRUE streaming for: ${operationId}`);

    // Set up parameters
    this.pyodide.globals.set('_operation_id', operationId);
    this.pyodide.globals.set('_path_params', pathParams || {});
    this.pyodide.globals.set('_query_params', queryParams || {});
    this.pyodide.globals.set('_request_body', body || null);
    this.pyodide.globals.set('_request_headers', headers || {});

    // 100% GENERIC: Inline streaming setup (works with ANY FastAPI endpoint!)
    await this.pyodide.runPythonAsync(`
import asyncio
import inspect
import json
from urllib.parse import urlencode
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from app.app_main import app

operation_id = globals().get('_operation_id')
path_params = globals().get('_path_params', {})
query_params = globals().get('_query_params', {})
request_body = globals().get('_request_body')
request_headers = globals().get('_request_headers', {})

if hasattr(path_params, 'to_py'):
    path_params = path_params.to_py()
if hasattr(query_params, 'to_py'):
    query_params = query_params.to_py()
if hasattr(request_headers, 'to_py'):
    request_headers = dict(request_headers.to_py())

print(f"🌊 100% Generic streaming: {operation_id}")

# STEP 1: Find route by operation_id (works for ANY endpoint)
target_route = None
for route in app.routes:
    if isinstance(route, APIRoute):
        if route.operation_id == operation_id or route.name == operation_id:
            target_route = route
            break

if not target_route:
    raise Exception(f"Endpoint not found: {operation_id}")

print(f"✅ Found route: {target_route.path}")

# STEP 2: Build complete mock Request for FastAPI's dependency resolution
class MockRequest:
    def __init__(self, method, url, path, headers, query_params, path_params, body, cookies=None):
        self.method = method
        self.url = url
        from starlette.datastructures import Headers, QueryParams
        self._headers = Headers(headers or {})
        self._query_params = QueryParams(query_params or {})
        self.path_params = path_params or {}
        self._body = body
        self._cookies = cookies or {}
        self.app = app
        self.state = type('State', (), {})()
        
        # Note: scope will be set after AsyncExitStack is created
        self.scope = None
    
    @property
    def headers(self):
        return self._headers
    
    @property
    def query_params(self):
        return self._query_params
    
    @property
    def cookies(self):
        """Cookies dict - required by FastAPI's dependency resolver."""
        return self._cookies
    
    async def json(self):
        if self._body:
            return json.loads(self._body.decode('utf-8') if isinstance(self._body, bytes) else self._body)
        return {}
    
    async def body(self):
        return self._body or b""
    
    async def form(self):
        """Form data - for multipart/form-data support."""
        return {}

# Build path
path = target_route.path
for key, value in path_params.items():
    path = path.replace(f'{{{key}}}', str(value))

query_string = urlencode(query_params) if query_params else ""
url = f"https://localhost{path}"
if query_string:
    url += f"?{query_string}"

# Prepare body
body_bytes = None
if request_body is not None:
    if isinstance(request_body, bytes):
        body_bytes = request_body
    elif isinstance(request_body, str):
        body_bytes = request_body.encode('utf-8')
    elif isinstance(request_body, dict):
        body_bytes = json.dumps(request_body).encode('utf-8')

method = list(target_route.methods)[0] if target_route.methods else 'GET'

# Add authorization header if available from localStorage (standard pattern)
if 'authorization' not in {k.lower(): v for k, v in request_headers.items()}:
    import js
    token = js.localStorage.getItem('access_token')
    if token and token != 'null':
        request_headers['Authorization'] = f'Bearer {token}'
        print(f"🔑 Added auth token from localStorage")

mock_request = MockRequest(method, url, path, request_headers, query_params, path_params, body_bytes)

print(f"📋 Setting up FastAPI dependency resolution...")

# STEP 3: Setup FastAPI's dependency resolution system
from fastapi.dependencies.utils import solve_dependencies
from contextlib import AsyncExitStack

# FastAPI requires TWO AsyncExitStack instances in scope
inner_astack = AsyncExitStack()
function_astack = AsyncExitStack()

# CRITICAL: Put both AsyncExitStacks in scope where FastAPI expects them
mock_request.scope = {
    'type': 'http',
    'method': method,
    'path': path,
    'query_string': urlencode(query_params).encode() if query_params else b'',
    'headers': [[k.lower().encode('latin-1'), str(v).encode('latin-1')] for k, v in request_headers.items()],
    'app': app,
    'state': {},
    'fastapi_inner_astack': inner_astack,      # For middleware/inner dependencies
    'fastapi_function_astack': function_astack, # For function-level dependencies
}

print(f"📋 Resolving dependencies with FastAPI's native system...")

# Use FastAPI's NATIVE dependency resolution system
# This handles ALL dependency types: Depends(), Query(), Path(), Body(), Header(), Cookie()
solved = await solve_dependencies(
    request=mock_request,
    dependant=target_route.dependant,
    async_exit_stack=function_astack,  # Use function astack for resolution
    embed_body_fields=True,
)

# Extract values and errors from SolvedDependency object
values = solved.values
errors = solved.errors

if errors:
    # FastAPI couldn't resolve dependencies - fail cleanly
    error_details = [str(e) for e in errors]
    print(f"❌ Dependency resolution failed: {error_details}")
    raise Exception(f"Cannot resolve dependencies: {error_details}")

print(f"✅ All dependencies resolved: {list(values.keys())}")

# STEP 4: Call endpoint
print(f"📞 Calling endpoint...")
result = await target_route.endpoint(**values)

print(f"📦 Result type: {type(result).__name__}")

# STEP 5: Extract generator from StreamingResponse
if isinstance(result, StreamingResponse):
    print("✅ StreamingResponse - extracting generator")
    _stream_generator = result.body_iterator
    _inner_astack = inner_astack  # Store for cleanup
    _function_astack = function_astack  # Store for cleanup
    print(f"✅ Generator type: {type(_stream_generator).__name__}")
else:
    # Not streaming - cleanup and return
    await inner_astack.aclose()
    await function_astack.aclose()
    raise Exception(f"Not a StreamingResponse: {type(result).__name__}")
    `);

    // Now manually iterate the generator, yielding control between iterations
    let chunkNumber = 0;
    while (true) {
      try {
        // Get next chunk from Python generator
        const result = await this.pyodide.runPythonAsync(`
import asyncio

result = None
try:
    # Get next chunk from generator
    chunk = await _stream_generator.__anext__()
    result = {'done': False, 'value': chunk}
except StopAsyncIteration:
    result = {'done': True, 'value': None}

result
        `);

        const jsResult = (result as PyodideObject).toJs() as { done: boolean; value: unknown };
        
        if (jsResult.done) {
          console.log('✅ Stream complete');
          // Cleanup: Close both async exit stacks
          await this.pyodide.runPythonAsync(`
if '_inner_astack' in globals() and '_function_astack' in globals():
    await _inner_astack.aclose()
    await _function_astack.aclose()
    print("🧹 Cleaned up all dependency resources")
          `);
          break;
        }

        // Convert chunk to proper format
        const chunk = jsResult.value;
        let chunkBytes: Uint8Array;
        
        if (!chunk) {
          continue; // Skip empty chunks
        }
        
        // Handle Pyodide proxy objects
        if (typeof (chunk as PyodideObject).toJs === 'function') {
          const jsChunk = (chunk as PyodideObject).toJs() as string | number[];
          chunkBytes = typeof jsChunk === 'string'
            ? new TextEncoder().encode(jsChunk)
            : new Uint8Array(jsChunk);
        } else if (typeof chunk === 'string') {
          chunkBytes = new TextEncoder().encode(chunk);
        } else if (chunk instanceof Uint8Array) {
          chunkBytes = chunk;
        } else {
          // Assume it's array-like
          chunkBytes = new Uint8Array(chunk as number[]);
        }

        chunkNumber++;
        console.log(`📨 Chunk ${chunkNumber}: ${chunkBytes.byteLength} bytes`);

        // Call the callback - this updates UI immediately!
        await onChunk(chunkBytes);

        // CRITICAL: Yield control to browser event loop
        // This allows React to process state updates before next chunk
        await new Promise(resolve => setTimeout(resolve, 0));

      } catch (error) {
        console.error('❌ Stream iteration error:', error);
        // Cleanup on error - close both exit stacks
        await this.pyodide.runPythonAsync(`
if '_inner_astack' in globals() and '_function_astack' in globals():
    await _inner_astack.aclose()
    await _function_astack.aclose()
    print("🧹 Cleaned up dependency resources (error path)")
        `);
        throw error;
      }
    }

    console.log(`🎉 Streaming finished - processed ${chunkNumber} chunks`);
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
