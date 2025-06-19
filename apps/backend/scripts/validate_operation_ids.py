#!/usr/bin/env python3
"""
Validation script to check that all FastAPI routes have operation_id.

This script validates that all route decorators have operation_id parameters
without modifying the source code. Suitable for CI/build validation.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def check_route_has_operation_id(lines: List[str], start_idx: int) -> Tuple[bool, str]:
    """
    Check if a route decorator has operation_id.

    Args:
        lines: List of file lines
        start_idx: Index of the decorator line

    Returns:
        Tuple of (has_operation_id, function_name)
    """
    # Look for the function definition after the decorator
    function_name = ""
    for i in range(start_idx + 1, min(len(lines), start_idx + 10)):
        line = lines[i].strip()
        if line.startswith('def ') or line.startswith('async def '):
            match = re.match(r'(?:async\s+)?def\s+(\w+)', line)
            if match:
                function_name = match.group(1)
                break

    # Check for operation_id in the decorator
    # Look for multi-line decorator
    decorator_text = ""
    paren_count = 0
    found_open = False

    for i in range(start_idx, len(lines)):
        line = lines[i]
        decorator_text += line

        for char in line:
            if char == '(':
                paren_count += 1
                found_open = True
            elif char == ')':
                paren_count -= 1
                if found_open and paren_count == 0:
                    return 'operation_id' in decorator_text, function_name

    return 'operation_id' in decorator_text, function_name


def validate_file(file_path: Path) -> List[str]:
    """
    Validate a Python file for missing operation_ids.

    Args:
        file_path: Path to the Python file

    Returns:
        List of error messages
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, IOError) as e:
        return [f"Error reading {file_path}: {e}"]

    errors = []
    route_pattern = r'@(app|router)\.(get|post|put|patch|delete|options|head)\s*\('

    for i, line in enumerate(lines):
        if re.search(route_pattern, line):
            has_operation_id, function_name = check_route_has_operation_id(
                lines, i)
            if not has_operation_id:
                errors.append(
                    f"{file_path}:{i+1} - Route decorator for function '{function_name}' is missing operation_id"
                )

    return errors


def main():
    """Main function to validate all Python files in the project."""
    if len(sys.argv) > 1:
        base_path = Path(sys.argv[1])
    else:
        base_path = Path('.')

    if not base_path.exists():
        print(f"Error: Path {base_path} does not exist")
        sys.exit(1)

    print(
        f"Validating operation_id in Python files under {base_path.absolute()}...")

    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(base_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in [
            '.git', '__pycache__', '.pytest_cache', 'node_modules']]

        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                python_files.append(Path(root) / file)

    print(f"Checking {len(python_files)} Python files...")

    all_errors = []
    for file_path in python_files:
        errors = validate_file(file_path)
        all_errors.extend(errors)

    print(f"\nValidation Results:")
    print(f"  Files checked: {len(python_files)}")
    print(f"  Errors found: {len(all_errors)}")

    if all_errors:
        print(
            f"\n❌ Validation failed! Missing operation_id in {len(all_errors)} routes:")
        for error in all_errors:
            print(f"  {error}")
        print(f"\nTo fix these errors, run:")
        print(
            f"  python apps/backend/scripts/add_operation_ids.py {base_path}")
        sys.exit(1)
    else:
        print(f"\n✅ All route decorators have operation_id!")


if __name__ == "__main__":
    main()
