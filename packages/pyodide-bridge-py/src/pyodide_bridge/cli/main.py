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
    )    # Validate operation_id subcommand
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

    # Generate pages subcommand
    generate_parser = subparsers.add_parser(
        "generate-pages",
        help="Generate React page components from FastAPI OpenAPI schema"
    )
    generate_parser.add_argument(
        "--backend-path",
        type=str,
        default="apps/backend/src",
        help="Path to the FastAPI backend source directory (default: apps/backend/src)"
    )
    generate_parser.add_argument(
        "--output-dir",
        type=str,
        default="apps/frontend/src/pages",
        help="Output directory for generated page components (default: apps/frontend/src/pages)"
    )
    generate_parser.add_argument(
        "--schema-file",
        type=str,
        help="Load OpenAPI schema from JSON file instead of backend"
    )
    generate_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "add-operation-ids":
        add_operation_ids_with_args(args)
    elif args.command == "validate-operation-ids":
        validate_operation_ids_with_args(args)
    elif args.command == "generate-pages":
        generate_pages_with_args(args)


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


def generate_pages_with_args(args):
    """Execute generate-pages command with parsed arguments."""
    from pathlib import Path
    from .generate_pages import PageGenerator, load_openapi_schema
    import json
    import logging

    # Setup logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        backend_path = Path(args.backend_path)
        output_dir = Path(args.output_dir)

        # Load OpenAPI schema
        if args.schema_file:
            logger.info(f"Loading OpenAPI schema from {args.schema_file}")
            with open(args.schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        else:
            logger.info(f"Loading OpenAPI schema from backend at {backend_path}")
            schema = load_openapi_schema(backend_path)

        logger.info(f"Found {len(schema.get('paths', {}))} API endpoints")

        if args.dry_run:
            logger.info("Dry run mode - analyzing schema structure...")
            generator = PageGenerator(schema, output_dir)
            domains = generator._group_endpoints_by_domain()

            print("\nDomains found:")
            for domain, endpoints in domains.items():
                print(f"  {domain}: {len(endpoints)} endpoints")
                for endpoint in endpoints[:3]:  # Show first 3
                    print(f"    {endpoint['method']} {endpoint['path']}")
                if len(endpoints) > 3:
                    print(f"    ... and {len(endpoints) - 3} more")

            print(f"\nWould generate {len([d for d in domains.keys() if d and d != 'general'])} page components in {output_dir}")
            return

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate pages
        generator = PageGenerator(schema, output_dir)
        generated_files = generator.generate_all_pages()

        if generated_files:
            logger.info(f"Successfully generated {len(generated_files)} files:")
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
