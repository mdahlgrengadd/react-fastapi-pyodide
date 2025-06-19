import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"], // ESM only for modern environments
  dts: true, // Generate type definitions
  clean: true, // Clean output directory before build
  target: "es2020",
  external: ["pyodide"], // Pyodide is provided as peer dependency
  sourcemap: true,
  minify: true,
  splitting: false, // Keep as single bundle for simplicity
  treeshake: true,
});
