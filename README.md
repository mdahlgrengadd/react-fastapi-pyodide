# React FastAPI Pyodide

A full-stack web application with **React frontend**, **FastAPI backend**, and **Pyodide bridge** for running Python in the browser.

## ✨ Features

- 🚀 **Auto-generated React pages** from FastAPI OpenAPI schema
- 🔗 **Type-safe API client** with `@hey-api/openapi-ts`
- 🐍 **Python in browser** via Pyodide bridge
- ⚡ **Fast builds** with Bun
- 📱 **Modern UI** with Tailwind CSS
- 🔄 **Live reloading** development server

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** 
- **Bun** (recommended) or npm

### Setup

```bash
# Clone and install
git clone <your-repo>
cd react-fastapi-pyodide
bun install

# Start backend server
bun run dev:backend

# Generate TypeScript client + React pages
bun run generate:pages:enhanced

# Start frontend
bun run dev:frontend
```

Visit `http://localhost:3000` 🎉

## 📁 Project Structure

```
├── apps/
│   ├── frontend/          # React app with Vite
│   └── backend/           # FastAPI application
├── packages/
│   ├── pyodide-bridge-ts/ # TypeScript bridge package
│   └── pyodide-bridge-py/ # Python bridge package
└── scripts/               # Build and generation scripts
```

## 🛠️ Development

### Backend
```bash
bun run dev:backend        # Start FastAPI server
```

### Frontend
```bash
bun run dev:frontend       # Start React dev server
bun run generate:pages:enhanced  # Generate pages from API
```

### Page Generation

**Enhanced Workflow** (Recommended):
```bash
bun run generate:pages:enhanced  # Full: client + pages
bun run generate:pages:quick     # Quick: pages only
```

**Original Generator**:
```bash
bun run generate:pages          # Python-based generator
```

## 📄 Generated Pages

The enhanced generator creates React pages from your FastAPI endpoints:

- **UsersPage** → `/users`, `/users/:id`
- **PostsPage** → `/posts`, `/posts/:id` 
- **DashboardPage** → `/dashboard`
- **AnalyticsPage** → `/analytics`

### Features:
- ✅ **Type-safe API calls** using generated client
- ✅ **List + Detail views** with React Router
- ✅ **Loading states** and error handling
- ✅ **Modern UI** with Tailwind CSS

## 🔧 Build & Deploy

```bash
# Build everything
bun run build

# Build individual parts
bun run build:frontend
bun run build:backend
bun run build:packages
```

## 📚 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React, TypeScript, Vite, Tailwind CSS |
| **Backend** | FastAPI, Python, SQLAlchemy |
| **Bridge** | Pyodide, Custom TypeScript/Python packages |
| **API Client** | `@hey-api/openapi-ts`, React Query |
| **Build** | Bun, Vite |

## 🎯 Key Scripts

| Command | Description |
|---------|-------------|
| `bun run dev:frontend` | Start React dev server |
| `bun run dev:backend` | Start FastAPI server |
| `bun run generate:pages:enhanced` | Generate pages from API |
| `bun run gen:client` | Generate TypeScript client |
| `bun run build` | Build for production |
| `bun run test` | Run all tests |

## 📖 Documentation

- **Page Generation**: See `PAGE_GENERATION_APPROACHES.md`
- **API Docs**: `http://localhost:8000/docs` (when backend running)
- **Package Docs**: Individual `README.md` in each package

## 🤝 Development Workflow

1. **Start backend**: `bun run dev:backend`
2. **Generate pages**: `bun run generate:pages:enhanced` 
3. **Start frontend**: `bun run dev:frontend`
4. **Make changes** to backend APIs
5. **Regenerate pages**: `bun run generate:pages:quick`

## 📦 Packages

### Frontend Dependencies
- `react` - UI framework
- `react-router-dom` - Routing
- `react-query` - Data fetching
- `@hey-api/openapi-ts` - API client generation

### Backend Dependencies  
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM
- `pydantic` - Data validation

## 🔍 Troubleshooting

**Page generation fails?**
- Ensure backend is running on `http://localhost:8000`
- Check OpenAPI schema at `http://localhost:8000/openapi.json`

**TypeScript errors?**  
- Run `bun run generate:pages:enhanced` to regenerate client
- Check `apps/frontend/src/client/` for generated types

**Build fails?**
- Ensure all dependencies: `bun install`
- Clean build: `rm -rf node_modules/.cache`

## 📄 License

MIT License - see `LICENSE` file.
