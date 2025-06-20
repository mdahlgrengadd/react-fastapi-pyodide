#!/usr/bin/env node

import { spawn } from 'child_process';
import path from 'path';
import http from 'http';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

// Get project paths
const scriptDir = __dirname;
const repoRoot = path.dirname(scriptDir);
const backendDir = path.join(repoRoot, 'apps', 'backend', 'src');

// Check if server is running
function checkServer() {
  return new Promise((resolve) => {
    const request = http.get('http://localhost:8000/docs', { timeout: 3000 }, (res) => {
      resolve(res.statusCode === 200);
    });
    
    request.on('error', () => resolve(false));
    request.on('timeout', () => {
      request.destroy();
      resolve(false);
    });
  });
}

// Find Python executable
function findPython() {
  const pythonCommands = ['python', 'python3', 'py'];
  
  return new Promise((resolve) => {
    let tried = 0;
    
    pythonCommands.forEach((cmd) => {
      const child = spawn(cmd, ['--version'], { stdio: 'pipe' });
      
      child.on('close', (code) => {
        tried++;
        if (code === 0) {
          resolve(cmd);
        } else if (tried === pythonCommands.length) {
          resolve(null);
        }
      });
      
      child.on('error', () => {
        tried++;
        if (tried === pythonCommands.length) {
          resolve(null);
        }
      });
    });
  });
}

// Start FastAPI server
async function startServer() {
  log('🔍 Checking if server is already running...', colors.cyan);
  
  const isRunning = await checkServer();
  if (isRunning) {
    log('✅ Server is already running at http://localhost:8000', colors.green);
    log('📖 API docs: http://localhost:8000/docs', colors.cyan);
    return;
  }
  
  log('🐍 Finding Python executable...', colors.cyan);
  const pythonCmd = await findPython();
  
  if (!pythonCmd) {
    log('❌ Python not found!', colors.red);
    log('Please install Python and make sure it\'s in your PATH', colors.yellow);
    log('Or install from: https://python.org/downloads/', colors.yellow);
    log('', colors.yellow);
    log('💡 Alternative: Use a Python virtual environment', colors.cyan);
    log('  python -m venv venv', colors.cyan);
    log('  venv\\Scripts\\activate  # Windows', colors.cyan);
    log('  source venv/bin/activate  # macOS/Linux', colors.cyan);
    process.exit(1);
  }
  
  log(`✅ Found Python: ${pythonCmd}`, colors.green);
  
  log('🚀 Starting FastAPI server...', colors.cyan);
  log(`📁 Working directory: ${backendDir}`, colors.blue);
  log('🌐 Server will be available at: http://localhost:8000', colors.blue);
  log('📖 API docs will be at: http://localhost:8000/docs', colors.blue);
  log('', colors.reset);
  log('Press Ctrl+C to stop the server', colors.yellow);
  log('', colors.reset);
  
  // Start the server
  const server = spawn(pythonCmd, [
    '-m', 'uvicorn', 
    'app.app_main:app', 
    '--host', '0.0.0.0', 
    '--port', '8000',
    '--reload'
  ], {
    cwd: backendDir,
    stdio: 'inherit'
  });
  
  server.on('error', (error) => {
    log(`❌ Failed to start server: ${error.message}`, colors.red);
    process.exit(1);
  });
  
  // Handle graceful shutdown
  process.on('SIGINT', () => {
    log('\n🛑 Shutting down server...', colors.yellow);
    server.kill('SIGINT');
    process.exit(0);
  });
  
  process.on('SIGTERM', () => {
    log('\n🛑 Shutting down server...', colors.yellow);
    server.kill('SIGTERM');
    process.exit(0);
  });
}

// Run the server starter
startServer().catch((error) => {
  log(`❌ Fatal error: ${error.message}`, colors.red);
  process.exit(1);
}); 