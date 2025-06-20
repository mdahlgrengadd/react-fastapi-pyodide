#!/usr/bin/env python3
"""
Fixed Page Generator for React components from OpenAPI schema.
This corrects the bugs in the original generator.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PageGeneratorFixed:
    """Fixed version of the page generator with corrected logic."""

    def __init__(self, schema: Dict[str, Any], output_dir: Path):
        self.schema = schema
        self.output_dir = output_dir
        self.paths = schema.get("paths", {})
        self.components = schema.get("components", {})
        self.schemas = self.components.get("schemas", {})

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
            "import { Link, useParams } from 'react-router-dom';",
            "import { useAPIQuery } from 'react-router-fastapi';"
        ]

        component_parts = [
            '// Auto-generated page component',
            *imports,
            '',
            interfaces,
            '',
            f"export const {component_name}: React.FC = () => {{",
            "  const { id } = useParams<{ id: string }>();",
            "",
        ]

        # Only show routing if we have both list and detail endpoints
        if list_endpoint and detail_endpoint:
            component_parts.extend([
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

    def _generate_list_component(self, domain: str, endpoint: Dict[str, Any], data_type: str) -> List[str]:
        """Generate list component code with fixed variable names."""
        component_name = f"{domain.capitalize()}List"
        query_key = domain
        endpoint_path = endpoint['path']

        # Determine if it's an array response
        is_array = data_type.endswith('[]')
        hook_type = data_type if is_array else f"{data_type}[]"
        data_var = f"{domain}Data"  # Use clear variable name
        items_var = f"{domain}Items"  # Use clear variable name for array items

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
            f"  // Ensure we have array data",
            f"  const {items_var} = Array.isArray({data_var}) ? {data_var} : [];",
            "",
            "  return (",
            "    <div className=\"min-h-screen bg-gray-50\">",
            "      <div className=\"max-w-6xl mx-auto p-8\">",
            "        {/* Header */}",
            "        <div className=\"flex items-center justify-between mb-8\">",
            "          <div>",
            f"            <h1 className=\"text-3xl font-bold text-gray-900 mb-2\">{domain.capitalize()} Management</h1>",
            f"            <p className=\"text-gray-600\">Manage {domain}s and their details</p>",
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
            f"              <p className=\"text-red-800 font-medium\">Failed to load {domain}s</p>",
            "              <p className=\"text-red-600 text-sm mt-1\">{error instanceof Error ? error.message : 'Unknown error'}</p>",
            "            </div>",
            "          </div>",
            "        )}",
            "",
            "        {/* Data */}",
            f"        {{{data_var} && {items_var}.length > 0 && (",
            "          <div className=\"bg-white rounded-lg shadow-lg overflow-hidden\">",
            "            <div className=\"p-6\">",
            f"              <h2 className=\"text-xl font-semibold text-gray-900 mb-4\">{domain.capitalize()}s</h2>",
            "              <div className=\"space-y-4\">",
            f"                {{{items_var}.map((item: any, index: number) => (",
            "                  <div key={item.id || index} className=\"border rounded-lg p-4 hover:bg-gray-50\">",
            "                    <div className=\"flex items-center justify-between\">",
            "                      <div>",
            "                        <h3 className=\"font-medium text-gray-900\">",
            f"                          {{item.name || item.title || item.email || `{domain.capitalize()} ${{item.id || index + 1}}`}}",
            "                        </h3>",
            "                        {item.description && (",
            "                          <p className=\"text-gray-600 text-sm mt-1\">{item.description}</p>",
            "                        )}",
            "                      </div>",
            "                      {item.id && (",
            "                        <Link",
            f"                          to={{`/{domain}s/${{item.id}}`}}",
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
            "",
            f"        {/* No Data State */}}",
            f"        {{{data_var} && {items_var}.length === 0 && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            "            <div className=\"text-center py-8\">",
            f"              <p className=\"text-gray-500 text-lg\">No {domain}s found</p>",
            f"              <p className=\"text-gray-400 text-sm mt-2\">There are currently no {domain}s available.</p>",
            "            </div>",
            "          </div>",
            "        )}",
            "      </div>",
            "    </div>",
            "  );",
            "};",
            ""
        ]

    def _generate_detail_component(self, domain: str, endpoint: Dict[str, Any], data_type: str) -> List[str]:
        """Generate detail component code with fixed variable names."""
        component_name = f"{domain.capitalize()}Detail"
        base_type = data_type.replace('[]', '')
        endpoint_path = endpoint['path']
        data_var = f"{domain}Data"

        return [
            f"const {component_name}: React.FC<{{ id: string }}> = ({{ id }}) => {{",
            "  const {",
            f"    data: {data_var},",
            "    isLoading,",
            "    error",
            f"  }} = useAPIQuery<{base_type}>(",
            f"    ['{domain}', id],",
            f"    '{endpoint_path}'.replace('{{id}}', id)",
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
            f"              to=\"/{domain}s\"",
            "              className=\"px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors\"",
            "            >",
            f"              ← Back to {domain.capitalize()}s",
            "            </Link>",
            "            <Link",
            "              to=\"/\"",
            "              className=\"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors\"",
            "            >",
            "              ← Home",
            "            </Link>",
            "          </div>",
            "        </div>",
            "",
            "        {/* Loading State */}",
            "        {isLoading && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            "            <div className=\"animate-pulse space-y-4\">",
            "              {[...Array(3)].map((_, i) => (",
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
            f"              <p className=\"text-red-800 font-medium\">Failed to load {domain} details</p>",
            "              <p className=\"text-red-600 text-sm mt-1\">{error instanceof Error ? error.message : 'Unknown error'}</p>",
            "            </div>",
            "          </div>",
            "        )}",
            "",
            "        {/* Data */}",
            f"        {{{data_var} && (",
            "          <div className=\"bg-white rounded-lg shadow-lg p-6\">",
            f"            <h2 className=\"text-xl font-semibold text-gray-900 mb-4\">{domain.capitalize()} Information</h2>",
            "            <div className=\"space-y-4\">",
            f"              {{Object.entries({data_var}).map(([key, value]) => (",
            "                <div key={key} className=\"border-b border-gray-200 pb-2\">",
            "                  <div className=\"flex justify-between\">",
            "                    <span className=\"font-medium text-gray-900 capitalize\">{key.replace(/([A-Z])/g, ' $1').trim()}:</span>",
            "                    <span className=\"text-gray-600\">{String(value)}</span>",
            "                  </div>",
            "                </div>",
            "              ))}",
            "            </div>",
            "          </div>",
            "        )}",
            "      </div>",
            "    </div>",
            "  );",
            "};",
            ""
        ]

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


def apply_fixes_to_generated_files(pages_dir: Path):
    """Apply the bug fixes to already generated page files."""
    logger.info(f"Applying fixes to generated page files in {pages_dir}")

    for page_file in pages_dir.glob("*Page.tsx"):
        # Skip manually created pages
        if page_file.name in ["DashboardPage.tsx", "HomePage.tsx", "GeneratedClientDemo.tsx",
                              "PostsPage.tsx", "SystemPage.tsx", "UsersPage.tsx"]:
            continue

        logger.info(f"Fixing {page_file.name}")

        # Read the file
        content = page_file.read_text(encoding='utf-8')

        # Apply fixes
        fixed_content = apply_content_fixes(content)

        # Write back
        page_file.write_text(fixed_content, encoding='utf-8')
        logger.info(f"Fixed {page_file.name}")


def apply_content_fixes(content: str) -> str:
    """Apply specific fixes to generated page content."""
    import re

    # Fix 1: Replace undefined Detail components with fallback
    detail_pattern = r'return <(\w+)Detail id=\{id\} />;'
    matches = re.findall(detail_pattern, content)
    for match in matches:
        domain = match.lower()
        # Check if Detail component is actually defined in the file
        if f"const {match}Detail:" not in content:
            # Replace with a fallback
            content = content.replace(
                f"return <{match}Detail id={{id}} />;",
                f"return <div>Detail view for {domain} (ID: {{id}}) - coming soon</div>;"
            )

    # Fix 2: Fix data variable inconsistencies
    # Pattern: {data && {domain}s &&
    data_pattern = r'\{data && (\w+)s &&'
    content = re.sub(
        data_pattern, r'{\1Data && \1Items.length > 0 &&', content)

    # Fix 3: Fix map variable inconsistencies
    # Pattern: {{domain}s.map(
    map_pattern = r'\{(\w+)s\.map\('
    content = re.sub(map_pattern, r'{\1Items.map(', content)

    # Fix 4: Add missing variable declarations
    # Add data variable declarations after the hook
    hook_pattern = r'(const \{\s*data: (\w+),\s*isLoading,\s*error\s*\} = useAPIQuery[^;]+;)'

    def add_data_vars(match):
        hook_line = match.group(1)
        data_var = match.group(2)

        # Extract domain from data variable (e.g., "analyticsData" -> "analytics")
        domain = data_var.replace('Data', '').lower()
        items_var = f"{domain}Items"

        return f"""{hook_line}

  // Ensure we have array data
  const {items_var} = Array.isArray({data_var}) ? {data_var} : [];"""

    content = re.sub(hook_pattern, add_data_vars, content)

    # Fix 5: Fix template string issues
    # Pattern: ${domain.capitalize()}
    content = content.replace(
        '${domain.capitalize()}', '{domain.charAt(0).toUpperCase() + domain.slice(1)}')

    # Fix 6: Add React import if missing
    if "import React from 'react';" not in content:
        content = content.replace(
            "import { Link, useParams }", "import React from 'react';\nimport { Link, useParams }")

    return content


if __name__ == "__main__":
    # Quick fix for existing files
    pages_dir = Path("d:/react-fastapi-pyodide/apps/frontend/src/pages")
    if pages_dir.exists():
        apply_fixes_to_generated_files(pages_dir)
        print("Applied fixes to existing generated page files!")
