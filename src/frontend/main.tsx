import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import PyodideApp from "./pages/pyodide-demo/App";

// Register ASGI Service Worker for API interception and caching
// Register as early as possible so API calls during initial render
// are already intercepted instead of hitting the Vite fallback.
const registerServiceWorker = () => {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  const baseScope = import.meta.env.BASE_URL || "/";
  const swPath = `${baseScope}pyodide-asgi-worker.js`.replace(/\/+/g, "/");

  navigator.serviceWorker
    .register(swPath, {
      scope: baseScope,
    })
    .then((registration) => {
      console.log("ASGI Service Worker registered:", registration);
    })
    .catch((error) => {
      console.warn("ASGI Service Worker registration failed:", error);
    });
};

if (document.readyState === "complete" || document.readyState === "interactive") {
  registerServiceWorker();
} else {
  window.addEventListener("DOMContentLoaded", registerServiceWorker);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PyodideApp />
  </StrictMode>
);
