# Code Examples - Python Modern Practices

Complete, production-ready code patterns for reference.

---

## Complete Module Example

```python
"""User management service.

Handles user creation, retrieval, and updates.
"""
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from pydantic import BaseModel, EmailStr, Field

from myapp.core.exceptions import UserNotFoundError, ValidationError
from myapp.database import Repository

logger = logging.getLogger(__name__)


# Type alias (PEP 695 syntax)
type UserId = int


@dataclass(frozen=True, slots=True)
class User:
    """Domain model for a user."""

    id: UserId
    name: str
    email: str
    is_active: bool = True


class CreateUserRequest(BaseModel):
    """Validated input for user creation."""

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = True


class UserService:
    """Service for user operations."""

    def __init__(self, repository: Repository[User]) -> None:
        self._repository = repository

    def create_user(self, request: CreateUserRequest) -> User:
        """Create a new user from validated request."""
        if self._email_exists(request.email):
            raise ValidationError(f"Email already registered: {request.email}")

        user = User(
            id=self._generate_id(),
            name=request.name,
            email=request.email,
            is_active=request.is_active,
        )

        self._repository.save(user)
        logger.info("User created", extra={"user_id": user.id, "email": user.email})

        return user

    def get_user(self, user_id: UserId) -> User:
        """Retrieve user by ID or raise UserNotFoundError."""
        user = self._repository.find_by_id(user_id)

        if user is None:
            logger.warning("User not found", extra={"user_id": user_id})
            raise UserNotFoundError(f"No user with ID: {user_id}")

        return user

    def get_user_or_none(self, user_id: UserId) -> User | None:
        """Retrieve user by ID, returning None if not found."""
        return self._repository.find_by_id(user_id)

    def list_active_users(self) -> Sequence[User]:
        """Return all active users."""
        return [u for u in self._repository.find_all() if u.is_active]

    def _email_exists(self, email: str) -> bool:
        return self._repository.find_by_email(email) is not None

    def _generate_id(self) -> UserId:
        return self._repository.next_id()
```

---

## Generic Function with Type Parameters

```python
from collections.abc import Callable, Sequence


def first[T](items: Sequence[T]) -> T | None:
    """Return first item or None if empty."""
    return items[0] if items else None


def find[T](items: Sequence[T], predicate: Callable[[T], bool]) -> T | None:
    """Return first item matching predicate or None."""
    for item in items:
        if predicate(item):
            return item
    return None


def partition[T](
    items: Sequence[T],
    predicate: Callable[[T], bool],
) -> tuple[list[T], list[T]]:
    """Split items into (matching, non-matching) based on predicate."""
    matching: list[T] = []
    non_matching: list[T] = []

    for item in items:
        if predicate(item):
            matching.append(item)
        else:
            non_matching.append(item)

    return matching, non_matching


def group_by[T, K](items: Sequence[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """Group items by key function."""
    groups: dict[K, list[T]] = {}

    for item in items:
        k = key(item)
        if k not in groups:
            groups[k] = []
        groups[k].append(item)

    return groups
```

---

## Exception Handling Pattern

```python
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration loading error."""


class Config:
    """Application configuration."""

    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load configuration from JSON file."""
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigError(f"Cannot read config file: {path}") from e

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config: {path}") from e

        if not isinstance(data, dict):
            raise ConfigError(f"Config must be object, got {type(data).__name__}")

        return cls(data)

    def get(self, key: str) -> str:
        """Get configuration value or raise KeyError."""
        return self._data[key]

    def get_or_default(self, key: str, default: str) -> str:
        """Get configuration value or return default."""
        return self._data.get(key, default)
```

---

## Repository Pattern with Type Hints

```python
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Entity:
    """Base entity with ID."""

    id: int


class Repository[T: Entity](ABC):
    """Generic repository interface."""

    @abstractmethod
    def find_by_id(self, entity_id: int) -> T | None:
        """Find entity by ID or return None."""
        ...

    @abstractmethod
    def find_all(self) -> Sequence[T]:
        """Return all entities."""
        ...

    @abstractmethod
    def save(self, entity: T) -> None:
        """Persist entity."""
        ...

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete entity, return True if existed."""
        ...


class InMemoryRepository[T: Entity](Repository[T]):
    """In-memory implementation of Repository."""

    def __init__(self) -> None:
        self._storage: dict[int, T] = {}

    def find_by_id(self, entity_id: int) -> T | None:
        return self._storage.get(entity_id)

    def find_all(self) -> Sequence[T]:
        return list(self._storage.values())

    def save(self, entity: T) -> None:
        self._storage[entity.id] = entity

    def delete(self, entity_id: int) -> bool:
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False
```

---

## Dataclass Patterns

```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto


class OrderStatus(Enum):
    """Order status enumeration."""

    PENDING = auto()
    CONFIRMED = auto()
    SHIPPED = auto()
    DELIVERED = auto()
    CANCELLED = auto()


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable money value object."""

    amount: Decimal
    currency: str = "USD"

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True, slots=True)
class OrderItem:
    """Single item in an order."""

    product_id: int
    name: str
    quantity: int
    unit_price: Money

    @property
    def total(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)


@dataclass(slots=True)
class Order:
    """Mutable order aggregate."""

    id: int
    customer_id: int
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total(self) -> Money:
        if not self.items:
            return Money(Decimal("0"))

        result = self.items[0].total
        for item in self.items[1:]:
            result = result + item.total
        return result

    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify non-pending order")
        self.items.append(item)

    def confirm(self) -> None:
        if self.status != OrderStatus.PENDING:
            raise ValueError("Can only confirm pending orders")
        if not self.items:
            raise ValueError("Cannot confirm empty order")
        self.status = OrderStatus.CONFIRMED
```

---

## Context Manager Pattern

```python
import logging
from collections.abc import Generator
from contextlib import contextmanager
from time import perf_counter

logger = logging.getLogger(__name__)


@contextmanager
def timed_operation(name: str) -> Generator[None, None, None]:
    """Log duration of code block."""
    start = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        logger.info(
            "Operation completed",
            extra={"operation": name, "duration_ms": elapsed * 1000},
        )


@contextmanager
def transaction[T](connection: T) -> Generator[T, None, None]:
    """Database transaction context manager."""
    try:
        yield connection
        connection.commit()  # type: ignore[attr-defined]
    except Exception:
        connection.rollback()  # type: ignore[attr-defined]
        raise


# Usage
with timed_operation("data_processing"):
    process_large_dataset()
```

---

## Pydantic Models for API

```python
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Request model for creating a user."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v


class UserResponse(BaseModel):
    """Response model for user data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class PaginatedResponse[T](BaseModel):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class MoneyModel(BaseModel):
    """Pydantic model for money values."""

    amount: Decimal = Field(decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
```

---

## Testing Patterns

```python
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import Mock

import pytest


@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str
    email: str


class UserRepository:
    def find_by_id(self, user_id: int) -> User | None: ...
    def save(self, user: User) -> None: ...


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def get_user(self, user_id: int) -> User | None:
        return self._repo.find_by_id(user_id)


# Fixtures
@pytest.fixture
def mock_repository() -> Mock:
    return Mock(spec=UserRepository)


@pytest.fixture
def user_service(mock_repository: Mock) -> UserService:
    return UserService(mock_repository)


@pytest.fixture
def sample_user() -> User:
    return User(id=1, name="Alice", email="alice@example.com")


# Tests
class TestUserService:
    def test_get_user_returns_user_when_found(
        self,
        user_service: UserService,
        mock_repository: Mock,
        sample_user: User,
    ) -> None:
        mock_repository.find_by_id.return_value = sample_user

        result = user_service.get_user(1)

        assert result == sample_user
        mock_repository.find_by_id.assert_called_once_with(1)

    def test_get_user_returns_none_when_not_found(
        self,
        user_service: UserService,
        mock_repository: Mock,
    ) -> None:
        mock_repository.find_by_id.return_value = None

        result = user_service.get_user(999)

        assert result is None


# Parametrized tests
@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("hello", "HELLO"),
        ("World", "WORLD"),
        ("", ""),
        ("123", "123"),
    ],
)
def test_uppercase(input_value: str, expected: str) -> None:
    assert input_value.upper() == expected
```
