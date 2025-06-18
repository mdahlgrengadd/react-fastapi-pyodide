#!/usr/bin/env node

/**
 * Script to run preview server with GitHub Pages configuration
 */

import { spawn } from "child_process";
import path from "path";

// Get the repository name for GitHub Pages
const repo =
  process.env.GITHUB_REPOSITORY?.split("/")[1] || "react-router-fastapi";
const basePath = `/${repo}/`;

console.log(`Starting preview server with GitHub Pages base path: ${basePath}`);

// Run the vite preview command with the correct base path
const viteProcess = spawn(
  "npx",
  ["vite", "preview", "--port", "3000", "--base", basePath],
  {
    stdio: "inherit",
    shell: true,
  }
);

viteProcess.on("close", (code) => {
  process.exit(code);
});
