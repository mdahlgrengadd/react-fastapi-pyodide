#!/usr/bin/env python3
"""
Generate App.tsx with automatic routing based on discovered endpoints.
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def generate_app_tsx(pages_dir: Path, output_file: Path) -> None:
    """Generate App.tsx with automatic routing."""

    # Read the pages index to get available pages
    index_file = pages_dir / "index.ts"
    if not index_file.exists():
        logger.error(f"Pages index file not found: {index_file}")
        return

    content = index_file.read_text(encoding='utf-8')

    # Extract page names from export statements
    page_pattern = r'export\s*\{\s*(\w+Page)\s*\}'
    page_imports = re.findall(page_pattern, content)

    if not page_imports:
        logger.warning("No page components found in index.ts")
        return

    logger.info(f"Found {len(page_imports)} page components: {page_imports}")

    # Generate import statement
    imports_text = ",\n  ".join(sorted(page_imports))

    # Generate route configurations
    route_configs = []
    for page_name in sorted(page_imports):
        # Extract domain from page name (e.g., "UsersPage" -> "users")
        domain = page_name.replace("Page", "").lower()

        # Skip dashboard as it's the home page
        if domain == "dashboard":
            continue

        route_configs.append(
            f"""          <Route path="/{domain}" element={{<{page_name} />}} />""")

        # Add detail route for entities that typically have details
        if domain in ["users", "posts"]:
            route_configs.append(
                f"""          <Route path="/{domain}/:id" element={{<{page_name} />}} />""")

    routes_text = "\n".join(route_configs)

    # Generate the complete App.tsx content
    app_content = f"""import './App.css';

import {{ Bridge }} from 'pyodide-bridge-ts';
import {{ useEffect, useRef, useState }} from 'react';
import {{ BrowserRouter as Router, Routes, Route }} from 'react-router-dom';
import {{ QueryClient, QueryClientProvider }} from 'react-query';
import {{ ReactQueryDevtools }} from 'react-query/devtools';
import {{ OpenAPI }} from './client';

// Auto-generated page imports
import {{ 
  {imports_text}
}} from './pages';

// Create QueryClient instance
const queryClient = new QueryClient({{
  defaultOptions: {{
    queries: {{
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }},
  }},
}});

function App() {{
  const [bridge] = useState(
    () =>
      new Bridge({{
        debug: true,
        packages: ["fastapi", "pydantic", "sqlalchemy", "httpx"],
      }})
  );

  const [status, setStatus] = useState<string>("Initializing…");
  const [bridgeReady, setBridgeReady] = useState(false);
  const [interceptor, setInterceptor] = useState<any>(null);
  const initializationRef = useRef(false);

  // Initialize bridge and setup client
  useEffect(() => {{
    const initializeBridge = async () => {{
      if (initializationRef.current) {{
        console.log("🔄 Skipping duplicate initialization");
        return;
      }}
      initializationRef.current = true;

      try {{
        console.log("🚀 Starting bridge initialization...");
        setStatus("Loading Pyodide…");
        await bridge.initialize();

        setStatus("Fetching backend sources…");
        const fileListResponse = await fetch("/backend/backend_filelist.json");
        if (!fileListResponse.ok) {{
          throw new Error(`Failed to fetch file list: ${{fileListResponse.statusText}}`);
        }}

        const fileList = await fileListResponse.json();
        setStatus("Loading backend files…");
        
        for (const file of fileList) {{
          try {{
            const response = await fetch(`/backend/${{file}}`);
            if (response.ok) {{
              const content = await response.text();
              await bridge.loadFile(`/${{file}}`, content);
            }}
          }} catch (e) {{
            console.warn(`Failed to load file ${{file}}:`, e);
          }}
        }}

        setStatus("Starting FastAPI server…");
        await bridge.loadBackend("/backend", "directory");

        // Configure the generated client to use the bridge
        OpenAPI.BASE = ""; // Use relative URLs since we're on same origin
        
        // Set up request interceptor to route API calls through the bridge
        const {{ FetchInterceptor }} = await import("pyodide-bridge-ts");
        const fetchInterceptor = new FetchInterceptor(bridge, {{
          apiPrefix: "/api/v1",
          debug: true,
          routeMatcher: (url: string) => {{
            // Route API calls and docs through the bridge
            return url.startsWith("/api/v1/") || url === "/docs" || url === "/openapi.json" || url === "/redoc";
          }},
        }});
        
        setInterceptor(fetchInterceptor);
        setBridgeReady(true);
        setStatus("Ready - API Client Active");
        console.log("✅ Bridge and client ready");
      }} catch (e) {{
        console.error("❌ Bridge initialization failed:", e);
        setStatus(`❌ ${{(e as Error).message}}`);
        initializationRef.current = false;
      }}
    }};

    if (!bridgeReady && !initializationRef.current) {{
      initializeBridge();
    }}

    return () => {{
      if (interceptor) {{
        interceptor.restore();
      }}
    }};
  }}, [bridge]);

  if (!bridgeReady) {{
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Initializing FastAPI Bridge</h2>
          <p className={{`text-lg ${{status.includes("❌") ? "text-red-600" : "text-gray-600"}}`}}>
            {{status}}
            {{!status.includes("Ready") && !status.includes("❌") && (
              <span className="inline-block ml-2 animate-spin">⚪</span>
            )}}
          </p>
        </div>
      </div>
    );
  }}

  return (
    <QueryClientProvider client={{queryClient}}>
      <Router>
        <Routes>
          <Route path="/" element={{<DashboardPage />}} />
{routes_text}
        </Routes>
      </Router>
      <ReactQueryDevtools initialIsOpen={{false}} />
    </QueryClientProvider>
  );
}}

export default App;
"""

    # Write the App.tsx file
    output_file.write_text(app_content, encoding='utf-8')
    logger.info(f"Generated App.tsx with automatic routing: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate App.tsx with automatic routing")
    parser.add_argument(
        "--pages-dir",
        type=Path,
        default=Path("apps/frontend/src/pages"),
        help="Pages directory containing index.ts"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("apps/frontend/src/App.tsx"),
        help="Output path for App.tsx"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()
    setup_logging(args.debug)

    generate_app_tsx(args.pages_dir, args.output)


if __name__ == "__main__":
    main()
