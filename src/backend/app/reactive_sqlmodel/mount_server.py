"""Server-side reactive sync mounting."""

from __future__ import annotations
import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Set
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, SQLModel, select

from .runtime import Runtime, set_runtime
from .sync_tables import ChangeLog

logger = logging.getLogger(__name__)


def mount_server(
    app: FastAPI,
    *,
    open_session: Callable[[], Session],
    get_session_dep,
    apply_mutation: Callable[[Session, dict, Any], dict],
    get_current_user: Optional[Callable] = None,
    can_read_topic: Optional[Callable[[Any, str], bool]] = None,
    can_write_topic: Optional[Callable[[Any, str], bool]] = None,
    sync_prefix: str = "/_sync",
    ensure_tables: bool = True,
) -> None:
    """Mount server-side reactive sync endpoints.

    Adds three endpoints to the FastAPI app:
    - POST {sync_prefix}/pull - Client pulls changes for a topic
    - POST {sync_prefix}/push - Client pushes mutations to server
    - GET {sync_prefix}/events - SSE stream for poke notifications

    Args:
        app: FastAPI application instance
        open_session: Factory function that returns a Session
        get_session_dep: FastAPI dependency for getting a session
        apply_mutation: Callback (session, mutation_dict, user) -> dict{topic, table, pk, row}
        get_current_user: Optional auth dependency
        can_read_topic: Optional (user, topic) -> bool callback
        can_write_topic: Optional (user, topic) -> bool callback
        sync_prefix: URL prefix for sync endpoints (default: "/_sync")
        ensure_tables: Whether to create sync tables on startup (default: True)
    """

    # Set runtime for active-record support on server
    set_runtime(Runtime(open_session=open_session, sync=None))

    # SSE connection management
    # Dict[topic, Set[asyncio.Queue]] - each queue is for one SSE connection
    topic_subscribers: Dict[str, Set[asyncio.Queue]] = {}

    async def poke(topic: str, checkpoint: int) -> None:
        """Broadcast a poke notification to all subscribers of a topic.

        Args:
            topic: Topic string (e.g., "room:general")
            checkpoint: Latest version number for this topic
        """
        if topic not in topic_subscribers:
            return

        message = {
            "type": "poke",
            "topic": topic,
            "checkpoint": checkpoint,
        }
        message_json = json.dumps(message)

        # Send to all subscribers
        dead_queues = set()
        for queue in topic_subscribers[topic]:
            try:
                queue.put_nowait(message_json)
            except asyncio.QueueFull:
                # Mark for removal
                dead_queues.add(queue)
            except Exception:
                dead_queues.add(queue)

        # Clean up dead connections
        for queue in dead_queues:
            topic_subscribers[topic].discard(queue)

    @app.on_event("startup")
    def _startup() -> None:
        """Create ChangeLog table on startup if needed."""
        if not ensure_tables:
            return

        with open_session() as session:
            # Create only the ChangeLog table (sync metadata)
            # Model tables should be created by the app's normal init process
            engine = session.get_bind()
            SQLModel.metadata.create_all(
                engine,
                tables=[ChangeLog.__table__]
            )

    # Build auth dependency if provided
    def _get_auth_dep():
        if get_current_user is not None:
            return Depends(get_current_user)
        return None

    @app.post(f"{sync_prefix}/pull")
    def pull(
        payload: dict,
        session: Session = Depends(get_session_dep),
        user: Any = _get_auth_dep(),
    ) -> dict:
        """Pull changes for a topic since a checkpoint.

        Request body:
            {
                "topic": "room:general",
                "since": 123
            }

        Response:
            {
                "topic": "room:general",
                "checkpoint": 150,
                "changes": [
                    {
                        "version": 124,
                        "topic": "room:general",
                        "table": "messages",
                        "pk": "uuid-123",
                        "row": {...} or null
                    },
                    ...
                ]
            }
        """
        topic = payload.get("topic")
        since = int(payload.get("since", 0))

        if not topic:
            raise HTTPException(status_code=400, detail="Missing 'topic' field")

        # Check authorization
        if can_read_topic is not None and not can_read_topic(user, topic):
            raise HTTPException(status_code=403, detail="No access to topic")

        # Query ChangeLog for changes since checkpoint
        statement = (
            select(ChangeLog)
            .where(ChangeLog.topic == topic)
            .where(ChangeLog.version > since)
            .order_by(ChangeLog.version)
        )

        rows = session.exec(statement).all()

        # Build response
        checkpoint = since
        changes = []
        for row in rows:
            checkpoint = int(row.version)
            changes.append({
                "version": checkpoint,
                "topic": row.topic,
                "table": row.table_name,
                "pk": row.pk,
                "row": json.loads(row.row_json) if row.row_json is not None else None,
            })

        return {
            "topic": topic,
            "checkpoint": checkpoint,
            "changes": changes,
        }

    @app.post(f"{sync_prefix}/push")
    async def push(
        payload: dict,
        session: Session = Depends(get_session_dep),
        user: Any = _get_auth_dep(),
    ) -> dict:
        """Push mutations from client to server.

        Request body:
            {
                "mutations": [
                    {
                        "id": "uuid-abc",
                        "topic": "room:general",
                        "table": "messages",
                        "pk": "123",
                        "patch": {...}
                    },
                    ...
                ]
            }

        Response:
            {
                "accepted": ["uuid-abc", ...]
            }
        """
        # CRITICAL: Log immediately to verify function is called
        logger.error("=" * 80)  # Use error level to ensure it shows
        logger.error("[push] FUNCTION CALLED - AFTER DOCSTRING")
        logger.error(f"[push] Payload type: {type(payload)}")
        logger.error(f"[push] Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'NOT A DICT'}")
        logger.error("=" * 80)
        import sys
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("[push] STDERR TEST\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        try:
            # Use both logger and print to ensure we see the output
            import sys
            sys.stdout.flush()  # Force flush
            print(f"[push] ENDPOINT CALLED - Payload keys: {list(payload.keys())}", flush=True)
            logger.info(f"[push] ENDPOINT CALLED - Payload keys: {list(payload.keys())}")
            mutations = payload.get("mutations", [])
            accepted = []
            
            logger.info(f"[push] Received {len(mutations)} mutations")
            logger.info(f"[push] can_write_topic: {can_write_topic}")
            logger.info(f"[push] user: {user}")

            for mutation in mutations:
                logger.info(f"[push] Processing mutation {mutation.get('id')}")
                logger.info(f"[push] Full mutation: {mutation}")
                topic = mutation.get("topic")
                logger.info(f"[push] Topic: {topic}")

                # Check authorization
                if can_write_topic is not None and not can_write_topic(user, topic):
                    logger.warning(f"[push] Authorization failed for topic: {topic}")
                    continue  # Skip unauthorized mutations
                else:
                    logger.info(f"[push] Authorization passed (can_write_topic is None or check passed)")

                # Apply mutation via callback
                try:
                    result = apply_mutation(session, mutation, user)
                    # result = {topic, table, pk, row}

                    # Write to ChangeLog
                    changelog_entry = ChangeLog(
                        topic=result["topic"],
                        table_name=result["table"],
                        pk=result["pk"],
                        row_json=json.dumps(result["row"]) if result["row"] is not None else None,
                    )
                    session.add(changelog_entry)
                    session.commit()
                    session.refresh(changelog_entry)

                    # Broadcast poke notification
                    await poke(result["topic"], int(changelog_entry.version))

                    # Mark as accepted
                    accepted.append(mutation["id"])

                except Exception as e:
                    # Log error but continue processing other mutations
                    import traceback
                    error_tb = traceback.format_exc()
                    logger.error(f"Error applying mutation {mutation.get('id')}: {e}")
                    logger.error(f"Traceback: {error_tb}")
                    print(f"[push] ERROR applying mutation {mutation.get('id')}: {e}", flush=True)
                    print(f"[push] Traceback:\n{error_tb}", flush=True)
                    import sys
                    sys.stderr.write(f"[push] ERROR: {e}\n{error_tb}\n")
                    sys.stderr.flush()
                    continue

            logger.info(f"[push] Returning accepted: {accepted}")
            print(f"[push] Returning accepted: {accepted}", flush=True)
            return {"accepted": accepted}
        except Exception as e:
            import traceback
            error_msg = f"[push] EXCEPTION: {e}\n{traceback.format_exc()}"
            print(error_msg, flush=True)
            logger.error(error_msg)
            return {"accepted": []}

    @app.get(f"{sync_prefix}/events")
    async def events(
        topics: str,  # Comma-separated topic list
        user: Any = _get_auth_dep(),
    ) -> StreamingResponse:
        """SSE stream for poke notifications.

        Query params:
            topics: Comma-separated list of topics to subscribe to
                    e.g., "room:general,user:123"

        SSE format:
            data: {"type":"poke","topic":"room:general","checkpoint":150}\\n\\n
        """
        # Parse topics
        topic_list = [t.strip() for t in topics.split(",") if t.strip()]

        if not topic_list:
            raise HTTPException(status_code=400, detail="No topics specified")

        # Check authorization
        if can_read_topic is not None:
            for topic in topic_list:
                if not can_read_topic(user, topic):
                    raise HTTPException(
                        status_code=403,
                        detail=f"No access to topic: {topic}"
                    )

        # Create queue for this connection
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

        # Subscribe to all requested topics
        for topic in topic_list:
            if topic not in topic_subscribers:
                topic_subscribers[topic] = set()
            topic_subscribers[topic].add(queue)

        async def event_generator():
            """Generate SSE events from the queue."""
            try:
                # Send initial connection confirmation
                yield f"data: {json.dumps({'type': 'connected', 'topics': topic_list})}\\n\\n"

                while True:
                    # Wait for next message (with timeout for keepalive)
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"data: {message}\\n\\n"
                    except asyncio.TimeoutError:
                        # Send keepalive ping
                        yield f": keepalive\\n\\n"

            except asyncio.CancelledError:
                # Connection closed
                pass
            finally:
                # Cleanup: unsubscribe from all topics
                for topic in topic_list:
                    if topic in topic_subscribers:
                        topic_subscribers[topic].discard(queue)
                        if not topic_subscribers[topic]:
                            del topic_subscribers[topic]

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
