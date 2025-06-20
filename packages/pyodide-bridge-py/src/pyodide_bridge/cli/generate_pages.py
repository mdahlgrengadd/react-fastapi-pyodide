#!/usr/bin/env python3
"""
Generate React page components from FastAPI OpenAPI schema.

This tool analyzes your FastAPI application's OpenAPI schema and generates
React page components with proper TypeScript types, API calls, and modern UI.
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


class PageGenerator:
    """Generate React page components from OpenAPI schema."""

    def __init__(self, schema: Dict[str, Any], output_dir: Path):
        self.schema = schema
        self.output_dir = output_dir
        self.paths = schema.get("paths", {})
        self.components = schema.get("components", {})
        self.schemas = self.components.get("schemas", {})

    def generate_all_pages(self) -> List[str]:
        """Generate all page components and return list of generated files."""
        generated_files = []

        # Group endpoints by logical domains
        domains = self._group_endpoints_by_domain()

        for domain, endpoints in domains.items():
            if domain and endpoints:
                file_path = self._generate_domain_page(domain, endpoints)
                if file_path:
                    generated_files.append(str(file_path))

        # Generate index file
        index_path = self._generate_index_file(domains.keys())
        if index_path:
            generated_files.append(str(index_path))

        return generated_files

    def _group_endpoints_by_domain(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group API endpoints by logical domain based on path structure."""
        domains: Dict[str, List[Dict[str, Any]]] = {}

        for path, methods in self.paths.items():
            # Extract domain from path (e.g., /api/v1/users -> users)
            domain = self._extract_domain_from_path(path)

            for method, spec in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    endpoint_info = {
                        'path': path,
                        'method': method.upper(),
                        'spec': spec,
                        'operation_id': spec.get('operationId'),
                        'summary': spec.get('summary', ''),
                        'description': spec.get('description', ''),
                        'parameters': spec.get('parameters', []),
                        'responses': spec.get('responses', {}),
                        'request_body': spec.get('requestBody'),
                    }

                    if domain not in domains:
                        domains[domain] = []
                    domains[domain].append(endpoint_info)
        return domains

    def _extract_domain_from_path(self, path: str) -> str:
        """Extract domain name from API path."""
        # Remove API prefix and version
        clean_path = re.sub(r'^/api/v\d+/', '', path)
        clean_path = re.sub(r'^/', '', clean_path)

        # Get first path segment
        segments = clean_path.split('/')
        if segments and segments[0]:
            domain = segments[0]
            # Remove path parameters
            # Clean up domain name: remove hyphens and special chars
            domain = re.sub(r'\{[^}]+\}', '', domain)
            domain = re.sub(r'[^a-zA-Z0-9]', '', domain)
            return domain.strip().lower()

        return 'general'

    def _generate_domain_page(self, domain: str, endpoints: List[Dict[str, Any]]) -> Optional[Path]:
        """Generate a React page component for a domain."""
        if not endpoints:
            return None

        # Determine primary endpoints
        list_endpoint = self._find_list_endpoint(endpoints)
        detail_endpoint = self._find_detail_endpoint(endpoints)
        create_endpoint = self._find_create_endpoint(endpoints)

        # Generate TypeScript interfaces
        interfaces = self._generate_interfaces_for_domain(domain, endpoints)

        # Generate component
        component_name = f"{domain.capitalize()}Page"
        file_name = f"{component_name}.tsx"
        file_path = self.output_dir / file_name

        # Skip if file already exists (preserve manual pages)
        if file_path.exists():
            logger.info(f"Skipping {file_path} - file already exists")
            return None

        component_code = self._generate_page_component(
            domain=domain,
            component_name=component_name,
            endpoints=endpoints,
            list_endpoint=list_endpoint,
            detail_endpoint=detail_endpoint,
            create_endpoint=create_endpoint,
            interfaces=interfaces
        )

        # Write file
        file_path.write_text(component_code, encoding='utf-8')
        logger.info(f"Generated {file_path}")

        return file_path

    def _find_list_endpoint(self, endpoints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the main list/collection endpoint."""
        for endpoint in endpoints:
            if (endpoint['method'] == 'GET' and
                not self._has_path_parameters(endpoint['path']) and
                not endpoint['path'].endswith('/info') and
                    not endpoint['path'].endswith('/status')):
                return endpoint
        return None

    def _find_detail_endpoint(self, endpoints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the detail/single item endpoint."""
        for endpoint in endpoints:
            if (endpoint['method'] == 'GET' and
                    self._has_path_parameters(endpoint['path'])):
                return endpoint
        return None

    def _find_create_endpoint(self, endpoints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the create endpoint."""
        for endpoint in endpoints:
            if endpoint['method'] == 'POST':
                return endpoint
        return None

    def _has_path_parameters(self, path: str) -> bool:
        """Check if path has parameters like {id}."""
        return '{' in path and '}' in path

    def _generate_interfaces_for_domain(self, domain: str, endpoints: List[Dict[str, Any]]) -> str:
        """Generate TypeScript interfaces for domain models."""
        interfaces = []

        # Find response schemas
        schemas_used = set()
        for endpoint in endpoints:
            for response_code, response in endpoint['responses'].items():
                if response_code.startswith('2'):  # Success responses
                    content = response.get('content', {})
                    for media_type, media_spec in content.items():
                        if 'schema' in media_spec:
                            schema_ref = self._extract_schema_ref(
                                media_spec['schema'])
                            if schema_ref:
                                schemas_used.add(schema_ref)
          # Generate interfaces for used schemas
        for schema_name in schemas_used:
            if schema_name in self.schemas:
                interface = self._generate_typescript_interface(
                    schema_name, self.schemas[schema_name])
                interfaces.append(interface)

        return '\n\n'.join(interfaces)

    def _extract_schema_ref(self, schema: Dict[str, Any]) -> Optional[str]:
        """Extract schema reference name."""
        if '$ref' in schema:
            ref = schema['$ref']
            if ref.startswith('#/components/schemas/'):
                return ref.split('/')[-1]
        elif 'items' in schema and '$ref' in schema['items']:
            ref = schema['items']['$ref']
            if ref.startswith('#/components/schemas/'):
                return ref.split('/')[-1]
        return None

    def _generate_typescript_interface(self, name: str, schema: Dict[str, Any]) -> str:
        """Generate TypeScript interface from JSON schema."""
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))

        fields = []
        for prop_name, prop_schema in properties.items():
            field_type = self._json_schema_to_typescript_type(prop_schema)
            optional_marker = '' if prop_name in required else '?'
            fields.append(f"  {prop_name}{optional_marker}: {field_type};")

        return f"interface {name} {{\n" + '\n'.join(fields) + "\n}"

    def _json_schema_to_typescript_type(self, schema: Dict[str, Any]) -> str:
        """Convert JSON schema type to TypeScript type."""
        schema_type = schema.get('type', 'any')

        if schema_type == 'string':
            return 'string'
        elif schema_type == 'number' or schema_type == 'integer':
            return 'number'
        elif schema_type == 'boolean':
            return 'boolean'
        elif schema_type == 'array':
            items = schema.get('items', {})
            item_type = self._json_schema_to_typescript_type(items)
            return f"{item_type}[]"
        elif schema_type == 'object':
            return 'Record<string, any>'
        elif '$ref' in schema:
            ref = schema['$ref']
            if ref.startswith('#/components/schemas/'):
                return ref.split('/')[-1]

        return 'any'

    def _generate_page_component(
        self,
        domain: str,
        component_name: str,
        endpoints: List[Dict[str, Any]],
        list_endpoint: Optional[Dict[str, Any]],
        detail_endpoint: Optional[Dict[str, Any]],
        create_endpoint: Optional[Dict[str, Any]],
        interfaces: str
    ) -> str:
        """Generate the React page component code."""

        # Determine primary data type
        data_type = self._infer_data_type(domain, list_endpoint)
        # Generate imports
        imports = [
            "import React from 'react';",
            "import { Link } from 'react-router-dom';",
            "import { useAPIQuery } from 'react-router-fastapi';"
        ]
        # Add useParams only if we need it
        if list_endpoint and detail_endpoint:
            imports[1] = "import { Link, useParams } from 'react-router-dom';"

        component_parts = [
            '// Auto-generated page component',
            *imports,
            '',
            interfaces,
            '',
            f"export const {component_name}: React.FC = () => {{",
        ]

        # Only show routing if we have both list and detail endpoints
        if list_endpoint and detail_endpoint:
            component_parts.extend([
                "  const { id } = useParams<{ id: string }>();",
                "",
                "  // If we have an id, show detail view, otherwise show list view",
                "  if (id) {",
                f"    return <{domain.capitalize()}Detail id={{id}} />;",
                "  }",
                "",
                f"  return <{domain.capitalize()}List />;",
                "};",
                ""
            ])
        elif list_endpoint:
            # Only list component
            component_parts.extend([
                f"  return <{domain.capitalize()}List />;",
                "};",
                ""
            ])
        elif detail_endpoint:
            # Only detail component (unusual but possible)
            component_parts.extend([
                "  const { id } = useParams<{ id: string }>();",
                "",
                "  if (!id) {",
                "    return <div>ID parameter is required</div>;",
                "  }",
                f"  return <{domain.capitalize()}Detail id={{id}} />;",
                "};",
                ""
            ])
        else:
            # Fallback - no endpoints
            component_parts.extend([
                f"  return <div>{domain.capitalize()} page - no endpoints available</div>;",
                "};",
                ""
            ])

        # Generate list component
        if list_endpoint:
            component_parts.extend(self._generate_list_component(
                domain, list_endpoint, data_type))

        # Generate detail component
        if detail_endpoint:
            component_parts.extend(self._generate_detail_component(
                domain, detail_endpoint, data_type))

        return '\n'.join(component_parts)

    def _infer_data_type(self, domain: str, list_endpoint: Optional[Dict[str, Any]]) -> str:
        """Infer the primary data type for the domain."""
        if not list_endpoint:
            return 'any'

        # Look at successful response schema
        responses = list_endpoint.get('responses', {})
        for response_code, response in responses.items():
            if response_code.startswith('2'):
                content = response.get('content', {})
                for media_type, media_spec in content.items():
                    if 'schema' in media_spec:
                        schema_ref = self._extract_schema_ref(
                            media_spec['schema'])
                        if schema_ref:
                            return schema_ref
                        elif media_spec['schema'].get('type') == 'array':
                            items_ref = self._extract_schema_ref(
                                media_spec['schema'].get('items', {}))
                            if items_ref:
                                return f"{items_ref}[]"
        return 'any'

    def _generate_list_component(self, domain: str, endpoint: Dict[str, Any], data_type: str) -> List[str]:
        """Generate list component code."""
        component_name = f"{domain.capitalize()}List"
        query_key = domain  # Use singular form for query key
        endpoint_path = endpoint['path']

        # Determine if it's an array response
        is_array = data_type.endswith('[]')
        hook_type = data_type if is_array else f"{data_type}[]"
        data_var = domain  # Use singular form for data variable

        return [
            f"const {component_name}: React.FC = () => {{",
            "  const {",
            f"    data: {data_var},",
            "    isLoading,",
            "    error",
            f"  }} = useAPIQuery<{hook_type}>(",
            f"    ['{query_key}'],",
            f"    '{endpoint_path}'",
            "  );",
            "",
            "  return (",
            "    <div className=\"min-h-screen bg-gray-50\">",
            "      <div className=\"max-w-6xl mx-auto p-8\">",
            "        {/* Header */}",
            "        <div className=\"flex items-center justify-between mb-8\">",
            "          <div>",
            f"            <h1 className=\"text-3xl font-bold text-gray-900 mb-2\">{domain.capitalize()} Management</h1>",
            f"            <p className=\"text-gray-600\">Manage {domain} data and entries</p>",
            "          </div>",
            "          <Link",
            "            to=\"/\"",
            "            className=\"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors\"",
            "          >",
            "            ← Home",
            "          </Link>",
            "        </div>",
            "",
            "        {/* Loading State */}",
            "        {isLoading && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            "            <div className=\"animate-pulse space-y-4\">",
            "              {[...Array(5)].map((_, i) => (",
            "                <div key={i} className=\"h-4 bg-gray-200 rounded w-full\"></div>",
            "              ))}",
            "            </div>",
            "          </div>",
            "        )}",
            "",
            "        {/* Error State */}",
            "        {error && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            "            <div className=\"bg-red-50 border border-red-200 rounded-lg p-4\">",
            f"              <p className=\"text-red-800 font-medium\">Failed to load {domain}</p>",
            "              <p className=\"text-red-600 text-sm mt-1\">{error instanceof Error ? error.message : 'Unknown error'}</p>",
            "            </div>",
            "          </div>",
            "        )}",
            "",        "        {/* Data */}",
            f"        {{{data_var} && Array.isArray({data_var}) && {data_var}.length > 0 && (",
            "          <div className=\"bg-white rounded-lg shadow-lg overflow-hidden\">",
            "            <div className=\"p-6\">",
            f"              <h2 className=\"text-xl font-semibold text-gray-900 mb-4\">{domain.capitalize()}</h2>",
            "              <div className=\"space-y-4\">",
            f"                {{{data_var}.map((item: any, index: number) => (",
            "                  <div key={item.id || index} className=\"border rounded-lg p-4 hover:bg-gray-50\">",
            "                    <div className=\"flex items-center justify-between\">",
            "                      <div>",                        "                        <h3 className=\"font-medium text-gray-900\">",
            f"                          {{item.name || item.title || item.email || `{domain.capitalize()} ${{item.id || index + 1}}`}}",
            "                        </h3>",
            "                        {item.description && (",
            "                          <p className=\"text-gray-600 text-sm mt-1\">{item.description}</p>",
            "                        )}",
            "                      </div>",
            "                      {item.id && (",
            "                        <Link",
            f"                          to={{`/{domain}/${{item.id}}`}}",
            "                          className=\"px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700\"",
            "                        >",
            "                          View Details",
            "                        </Link>",
            "                      )}",
            "                    </div>",
            "                  </div>",
            "                ))}",
            "              </div>",
            "            </div>",
            "          </div>",
            "        )}",
            "      </div>",
            "    </div>",            "  );",
            "};",
            ""
        ]

    def _generate_detail_component(self, domain: str, endpoint: Dict[str, Any], data_type: str) -> List[str]:
        """Generate detail component code."""
        component_name = f"{domain.capitalize()}Detail"
        base_type = data_type.replace('[]', '')
        endpoint_path = endpoint['path']
        data_var = domain  # Use domain as the data variable name

        # Extract path parameter name (e.g., {user_id} from /api/v1/users/{user_id})
        import re
        path_params = re.findall(r'\{([^}]+)\}', endpoint_path)
        # fallback to 'id'
        path_param = path_params[0] if path_params else 'id'

        return [
            f"const {component_name}: React.FC<{{ id: string }}> = ({{ id }}) => {{",
            "  const {",
            f"    data: {domain},",
            "    isLoading,",
            "    error",
            f"  }} = useAPIQuery<{base_type}>(",
            f"    ['{domain}', id],",
            f"    '{endpoint_path}'.replace('{{{path_param}}}', id)",
            "  );",
            "",
            "  return (",
            "    <div className=\"min-h-screen bg-gray-50\">",
            "      <div className=\"max-w-4xl mx-auto p-8\">",
            "        {/* Header */}",
            "        <div className=\"flex items-center justify-between mb-8\">",
            "          <div>",
            f"            <h1 className=\"text-3xl font-bold text-gray-900 mb-2\">{domain.capitalize()} Details</h1>",
            f"            <p className=\"text-gray-600\">View detailed information for this {domain}</p>",
            "          </div>",
            "          <div className=\"space-x-2\">",
            "            <Link",
            f"              to=\"/{domain}\"",
            "              className=\"px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors\"",
            "            >",
            f"              ← Back to {domain.capitalize()}",
            "            </Link>",
            "            <Link",
            "              to=\"/\"",
            "              className=\"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors\"",
            "            >",
            "              Home",
            "            </Link>",
            "          </div>",
            "        </div>",
            "",
            "        {/* Loading State */}",
            "        {isLoading && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            "            <div className=\"animate-pulse space-y-4\">",
            "              <div className=\"h-6 bg-gray-200 rounded w-1/3\"></div>",
            "              <div className=\"h-4 bg-gray-200 rounded w-2/3\"></div>",
            "              <div className=\"h-4 bg-gray-200 rounded w-1/2\"></div>",
            "            </div>",
            "          </div>",
            "        )}",
            "",
            "        {/* Error State */}",
            "        {error && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            "            <div className=\"bg-red-50 border border-red-200 rounded-lg p-4\">",
            f"              <p className=\"text-red-800 font-medium\">Failed to load {domain} details</p>",
            "              <p className=\"text-red-600 text-sm mt-1\">{error instanceof Error ? error.message : 'Unknown error'}</p>",
            "            </div>",
            "          </div>",
            "        )}",
            "",        "        {/* Data */}",
            f"        {{{domain} && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            f"            <h2 className=\"text-xl font-semibold text-gray-900 mb-4\">{domain.capitalize()} Information</h2>",
            "            <div className=\"grid md:grid-cols-2 gap-6\">",
            f"              {{Object.entries({domain}).map(([key, value]) => (",
            "                <div key={key} className=\"border-b border-gray-200 pb-2\">",
            "                  <dt className=\"text-sm font-medium text-gray-500 capitalize\">",
            "                    {key.replace('_', ' ')}",
            "                  </dt>",
            "                  <dd className=\"mt-1 text-sm text-gray-900\">",
            "                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}",
            "                  </dd>",
            "                </div>",
            "              ))}",
            "            </div>",
            "          </div>",
            "        )}",
            "      </div>",
            "    </div>",
            "  );",
            "};",            ""
        ]

    def _generate_index_file(self, domains: Set[str]) -> Optional[Path]:
        """Generate index.ts file that exports all page components."""
        if not domains:
            return None

        # Find all existing page components in the output directory
        existing_components = []
        if self.output_dir.exists():
            for tsx_file in self.output_dir.glob("*Page.tsx"):
                component_name = tsx_file.stem  # Remove .tsx extension
                if component_name.endswith('Page'):
                    existing_components.append(component_name)

        # Sort for consistent output
        existing_components.sort()

        if not existing_components:
            return None

        exports = []
        for component_name in existing_components:
            exports.append(
                f"export {{ {component_name} }} from './{component_name}';")

        content = "// Auto-generated page component exports\n" + \
            '\n'.join(exports) + '\n'

        index_path = self.output_dir / 'index.ts'
        index_path.write_text(content, encoding='utf-8')
        logger.info(f"Generated {index_path}")

        return index_path


def load_openapi_schema(backend_path: Path) -> Dict[str, Any]:
    """Load OpenAPI schema from FastAPI backend."""
    # Add backend to Python path
    sys.path.insert(0, str(backend_path.resolve()))

    try:
        # Import the FastAPI app - adjust import based on structure
        # First try the standard structure: backend_path/app/app_main.py
        try:
            from app.app_main import app
        except ImportError:
            # Try alternative import if backend_path points directly to app directory
            try:
                from app_main import app
            except ImportError:
                # Try if backend_path is the project root and app is in src/app
                backend_src = backend_path / "src"
                if backend_src.exists():
                    sys.path.insert(0, str(backend_src.resolve()))
                    from app.app_main import app
                else:
                    raise ImportError(
                        "Could not find app.app_main or app_main module")
          # Generate OpenAPI schema
        schema = app.openapi()
        return schema

    except ImportError as e:
        logger.error(f"Failed to import FastAPI app: {e}")
        logger.error(
            "Make sure the backend is properly configured with a 'app' variable in app_main.py")
        logger.error(f"Backend path: {backend_path}")

        # List available Python files for debugging
        if backend_path.exists():
            py_files = list(backend_path.glob("**/*.py"))
            logger.error(
                f"Available Python files: {[str(f.relative_to(backend_path)) for f in py_files[:10]]}")
        else:
            logger.error(f"Backend path does not exist!")

        raise
    except Exception as e:
        logger.error(f"Failed to generate OpenAPI schema: {e}")
        raise
    finally:
        # Clean up path
        paths_to_remove = [str(backend_path.resolve())]
        backend_src = backend_path / "src"
        if backend_src.exists():
            paths_to_remove.append(str(backend_src.resolve()))

        for path in paths_to_remove:
            if path in sys.path:
                sys.path.remove(path)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate React page components from FastAPI OpenAPI schema"
    )
    parser.add_argument(
        '--backend-path',
        type=Path,
        default=Path.cwd() / 'apps' / 'backend' / 'src',
        help='Path to the FastAPI backend source directory (default: ./apps/backend/src)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path.cwd() / 'apps' / 'frontend' / 'src' / 'pages',
        help='Output directory for generated page components (default: ./apps/frontend/src/pages)'
    )
    parser.add_argument(
        '--schema-file',
        type=Path,
        help='Load OpenAPI schema from JSON file instead of backend'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without writing files'
    )

    args = parser.parse_args()
    setup_logging(args.debug)

    try:
        # Load OpenAPI schema
        if args.schema_file:
            logger.info(f"Loading OpenAPI schema from {args.schema_file}")
            with open(args.schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        else:
            logger.info(
                f"Loading OpenAPI schema from backend at {args.backend_path}")
            schema = load_openapi_schema(args.backend_path)

        logger.info(f"Found {len(schema.get('paths', {}))} API endpoints")

        if args.dry_run:
            logger.info("Dry run mode - analyzing schema structure...")
            generator = PageGenerator(schema, args.output_dir)
            domains = generator._group_endpoints_by_domain()

            print("\nDomains found:")
            for domain, endpoints in domains.items():
                print(f"  {domain}: {len(endpoints)} endpoints")
                for endpoint in endpoints[:3]:  # Show first 3
                    print(f"    {endpoint['method']} {endpoint['path']}")
                if len(endpoints) > 3:
                    print(f"    ... and {len(endpoints) - 3} more")

            print(
                f"\nWould generate {len([d for d in domains.keys() if d and d != 'general'])} page components in {args.output_dir}")
            return

        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate pages
        generator = PageGenerator(schema, args.output_dir)
        generated_files = generator.generate_all_pages()

        if generated_files:
            logger.info(
                f"Successfully generated {len(generated_files)} files:")
            for file_path in generated_files:
                logger.info(f"  {file_path}")
        else:
            logger.warning("No page components were generated")

    except Exception as e:
        logger.error(f"Failed to generate page components: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
