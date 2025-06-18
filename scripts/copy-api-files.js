#!/usr/bin/env node
// Script to copy Python backend files from src/backend to public/backend for deployment
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function copyDirectory(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const items = fs.readdirSync(src);

  for (const item of items) {
    const srcPath = path.join(src, item);
    const destPath = path.join(dest, item);
    if (fs.statSync(srcPath).isDirectory()) {
      // Skip __pycache__ directories
      if (item === "__pycache__") {
        continue;
      }

      copyDirectory(srcPath, destPath);
      // Create __init__.py in each subdirectory to make it a Python package
      const initPath = path.join(destPath, "__init__.py");
      if (!fs.existsSync(initPath)) {
        fs.writeFileSync(initPath, `# Package: ${item}\n`);
        console.log(`Created: ${initPath}`);
      }
    } else if (item.endsWith(".py")) {
      fs.copyFileSync(srcPath, destPath);
      console.log(`Copied: ${srcPath} -> ${destPath}`);
    }
  }
}

function main() {
  const srcApiDir = path.join(__dirname, "..", "src", "backend");
  const publicBackendDir = path.join(__dirname, "..", "public", "backend");

  // Create the destination directory structure
  if (!fs.existsSync(publicBackendDir)) {
    fs.mkdirSync(publicBackendDir, { recursive: true });
  }

  console.log("Copying Python API files to public/backend...");

  // Copy all Python files from src/backend to public/backend preserving directory structure
  copyDirectory(srcApiDir, publicBackendDir);
  // Create an __init__.py file in the root to make it a proper Python package
  const initContent = `# API package for Pyodide
# This directory structure is mirrored from src/backend/
`;

  fs.writeFileSync(path.join(publicBackendDir, "__init__.py"), initContent);
  console.log("Created: public/backend/__init__.py");

  console.log("Python API files copied successfully!");
  console.log(`Source: ${srcApiDir}`);
  console.log(`Destination: ${publicBackendDir}`);
}

// Always run main when this script is executed directly
main();
