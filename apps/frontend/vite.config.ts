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
        if (req.url && req.url.endsWith(".py")) {
          try {
            // Construct the file path relative to the public directory
            const filePath = path.join(process.cwd(), "../../public", req.url);

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
