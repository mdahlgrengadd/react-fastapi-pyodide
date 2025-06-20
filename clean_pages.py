#!/usr/bin/env python3
"""
Final cleanup script to fix remaining issues in generated page files.
"""

import re
from pathlib import Path


def fix_page_file(file_path: Path):
    """Fix remaining issues in a generated page file."""
    print(f"Cleaning up {file_path.name}")

    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # Extract domain from filename (e.g., "AnalyticsPage.tsx" -> "analytics")
    domain = file_path.stem.replace('Page', '').lower()
    domain_title = domain.capitalize()

    # Fix 1: Add React import if missing
    if "import React from 'react';" not in content:
        content = content.replace(
            "import { Link, useParams } from 'react-router-dom';",
            "import React from 'react';\nimport { Link } from 'react-router-dom';"
        )
        content = content.replace(
            "import { Link, useParams } from 'react-router-dom';",
            "import { Link } from 'react-router-dom';"
        )

    # Fix 2: Remove unused useParams if no Detail component
    if "Detail" not in content and "useParams" in content:
        content = content.replace(
            "import { Link, useParams } from 'react-router-dom';",
            "import { Link } from 'react-router-dom';"
        )        # Remove unused id parameter
        content = re.sub(
            r'export const \w+Page: React\.FC = \(\) => \{\s*const \{ id \} = useParams<\{ id: string \}>\(\);\s*',
            f'export const {domain_title}Page: React.FC = () => {{\n  ',
            content
        )

    # Fix 3: Fix double 's' issues
    content = content.replace(f"{domain}ss", f"{domain}s")
    content = content.replace(f"{domain_title}ss", f"{domain_title}s")

    # Fix 4: Fix URL paths to use singular form
    content = re.sub(
        rf'to=\{{`/{domain}s/\$\{{item\.id\}}\`\}}',
        f'to={{`/{domain}/${{item.id}}`}}',
        content
    )

    # Fix 5: Standardize titles and descriptions
    content = content.replace(
        f"Manage {domain}s and their details",
        f"Manage {domain} data and entries"
    )

    # Only write if content changed
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print(f"  ✅ Fixed {file_path.name}")
    else:
        print(f"  ⏭ No changes needed for {file_path.name}")


def main():
    """Fix all generated page files."""
    pages_dir = Path("apps/frontend/src/pages")

    # Skip manually created pages
    manual_pages = {
        "DashboardPage.tsx", "HomePage.tsx", "GeneratedClientDemo.tsx",
        "PostsPage.tsx", "SystemPage.tsx", "UsersPage.tsx"
    }

    fixed_count = 0
    for page_file in pages_dir.glob("*Page.tsx"):
        if page_file.name not in manual_pages:
            try:
                fix_page_file(page_file)
                fixed_count += 1
            except Exception as e:
                print(f"  ❌ Error fixing {page_file.name}: {e}")

    print(f"\n🎉 Processed {fixed_count} generated page files")


if __name__ == "__main__":
    main()
