#!/usr/bin/env python3
"""
CLI utilities for managing operation_id in FastAPI applications using pyodide-bridge.

This module provides command-line tools for:
- Adding missing operation_id to route decorators
- Validating that all routes have operation_id
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .operation_id_manager import OperationIdManager


def main():
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="PyodideBridge CLI utilities",
        prog="pyodide-bridge"
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # Add operation_id subcommand
    add_parser = subparsers.add_parser(
        "add-operation-ids",
        help="Add missing operation_id to FastAPI route decorators"
    )
    add_parser.add_argument(
        "path",
        type=str,
        help="Path to directory or file to process"
    )
    add_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    add_parser.add_argument(
        "--extensions",
        type=str,
        default=".py",
        help="File extensions to process (comma-separated, default: .py)"
    )

    # Validate operation_id subcommand
    validate_parser = subparsers.add_parser(
        "validate-operation-ids",
        help="Validate that all FastAPI routes have operation_id"
    )
    validate_parser.add_argument(
        "path",
        type=str,
        help="Path to directory or file to validate"
    )
    validate_parser.add_argument(
        "--extensions",
        type=str,
        default=".py",
        help="File extensions to check (comma-separated, default: .py)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "add-operation-ids":
        add_operation_ids_with_args(args)
    elif args.command == "validate-operation-ids":
        validate_operation_ids_with_args(args)


def add_operation_ids_with_args(args):
    """Execute add-operation-ids command with parsed arguments."""
    manager = OperationIdManager()
    extensions = [ext.strip() for ext in args.extensions.split(",")]

    try:
        modified_files = manager.add_missing_operation_ids(
            path=Path(args.path),
            dry_run=args.dry_run,
            file_extensions=extensions
        )

        if args.dry_run:
            print(
                f"Dry run completed. Would modify {len(modified_files)} files.")
        else:
            print(
                f"Successfully added operation_id to {len(modified_files)} files.")

        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def validate_operation_ids_with_args(args):
    """Execute validate-operation-ids command with parsed arguments."""
    manager = OperationIdManager()
    extensions = [ext.strip() for ext in args.extensions.split(",")]

    try:
        errors = manager.validate_operation_ids(
            path=Path(args.path),
            file_extensions=extensions
        )

        if errors:
            print(
                f"❌ Validation failed! Found {len(errors)} missing operation_id:")
            for error in errors:
                print(f"  {error}")
            print(f"\nTo fix these issues, run:")
            print(f"  pyodide-bridge add-operation-ids {args.path}")
            sys.exit(1)
        else:
            print("✅ All route decorators have operation_id!")
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def add_operation_ids_command():
    """CLI command to add missing operation_id to route decorators."""
    parser = argparse.ArgumentParser(
        description="Add missing operation_id to FastAPI route decorators"
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to directory or file to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=".py",
        help="File extensions to process (comma-separated, default: .py)"
    )

    args = parser.parse_args()
    add_operation_ids_with_args(args)


def validate_operation_ids_command():
    """CLI command to validate that all routes have operation_id."""
    parser = argparse.ArgumentParser(
        description="Validate that all FastAPI routes have operation_id"
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to directory or file to validate"
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=".py",
        help="File extensions to check (comma-separated, default: .py)"
    )

    args = parser.parse_args()
    validate_operation_ids_with_args(args)


if __name__ == "__main__":
    main()
