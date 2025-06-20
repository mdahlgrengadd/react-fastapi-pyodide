"""
Test demonstrating monkey-patch functionality.

This shows how existing FastAPI code can work unchanged in Pyodide.
"""


def test_monkey_patch():
    """Test that monkey-patching allows unmodified FastAPI code to work."""

    # Step 1: Enable monkey-patch
    from pyodide_bridge import enable_monkey_patch
    enable_monkey_patch()

    # Step 2: Import FastAPI normally (this is now the bridge version!)
    from fastapi import FastAPI

    # Step 3: Write normal FastAPI code with NO changes
    app = FastAPI(title="Monkey-Patched API")

    @app.get("/users/{user_id}")  # No operation_id needed!
    async def get_user(user_id: int):
        return {"id": user_id, "name": f"User {user_id}"}

    @app.post("/users")  # No operation_id needed!
    async def create_user(name: str):
        return {"id": 123, "name": name}

    # Step 4: Use bridge functionality (this works because of monkey-patch!)
    print("Testing monkey-patched FastAPI app...")

    # Check that we have bridge methods
    assert hasattr(app, 'invoke'), "App should have bridge invoke method"
    assert hasattr(
        app, 'get_endpoints'), "App should have bridge get_endpoints method"

    # Check that endpoints were registered with auto-generated operation_ids
    endpoints = app.get_endpoints()
    print(f"Found {len(endpoints)} endpoints:")
    for endpoint in endpoints:
        print(
            f"  - {endpoint['operationId']}: {endpoint['method']} {endpoint['path']}")

    # The operation_ids should be auto-generated from function names
    operation_ids = [ep['operationId'] for ep in endpoints]
    assert 'get_user' in operation_ids, "get_user operation_id should be auto-generated"
    assert 'create_user' in operation_ids, "create_user operation_id should be auto-generated"

    print("✅ Monkey-patch test passed!")
    print("✅ Existing FastAPI code works unchanged!")

    return app


if __name__ == "__main__":
    app = test_monkey_patch()

    # Demonstrate that this is actually the bridge version
    print(f"\nApp type: {type(app)}")
    print(f"Has bridge methods: {hasattr(app, 'invoke')}")

    # Show endpoints
    endpoints = app.get_endpoints()
    print(f"\nRegistered endpoints: {len(endpoints)}")
    for ep in endpoints:
        print(f"  {ep['operationId']}: {ep['method']} {ep['path']}")
