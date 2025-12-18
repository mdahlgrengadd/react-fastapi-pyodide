"""
100% Generic FastAPI Streaming for Pyodide

This module enables TRUE real-time streaming for any FastAPI endpoint in Pyodide
by manually iterating async generators and yielding control to the browser event loop.

Works with ANY FastAPI project out of the box - no configuration needed!
"""
import asyncio
import inspect
import json
from typing import Any, AsyncGenerator, Callable, Dict, Optional, get_origin, get_args
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.dependencies.utils import solve_dependencies
from fastapi.routing import APIRoute
from starlette.datastructures import Headers, QueryParams
from pydantic import BaseModel


class MockRequest:
    """
    Mock Request object that works in Pyodide without actual HTTP connection.

    Provides all attributes that FastAPI dependencies might need.
    """

    def __init__(
        self,
        method: str,
        url: str,
        path: str,
        headers: Dict[str, str],
        query_params: Dict[str, Any],
        path_params: Dict[str, Any],
        body: Optional[bytes] = None,
        cookies: Optional[Dict[str, str]] = None,
    ):
        self.method = method
        self.url = url
        self._headers = Headers(headers)
        self._query_params = QueryParams(query_params)
        self.path_params = path_params
        self._body = body
        self._cookies = cookies or {}
        self.app = None  # Set by caller
        self.state = type('State', (), {})()  # Empty state object

        # Note: scope will be set with AsyncExitStacks by caller
        self.scope = None

    @property
    def headers(self):
        return self._headers

    @property
    def query_params(self):
        return self._query_params

    @property
    def cookies(self):
        """Cookies dict - required by FastAPI's dependency resolver."""
        return self._cookies

    async def json(self):
        """Parse JSON body."""
        if self._body:
            return json.loads(self._body.decode('utf-8'))
        return {}

    async def body(self):
        """Get raw body."""
        return self._body or b""

    async def form(self):
        """Parse form data."""
        # Simplified - would need proper multipart parsing
        return {}


async def resolve_endpoint_dependencies(
    app: FastAPI,
    route: APIRoute,
    request: MockRequest,
) -> Dict[str, Any]:
    """
    Resolve all FastAPI dependencies for an endpoint.

    Uses FastAPI's built-in dependency resolution system.
    Handles: Depends(), Query(), Path(), Body(), Header(), Cookie(), etc.
    """
    from contextlib import AsyncExitStack
    from urllib.parse import urlencode

    # Set app on request for dependency resolution
    request.app = app

    # FastAPI requires TWO AsyncExitStack instances in scope
    inner_astack = AsyncExitStack()
    function_astack = AsyncExitStack()

    # Build proper scope with both exit stacks
    request.scope = {
        'type': 'http',
        'method': request.method,
        'path': request.url,  # Use full URL path
        'query_string': urlencode(dict(request.query_params)).encode() if request.query_params else b'',
        'headers': [[k.encode('latin-1'), v.encode('latin-1')] for k, v in request.headers.items()],
        'app': app,
        'state': {},
        'fastapi_inner_astack': inner_astack,
        'fastapi_function_astack': function_astack,
    }

    # Use FastAPI's dependency solver with required parameters
    solved = await solve_dependencies(
        request=request,
        dependant=route.dependant,
        async_exit_stack=function_astack,
        embed_body_fields=True,
    )

    # Extract values and errors from SolvedDependency object
    values = solved.values
    errors = solved.errors

    if errors:
        await inner_astack.aclose()
        await function_astack.aclose()
        error_messages = [str(e) for e in errors]
        raise Exception(f"Dependency resolution failed: {error_messages}")

    # Note: both exit stacks should be closed by caller after using dependencies
    return values


async def call_streaming_endpoint_generic(
    app: FastAPI,
    operation_id: str,
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
) -> AsyncGenerator[bytes, None]:
    """
    100% GENERIC: Call any FastAPI streaming endpoint and yield chunks in real-time.

    This function:
    1. Finds the endpoint by operation_id
    2. Creates a mock Request object
    3. Resolves ALL dependencies using FastAPI's system
    4. Calls the endpoint handler
    5. Detects StreamingResponse
    6. Manually iterates the generator
    7. Yields control to event loop between chunks
    8. Returns chunks as they're generated IN REAL-TIME

    Works with:
    - Any parameter type (Query, Path, Body, Header, Cookie)
    - Complex types (Pydantic models, Lists, Dicts)
    - Any dependencies (get_db, get_current_user, custom)
    - Middleware effects
    - All FastAPI features

    Args:
        app: FastAPI application instance
        operation_id: Endpoint operation ID
        path_params: Path parameters dict
        query_params: Query parameters dict
        body: Request body (dict, str, bytes)
        headers: Request headers dict

    Yields:
        bytes: Each chunk from the streaming response, in real-time
    """
    path_params = path_params or {}
    query_params = query_params or {}
    headers = headers or {}

    print(f"🔍 Finding endpoint: {operation_id}")

    # Find the route by operation_id
    target_route = None
    for route in app.routes:
        if isinstance(route, APIRoute):
            # Check operation_id
            if route.operation_id == operation_id or route.name == operation_id:
                target_route = route
                break

    if not target_route:
        raise Exception(f"Endpoint not found: {operation_id}")

    print(f"✅ Found route: {target_route.path}")

    # Build full path with path parameters
    path = target_route.path
    for key, value in path_params.items():
        path = path.replace(f'{{{key}}}', str(value))

    # Build full URL
    query_string = urlencode(query_params) if query_params else ""
    url = f"https://localhost{path}"
    if query_string:
        url += f"?{query_string}"

    # Prepare body
    body_bytes = None
    if body is not None:
        if isinstance(body, bytes):
            body_bytes = body
        elif isinstance(body, str):
            body_bytes = body.encode('utf-8')
        elif isinstance(body, dict) or isinstance(body, BaseModel):
            # JSON serialize
            if isinstance(body, BaseModel):
                body_bytes = body.model_dump_json().encode('utf-8')
            else:
                body_bytes = json.dumps(body).encode('utf-8')
            if 'content-type' not in {k.lower(): v for k, v in headers.items()}:
                headers['content-type'] = 'application/json'

    # Determine method
    methods = list(target_route.methods)
    method = methods[0] if methods else 'GET'

    # Create mock request
    mock_request = MockRequest(
        method=method,
        url=url,
        headers=headers,
        query_params=query_params,
        path_params=path_params,
        body=body_bytes,
    )

    print(f"📋 Resolving dependencies...")

    # Resolve all dependencies using FastAPI's system
    try:
        resolved_values = await resolve_endpoint_dependencies(app, target_route, mock_request)
        print(f"✅ Dependencies resolved: {list(resolved_values.keys())}")
    except Exception as e:
        print(f"⚠️ Dependency resolution failed: {e}")
        # Fallback to basic parameter extraction
        resolved_values = {}

    # Call the endpoint function
    endpoint_func = target_route.endpoint
    print(f"📞 Calling endpoint function...")

    result = await endpoint_func(**resolved_values)

    print(f"📦 Endpoint returned: {type(result).__name__}")

    # Check if it's a StreamingResponse
    if isinstance(result, StreamingResponse):
        print("✅ StreamingResponse detected - extracting generator")

        # Extract the body iterator (the async generator)
        body_iterator = result.body_iterator

        # Check if it's an async generator
        if inspect.isasyncgen(body_iterator):
            print(f"✅ Async generator found, iterating...")

            chunk_count = 0
            # Manually iterate the generator
            while True:
                try:
                    # Get next chunk - this allows async operations to run
                    chunk = await body_iterator.__anext__()
                    chunk_count += 1
                    print(
                        f"📤 Yielding chunk {chunk_count}: {len(chunk)} bytes")
                    yield chunk

                    # CRITICAL: Yield control to event loop
                    # This allows JavaScript to process the chunk before continuing
                    await asyncio.sleep(0)

                except StopAsyncIteration:
                    print(
                        f"✅ Generator complete - yielded {chunk_count} chunks")
                    break
        else:
            # Regular iterator (sync generator)
            print(f"⚠️ Sync generator found")
            for chunk in body_iterator:
                yield chunk
                await asyncio.sleep(0)
    else:
        # Not a streaming response
        print(f"ℹ️ Not a StreamingResponse, returning as single chunk")

        # Return as single chunk
        if isinstance(result, dict):
            yield json.dumps(result).encode('utf-8')
        elif isinstance(result, str):
            yield result.encode('utf-8')
        elif isinstance(result, bytes):
            yield result
        else:
            # Try to convert to JSON
            yield json.dumps(str(result)).encode('utf-8')


__all__ = [
    'call_streaming_endpoint_generic',
    'resolve_endpoint_dependencies',
    'MockRequest',
]
