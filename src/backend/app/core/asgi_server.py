"""
Pyodide ASGI Server - Clean Architecture Alternative to Monkey-Patching

This module implements a proper ASGI 3.0 server that can run FastAPI
applications in Pyodide without any monkey-patching or modifications to FastAPI.

Usage:
    from fastapi import FastAPI
    from asgi_server import PyodideASGIServer

    app = FastAPI()

    @app.get("/api/users")
    def get_users():
        return {"users": []}

    # Wrap with ASGI server
    server = PyodideASGIServer(app)

    # Call from JavaScript
    response = await server.handle_request(scope)
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional
from urllib.parse import parse_qs

__version__ = "0.1.0"


class PyodideASGIServer:
    """
    ASGI 3.0 compliant server for running ASGI apps in Pyodide.

    This server implements the ASGI specification, allowing FastAPI and other
    ASGI frameworks to run without modification in the browser environment.

    Key features:
    - No monkey-patching required
    - Standard ASGI interface
    - Full middleware support
    - Request/Response objects work
    - OAuth2, forms, headers all standard
    """

    def __init__(self, app: Callable):
        """
        Initialize the ASGI server with an ASGI application.

        Args:
            app: ASGI 3.0 application callable (e.g., FastAPI app)
        """
        self.app = app

    async def handle_request(self, scope_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an HTTP request through the ASGI interface.

        This is the main entry point called from JavaScript. It:
        1. Converts the scope dict to proper ASGI format
        2. Calls the ASGI app with scope, receive, send
        3. Collects the response
        4. Returns it as a dict for JavaScript

        Args:
            scope_dict: Dictionary containing HTTP request information:
                - method: HTTP method (GET, POST, etc.)
                - path: URL path
                - query_string: Query string (optional)
                - headers: List of [name, value] tuples
                - body: Request body as bytes or string (optional)

        Returns:
            Dict with:
                - status: HTTP status code (int)
                - headers: List of [name, value] tuples
                - body: Response body as bytes
        """
        # Prepare ASGI scope
        scope = self._prepare_scope(scope_dict)

        # Create receive/send queues
        receive_queue = []
        send_queue = []

        # Prepare receive callable
        async def receive() -> Dict[str, Any]:
            """ASGI receive callable - provides request body."""
            if receive_queue:
                return receive_queue.pop(0)
            # No more body
            return {"type": "http.disconnect"}

        # Prepare send callable
        async def send(message: Dict[str, Any]) -> None:
            """ASGI send callable - collects response."""
            send_queue.append(message)

        # Add request body to receive queue
        body = scope_dict.get("body")
        if body:
            # Convert string to bytes if needed
            if isinstance(body, str):
                body = body.encode("utf-8")

            receive_queue.append({
                "type": "http.request",
                "body": body,
                "more_body": False
            })
        else:
            # Empty body
            receive_queue.append({
                "type": "http.request",
                "body": b"",
                "more_body": False
            })

        # Call the ASGI application
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            # Return error response
            return {
                "status": 500,
                "headers": [[b"content-type", b"application/json"]],
                "body": json.dumps({
                    "error": "Internal Server Error",
                    "detail": str(e)
                }).encode("utf-8")
            }

        # Build response from send_queue
        response = self._build_response(send_queue)
        return response

    def _prepare_scope(self, scope_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare ASGI scope from JavaScript request dict.

        Converts the simple JavaScript dict to a full ASGI 3.0 scope.
        """
        # Parse query string
        query_string = scope_dict.get("query_string", "")
        if isinstance(query_string, str):
            query_string = query_string.encode("utf-8")

        # Convert headers to bytes tuples
        headers = []
        for name, value in scope_dict.get("headers", []):
            if isinstance(name, str):
                name = name.encode("latin-1")
            if isinstance(value, str):
                value = value.encode("latin-1")
            headers.append([name, value])

        # Build ASGI scope
        scope = {
            "type": "http",
            "asgi": {
                "version": "3.0",
                "spec_version": "2.3"
            },
            "http_version": "1.1",
            "method": scope_dict.get("method", "GET").upper(),
            "scheme": scope_dict.get("scheme", "https"),
            "path": scope_dict.get("path", "/"),
            "query_string": query_string,
            "root_path": "",
            "headers": headers,
            "server": ("localhost", 443),
            "client": ("127.0.0.1", 0),
            "extensions": {},
        }

        return scope

    def _build_response(self, send_queue: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build response dict from ASGI send messages.

        Extracts status, headers, and body from the send_queue.
        """
        response = {
            "status": 200,
            "headers": [],
            "body": b""
        }

        body_chunks = 0
        for message in send_queue:
            msg_type = message.get("type")

            if msg_type == "http.response.start":
                response["status"] = message.get("status", 200)
                response["headers"] = message.get("headers", [])

            elif msg_type == "http.response.body":
                body = message.get("body", b"")
                if isinstance(body, str):
                    body = body.encode("utf-8")
                response["body"] += body
                body_chunks += 1

        print(
            f"📦 Collected {body_chunks} body chunks, total size: {len(response['body'])} bytes")
        return response


class StreamingASGIServer(PyodideASGIServer):
    """
    Enhanced ASGI server with streaming response support.

    This extends the basic server to support streaming responses,
    useful for Server-Sent Events (SSE) or large file transfers.
    """

    async def handle_streaming_request(
        self,
        scope_dict: Dict[str, Any],
        on_chunk: Callable[[bytes], Awaitable[None]],
        on_start: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Handle a request with streaming response support.

        Args:
            scope_dict: Request scope dictionary
            on_chunk: Async callback called for each response chunk

        Returns:
            Dict with status and headers (body streamed via on_chunk)
        """
        scope = self._prepare_scope(scope_dict)

        receive_queue = []
        response_info = {"status": 200, "headers": []}

        # Prepare receive
        async def receive() -> Dict[str, Any]:
            if receive_queue:
                return receive_queue.pop(0)
            return {"type": "http.disconnect"}

        # Prepare send with streaming
        async def send(message: Dict[str, Any]) -> None:
            msg_type = message.get("type")

            if msg_type == "http.response.start":
                response_info["status"] = message.get("status", 200)
                response_info["headers"] = message.get("headers", [])
                if on_start:
                    await on_start(response_info)

            elif msg_type == "http.response.body":
                body = message.get("body", b"")
                if body:
                    await on_chunk(body)

        # Add body to receive queue
        body = scope_dict.get("body")
        if body:
            if isinstance(body, str):
                body = body.encode("utf-8")
            receive_queue.append({
                "type": "http.request",
                "body": body,
                "more_body": False
            })
        else:
            receive_queue.append({
                "type": "http.request",
                "body": b"",
                "more_body": False
            })

        # Call app
        await self.app(scope, receive, send)

        return response_info


# Helper function to create server instance
def create_asgi_server(app: Callable, streaming: bool = False) -> PyodideASGIServer:
    """
    Create an ASGI server instance.

    Args:
        app: ASGI application (e.g., FastAPI app)
        streaming: Whether to enable streaming support

    Returns:
        PyodideASGIServer instance
    """
    if streaming:
        return StreamingASGIServer(app)
    return PyodideASGIServer(app)


__all__ = [
    "PyodideASGIServer",
    "StreamingASGIServer",
    "create_asgi_server",
]
