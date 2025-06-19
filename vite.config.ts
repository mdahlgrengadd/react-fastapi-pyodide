import fs from "fs";
import path from "path";
import { visualizer } from "rollup-plugin-visualizer";
import { defineConfig } from "vite";

import react from "@vitejs/plugin-react";

// Plugin to serve Python files correctly
const pythonFilesPlugin = () => {
  return {
    name: "python-files",
    configureServer(server: any) {
      // Handle Python file serving
      server.middlewares.use("/backend", (req: any, res: any, next: any) => {
        if (req.url && req.url.endsWith(".py")) {
          try {
            // Construct the file path relative to the public directory
            const filePath = path.join(process.cwd(), "public", req.url);

            if (fs.existsSync(filePath)) {
              const content = fs.readFileSync(filePath, "utf-8");
              res.setHeader("Content-Type", "text/plain; charset=utf-8");
              res.setHeader("Cache-Control", "no-cache");
              res.end(content);
              return;
            }
          } catch (error) {
            console.error("Error serving Python file:", error);
          }
        }
        next();
      });

      // Handle API route redirection to inform client about Pyodide routing
      server.middlewares.use(
        "/api/backend",
        (req: any, res: any, next: any) => {
          // Return a helpful error message for API calls
          res.setHeader("Content-Type", "application/json");
          res.statusCode = 404;
          res.end(
            JSON.stringify({
              error: "API route not handled by server",
              message:
                "This API endpoint should be handled by the Pyodide engine in the browser. Make sure the Pyodide app is loaded and the API calls are being intercepted by the frontend.",
              path: req.url,
              suggestion:
                "This endpoint will work once the Pyodide FastAPI app is running in the browser.",
            })
          );
        }
      );
    },
  };
};

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    pythonFilesPlugin(),
    // Add bundle analyzer when ANALYZE=true
    ...(process.env.ANALYZE === "true"
      ? [
          visualizer({
            filename: "dist/stats.html",
            open: true,
            gzipSize: true,
            brotliSize: true,
          }),
        ]
      : []),
  ],
  base:
    process.env.GITHUB_PAGES === "true"
      ? `/${
          process.env.GITHUB_REPOSITORY?.split("/")[1] || "react-router-fastapi"
        }/`
      : "/",
  build: {
    // Enable code splitting for better performance
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunks for better caching
          "vendor-react": ["react", "react-dom"],
          "vendor-router": ["react-router-dom"],
          "vendor-query": ["react-query"],
          "vendor-ui": ["swagger-ui-react", "lucide-react"],
          // Only create chunks for dependencies that are actually used
        },
      },
    },
    // Add CommonJS wrapping for core-js-pure helpers so that default exports exist
    commonjsOptions: {
      include: [/core-js-pure/, /node_modules/],
    },
    // Enable compression and optimization
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: process.env.NODE_ENV === "production",
        drop_debugger: true,
      },
    },
    // Increase chunk size warning limit for Pyodide
    chunkSizeWarningLimit: 1000,
  },
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "react-query",
      "axios",
      // Ensure the Babel helpers used by swagger-ui-react get pre-bundled
      "core-js-pure/features/object/assign",
      "core-js-pure/features/object/assign.js",
      "core-js-pure/features/object/define-property",
      "core-js-pure/features/object/define-property.js",
      "core-js-pure/features/instance/bind",
      "core-js-pure/features/instance/bind.js",
      "core-js-pure/features/symbol",
      "core-js-pure/features/symbol.js",
      // Immutable library required by swagger-ui-react helpers
      "immutable",
      "immutable/dist/immutable.js",
      // Pre-bundle swagger-ui-react itself so that all its transitive deps
      // (immutable, deepmerge, core-js-pure helpers, etc.) are wrapped once
      "swagger-ui-react",
    ],
    // Don't pre-bundle large external dependencies
    exclude: ["lucide-react"],
  },
  server: {
    // Development server optimizations
    fs: {
      strict: false,
    },
    // Optimize HMR
    hmr: {
      overlay: false,
    },
    // Reduce latency
    headers: {
      "Cache-Control": "no-cache",
    },
    // Enable compression
    middlewareMode: false, // Optimize file watching
    watch: {
      usePolling: false,
      interval: 100,
    },
  },
});
