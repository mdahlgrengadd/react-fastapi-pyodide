#!/usr/bin/env node

import fs from "fs";
import path from "path";
import { spawn } from "child_process";
import http from "http";
import { fileURLToPath } from "url";

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const CONFIG = {
  specUrl: "http://localhost:8000/openapi.json",
  serverCheckUrl: "http://localhost:8000/docs",
  serverHost: "0.0.0.0",
  serverPort: 8000,
  maxRetries: 10,
  retryDelay: 2000,
};

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

// Get project paths
const scriptDir = __dirname;
const repoRoot = path.dirname(scriptDir);
const backendDir = path.join(repoRoot, "apps", "backend", "src");
const outDir = path.join(repoRoot, "apps", "frontend", "src", "client");
const tmpSpec = path.join(scriptDir, "openapi.json");

// Check if server is running
function checkServer() {
  return new Promise((resolve) => {
    const request = http.get(
      CONFIG.serverCheckUrl,
      { timeout: 5000 },
      (res) => {
        resolve(res.statusCode === 200);
      }
    );

    request.on("error", () => resolve(false));
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
  });
}

// Download OpenAPI spec
function downloadSpec() {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(tmpSpec);

    const request = http.get(CONFIG.specUrl, (response) => {
      if (response.statusCode !== 200) {
        reject(
          new Error(`HTTP ${response.statusCode}: ${response.statusMessage}`)
        );
        return;
      }

      response.pipe(file);

      file.on("finish", () => {
        file.close();
        resolve();
      });
    });

    request.on("error", reject);
    file.on("error", reject);
  });
}

// Run command with promise
function runCommand(command, args = [], options = {}) {
  return new Promise((resolve, reject) => {
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

// Generate TypeScript client
async function generateClient() {
  log("🔍 Checking if FastAPI server is running...", colors.cyan);

  const isServerRunning = await checkServer();

  if (!isServerRunning) {
    log("❌ FastAPI server is not running!", colors.red);
    log("Please start the server first:", colors.yellow);
    log("  npm run start:server", colors.yellow);
    log("  # or manually:", colors.yellow);
    log("  cd apps/backend/src", colors.yellow);
    log(
      "  python -m uvicorn app.app_main:app --host 0.0.0.0 --port 8000",
      colors.yellow
    );
    process.exit(1);
  }

  log("✅ FastAPI server is running!", colors.green);

  try {
    log("📥 Downloading OpenAPI schema...", colors.cyan);
    await downloadSpec();
    log("✅ OpenAPI schema downloaded", colors.green);

    log("📂 Creating output directory...", colors.cyan);
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }
    log("🛠️ Generating TypeScript SDK...", colors.cyan);
    await runCommand("bun", [
      "x",
      "@hey-api/openapi-ts",
      "-i",
      tmpSpec,
      "-o",
      outDir,
      "-c",
      "legacy/fetch",
    ]);

    log("✅ Client generated successfully!", colors.green);
  } catch (error) {
    log(`❌ Error: ${error.message}`, colors.red);
    process.exit(1);
  } finally {
    // Clean up temp file
    if (fs.existsSync(tmpSpec)) {
      fs.unlinkSync(tmpSpec);
    }
  }

  log("", colors.green);
  log("🎉 TypeScript client generated successfully!", colors.green);
  log(`📁 Generated files are in: apps/frontend/src/client/`, colors.cyan);
  log(
    `📖 Import functions like: import { getUsers, getPosts } from '../client'`,
    colors.cyan
  );
}

// Run the generator
generateClient().catch((error) => {
  log(`❌ Fatal error: ${error.message}`, colors.red);
  process.exit(1);
});
