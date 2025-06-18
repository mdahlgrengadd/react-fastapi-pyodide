import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import PyodideApp from "./pages/pyodide-demo/App";

// Register Service Worker for better caching
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    // Use the correct base path for GitHub Pages
    const swPath = import.meta.env.BASE_URL + "sw.js";
    navigator.serviceWorker
      .register(swPath)
      .then((registration) => {
        console.log(" Service Worker registered:", registration);
      })
      .catch((error) => {
        console.warn(" Service Worker registration failed:", error);
      });
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PyodideApp />
  </StrictMode>
);
