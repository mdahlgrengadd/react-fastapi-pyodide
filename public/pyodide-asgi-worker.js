/**
 * Pyodide ASGI Service Worker
 *
 * This Service Worker intercepts HTTP requests to /api/* and forwards them
 * to a Pyodide ASGI server, enabling FastAPI to run without monkey-patching.
 *
 * Architecture:
 * Browser fetch() → Service Worker → ASGI scope → Pyodide → FastAPI → Response
 */

const CACHE_NAME = "pyodide-asgi-v1";
const API_PREFIX = "/api/backend";

// Flag to track if Pyodide is ready
let pyodideReady = false;
let pyodidePort = null;

// Listen for messages from the main thread
self.addEventListener("message", (event) => {
  if (event.data.type === "PYODIDE_READY") {
    pyodideReady = true;
    pyodidePort = event.ports[0];
    console.log("[Service Worker] Pyodide connection established");
  }
});

// Install event
self.addEventListener("install", (event) => {
  console.log("[Service Worker] Installing Pyodide ASGI Worker");
  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Activate event
self.addEventListener("activate", (event) => {
  console.log("[Service Worker] Activating Pyodide ASGI Worker");
  // Claim all clients immediately
  event.waitUntil(self.clients.claim());
});

// Fetch event - intercept API requests
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Only intercept API requests
  if (url.pathname.startsWith(API_PREFIX)) {
    event.respondWith(handleASGIRequest(event.request));
  }
  // All other requests pass through
});

/**
 * Handle an API request through the ASGI interface
 */
async function handleASGIRequest(request) {
  try {
    // Wait for Pyodide to be ready
    if (!pyodideReady) {
      return new Response(
        JSON.stringify({
          error: "Pyodide not ready",
          detail: "The Python environment is still loading. Please try again.",
        }),
        {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Convert fetch Request to ASGI scope
    const scope = await requestToASGIScope(request);

    // Send request to Pyodide via MessageChannel
    const asgiResponse = await callPyodideASGI(scope);

    // Convert ASGI response to fetch Response
    return asgiResponseToFetchResponse(asgiResponse);
  } catch (error) {
    console.error("[Service Worker] Error handling request:", error);
    return new Response(
      JSON.stringify({
        error: "Internal Server Error",
        detail: error.message,
        stack: error.stack,
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

/**
 * Convert a fetch Request to an ASGI scope dictionary
 */
async function requestToASGIScope(request) {
  const url = new URL(request.url);

  // Remove API prefix from path
  const path = url.pathname.replace(API_PREFIX, "") || "/";

  // Extract headers as array of [name, value] tuples
  const headers = [];
  request.headers.forEach((value, name) => {
    headers.push([name, value]);
  });

  // Read body if present
  let body = null;
  if (request.method !== "GET" && request.method !== "HEAD") {
    // Check content type
    const contentType = request.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      // JSON body
      body = await request.text();
    } else if (contentType.includes("application/x-www-form-urlencoded")) {
      // Form data - keep as string
      body = await request.text();
    } else if (contentType.includes("multipart/form-data")) {
      // FormData - would need special handling
      body = await request.text();
    } else {
      // Default - read as text
      body = await request.text();
    }
  }

  // Build ASGI scope
  const scope = {
    type: "http",
    method: request.method,
    scheme: url.protocol.replace(":", ""),
    path: path,
    query_string: url.search.slice(1), // Remove leading '?'
    headers: headers,
    body: body,
  };

  return scope;
}

/**
 * Call Pyodide ASGI server via MessageChannel
 */
async function callPyodideASGI(scope) {
  return new Promise((resolve, reject) => {
    if (!pyodidePort) {
      reject(new Error("Pyodide port not available"));
      return;
    }

    // Create a unique ID for this request
    const requestId = Math.random().toString(36).substring(7);

    // Set up one-time listener for the response
    const handleResponse = (event) => {
      if (event.data.requestId === requestId) {
        pyodidePort.removeEventListener("message", handleResponse);
        if (event.data.error) {
          reject(new Error(event.data.error));
        } else {
          resolve(event.data.response);
        }
      }
    };

    pyodidePort.addEventListener("message", handleResponse);

    // Send request to Pyodide
    pyodidePort.postMessage({
      type: "ASGI_REQUEST",
      requestId: requestId,
      scope: scope,
    });

    // Timeout after 30 seconds
    setTimeout(() => {
      pyodidePort.removeEventListener("message", handleResponse);
      reject(new Error("Request timeout"));
    }, 30000);
  });
}

/**
 * Convert ASGI response to fetch Response
 */
function asgiResponseToFetchResponse(asgiResponse) {
  const { status, headers, body } = asgiResponse;

  // Convert headers array to Headers object
  const responseHeaders = new Headers();
  for (const [name, value] of headers) {
    // Convert bytes to string if needed
    const nameStr = typeof name === "string" ? name : new TextDecoder().decode(name);
    const valueStr = typeof value === "string" ? value : new TextDecoder().decode(value);
    responseHeaders.append(nameStr, valueStr);
  }

  // Ensure CORS headers for local development
  if (!responseHeaders.has("Access-Control-Allow-Origin")) {
    responseHeaders.set("Access-Control-Allow-Origin", "*");
  }

  // Convert body to appropriate format
  let responseBody;
  if (typeof body === "string") {
    responseBody = body;
  } else if (body instanceof Uint8Array || body instanceof ArrayBuffer) {
    responseBody = body;
  } else {
    // Assume it's JSON-serializable
    responseBody = JSON.stringify(body);
  }

  return new Response(responseBody, {
    status: status,
    statusText: getStatusText(status),
    headers: responseHeaders,
  });
}

/**
 * Get HTTP status text for a status code
 */
function getStatusText(code) {
  const statusTexts = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
    503: "Service Unavailable",
  };
  return statusTexts[code] || "Unknown";
}
