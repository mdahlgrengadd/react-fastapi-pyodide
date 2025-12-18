"""Sync metadata tables for reactive synchronization."""

from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field


class ChangeLog(SQLModel, table=True):
    """Server-side change log tracking all mutations.

    Each row represents a change to a specific record in a specific table.
    Clients pull changes by querying for version > their checkpoint.

    Attributes:
        version: Auto-incrementing sequence number (PRIMARY KEY)
        topic: Subscription topic (e.g., "room:general", "user:123")
        table_name: Name of the table that changed
        pk: Primary key of the changed record (as string)
        row_json: JSON-serialized row data (None = delete tombstone)
    """
    __tablename__ = "changelog"

    version: Optional[int] = Field(default=None, primary_key=True)
    topic: str = Field(index=True)
    table_name: str
    pk: str
    row_json: Optional[str] = None  # None indicates delete


class Checkpoint(SQLModel, table=True):
    """Client-side checkpoint tracking sync state per topic.

    Stores the last version number the client has synchronized for each topic.

    Attributes:
        topic: Subscription topic (PRIMARY KEY)
        ver: Last synchronized version number
    """
    __tablename__ = "checkpoint"

    topic: str = Field(primary_key=True)
    ver: int = 0


class Mutation(SQLModel, table=True):
    """Client-side pending mutations queue.

    Stores local changes that haven't been pushed to the server yet.

    Attributes:
        id: Unique mutation ID (UUID, PRIMARY KEY)
        topic: Subscription topic for this mutation
        table_name: Name of the table being mutated
        pk: Primary key of the record (as string)
        patch_json: JSON-serialized row data (full row for v0.1)
    """
    __tablename__ = "mutation"

    id: str = Field(primary_key=True)
    topic: str
    table_name: str
    pk: str
    patch_json: str  # JSON-serialized row data
