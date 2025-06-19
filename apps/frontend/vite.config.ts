/* eslint-disable @typescript-eslint/no-explicit-any */
import fs from 'fs';
import path from 'path';
import { defineConfig } from 'vite';

import react from '@vitejs/plugin-react';

// Plugin to serve Python files correctly for Pyodide
const pythonFilesPlugin = () => {
  return {
    name: "python-files",
    configureServer(server: any) {
      // Handle Python file serving
      server.middlewares.use("/backend", (req: any, res: any, next: any) => {
        if (req.url) {
          // Support .py, .json and other text files inside backend folder
          const ext = path.extname(req.url);
          const isText = [".py", ".json", ".txt"].includes(ext);
          if (!isText) {
            return next();
          }
          try {
            // Construct the file path relative to the public directory
            const filePath = path.join(
              process.cwd(),
              "../../public/backend",
              req.url.replace(/^\//, "")
            );

            console.log(
              "[pythonFilesPlugin] req.url",
              req.url,
              "resolved",
              filePath
            );

            if (fs.existsSync(filePath)) {
              const content = fs.readFileSync(filePath, "utf-8");
              const mime = ext === ".json" ? "application/json" : "text/plain";
              res.setHeader("Content-Type", `${mime}; charset=utf-8`);
              res.setHeader("Cache-Control", "no-cache");
              res.end(content);
              return;
            }
          } catch (error) {
            console.error("Error serving Python file:", error);
          }
          // Continue to next middleware if file not handled
          return next();
        }
      });
    },
  };
};

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), pythonFilesPlugin()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
