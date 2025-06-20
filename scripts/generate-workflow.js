#!/usr/bin/env node

import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Colors for console output
const colors = {
  reset: "\x1b[0m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

// Run command with promise
function runCommand(command, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    log(`🔧 Running: ${command} ${args.join(" ")}`, colors.cyan);

    const child = spawn(command, args, {
      stdio: "inherit",
      shell: true,
      ...options,
    });

    child.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Command failed with exit code ${code}`));
      }
    });

    child.on("error", reject);
  });
}

async function fullWorkflow() {
  log("🚀 Starting full page generation workflow...", colors.green);

  try {
    // Step 1: Generate TypeScript client from OpenAPI schema
    log(
      "\n📡 Step 1: Generating TypeScript client from OpenAPI schema...",
      colors.blue
    );
    await runCommand("node", ["scripts/generate-client.js"]);    // Step 2: Generate React pages using the TypeScript client
    log(
      "\n📝 Step 2: Generating React pages from TypeScript client...",
      colors.blue
    );
    await runCommand("python", [
      "scripts/generate-pages-enhanced.py",
      "--debug",
    ]);
    
    // Step 3: Generate App.tsx with automatic routing
    log(
      "\n🔀 Step 3: Generating App.tsx with automatic routing...",
      colors.blue
    );
    await runCommand("python", [
      "scripts/generate-app-routing.py",
      "--debug",
    ]);
    
    // Step 4: Optional - Run type checking
    log("\n🔍 Step 4: Running TypeScript type checking...", colors.blue);
    await runCommand("bun", ["run", "typecheck"], { cwd: "apps/frontend" });

    log("\n✅ Full workflow completed successfully!", colors.green);    log("📁 Generated files:", colors.cyan);
    log("  - TypeScript client: apps/frontend/src/client/", colors.cyan);
    log("  - React pages: apps/frontend/src/pages/", colors.cyan);
    log("  - App.tsx with routing: apps/frontend/src/App.tsx", colors.cyan);
  } catch (error) {
    log(`\n❌ Workflow failed: ${error.message}`, colors.red);
    process.exit(1);
  }
}

async function quickGenerate() {
  log(
    "⚡ Quick page generation (assumes client is already generated)...",
    colors.yellow
  );

  try {
    await runCommand("python", ["scripts/generate-pages-enhanced.py"]);
    log("✅ Quick generation completed!", colors.green);
  } catch (error) {
    log(`❌ Quick generation failed: ${error.message}`, colors.red);
    process.exit(1);
  }
}

// Parse command line arguments
const command = process.argv[2];

switch (command) {
  case "full":
    fullWorkflow();
    break;
  case "quick":
    quickGenerate();
    break;
  default:
    log("🔧 Page Generation Workflow", colors.green);
    log("");
    log("Usage:", colors.cyan);
    log(
      "  node scripts/generate-workflow.js full   # Full workflow: client + pages",
      colors.cyan
    );
    log(
      "  node scripts/generate-workflow.js quick  # Quick: pages only",
      colors.cyan
    );
    log("");
    log("Available commands:", colors.yellow);
    log(
      "  full  - Generate TypeScript client from OpenAPI + React pages",
      colors.yellow
    );
    log(
      "  quick - Generate React pages from existing TypeScript client",
      colors.yellow
    );
    break;
}
