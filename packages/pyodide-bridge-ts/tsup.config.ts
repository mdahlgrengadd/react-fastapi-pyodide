import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"], // ESM only for modern environments
  dts: {
    compilerOptions: {
      module: "es2020",
      moduleResolution: "node",
      jsx: "react-jsx"
    }
  }, // Generate type definitions with custom options
  clean: true, // Clean output directory before build
  target: "es2020",
  external: ["pyodide", "react", "react-dom", "react-router-dom", "react-query"], // External dependencies
  sourcemap: true,
  minify: false, // Disable minification to avoid issues with dynamic imports
  splitting: false, // Keep as single bundle for simplicity
  treeshake: true,
  esbuildOptions(options) {
    options.jsx = 'automatic';
  },
});
