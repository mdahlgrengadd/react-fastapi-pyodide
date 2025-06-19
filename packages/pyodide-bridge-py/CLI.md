# PyodideBridge CLI Tools

The PyodideBridge package includes command-line utilities to help manage FastAPI applications that use the bridge.

## Installation

Install the pyodide-bridge-py package:

```bash
pip install pyodide-bridge-py
```

Or for development:

```bash
cd packages/pyodide-bridge-py
pip install -e .
```

## Commands

### validate-operation-ids

Validates that all FastAPI route decorators have the required `operation_id` parameter.

```bash
pyodide-bridge validate-operation-ids <path>
```

**Arguments:**
- `path`: Directory or file to validate

**Options:**
- `--extensions`: File extensions to check (default: `.py`)

**Example:**
```bash
# Validate all routes in the src directory
pyodide-bridge validate-operation-ids src/

# Validate only specific file extensions
pyodide-bridge validate-operation-ids src/ --extensions .py,.pyx
```

### add-operation-ids

Automatically adds missing `operation_id` parameters to FastAPI route decorators.

```bash
pyodide-bridge add-operation-ids <path>
```

**Arguments:**
- `path`: Directory or file to process

**Options:**
- `--dry-run`: Show what would be changed without making changes
- `--extensions`: File extensions to process (default: `.py`)

**Example:**
```bash
# Add operation_id to all routes (dry run first)
pyodide-bridge add-operation-ids src/ --dry-run

# Actually add operation_id to all routes
pyodide-bridge add-operation-ids src/

# Process only specific file extensions
pyodide-bridge add-operation-ids src/ --extensions .py,.pyx
```

## Why operation_id is Required

The PyodideBridge requires all FastAPI routes to have an `operation_id` for:

1. **Bridge invocation**: The bridge uses `operation_id` to invoke specific endpoints
2. **Route discovery**: Endpoints are registered and discoverable by their `operation_id`
3. **Frontend integration**: The frontend calls endpoints using their `operation_id`

## Integration with Build Scripts

You can integrate these tools into your build process:

**package.json example:**
```json
{
  "scripts": {
    "validate:operation-ids": "pyodide-bridge validate-operation-ids src/",
    "migrate:operation-ids": "pyodide-bridge add-operation-ids src/",
    "build": "npm run validate:operation-ids && python -m build"
  }
}
```

**CI/CD example:**
```yaml
# .github/workflows/ci.yml
- name: Validate operation_ids
  run: pyodide-bridge validate-operation-ids src/
```

This ensures that all routes have the required `operation_id` before deployment.
