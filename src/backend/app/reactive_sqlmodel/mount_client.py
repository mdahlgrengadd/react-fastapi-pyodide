"""Client-side reactive sync mounting."""

from __future__ import annotations
import json
import uuid
from typing import Any, Callable, Dict, List, Optional
from fastapi import FastAPI
from sqlmodel import Session, SQLModel, select

from .runtime import Runtime, set_runtime
from .sync_tables import Checkpoint, Mutation
from .transport import Transport


class ClientSync:
    """Client-side synchronization manager.

    Handles:
    - Mutation queueing and acknowledgement
    - Checkpoint tracking per topic
    - Push/pull operations
    - Hooks for ReactiveModel save/delete
    """

    def __init__(
        self,
        *,
        transport: Transport,
        open_session: Callable[[], Session],
        sync_prefix: str = "/_sync",
    ):
        """Initialize client sync.

        Args:
            transport: Transport instance for server communication
            open_session: Factory function that returns a Session
            sync_prefix: URL prefix for sync endpoints
        """
        self.transport = transport
        self.open_session = open_session
        self.sync_prefix = sync_prefix

    def _get_checkpoint(self, topic: str) -> int:
        """Get the last synchronized version for a topic.

        Args:
            topic: Topic string

        Returns:
            Last synchronized version number (0 if never synced)
        """
        with self.open_session() as session:
            row = session.get(Checkpoint, topic)
            return row.ver if row else 0

    def _set_checkpoint(self, topic: str, ver: int) -> None:
        """Update the synchronized version for a topic.

        Args:
            topic: Topic string
            ver: New version number
        """
        with self.open_session() as session:
            row = session.get(Checkpoint, topic)
            if row:
                row.ver = ver
            else:
                row = Checkpoint(topic=topic, ver=ver)
            session.add(row)
            session.commit()

    def _enqueue(self, topic: str, table: str, pk: str, patch: dict) -> str:
        """Enqueue a pending mutation.

        Args:
            topic: Topic string
            table: Table name
            pk: Primary key (as string)
            patch: Full row data as dict

        Returns:
            Mutation ID (UUID)
        """
        mutation_id = str(uuid.uuid4())

        with self.open_session() as session:
            mutation = Mutation(
                id=mutation_id,
                topic=topic,
                table_name=table,
                pk=pk,
                patch_json=json.dumps(patch),
            )
            session.add(mutation)
            session.commit()

        return mutation_id

    def _dequeue(self) -> List[Dict[str, Any]]:
        """Get all pending mutations.

        Returns:
            List of mutation dicts
        """
        with self.open_session() as session:
            rows = list(session.exec(select(Mutation)))
            return [
                {
                    "id": row.id,
                    "topic": row.topic,
                    "table": row.table_name,
                    "pk": row.pk,
                    "patch": json.loads(row.patch_json),
                }
                for row in rows
            ]

    def _ack(self, ids: List[str]) -> None:
        """Acknowledge and remove accepted mutations.

        Args:
            ids: List of mutation IDs to acknowledge
        """
        if not ids:
            return

        with self.open_session() as session:
            for mutation_id in ids:
                row = session.get(Mutation, mutation_id)
                if row:
                    session.delete(row)
            session.commit()

    def push(self) -> None:
        """Push pending mutations to server.

        Sends all queued mutations to the server and acknowledges
        accepted ones. Non-blocking - uses fire-and-forget approach.
        """
        # Get pending mutations
        mutations = self._dequeue()
        if not mutations:
            return

        # Push to server (non-blocking - transport uses setTimeout on JS side)
        # Transport returns {"accepted": []} immediately to avoid blocking
        # Mutations will be retried on next push() if sync fails
        try:
            response = self.transport.post_json(
                f"{self.sync_prefix}/push",
                {"mutations": mutations},
            )

            # Acknowledge accepted mutations (if any)
            accepted = response.get("accepted", [])
            if accepted:
                self._ack(accepted)

        except Exception as e:
            # Log error but don't raise - mutations stay queued for retry
            print(f"Error pushing mutations: {e}")

    def pull(self, topic: str, apply_change: Callable[[str, str, Optional[dict]], None]) -> None:
        """Pull changes from server for a topic.

        Args:
            topic: Topic to pull changes for
            apply_change: Callback (table, pk, row) to apply each change
        """
        # Get current checkpoint
        since = self._get_checkpoint(topic)

        try:
            # Pull from server
            response = self.transport.post_json(
                f"{self.sync_prefix}/pull",
                {"topic": topic, "since": since},
            )

            # Apply changes
            for change in response.get("changes", []):
                apply_change(
                    change["table"],
                    change["pk"],
                    change["row"],
                )

            # Update checkpoint
            new_checkpoint = int(response.get("checkpoint", since))
            self._set_checkpoint(topic, new_checkpoint)

        except Exception as e:
            # Log error but don't raise
            print(f"Error pulling topic {topic}: {e}")

    def on_save(self, obj: Any) -> None:
        """Hook called by ReactiveModel.save().

        Enqueues a mutation and immediately pushes to server.

        Args:
            obj: Model instance being saved
        """
        # Get topics for this object
        topics_func = getattr(obj, "__topics__", None)
        if callable(topics_func):
            topics = topics_func(obj)
        else:
            # Fallback: use table name
            topics = [f"table:{obj.__table__.name}"]

        if not topics:
            return

        # Use first topic for mutation
        topic = topics[0]

        # Get primary key
        pk = str(getattr(obj, "id"))  # Assume 'id' field for now

        # Serialize full row (use mode='json' to handle datetime objects)
        patch = obj.model_dump(mode='json')
        
        # Filter out immutable fields that shouldn't be sent in mutations
        # These fields are set by the database/server and shouldn't be updated
        immutable_fields = {'created_at', 'updated_at'}  # Add other immutable fields as needed
        patch = {k: v for k, v in patch.items() if k not in immutable_fields}

        # Enqueue mutation
        self._enqueue(topic, obj.__table__.name, pk, patch)

        # Push immediately
        self.push()

    def on_delete(self, obj: Any) -> None:
        """Hook called by ReactiveModel.delete().

        Enqueues a delete mutation and immediately pushes to server.

        Args:
            obj: Model instance being deleted
        """
        # Get topics for this object
        topics_func = getattr(obj, "__topics__", None)
        if callable(topics_func):
            topics = topics_func(obj)
        else:
            # Fallback: use table name
            topics = [f"table:{obj.__table__.name}"]

        if not topics:
            return

        # Use first topic for mutation
        topic = topics[0]

        # Get primary key
        pk = str(getattr(obj, "id"))

        # Enqueue delete mutation (patch=None for tombstone)
        # Note: In v0.1, we're using full row patch, so we send the current state
        # Future: Implement proper delete tombstones
        patch = obj.model_dump(mode='json')

        self._enqueue(topic, obj.__table__.name, pk, patch)

        # Push immediately
        self.push()


def mount_client(
    app: FastAPI,
    *,
    local_engine,
    models: List[type[SQLModel]],
    transport: Transport,
    sync_prefix: str = "/_sync",
) -> None:
    """Mount client-side reactive sync.

    Sets up:
    - Local SQLite cache with sync tables
    - ClientSync instance
    - Runtime with active-record support
    - Poke handler for TypeScript integration

    Args:
        app: FastAPI application instance
        local_engine: SQLAlchemy Engine for local SQLite database
        models: List of model classes to sync
        transport: Transport instance for server communication
        sync_prefix: URL prefix for sync endpoints
    """
    # Create all tables (models + sync metadata)
    all_tables = [m.__table__ for m in models] + [
        Checkpoint.__table__,
        Mutation.__table__,
    ]
    SQLModel.metadata.create_all(local_engine, tables=all_tables)

    # Session factory
    def open_session() -> Session:
        return Session(local_engine)

    # Build table name -> model class mapping
    table_to_model: Dict[str, type[SQLModel]] = {
        model.__table__.name: model for model in models
    }

    def apply_change(table: str, pk: str, row: Optional[dict]) -> None:
        """Apply a change from the server to local cache.

        Args:
            table: Table name
            pk: Primary key (as string)
            row: Row data dict (None = delete)
        """
        model_class = table_to_model.get(table)
        if not model_class:
            print(f"Warning: Unknown table '{table}' in change")
            return

        with open_session() as session:
            if row is None:
                # Delete
                obj = session.get(model_class, pk)
                if obj:
                    session.delete(obj)
            else:
                # Upsert
                try:
                    # Validate and create model instance
                    obj = model_class.model_validate(row)
                    # Use merge to handle both insert and update
                    session.merge(obj)
                except Exception as e:
                    print(f"Error applying change to {table}#{pk}: {e}")
                    return

            session.commit()

    # Create sync instance
    sync = ClientSync(
        transport=transport,
        open_session=open_session,
        sync_prefix=sync_prefix,
    )

    # Set runtime for active-record support
    runtime_obj = Runtime(open_session=open_session, sync=sync)
    set_runtime(runtime_obj)
    print(f"🔧 Set runtime in mount_client: {runtime_obj}")
    
    # Verify it was set
    from .runtime import get_runtime
    try:
        verified = get_runtime()
        print(f"✅ Verified runtime is set: {verified}")
    except RuntimeError as e:
        print(f"❌ Runtime verification failed: {e}")

    # Expose poke handler for TypeScript
    # TypeScript will call: app.state.handle_poke(topic)
    app.state.handle_poke = lambda topic: sync.pull(topic, apply_change)
    
    # Expose acknowledgment callback for JavaScript
    # JavaScript will call: __reactive_sync_ack(accepted_ids) after push response
    def ack_mutations(accepted_ids):
        """Acknowledge mutations that were accepted by the server.
        
        Called by JavaScript after receiving push response.
        """
        sync._ack(accepted_ids)
    
    # Store in global scope for JavaScript access
    import builtins
    builtins.__reactive_sync_ack = ack_mutations
