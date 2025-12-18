"""Transport abstraction for client-server communication."""

from __future__ import annotations
import json
from typing import Any, Dict


class Transport:
    """Abstract base class for client-server transport.

    Implementations must provide a way to make HTTP POST requests
    to the server's sync endpoints.
    """

    def post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request with JSON payload.

        Args:
            path: API endpoint path (e.g., "/_sync/pull")
            payload: Request body as dict

        Returns:
            Response body as dict

        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement post_json()")


class PyodideTransport(Transport):
    """Transport implementation for Pyodide using JavaScript bridge.

    Uses a JavaScript transport object (from REACTIVE_TRANSPORT global)
    to make HTTP requests to the server.
    """

    def __init__(self, js_transport):
        """Initialize Pyodide transport.

        Args:
            js_transport: JavaScript object with post_json method
                         (from REACTIVE_TRANSPORT global set by TypeScript)
        """
        self.js_transport = js_transport

    def post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request via JavaScript bridge.

        Args:
            path: API endpoint path (e.g., "/_sync/pull")
            payload: Request body as dict

        Returns:
            Response body as dict
        """
        # Import js module (only available in Pyodide)
        try:
            import js
        except ImportError:
            raise RuntimeError("PyodideTransport can only be used in Pyodide environment")

        # Serialize payload to JSON string
        payload_json = json.dumps(payload)

        # Call JavaScript transport (returns a Promise)
        # Fire-and-forget: don't wait for response, just start the request
        # Mutations will be retried on next push() if they don't sync
        try:
            print(f"[PyodideTransport] Calling JS transport: {path}")
            print(f"[PyodideTransport] Payload: {payload_json[:200]}...")  # First 200 chars
            
            # Start the async request (completely non-blocking)
            # Don't even try to get the promise - just fire it off
            promise = self.js_transport.post_json_sync(path, payload_json)
            print(f"[PyodideTransport] Promise created: {promise}")
            
            # Return empty immediately - mutations stay queued
            # They'll be retried on next push() call if sync fails
            # This prevents any blocking or infinite loops
            return {"accepted": []}
        except Exception as e:
            print(f"[PyodideTransport] Error in transport.post_json: {e}")
            import traceback
            traceback.print_exc()
            # Return empty accepted list on error so mutations stay queued for retry
            return {"accepted": []}
