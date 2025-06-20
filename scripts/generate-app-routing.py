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

import {{ BridgeRouter }} from 'pyodide-bridge-ts';
import {{ Routes, Route }} from 'react-router-dom';

// Auto-generated page imports
import {{ 
  {imports_text}
}} from './pages';

function App() {{
  return (
    <BridgeRouter
      packages={{["fastapi", "pydantic", "sqlalchemy", "httpx"]}}
      debug={{true}}
      showDevtools={{process.env.NODE_ENV === 'development'}}
    >
      <Routes>
        <Route path="/" element={{<DashboardPage />}} />
{routes_text}
      </Routes>
    </BridgeRouter>
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
