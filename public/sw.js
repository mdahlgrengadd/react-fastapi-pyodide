// Service Worker for PyodideFastAPI Demo
const CACHE_NAME = "pyodide-fastapi-v6";

// Get the base path from the service worker URL
const basePath = self.location.pathname.replace("/sw.js", "") || "";

const STATIC_RESOURCES = [
  basePath + "/",
  basePath + "/backend/v1/main.py",
  basePath + "/backend/app/core/bridge.py",
  basePath + "/backend/app/core/settings.py",
  basePath + "/backend/app/core/logging.py",
  basePath + "/backend/app/core/security.py",
  basePath + "/backend/app/core/runtime.py",
  basePath + "/backend/app/core/__init__.py",
  basePath + "/backend/app/db/base.py",
  basePath + "/backend/app/db/session.py",
  basePath + "/backend/app/db/init_db.py",
  basePath + "/backend/app/db/__init__.py",
  basePath + "/backend/app/domains/users/models.py",
  basePath + "/backend/app/domains/users/schemas.py",
  basePath + "/backend/app/domains/users/__init__.py",
  basePath + "/backend/app/domains/posts/models.py",
  basePath + "/backend/app/domains/posts/schemas.py",
  basePath + "/backend/app/domains/posts/__init__.py",
  basePath + "/backend/app/domains/__init__.py",
  basePath + "/backend/app/__init__.py",
  basePath + "/backend/v1/__init__.py",
  basePath + "/backend/__init__.py",
  basePath + "/vite.svg",
];

// Pyodide CDN resources to cache
const PYODIDE_RESOURCES = [
  "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js",
  "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.asm.wasm",
  "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/python_stdlib.zip",
];

// Install event - cache essential resources
self.addEventListener("install", (event) => {
  console.log(" Service Worker: Installing...");
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log(" Service Worker: Caching static resources");
        return cache.addAll(STATIC_RESOURCES);
      })
      .then(() => {
        console.log(" Service Worker: Installation complete");
        self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  console.log("Service Worker: Activating...");
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log(" Service Worker: Deleting old cache:", cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log(" Service Worker: Activation complete");
        self.clients.claim();
      })
  );
});

// Fetch event - implement caching strategies
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  // Strategy 1: Cache Python files and static resources (Cache First)
  if (
    request.url.endsWith(".py") ||
    request.url.includes("/backend/") ||
    request.url.endsWith(".svg")
  ) {
    event.respondWith(
      caches.match(request).then((response) => {
        if (response) {
          console.log(" Service Worker: Serving from cache:", request.url);
          return response;
        }
        console.log(" Service Worker: Fetching and caching:", request.url);
        return fetch(request).then((response) => {
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        });
      })
    );
  }

  // Strategy 2: Pyodide CDN resources (Cache First with long TTL)
  else if (
    url.hostname === "cdn.jsdelivr.net" &&
    url.pathname.includes("pyodide")
  ) {
    event.respondWith(
      caches.match(request).then((response) => {
        if (response) {
          console.log(
            " Service Worker: Serving Pyodide from cache:",
            request.url
          );
          return response;
        }
        console.log(
          " Service Worker: Fetching and caching Pyodide:",
          request.url
        );
        return fetch(request).then((response) => {
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        });
      })
    );
  }

  // Strategy 3: Everything else (Network First)
  else {
    event.respondWith(
      fetch(request).catch(() => {
        return caches.match(request);
      })
    );
  }
});

// Handle messages from main thread
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
