import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import PyodideApp from "./pages/pyodide-demo/App";

// Register ASGI Service Worker for API interception and caching
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    // Use the correct base path for GitHub Pages
    const swPath = import.meta.env.BASE_URL + "pyodide-asgi-worker.js";
    navigator.serviceWorker
      .register(swPath, {
        scope: import.meta.env.BASE_URL,
      })
      .then((registration) => {
        console.log("✅ ASGI Service Worker registered:", registration);
      })
      .catch((error) => {
        console.warn("⚠️ ASGI Service Worker registration failed:", error);
      });
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PyodideApp />
  </StrictMode>
);
