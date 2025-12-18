"""ReactiveModel base class with active-record pattern."""

from __future__ import annotations
from typing import Any, ClassVar, Optional, Callable, List
from sqlmodel import SQLModel, select

from .runtime import get_runtime


class ReactiveModel(SQLModel):
    """Base class for reactive models with active-record pattern.

    Provides class methods for querying and instance methods for persistence
    that automatically trigger synchronization.

    Usage:
        class User(ReactiveModel, table=True):
            id: Optional[int] = Field(default=None, primary_key=True)
            name: str

            @staticmethod
            def __topics__(user: "User") -> list[str]:
                return [f"user:{user.id}"]

        # Query
        user = User.get(1)
        users = User.all()
        active_users = User.find(is_active=True)

        # Persist
        user.name = "Updated"
        user.save()  # Triggers sync
        user.delete()  # Triggers sync

    Attributes:
        __topics__: Optional callable that returns list of topic strings for an instance
    """

    # Override this in subclasses to specify topic mapping
    __topics__: ClassVar[Optional[Callable[[Any], List[str]]]] = None

    @classmethod
    def get(cls, pk: Any):
        """Get a single record by primary key.

        Args:
            pk: Primary key value

        Returns:
            Model instance or None if not found

        Example:
            >>> user = User.get(1)
            >>> if user:
            ...     print(user.name)
        """
        runtime = get_runtime()
        with runtime.open_session() as session:
            return session.get(cls, pk)

    @classmethod
    def all(cls):
        """Get all records for this model.

        Returns:
            List of model instances

        Example:
            >>> users = User.all()
            >>> for user in users:
            ...     print(user.name)
        """
        runtime = get_runtime()
        with runtime.open_session() as session:
            statement = select(cls)
            results = session.exec(statement)
            return list(results)

    @classmethod
    def find(cls, **filters):
        """Find records matching filter criteria.

        Args:
            **filters: Keyword arguments for filtering (field=value)

        Returns:
            List of model instances matching the filters

        Example:
            >>> active_users = User.find(is_active=True)
            >>> bob_users = User.find(name="Bob")
        """
        runtime = get_runtime()
        with runtime.open_session() as session:
            statement = select(cls)

            # Apply filters
            for field_name, value in filters.items():
                if not hasattr(cls, field_name):
                    raise AttributeError(
                        f"{cls.__name__} has no attribute '{field_name}'"
                    )
                field = getattr(cls, field_name)
                statement = statement.where(field == value)

            results = session.exec(statement)
            return list(results)

    def save(self):
        """Save this instance to the database and trigger sync.

        On the client side, this will queue a mutation and push to server.
        On the server side, this just persists to the canonical database.

        Returns:
            self (for method chaining)

        Example:
            >>> user = User(name="Alice", email="alice@example.com")
            >>> user.save()
            >>> user.name = "Alice Smith"
            >>> user.save()  # Update
        """
        runtime = get_runtime()

        # Persist to database
        with runtime.open_session() as session:
            # Use merge to handle objects from other sessions or new objects
            merged = session.merge(self)
            session.commit()
            session.refresh(merged)
            # Update self with merged instance attributes
            for key in merged.__dict__:
                if not key.startswith('_'):
                    setattr(self, key, getattr(merged, key))

        # Trigger sync on client side
        if runtime.sync is not None:
            runtime.sync.on_save(self)

        return self

    def delete(self):
        """Delete this instance from the database and trigger sync.

        On the client side, this will queue a delete mutation and push to server.
        On the server side, this just deletes from the canonical database.

        Example:
            >>> user = User.get(1)
            >>> if user:
            ...     user.delete()
        """
        runtime = get_runtime()

        # Delete from database
        with runtime.open_session() as session:
            # Re-attach to session if detached
            if not session.is_modified(self):
                # Merge to get attached instance
                attached = session.merge(self)
            else:
                attached = self

            session.delete(attached)
            session.commit()

        # Trigger sync on client side
        if runtime.sync is not None:
            runtime.sync.on_delete(self)
