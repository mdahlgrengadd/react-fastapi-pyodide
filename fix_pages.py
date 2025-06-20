#!/usr/bin/env python3
"""
Simple fix script to repair the broken generated page components.
"""

import re
from pathlib import Path


def fix_page_file(file_path: Path):
    """Fix a single page file."""
    print(f"Fixing {file_path.name}")

    content = file_path.read_text(encoding='utf-8')

    # Fix 1: Add React import if missing
    if "import React from 'react';" not in content:
        content = content.replace(
            "import { Link, useParams } from 'react-router-dom';",
            "import React from 'react';\nimport { Link, useParams } from 'react-router-dom';"
        )

    # Fix 2: Replace undefined Detail components with fallback
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

    # Fix 3: Fix data variable inconsistencies in data checks
    # Pattern: {data && {domain}s &&
    content = re.sub(r'\{data && (\w+)s &&',
                     r'{\1 && Array.isArray(\1) &&', content)

    # Fix 4: Fix map variable inconsistencies
    # Pattern: {{domain}s.map(
    content = re.sub(r'\{(\w+)s\.map\(', r'{\1 && \1.map(', content)

    # Fix 5: Fix template string literal issues
    # Replace the problematic template literal with a proper one
    content = re.sub(
        r'\{item\.name \|\| item\.title \|\| item\.email \|\| `\$\{domain\.capitalize\(\)\} \$\{item\.id \|\| index \+ 1\}`\}',
        r'{item.name || item.title || item.email || `Item ${item.id || index + 1}`}'
    )

    # Fix 6: Fix variable naming - replace 'data' with proper variable names
    # Extract the data variable name from the hook
    hook_match = re.search(r'data: (\w+),', content)
    if hook_match:
        data_var = hook_match.group(1)
        # Replace incorrect references to 'data' with the proper variable
        content = content.replace('{data && ', f'{{{data_var} && ')

    # Write back
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed {file_path.name}")


def main():
    """Fix all problematic generated page files."""
    pages_dir = Path("d:/react-fastapi-pyodide/apps/frontend/src/pages")

    # Skip manually created pages
    manual_pages = {
        "DashboardPage.tsx", "HomePage.tsx", "GeneratedClientDemo.tsx",
        "PostsPage.tsx", "SystemPage.tsx", "UsersPage.tsx"
    }

    for page_file in pages_dir.glob("*Page.tsx"):
        if page_file.name not in manual_pages:
            try:
                fix_page_file(page_file)
            except Exception as e:
                print(f"Error fixing {page_file.name}: {e}")


if __name__ == "__main__":
    main()
