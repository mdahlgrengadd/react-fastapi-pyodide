# Packages & Migration Guide

This document provides a comprehensive overview of the **React FastAPI Pyodide** monorepo structure, the bridge packages that enable seamless Python-TypeScript integration, and the migration from the original single-app structure.

## 📁 Monorepo Structure

The project has been migrated from a single application to a structured monorepo with separate packages and applications:

```
react-fastapi-pyodide/
├── packages/                    # Reusable bridge packages
│   ├── pyodide-bridge-ts/      # TypeScript bridge package
│   └── pyodide-bridge-py/      # Python bridge package
├── apps/                       # Application implementations
│   ├── frontend/               # React application
│   └── backend/                # FastAPI backend
├── scripts/                    # Build and utility scripts
└── src/                        # Legacy source code (being phased out)
```

## 🌉 Bridge Packages

The core innovation of this project lies in the **bridge packages** that enable seamless communication between Python (Pyodide) and TypeScript in the browser.

### 🔧 `pyodide-bridge-py`

**Python FastAPI Bridge for Pyodide Environments**

A Python package that provides utilities and adapters for running FastAPI applications efficiently within Pyodide.

#### Features
- **FastAPI Optimization**: Custom middleware and routing optimizations for Pyodide
- **Memory Management**: Efficient handling of Python objects in WASM environment
- **Error Handling**: Robust error propagation between Python and JavaScript
- **Type Safety**: Pydantic integration for request/response validation

#### Key Components
- `fastapi_bridge.py` - Main bridge implementation
- `utils.py` - Utility functions for Pyodide integration
- `__init__.py` - Package exports and initialization

#### Installation
```bash
pip install pyodide-bridge-py
```

#### Usage
```python
from pyodide_bridge import FastAPIBridge

# Create bridge instance
bridge = FastAPIBridge()

# Register FastAPI app
bridge.register_app(app)
```

### 🎯 `pyodide-bridge-ts`

**TypeScript Bridge for Pyodide FastAPI Integration**

A TypeScript package that provides a clean, type-safe interface for interacting with Python FastAPI applications running in Pyodide.

#### Features
- **Type Safety**: Full TypeScript support with comprehensive type definitions
- **Streaming Support**: Real-time streaming of endpoint responses
- **Router Integration**: Native React Router integration
- **Error Handling**: Robust error handling and propagation
- **Event System**: Event-driven architecture for real-time updates

#### Key Components
- `bridge.ts` - Main Bridge class implementation (620 lines)
- `types.ts` - Comprehensive type definitions (165 lines)
- `index.ts` - Package exports and public API

#### Installation
```bash
npm install pyodide-bridge-ts
```

#### Usage
```typescript
import { Bridge } from 'pyodide-bridge-ts';

// Initialize bridge
const bridge = new Bridge({
  pyodide: pyodideInstance,
  persistence: true
});

// Call Python endpoints
const response = await bridge.call('/api/users', {
  method: 'GET'
});
```

## 🎯 Applications

### Frontend App (`apps/frontend/`)

A React application that demonstrates the bridge packages in action.

**Dependencies:**
- `pyodide-bridge-ts`: Workspace package for Python integration
- `react` & `react-dom`: React framework
- `react-router-dom`: Client-side routing
- `pyodide`: WebAssembly Python runtime

**Key Features:**
- TypeScript integration with the bridge package
- Modern React with hooks and functional components
- Tailwind CSS for styling
- Vite for fast development and building

### Backend App (`apps/backend/`)

A FastAPI application optimized for Pyodide execution.

**Dependencies:**
- `pyodide-bridge-py`: Workspace package for Pyodide optimization
- `fastapi`: Modern Python web framework
- `sqlalchemy`: ORM for database operations
- `pydantic`: Data validation and serialization

## 🔄 Migration Summary

### Before: Monolithic Structure
```
src/
├── backend/           # FastAPI code
├── frontend/          # React code
└── backend-simple/    # Alternative backend
```

### After: Monorepo with Bridge Packages
```
packages/              # Reusable packages
├── pyodide-bridge-ts/ # TypeScript bridge
└── pyodide-bridge-py/ # Python bridge

apps/                  # Applications
├── frontend/          # React app using bridge-ts
└── backend/           # FastAPI app using bridge-py
```

### Key Migration Benefits

1. **Separation of Concerns**: Bridge logic is isolated from application code
2. **Reusability**: Packages can be used in other projects
3. **Type Safety**: Better TypeScript integration across the stack
4. **Maintainability**: Smaller, focused codebases
5. **Testing**: Independent testing of bridge functionality
6. **Versioning**: Independent versioning of packages and apps

### Breaking Changes

1. **Import Paths**: Updated to use workspace packages
   ```typescript
   // Before
   import { PyodideEngine } from '../services/pyodide';
   
   // After
   import { Bridge } from 'pyodide-bridge-ts';
   ```

2. **Configuration**: Centralized configuration in root `package.json`
3. **Build Process**: Updated to handle multi-package builds
4. **Scripts**: New npm scripts for package and app management

## 🚀 Getting Started

### Prerequisites
- Node.js ≥18.0.0
- Python ≥3.10
- Modern browser with WebAssembly support

### Installation
```bash
# Install all dependencies
npm install

# Build packages
npm run build:packages

# Build applications
npm run build:apps
```

### Development
```bash
# Start frontend development
npm run dev:frontend

# Start backend development (CPython)
npm run dev:backend

# Run tests
npm run test

# Lint and format
npm run lint:fix
```

## 📦 Package Management

### Building Packages
```bash
# Build all packages
npm run build:packages

# Build TypeScript package only
npm run build:ts

# Build Python package only
npm run build:py
```

### Testing
```bash
# Test all packages
npm run test:packages

# Test TypeScript package
npm run test:ts

# Test Python package
npm run test:py
```

### Publishing
```bash
# TypeScript package
cd packages/pyodide-bridge-ts
npm publish

# Python package
cd packages/pyodide-bridge-py
python -m build
twine upload dist/*
```

## 🔧 Configuration

### Workspace Configuration
The root `package.json` defines workspaces:
```json
{
  "workspaces": [
    "packages/*",
    "apps/*"
  ]
}
```

### TypeScript Package (`pyodide-bridge-ts`)
- **Build Tool**: tsup for fast bundling
- **Testing**: Vitest for unit tests
- **Linting**: ESLint with TypeScript rules

### Python Package (`pyodide-bridge-py`)
- **Build Tool**: setuptools with pyproject.toml
- **Testing**: pytest with async support
- **Code Quality**: black, isort, mypy

## 🤝 Contributing

1. **Package Development**: Work in `packages/` for bridge functionality
2. **Application Development**: Work in `apps/` for application features
3. **Testing**: Ensure both package and integration tests pass
4. **Documentation**: Update this README for structural changes

### Development Workflow
1. Make changes in relevant package/app
2. Build packages: `npm run build:packages`
3. Test changes: `npm run test`
4. Lint code: `npm run lint:fix`
5. Submit pull request

## 📄 License

MIT - See LICENSE file for details.

---

This migration represents a significant architectural improvement, providing better separation of concerns, reusability, and maintainability while preserving all existing functionality. 