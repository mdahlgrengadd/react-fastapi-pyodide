#!/usr/bin/env python3
"""
Migration script to add operation_id to FastAPI route decorators.

This script scans Python files and automatically adds operation_id
parameters to route decorators where they're missing.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def extract_function_name_from_decorator(lines: List[str], start_idx: int) -> str:
    """
    Extract the function name that follows a route decorator.

    Args:
        lines: List of file lines
        start_idx: Index of the decorator line

    Returns:
        Function name or empty string if not found
    """
    # Look for the function definition after the decorator
    for i in range(start_idx + 1, min(len(lines), start_idx + 10)):
        line = lines[i].strip()
        if line.startswith('def ') or line.startswith('async def '):
            # Extract function name
            match = re.match(r'(?:async\s+)?def\s+(\w+)', line)
            if match:
                return match.group(1)
    return ""


def process_route_decorator(line: str, function_name: str) -> str:
    """
    Process a route decorator line and add operation_id if missing.

    Args:
        line: The decorator line
        function_name: The function name to use for operation_id

    Returns:
        Updated line with operation_id added
    """
    # Check if operation_id is already present
    if 'operation_id' in line:
        return line

    if not function_name:
        return line

    # Find the route decorator pattern
    route_pattern = r'@(app|router)\.(get|post|put|patch|delete|options|head)\s*\('
    match = re.search(route_pattern, line)

    if not match:
        return line

    # Check if the decorator has parameters
    if line.strip().endswith('('):
        # Decorator with no parameters yet
        return line  # Will be handled by the closing parenthesis
    elif line.strip().endswith(')'):
        # Single line decorator - insert operation_id before closing
        insert_pos = line.rfind(')')
        operation_id = f'operation_id="{function_name}"'

        # Check if there are already parameters
        if '(' in line and line.count('(') == line.count(')'):
            # Check what's between the parentheses
            paren_content = line[line.find('(') + 1:line.rfind(')')].strip()
            if paren_content:
                # Has parameters, add comma
                new_line = line[:insert_pos] + \
                    f', {operation_id}' + line[insert_pos:]
            else:
                # No parameters, add without comma
                new_line = line[:insert_pos] + operation_id + line[insert_pos:]
        else:
            new_line = line[:insert_pos] + operation_id + line[insert_pos:]

        return new_line

    return line


def process_multiline_decorator(lines: List[str], start_idx: int, function_name: str) -> List[str]:
    """
    Process a multiline route decorator and add operation_id.

    Args:
        lines: All file lines
        start_idx: Starting line index of the decorator
        function_name: Function name for operation_id

    Returns:
        Updated lines
    """
    # Find the end of the decorator (closing parenthesis)
    end_idx = start_idx
    paren_count = 0
    found_open = False

    for i in range(start_idx, len(lines)):
        line = lines[i]
        for char in line:
            if char == '(':
                paren_count += 1
                found_open = True
            elif char == ')':
                paren_count -= 1
                if found_open and paren_count == 0:
                    end_idx = i
                    break
        if found_open and paren_count == 0:
            break

    if end_idx == start_idx:
        return lines  # Couldn't find end

    # Check if operation_id is already present
    decorator_text = ''.join(lines[start_idx:end_idx + 1])
    if 'operation_id' in decorator_text:
        return lines

    # Add operation_id before the closing parenthesis
    new_lines = lines.copy()

    # Find the last line with meaningful content before closing paren
    insert_line_idx = end_idx
    closing_line = lines[end_idx]

    # Check if we need a comma
    need_comma = False
    for i in range(start_idx, end_idx + 1):
        line_content = lines[i]
        # Remove the decorator prefix and check for parameters
        if i == start_idx:
            line_content = re.sub(r'@\w+\.\w+\s*\(', '', line_content)
        if i == end_idx:
            line_content = line_content.replace(')', '')

        if line_content.strip() and '=' in line_content:
            need_comma = True
            break

    # Insert operation_id
    operation_id_line = f'    operation_id="{function_name}"'
    if need_comma:
        operation_id_line = '    ' + operation_id_line + ','

    # Find appropriate insertion point
    if ')' in closing_line and closing_line.strip() != ')':
        # Closing paren is on same line as last parameter
        paren_pos = closing_line.find(')')
        new_closing_line = closing_line[:paren_pos] + ',\n' + \
            operation_id_line + '\n' + closing_line[paren_pos:]
        new_lines[end_idx] = new_closing_line
    else:
        # Insert before closing line
        new_lines.insert(end_idx, operation_id_line + ',\n')

    return new_lines


def process_file(file_path: Path) -> bool:
    """
    Process a Python file to add operation_ids to route decorators.

    Args:
        file_path: Path to the Python file

    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, IOError) as e:
        print(f"Error reading {file_path}: {e}")
        return False

    new_lines = []
    modified = False
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for route decorator
        route_pattern = r'@(app|router)\.(get|post|put|patch|delete|options|head)\s*\('
        if re.search(route_pattern, line):
            # Found a route decorator
            function_name = extract_function_name_from_decorator(lines, i)

            if function_name:
                if line.strip().endswith(')'):
                    # Single line decorator
                    new_line = process_route_decorator(line, function_name)
                    if new_line != line:
                        modified = True
                    new_lines.append(new_line)
                    i += 1
                else:
                    # Multiline decorator
                    old_len = len(new_lines)
                    result_lines = process_multiline_decorator(
                        lines, i, function_name)

                    # Find how many lines were processed
                    processed_count = 1
                    for j in range(i + 1, len(lines)):
                        if ')' in lines[j]:
                            processed_count = j - i + 1
                            break

                    # Add the processed lines
                    new_lines.extend(result_lines[i:i + processed_count])

                    if len(result_lines) != len(lines):
                        modified = True

                    i += processed_count
            else:
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1

    if modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✓ Modified {file_path}")
            return True
        except IOError as e:
            print(f"Error writing {file_path}: {e}")
            return False

    return False


def main():
    """Main function to process all Python files in the project."""
    if len(sys.argv) > 1:
        base_path = Path(sys.argv[1])
    else:
        base_path = Path('.')

    if not base_path.exists():
        print(f"Error: Path {base_path} does not exist")
        sys.exit(1)

    print(f"Scanning for Python files in {base_path.absolute()}...")

    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(base_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in [
            '.git', '__pycache__', '.pytest_cache', 'node_modules']]

        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                python_files.append(Path(root) / file)

    print(f"Found {len(python_files)} Python files")

    modified_files = 0
    for file_path in python_files:
        if process_file(file_path):
            modified_files += 1

    print(f"\nSummary:")
    print(f"  Files scanned: {len(python_files)}")
    print(f"  Files modified: {modified_files}")

    if modified_files > 0:
        print(
            f"\n✓ Migration complete! Added operation_id to {modified_files} files.")
        print("Please review the changes and test your application.")
    else:
        print("\nNo modifications needed. All route decorators already have operation_id.")


if __name__ == "__main__":
    main()
