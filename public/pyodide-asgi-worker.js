/**
 * Pyodide ASGI Service Worker
 *
 * This Service Worker:
 * 1. Intercepts HTTP requests to /api/backend/* and forwards to Pyodide ASGI server
 * 2. Caches Pyodide runtime and Python files for faster loading
 * 3. Enables offline-capable FastAPI in the browser
 *
 * Architecture:
 * Browser fetch() → Service Worker → ASGI scope → Pyodide → FastAPI → Response
 */

const CACHE_NAME = "pyodide-asgi-v2";
const API_PREFIX = "/api/backend";

// Pyodide CDN resources to cache
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full";
const PYODIDE_RESOURCES = [
  `${PYODIDE_CDN}/pyodide.js`,
  `${PYODIDE_CDN}/pyodide.asm.wasm`,
  `${PYODIDE_CDN}/python_stdlib.zip`,
];

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
  console.log("[ASGI Worker] Installing Pyodide ASGI Worker");
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[ASGI Worker] Caching Pyodide resources");
      // Pre-cache Pyodide resources for faster loading
      return cache.addAll(PYODIDE_RESOURCES).catch((err) => {
        console.warn("[ASGI Worker] Failed to cache some resources:", err);
        // Continue even if some resources fail to cache
      });
    }).then(() => {
      // Skip waiting to activate immediately
      return self.skipWaiting();
    })
  );
});

// Activate event
self.addEventListener("activate", (event) => {
  console.log("[ASGI Worker] Activating Pyodide ASGI Worker");
  
  event.waitUntil(
    // Clean up old caches
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName.startsWith("pyodide-")) {
            console.log("[ASGI Worker] Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Claim all clients immediately
      return self.clients.claim();
    })
  );
});

// Fetch event - intercept API requests and cache Pyodide resources
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Strategy 1: Intercept API requests and forward to ASGI
  const apiIndex = url.pathname.indexOf(API_PREFIX);
  if (apiIndex !== -1) {
    event.respondWith(handleASGIRequest(event.request, apiIndex));
    return;
  }

  // Strategy 2: Cache Pyodide CDN resources (Cache First)
  if (url.hostname === "cdn.jsdelivr.net" && url.pathname.includes("pyodide")) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        if (response) {
          console.log("[ASGI Worker] Serving Pyodide from cache:", url.pathname);
          return response;
        }
        console.log("[ASGI Worker] Fetching and caching Pyodide:", url.pathname);
        return fetch(event.request).then((response) => {
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // Strategy 3: Cache Python files (Cache First)
  if (event.request.url.endsWith(".py") || event.request.url.includes("/backend/")) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request).then((response) => {
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // All other requests pass through (Network First)
});

/**
 * Handle an API request through the ASGI interface
 */
async function handleASGIRequest(request, apiIndex = 0) {
  try {
    // Wait for Pyodide to be ready (queue briefly instead of failing fast)
    const ready = await waitForPyodideReady(15000);
    if (!ready) {
      return new Response(
        JSON.stringify({
          error: "Pyodide not ready",
          detail:
            "The Python environment is still loading. Please try again in a moment.",
        }),
        {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Convert fetch Request to ASGI scope
    const scope = await requestToASGIScope(request, apiIndex);

    // Use streaming pipeline for SSE
    if (isSSERequest(request)) {
      return await handleStreamingASGI(scope);
    }

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
async function requestToASGIScope(request, apiIndex = 0) {
  const url = new URL(request.url);

  // Remove API prefix from path (supports base paths)
  const pathAfterPrefix =
    apiIndex >= 0 ? url.pathname.slice(apiIndex + API_PREFIX.length) : "";
  const path = pathAfterPrefix || "/";
  let normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Auto-prefix API v1 routes when missing (leave docs/openapi as-is)
  const passthroughPrefixes = ["/openapi", "/docs", "/redoc", "/static"];
  const needsApiPrefix =
    !normalizedPath.startsWith("/api/") &&
    !passthroughPrefixes.some((p) => normalizedPath.startsWith(p));
  if (needsApiPrefix) {
    normalizedPath = `/api/v1${normalizedPath}`;
  }

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
    path: normalizedPath,
    query_string: url.search.slice(1), // Remove leading '?'
    headers: headers,
    body: body,
  };

  return scope;
}

function isSSERequest(request) {
  const accept = request.headers.get("accept") || "";
  return accept.includes("text/event-stream");
}

async function waitForPyodideReady(timeoutMs = 10000) {
  if (pyodideReady) return true;
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (pyodideReady) return true;
    await new Promise((r) => setTimeout(r, 100));
  }
  return pyodideReady;
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

async function handleStreamingASGI(scope) {
  const { status, headers, stream } = await callPyodideASGIStream(scope);

  const responseHeaders = new Headers();
  for (const [name, value] of headers) {
    const nameStr =
      typeof name === "string" ? name : new TextDecoder().decode(name);
    const valueStr =
      typeof value === "string" ? value : new TextDecoder().decode(value);
    responseHeaders.append(nameStr, valueStr);
  }

  if (!responseHeaders.has("Content-Type")) {
    responseHeaders.set("Content-Type", "text/event-stream");
  }
  if (!responseHeaders.has("Cache-Control")) {
    responseHeaders.set("Cache-Control", "no-cache");
  }
  if (!responseHeaders.has("Connection")) {
    responseHeaders.set("Connection", "keep-alive");
  }
  if (!responseHeaders.has("Access-Control-Allow-Origin")) {
    responseHeaders.set("Access-Control-Allow-Origin", "*");
  }

  return new Response(stream, {
    status: status,
    statusText: getStatusText(status),
    headers: responseHeaders,
  });
}

function callPyodideASGIStream(scope) {
  return new Promise((resolve, reject) => {
    if (!pyodidePort) {
      reject(new Error("Pyodide port not available"));
      return;
    }

    const requestId = Math.random().toString(36).substring(7);
    let handleResponse;
    let resolved = false;

    const stream = new ReadableStream({
      start(controller) {
        handleResponse = (event) => {
          const data = event.data;
          if (!data || data.requestId !== requestId) return;

          if (data.error) {
            controller.error(data.error);
            pyodidePort.removeEventListener("message", handleResponse);
            if (!resolved) {
              reject(new Error(data.error));
            }
            return;
          }

          if (data.type === "ASGI_STREAM_START") {
            resolved = true;
            resolve({
              status: data.response?.status ?? 200,
              headers: data.response?.headers ?? [],
              stream,
            });
            return;
          }

          if (data.type === "ASGI_STREAM_CHUNK") {
            let chunk = data.chunk;
            if (chunk instanceof ArrayBuffer) {
              chunk = new Uint8Array(chunk);
            } else if (!(chunk instanceof Uint8Array)) {
              chunk = new Uint8Array(chunk);
            }
            controller.enqueue(chunk);
            return;
          }

          if (data.type === "ASGI_STREAM_END") {
            pyodidePort.removeEventListener("message", handleResponse);
            controller.close();
            if (!resolved) {
              resolve({
                status: data.response?.status ?? 200,
                headers: data.response?.headers ?? [],
                stream,
              });
            }
          }
        };

        pyodidePort.addEventListener("message", handleResponse);

        pyodidePort.postMessage({
          type: "ASGI_STREAM_REQUEST",
          requestId: requestId,
          scope: scope,
        });
      },
      cancel() {
        if (handleResponse) {
          pyodidePort.removeEventListener("message", handleResponse);
        }
      },
    });
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
  if (body instanceof ReadableStream) {
    responseBody = body;
  } else if (typeof body === "string") {
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
