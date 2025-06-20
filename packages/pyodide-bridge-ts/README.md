# pyodide-bridge-ts

A TypeScript bridge package that provides seamless integration between React applications and FastAPI backends running in Pyodide (WebAssembly Python).

## 🚀 Features

- **🔒 Type Safety**: Full TypeScript support with comprehensive type definitions
- **🌊 Streaming Support**: Real-time streaming of endpoint responses  
- **🧭 Router Integration**: Native React Router integration
- **🚨 Error Handling**: Robust error handling and propagation
- **📡 Event System**: Event-driven architecture for real-time updates
- **💾 Persistence**: IndexedDB persistence for Python packages and data
- **⚡ Performance**: Optimized for browser-based Python execution

## 📦 Installation

```bash
npm install pyodide-bridge-ts
```

### Peer Dependencies
- `pyodide >= 0.27.0`

## 🎯 Quick Start

```typescript
import { Bridge } from 'pyodide-bridge-ts';
import { loadPyodide } from 'pyodide';

// Initialize Pyodide
const pyodide = await loadPyodide();

// Create bridge instance
const bridge = new Bridge({
  pyodide,
  persistence: true,
  baseUrl: '/api'
});

// Initialize the bridge
await bridge.init();

// Call a Python endpoint
const response = await bridge.call('/users', {
  method: 'GET'
});

console.log(response.data);
```

## 📚 API Reference

### Bridge Class

The main class for managing Pyodide-FastAPI integration.

#### Constructor

```typescript
new Bridge(config: BridgeConfig)
```

**BridgeConfig Options:**
```typescript
interface BridgeConfig {
  pyodide: PyodideInterface;          // Pyodide instance
  persistence?: boolean;              // Enable IndexedDB persistence
  baseUrl?: string;                   // API base URL
  timeout?: number;                   // Request timeout (ms)
  retries?: number;                   // Number of retries
  debug?: boolean;                    // Enable debug logging
  packages?: string[];                // Python packages to install
  onProgress?: (progress: number) => void; // Installation progress callback
}
```

#### Methods

##### `init(): Promise<void>`
Initialize the bridge and set up the Pyodide environment.

```typescript
await bridge.init();
```

##### `call(path: string, params?: CallParams): Promise<ApiResponse>`
Make a call to a Python endpoint.

```typescript
const response = await bridge.call('/users/123', {
  method: 'GET',
  headers: { 'Authorization': 'Bearer token' }
});
```

**CallParams:**
```typescript
interface CallParams {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: any;
  query?: Record<string, string>;
  timeout?: number;
}
```

##### `stream(path: string, params?: CallParams): AsyncGenerator<StreamChunk>`
Stream responses from a Python endpoint.

```typescript
for await (const chunk of bridge.stream('/data/stream')) {
  console.log('Received:', chunk.data);
}
```

##### `typed<T>(): TypedCall<T>`
Create a typed caller for specific endpoint schemas.

```typescript
interface User {
  id: number;
  name: string;
  email: string;
}

const typedBridge = bridge.typed<User>();
const user = await typedBridge.call('/users/123');
// user is typed as User
```

##### `loadFile(path: string): Promise<void>`
Load a Python file into the Pyodide environment.

```typescript
await bridge.loadFile('/backend/main.py');
```

##### `installPackages(packages: string[]): Promise<void>`
Install Python packages via micropip.

```typescript
await bridge.installPackages(['requests', 'pandas']);
```

##### `getStorageInfo(): Promise<StorageInfo>`
Get information about persistent storage usage.

```typescript
const info = await bridge.getStorageInfo();
console.log(`Used: ${info.used} bytes`);
```

### Event System

The bridge emits events for monitoring and debugging:

```typescript
bridge.on('init:start', () => console.log('Initialization started'));
bridge.on('init:complete', () => console.log('Initialization complete'));
bridge.on('call:start', (path) => console.log(`Calling ${path}`));
bridge.on('call:complete', (path, response) => console.log(`Response from ${path}`));
bridge.on('error', (error) => console.error('Bridge error:', error));
```

### Error Handling

The package provides specific error types:

```typescript
import { BridgeError, InitializationError, CallError } from 'pyodide-bridge-ts';

try {
  await bridge.call('/api/endpoint');
} catch (error) {
  if (error instanceof CallError) {
    console.error('API call failed:', error.message);
    console.error('Status:', error.status);
  } else if (error instanceof InitializationError) {
    console.error('Bridge initialization failed:', error.message);
  }
}
```

## 🎛️ Configuration Examples

### Basic Setup
```typescript
const bridge = new Bridge({
  pyodide: await loadPyodide(),
  baseUrl: '/api'
});
```

### Advanced Setup with Persistence
```typescript
const bridge = new Bridge({
  pyodide: await loadPyodide(),
  persistence: true,
  baseUrl: '/api',
  timeout: 30000,
  retries: 3,
  debug: true,
  packages: ['fastapi', 'sqlalchemy'],
  onProgress: (progress) => {
    console.log(`Installation progress: ${progress}%`);
  }
});
```

### React Integration
```typescript
import React, { useEffect, useState } from 'react';
import { Bridge } from 'pyodide-bridge-ts';

function App() {
  const [bridge, setBridge] = useState<Bridge | null>(null);
  const [users, setUsers] = useState([]);

  useEffect(() => {
    const initBridge = async () => {
      const pyodide = await loadPyodide();
      const bridgeInstance = new Bridge({ pyodide });
      await bridgeInstance.init();
      setBridge(bridgeInstance);
    };
    
    initBridge();
  }, []);

  const fetchUsers = async () => {
    if (!bridge) return;
    
    try {
      const response = await bridge.call('/users');
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  return (
    <div>
      <button onClick={fetchUsers} disabled={!bridge}>
        Fetch Users
      </button>
      {/* Render users */}
    </div>
  );
}
```

## 🔧 Development

### Building
```bash
npm run build
```

### Testing
```bash
npm run test
```

### Type Checking
```bash
npm run typecheck
```

### Linting
```bash
npm run lint
npm run lint:fix
```

## 🏗️ Architecture

The bridge consists of several key components:

- **Bridge**: Main orchestrator class
- **PyodideEngine**: Low-level Pyodide management
- **APIManager**: HTTP-like API interface
- **EndpointExecutor**: Python code execution
- **PackageManager**: Python package installation
- **Persistence**: IndexedDB storage management

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT - See [LICENSE](../../LICENSE) file for details.

## 🔗 Related Packages

- [`pyodide-bridge-py`](../pyodide-bridge-py/) - Python bridge for FastAPI integration
- [`pyodide`](https://pyodide.org/) - Python runtime for WebAssembly

## ✨ New: BridgeRouter Component

The `BridgeRouter` component encapsulates all the bridge initialization complexity, making it incredibly easy to get started:

### Before (Manual Setup)
```tsx
// 100+ lines of complex bridge setup...
const [bridge] = useState(() => new Bridge({ ... }));
const [status, setStatus] = useState("Initializing...");
// ... lots of useEffect logic for initialization
// ... manual interceptor setup
// ... manual QueryClient setup
```

### After (BridgeRouter)
```tsx
import { BridgeRouter } from 'pyodide-bridge-ts';
import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BridgeRouter
      packages={["fastapi", "pydantic", "sqlalchemy"]}
      debug={true}
      showDevtools={process.env.NODE_ENV === 'development'}
    >
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/users" element={<UsersPage />} />
      </Routes>
    </BridgeRouter>
  );
}
```

**That's it!** 🎉 The `BridgeRouter` handles:
- ✅ Pyodide initialization
- ✅ Backend file loading  
- ✅ FastAPI server startup
- ✅ Request interceptor setup
- ✅ React Query configuration
- ✅ Loading and error states
- ✅ Automatic cleanup

## BridgeRouter API

```tsx
interface BridgeRouterProps {
  children: ReactNode;
  
  // Bridge Configuration
  packages?: string[];                    // Default: ["fastapi", "pydantic", "sqlalchemy", "httpx"]
  debug?: boolean;                        // Default: true
  backendFileListUrl?: string;           // Default: "/backend/backend_filelist.json"
  backendFilesUrl?: string;              // Default: "/backend"
  apiPrefix?: string;                    // Default: "/api/v1"
  
  // UI Customization
  loadingComponent?: React.ComponentType<{ status: string }>;
  errorComponent?: React.ComponentType<{ error: string }>;
  
  // React Query
  queryClientOptions?: QueryClientOptions;
  showDevtools?: boolean;                // Default: false
}
```

## Custom Components

You can customize the loading and error screens:

```tsx
const CustomLoader = ({ status }) => (
  <div className="my-custom-loader">
    <h1>Loading: {status}</h1>
  </div>
);

const CustomError = ({ error }) => (
  <div className="my-error-screen">
    <h1>Oops! {error}</h1>
  </div>
);

<BridgeRouter
  loadingComponent={CustomLoader}
  errorComponent={CustomError}
>
  {/* Your routes */}
</BridgeRouter>
```

## Usage with Generated Pages

Works perfectly with the generated page components:

```tsx
// Generated by scripts/generate-pages-enhanced.py
import { UsersPage, PostsPage } from './pages';

function App() {
  return (
    <BridgeRouter>
      <Routes>
        <Route path="/users" element={<UsersPage />} />
        <Route path="/users/:id" element={<UsersPage />} />
        <Route path="/posts" element={<PostsPage />} />
        <Route path="/posts/:id" element={<PostsPage />} />
      </Routes>
    </BridgeRouter>
  );
}
```

The pages can immediately use react-query with the generated client:

```tsx
// In your page components
import { getUsers } from '../client';
import { useQuery } from 'react-query';

const { data: users, isLoading, error } = useQuery(['users'], () => getUsers());
```

## Advanced Configuration

```tsx
<BridgeRouter
  packages={["fastapi", "pydantic", "sqlalchemy", "asyncpg"]}
  debug={false}
  apiPrefix="/api/v2"
  queryClientOptions={{
    defaultOptions: {
      queries: {
        staleTime: 10 * 60 * 1000, // 10 minutes
        retry: 3,
      },
    },
  }}
  showDevtools={true}
>
  {/* Your app */}
</BridgeRouter>
```

## Migration Guide

### From Manual Bridge Setup

Replace your entire bridge initialization with `BridgeRouter`:

```tsx
// Remove all of this:
- import { Bridge, FetchInterceptor } from 'pyodide-bridge-ts';
- import { QueryClient, QueryClientProvider } from 'react-query';
- import { BrowserRouter } from 'react-router-dom';
- // ... 100+ lines of setup

// Add this:
+ import { BridgeRouter } from 'pyodide-bridge-ts';

// Replace your return statement:
- return (
-   <QueryClientProvider client={queryClient}>
-     <BrowserRouter>
-       {/* routes */}
-     </BrowserRouter>
-   </QueryClientProvider>
- );

+ return (
+   <BridgeRouter>
+     {/* routes */}
+   </BridgeRouter>
+ );
```

### From react-router-fastapi

Simply replace `FastAPIRouter` with `BridgeRouter`:

```tsx
- import { FastAPIRouter } from 'react-router-fastapi';
+ import { BridgeRouter } from 'pyodide-bridge-ts';
+ import { Routes, Route } from 'react-router-dom';

- <FastAPIRouter routes={routes} apiBaseURL="..." />
+ <BridgeRouter>
+   <Routes>
+     {routes.map(route => <Route key={route.path} {...route} />)}
+   </Routes>
+ </BridgeRouter>
```

## Benefits

1. **🚀 One-line setup**: Replace 100+ lines with a single component
2. **🔧 Zero configuration**: Works out of the box with sensible defaults  
3. **🎨 Customizable**: Override any part you need
4. **📦 All-in-one**: Includes routing, state management, and API client
5. **🛠️ Developer friendly**: Built-in devtools and error handling
6. **🔄 Compatible**: Works with existing generated pages and clients

---

## Legacy API (Manual Setup)

The manual `Bridge` and `FetchInterceptor` classes are still available for advanced use cases, but we recommend using `BridgeRouter` for most applications.

### Bridge Class

```typescript
import { Bridge } from 'pyodide-bridge-ts';

const bridge = new Bridge({
  debug: true,
  packages: ['fastapi', 'pydantic'],
});

await bridge.initialize();
await bridge.loadBackend('/backend', 'directory');
```

### FetchInterceptor

```typescript
import { FetchInterceptor } from 'pyodide-bridge-ts';

const interceptor = new FetchInterceptor(bridge, {
  apiPrefix: '/api/v1',
  debug: true,
});

// Don't forget to clean up!
interceptor.restore();
```

But seriously, just use `BridgeRouter` instead! 😄 