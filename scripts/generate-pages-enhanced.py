#!/usr/bin/env python3
"""
Enhanced page generator that leverages the generated TypeScript client.

This version:
1. Parses the generated SDK (sdk.gen.ts) to get actual function signatures
2. Uses the generated types (types.gen.ts) for proper TypeScript interfaces
3. Generates React components that use the generated client functions
4. Properly handles path parameters and request/response types
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


class TypeScriptParser:
    """Parse generated TypeScript files to extract API functions and types."""

    def __init__(self, client_dir: Path):
        self.client_dir = client_dir
        self.sdk_file = client_dir / "sdk.gen.ts"
        self.types_file = client_dir / "types.gen.ts"

    def parse_api_functions(self) -> Dict[str, Any]:
        """Parse sdk.gen.ts to extract API function signatures."""
        if not self.sdk_file.exists():
            logger.warning(f"SDK file not found: {self.sdk_file}")
            return {}

        functions = {}
        content = self.sdk_file.read_text(encoding='utf-8')
        # Extract export function declarations with multi-line support
        function_pattern = r'export const (\w+) = \(([^)]*)\): ([^=]+) => \{[^}]*return __request\(OpenAPI, \{(.*?)\}\);'

        for match in re.finditer(function_pattern, content, re.DOTALL):
            func_name = match.group(1)
            params = match.group(2)
            return_type = match.group(3).strip()
            request_config = match.group(4)

            logger.debug(f"Found function: {func_name}")
            # First 100 chars
            logger.debug(
                f"Request config for {func_name}: {request_config[:100]}...")

            # Parse the request configuration
            method_match = re.search(r"method: '(\w+)'", request_config)
            url_match = re.search(r"url: '([^']+)'", request_config)

            if method_match and url_match:
                functions[func_name] = {
                    'name': func_name,
                    'method': method_match.group(1),
                    'url': url_match.group(1),
                    'params': params,
                    'return_type': return_type,
                    'has_path_params': '{' in url_match.group(1),
                    'has_body': 'body: data.requestBody' in request_config,
                    'has_query': 'query:' in request_config
                }

        logger.info(
            f"Parsed {len(functions)} API functions from {self.sdk_file}")
        return functions

    def parse_types(self) -> Dict[str, str]:
        """Parse types.gen.ts to extract type definitions."""
        if not self.types_file.exists():
            logger.warning(f"Types file not found: {self.types_file}")
            return {}

        types = {}
        content = self.types_file.read_text(encoding='utf-8')

        # Extract type definitions
        type_pattern = r'export type (\w+) = \{([^}]+)\};'

        for match in re.finditer(type_pattern, content, re.DOTALL):
            type_name = match.group(1)
            type_body = match.group(2).strip()
            types[type_name] = type_body

        logger.info(f"Parsed {len(types)} types from {self.types_file}")
        return types


class EnhancedPageGenerator:
    """Generate React pages using the parsed TypeScript client."""

    def __init__(self, client_dir: Path, output_dir: Path):
        self.client_dir = client_dir
        self.output_dir = output_dir
        self.parser = TypeScriptParser(client_dir)
        self.api_functions = self.parser.parse_api_functions()
        self.types = self.parser.parse_types()

    def generate_all_pages(self) -> List[str]:
        """Generate all page components and return list of generated files."""
        generated_files = []

        # Group functions by domain
        domains = self._group_functions_by_domain()

        for domain, functions in domains.items():
            if domain and functions:
                file_path = self._generate_domain_page(domain, functions)
                if file_path:
                    generated_files.append(file_path)

        # Update index.ts
        self._update_page_index([d for d in domains.keys() if d])

        return generated_files

    def _group_functions_by_domain(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group API functions by domain."""
        domains = {}

        for func_name, func_info in self.api_functions.items():
            # Extract domain from function name or URL
            domain = self._extract_domain_from_function(
                func_name, func_info['url'])
            logger.debug(f"Function {func_name} -> domain: {domain}")
            if domain:
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(func_info)

        logger.info(f"Grouped functions into domains: {list(domains.keys())}")
        return domains

    def _extract_domain_from_function(self, func_name: str, url: str) -> Optional[str]:
        """Extract domain name from function name or URL."""
        # Try function name first (e.g., getUsers -> users, getUser -> users)
        patterns = [
            # getUsers -> Users (plural)
            r'^(get|create|update|delete)([A-Z][a-z]+)s$',
            # getUser -> Users (singular, make plural)
            r'^(get|create|update|delete)([A-Z][a-z]+)$',
        ]

        for pattern in patterns:
            match = re.match(pattern, func_name)
            if match:
                domain = match.group(2).lower()
                # Always pluralize domain names for consistency
                if not domain.endswith('s'):
                    domain = domain + 's'
                return domain

        # Try URL path (e.g., /api/v1/users -> users)
        url_match = re.search(r'/api/v1/(\w+)', url)
        if url_match:
            domain = url_match.group(1)
            # Skip generic endpoints
            if domain in ['async-simulation', 'async-data-stream', 'async-workflow', 'async-monitor', 'stream-progress', 'live-metrics']:
                return None
            # Normalize domain names
            if domain.startswith('async-'):
                return None  # Skip async utilities
            return domain

        return None

    def _generate_domain_page(self, domain: str, functions: List[Dict[str, Any]]) -> Optional[str]:
        """Generate a page component for a domain."""
        capitalized_domain = domain.capitalize()
        file_name = f"{capitalized_domain}Page.tsx"
        file_path = self.output_dir / file_name

        # Find list and detail functions
        list_func = next(
            (f for f in functions if f['method'] == 'GET' and not f['has_path_params']), None)
        detail_func = next(
            (f for f in functions if f['method'] == 'GET' and f['has_path_params']), None)

        if not list_func:
            logger.warning(f"No list function found for domain {domain}")
            return None

        # Generate the component
        component_code = self._generate_page_component(
            domain, capitalized_domain, list_func, detail_func, functions
        )

        # Write to file
        file_path.write_text(component_code, encoding='utf-8')
        logger.info(f"Generated {file_name}")

        return str(file_path)

    def _generate_page_component(
        self,
        domain: str,
        capitalized_domain: str,
        list_func: Dict[str, Any],
        detail_func: Optional[Dict[str, Any]],
        all_functions: List[Dict[str, Any]]
    ) -> str:
        """Generate the complete page component code."""

        # Determine which functions to import
        import_functions = [list_func['name']]
        if detail_func:
            import_functions.append(detail_func['name'])

        # Determine which types to import
        response_type = f"{capitalized_domain}Response"
        import_types = []
        if response_type in self.types:
            import_types.append(response_type)

        # Generate imports
        imports = self._generate_imports(
            import_functions, import_types, detail_func is not None)

        # Generate main component
        main_component = self._generate_main_component(
            capitalized_domain, detail_func is not None)

        # Generate list component
        list_component = self._generate_list_component(
            domain, capitalized_domain, list_func, response_type)

        # Generate detail component (if needed)
        detail_component = ""
        if detail_func:
            detail_component = self._generate_detail_component(
                domain, capitalized_domain, detail_func, response_type)

        return f"""// Auto-generated page component using generated TypeScript client
{imports}

{main_component}

{list_component}

{detail_component}
"""

    def _generate_imports(self, functions: List[str], types: List[str], has_detail: bool) -> str:
        """Generate import statements."""
        imports = ["import React from 'react';"]

        # React Router imports
        router_imports = ["Link"]
        if has_detail:
            router_imports.append("useParams")
        imports.append(
            f"import {{ {', '.join(router_imports)} }} from 'react-router-dom';")

        # API client imports
        if functions:
            imports.append(
                f"import {{ {', '.join(functions)} }} from '../client';")

        # Type imports
        if types:
            imports.append(
                f"import type {{ {', '.join(types)} }} from '../client';")
          # Query hook (assuming react-query or similar)
        imports.append("import { useQuery } from 'react-query';")

        return "\n".join(imports)

    def _generate_main_component(self, capitalized_domain: str, has_detail: bool) -> str:
        """Generate the main page component."""
        if has_detail:
            return f"""export const {capitalized_domain}Page: React.FC = () => {{
  const {{ id }} = useParams<{{ id: string }}>();

  if (id) {{
    return <{capitalized_domain}Detail id={{id}} />;
  }}
  return <{capitalized_domain}List />;
}};"""
        else:
            return f"""export const {capitalized_domain}Page: React.FC = () => {{
  return <{capitalized_domain}List />;
}};"""

    def _generate_list_component(self, domain: str, capitalized_domain: str, list_func: Dict[str, Any], response_type: str) -> str:
        """Generate the list component using the generated API function."""
        return f"""const {capitalized_domain}List: React.FC = () => {{
  const {{
    data: {domain},
    isLoading,
    error
  }} = useQuery(['{domain}'], () => {list_func['name']}());

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{capitalized_domain} Management</h1>
            <p className="text-gray-600">Manage {domain} data and entries</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            ← Home
          </Link>
        </div>        {{isLoading ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="animate-pulse space-y-4">
              {{[...Array(5)].map((_, i) => (
                <div key={{i}} className="h-4 bg-gray-200 rounded w-full"></div>
              ))}}
            </div>
          </div>
        ) : null}}

        {{error ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Failed to load {domain}</p>
              <p className="text-red-600 text-sm mt-1">{{error instanceof Error ? error.message : 'Unknown error'}}</p>
            </div>
          </div>
        ) : null}}

        {{{domain} && Array.isArray({domain}) && {domain}.length > 0 ? (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">{capitalized_domain}</h2>
              <div className="space-y-4">
                {{{domain}.map((item: any, index: number) => (
                  <div key={{item.id || index}} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {{item.name || item.title || item.email || `{capitalized_domain} ${{item.id || index + 1}}`}}
                        </h3>
                        {{item.description && (
                          <p className="text-gray-600 text-sm mt-1">{{item.description}}</p>
                        )}}
                      </div>
                      {{item.id && (
                        <Link
                          to={{`/{domain}/${{item.id}}`}}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
                          View Details
                        </Link>
                      )}}
                    </div>                  </div>
                ))}}
              </div>
            </div>
          </div>
        ) : null}}
      </div>
    </div>
  );
}};"""

    def _generate_detail_component(self, domain: str, capitalized_domain: str, detail_func: Dict[str, Any], response_type: str) -> str:
        """Generate the detail component using the generated API function."""
        # Determine the parameter name from the function signature
        param_name = self._extract_param_name(detail_func)

        return f"""const {capitalized_domain}Detail: React.FC<{{ id: string }}> = ({{ id }}) => {{
  const {{
    data: {domain},
    isLoading,
    error  }} = useQuery(['{domain}', id], () => {detail_func['name']}({{ {param_name}: parseInt(id) }}));

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-8">        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{capitalized_domain} Details</h1>
            <p className="text-gray-600">View detailed information for this {domain}</p>
          </div>
          <div className="space-x-2">
            <Link
              to="/{domain}"
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              ← Back to {capitalized_domain}
            </Link>
            <Link
              to="/"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Home
            </Link>
          </div>
        </div>        {{isLoading ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-gray-200 rounded w-1/3"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ) : null}}

        {{error ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Failed to load {domain} details</p>
              <p className="text-red-600 text-sm mt-1">{{error instanceof Error ? error.message : 'Unknown error'}}</p>
            </div>
          </div>
        ) : null}}

        {{{domain} ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">{capitalized_domain} Information</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {{Object.entries({domain}).map(([key, value]) => (
                <div key={{key}} className="border-b border-gray-200 pb-2">
                  <dt className="text-sm font-medium text-gray-500 capitalize">
                    {{key.replace('_', ' ')}}
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {{typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}}
                  </dd>
                </div>
              ))}}            </div>
          </div>
        ) : null}}
      </div>
    </div>
  );
}};"""

    def _extract_param_name(self, detail_func: Dict[str, Any]) -> str:
        """Extract the parameter name from the function signature."""
        # Parse the params string to find the data parameter structure
        params = detail_func.get('params', '')

        # Look for patterns like "data: GetUserData" and extract the property name from the type
        if 'Data' in params:
            # This is a simplified approach - in reality you'd parse the TypeScript types
            # For now, use common patterns
            func_name = detail_func['name']
            if 'user' in func_name.lower():
                return 'userId'
            elif 'post' in func_name.lower():
                return 'postId'
            else:
                return 'id'

        return 'id'

    def _update_page_index(self, domains: List[str]) -> None:
        """Update the pages index.ts file."""
        index_file = self.output_dir / "index.ts"

        # Generate exports
        exports = []
        for domain in sorted(domains):
            capitalized_domain = domain.capitalize()
            exports.append(
                f"export {{ {capitalized_domain}Page }} from './{capitalized_domain}Page';")

        # Add manual pages (preserve existing manual exports)
        manual_exports = []
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8')
            # Extract manual exports (those not matching the generated pattern)
            for line in content.split('\n'):
                if line.strip().startswith('export') and 'Page' in line:
                    # Check if this is not a generated export
                    if not any(domain.capitalize() in line for domain in domains):
                        manual_exports.append(line.strip())

        # Combine all exports
        all_exports = exports + manual_exports

        # Write the updated index
        content = "// Auto-generated exports - manual exports are preserved\n\n"
        content += "\n".join(all_exports)

        index_file.write_text(content, encoding='utf-8')
        logger.info("Updated pages index.ts")

 
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate React pages from TypeScript client")
    parser.add_argument(
        "--client-dir",
        type=Path,
        default=Path("apps/frontend/src/client"),
        help="Path to the generated TypeScript client directory"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("apps/frontend/src/pages"),
        help="Output directory for generated pages"    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--generate-app",
        action="store_true",
        help="Also generate App.tsx with automatic routing"
    )

    args = parser.parse_args()

    setup_logging(args.debug)

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)    # Generate pages
    generator = EnhancedPageGenerator(args.client_dir, args.output_dir)
    generated_files = generator.generate_all_pages()

    logger.info(f"Generated {len(generated_files)} page files:")
    for file_path in generated_files:
        logger.info(f"  {file_path}")


if __name__ == "__main__":
    main()
