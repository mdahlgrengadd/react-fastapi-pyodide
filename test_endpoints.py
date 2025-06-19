#!/usr/bin/env python3
"""Test script to show all available endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'backend', 'src'))

from app.app_main import app


print("🚀 FastAPI + Pyodide Bridge - Available Endpoints")
print("=" * 50)

endpoints = app.get_endpoints()
print(f"Found {len(endpoints)} user-facing endpoints:\n")

for ep in endpoints:
    print(f"• {ep['operationId']}")
    print(f"  Method: {ep['method']}")
    print(f"  Path: {ep['path']}")
    print(f"  Summary: {ep['summary']}")
    print(f"  Tags: {ep['tags']}")
    print()

# Also show all registered endpoints (including meta ones)
print("\n" + "=" * 50)
print("All registered endpoints (including meta):")
print("=" * 50)

registry = app.get_registry()
for op_id, route_info in registry.items():
    status = "🔒 Meta" if op_id in [
        "get_bridge_endpoints", "get_bridge_registry", "invoke_bridge_endpoint"] else "✅ Public"
    print(f"{status} {op_id}: {route_info['method']} {route_info['path']}")
