"""
Operation ID management utilities for FastAPI applications using pyodide-bridge.

This module provides functionality to add and validate operation_id parameters
in FastAPI route decorators, which are required by the pyodide-bridge.
"""

import os
import re
from pathlib import Path
from typing import List, Set, Tuple


class OperationIdManager:
    """Manager for adding and validating operation_id in FastAPI route decorators."""

    # Route decorator patterns
    ROUTE_PATTERN = re.compile(
        r'@(?:app|router|self)\.(?:get|post|put|patch|delete|options|head)\s*\(',
        re.IGNORECASE
    )

    def __init__(self):
        self._processed_files: Set[Path] = set()

    def add_missing_operation_ids(
        self,
        path: Path,
        dry_run: bool = False,
        file_extensions: List[str] = None
    ) -> List[Path]:
        """
        Add missing operation_id to route decorators in Python files.

        Args:
            path: Directory or file path to process
            dry_run: If True, show what would be changed without making changes
            file_extensions: List of file extensions to process (default: ['.py'])

        Returns:
            List of files that were (or would be) modified
        """
        if file_extensions is None:
            file_extensions = ['.py']

        modified_files = []

        if path.is_file():
            files_to_process = [path]
        else:
            files_to_process = self._find_python_files(path, file_extensions)

        for file_path in files_to_process:
            if self._add_operation_ids_to_file(file_path, dry_run):
                modified_files.append(file_path)

        return modified_files

    def validate_operation_ids(
        self,
        path: Path,
        file_extensions: List[str] = None
    ) -> List[str]:
        """
        Validate that all route decorators have operation_id.

        Args:
            path: Directory or file path to validate
            file_extensions: List of file extensions to check (default: ['.py'])

        Returns:
            List of error messages for missing operation_id
        """
        if file_extensions is None:
            file_extensions = ['.py']

        errors = []

        if path.is_file():
            files_to_check = [path]
        else:
            files_to_check = self._find_python_files(path, file_extensions)

        for file_path in files_to_check:
            file_errors = self._validate_file(file_path)
            errors.extend(file_errors)

        return errors

    def _find_python_files(self, directory: Path, extensions: List[str]) -> List[Path]:
        """Find all Python files in a directory recursively."""
        files = []
        for ext in extensions:
            pattern = f"**/*{ext}"
            files.extend(directory.rglob(pattern))
        return [f for f in files if f.is_file()]

    def _add_operation_ids_to_file(self, file_path: Path, dry_run: bool) -> bool:
        """Add missing operation_id to a single file. Returns True if file was modified."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return False

        modified = False
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            new_lines.append(line)

            # Check if this line contains a route decorator
            if self.ROUTE_PATTERN.search(line.strip()):
                decorator_lines, function_name, end_idx = self._parse_decorator_block(
                    lines, i)

                if function_name and not self._has_operation_id(decorator_lines):
                    # Add operation_id to the decorator
                    updated_decorator = self._add_operation_id_to_decorator(
                        decorator_lines, function_name
                    )

                    if dry_run:
                        print(
                            f"Would add operation_id='{function_name}' to {file_path}:{i+1}")
                    else:
                        # Replace the decorator lines
                        # Remove the line we just added
                        new_lines = new_lines[:-1]
                        new_lines.extend(updated_decorator)

                    modified = True
                    i = end_idx
                else:
                    i += 1
            else:
                i += 1

        # Write the modified file
        if modified and not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            except Exception as e:
                print(f"Warning: Could not write {file_path}: {e}")
                return False

        return modified

    def _validate_file(self, file_path: Path) -> List[str]:
        """Validate a single file and return list of errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return [f"{file_path}: Could not read file - {e}"]

        errors = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line contains a route decorator
            if self.ROUTE_PATTERN.search(line.strip()):
                decorator_lines, function_name, end_idx = self._parse_decorator_block(
                    lines, i)

                if function_name and not self._has_operation_id(decorator_lines):
                    errors.append(
                        f"{file_path}:{i+1} - Route decorator for function '{function_name}' is missing operation_id"
                    )

                i = end_idx
            else:
                i += 1

        return errors

    def _parse_decorator_block(self, lines: List[str], start_idx: int) -> Tuple[List[str], str, int]:
        """
        Parse a decorator block and find the associated function.

        Returns:
            Tuple of (decorator_lines, function_name, end_index)
        """
        decorator_lines = []
        function_name = ""

        # Collect all decorator lines (handle multi-line decorators)
        i = start_idx
        paren_count = 0
        in_decorator = True

        while i < len(lines) and in_decorator:
            line = lines[i]
            decorator_lines.append(line)

            # Count parentheses to handle multi-line decorators
            paren_count += line.count('(') - line.count(')')

            # If we've closed all parentheses, decorator is complete
            if paren_count == 0 and '(' in line:
                in_decorator = False

            i += 1

        # Look for the function definition after the decorator
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('def ') or line.startswith('async def '):
                # Extract function name
                match = re.match(r'(?:async\s+)?def\s+(\w+)', line)
                if match:
                    function_name = match.group(1)
                break
            elif line and not line.startswith('#'):
                # Non-comment, non-function line - stop looking
                break
            i += 1

        return decorator_lines, function_name, i

    def _has_operation_id(self, decorator_lines: List[str]) -> bool:
        """Check if decorator lines contain operation_id parameter."""
        decorator_text = ''.join(decorator_lines)
        return 'operation_id' in decorator_text

    def _add_operation_id_to_decorator(self, decorator_lines: List[str], function_name: str) -> List[str]:
        """Add operation_id parameter to decorator lines."""
        # Join all lines to work with the full decorator
        full_decorator = ''.join(decorator_lines)

        # Find the last parameter or the opening parenthesis
        # Look for the pattern before the closing parenthesis
        closing_paren_idx = full_decorator.rfind(')')
        if closing_paren_idx == -1:
            return decorator_lines  # Malformed decorator

        # Check if there are existing parameters
        opening_paren_idx = full_decorator.find('(')
        content_between = full_decorator[opening_paren_idx +
                                         1:closing_paren_idx].strip()

        if content_between:
            # There are existing parameters, add comma and operation_id
            operation_id_param = f',\n         operation_id="{function_name}"'
        else:
            # No existing parameters, just add operation_id
            operation_id_param = f'operation_id="{function_name}"'

        # Insert the operation_id parameter before the closing parenthesis
        new_decorator = (
            full_decorator[:closing_paren_idx] +
            operation_id_param +
            full_decorator[closing_paren_idx:]
        )

        return [new_decorator]
