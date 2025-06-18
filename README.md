# Project Documentation

Welcome to **React FastAPI Pyodide** – a framework that runs a real FastAPI backend entirely in the browser using Pyodide, seamlessly integrated with React Router.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Prerequisites](#prerequisites)
4. [Setup & Development](#setup--development)
5. [Building & Deployment](#building--deployment)
6. [Pyodide Integration](#pyodide-integration)
7. [API Reference](#api-reference)
8. [Frontend Overview](#frontend-overview)
9. [Contributing](#contributing)

---

## Project Overview
This project demonstrates how to run a full-featured FastAPI application in the browser using Pyodide, combined with a React frontend:
- **Backend**: Modular Python API in `src/backend/`, powered by FastAPI and SQLAlchemy, loaded into the browser via Pyodide.
- **Frontend**: React + Vite + React Router + Lucide icons, with components to load and interact with the Python API.
- **Persistence**: SQLite database and Python packages persist across sessions via IndexedDB (IDBFS).

## Directory Structure
```
root/
├── public/                 # Static assets and generated Python files
│   └── backend/            # Copied from src/backend before build/run
├── scripts/                # Build & deployment scripts
├── src/
│   ├── backend/            # Source Python API (FastAPI + SQLAlchemy)
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── v1/
│   └── frontend/           # React app source
│       ├── components/     # Reusable React components
│       └── pages/          # Page-level components
├── docs/                   # Project documentation (this file)
├── vite.config.ts          # Vite configuration
└── package.json            # Node.js project metadata
```

## Prerequisites
- Node.js 16+
- npm or yarn
- Modern browser (with WebAssembly support)

## Setup & Development
1. Clone repository:
   ```bash
   git clone <repo-url>
   cd react-fastapi-pyodide
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start development server (Pyodide mode):
   ```bash
   npm run dev:pyodide
   ```
4. Open http://localhost:5173 in your browser.

## Building & Deployment
- **Build for production** (Pyodide):
  ```bash
  npm run build:pyodide
  ```
- **Serve production build**:
  ```bash
  npm run prod:pyodide
  ```
- **GitHub Pages deployment**:
  ```bash
  npm run build:gh-pages
  npm run dev:gh-pages  # preview
  ```

## Pyodide Integration
1. `npm run copy-api` copies Python files from `src/backend/` to `public/backend/`.
2. `PyodideEngine` loads modules into IDBFS (`/persist/api`).
3. `/persist` is added to Python `sys.path`, enabling absolute imports (`import api.models.models`).
4. Python packages (FastAPI, SQLAlchemy, etc.) are installed via `micropip` and cached.

## API Reference
Once the app initializes, you can:
- View the Swagger UI at `/api/docs` (handled in the browser).
- Call endpoints under `/api/backend/v1/` (e.g., `/api/backend/v1/users`).

Example endpoints:
```http
GET  /api/backend/v1/users
POST /api/backend/v1/users
GET  /api/backend/v1/users/{user_id}
PUT  /api/backend/v1/users/{user_id}
DELETE /api/backend/v1/users/{user_id}
```

## Frontend Overview
- **`PyodideFileApp`**: Loads a Python file (main FastAPI app) and runs it.
- **`PyodideEndpointComponent`**: Renders a single endpoint result.
- **`PyodideSwaggerUI`**: Interactive API docs powered by Swagger UI.
- **`PyodideEngine`**: Manages Pyodide initialization, file loading, and endpoint registration.

## Contributing
1. Fork the repository and create your feature branch.
2. Make changes in `src/backend/` for Python or `src/frontend/` for React.
3. No emojis; use Lucide icons for UI.
4. Update tests and documentation if needed.
5. Submit a pull request.

---

Thank you for using **React FastAPI Pyodide**! If you encounter any issues or have suggestions, please open an issue on GitHub.
