# Anti-Patterns - BAD vs GOOD

Common mistakes and their corrections for Python 3.12+.

---

## Type Hints

### Legacy Typing Imports

```python
# BAD - Legacy syntax
from typing import List, Dict, Optional, Union, Tuple

def process(items: List[str]) -> Dict[str, int]:
    return {}

def get_user(id: int) -> Optional[User]:
    return None

def parse(value: Union[str, bytes]) -> Tuple[str, int]:
    return ("", 0)
```

```python
# GOOD - Python 3.12+ native syntax
def process(items: list[str]) -> dict[str, int]:
    return {}

def get_user(id: int) -> User | None:
    return None

def parse(value: str | bytes) -> tuple[str, int]:
    return ("", 0)
```

### Missing Return Types

```python
# BAD - No return type
def calculate_total(items):
    return sum(item.price for item in items)

def find_user(user_id):
    return db.query(User).filter_by(id=user_id).first()
```

```python
# GOOD - Fully typed
def calculate_total(items: list[CartItem]) -> Decimal:
    return sum(item.price for item in items)

def find_user(user_id: int) -> User | None:
    return db.query(User).filter_by(id=user_id).first()
```

### Using Any

```python
# BAD - Any everywhere
from typing import Any

def process_data(data: Any) -> Any:
    return data.transform()

config: dict[str, Any] = load_config()
```

```python
# GOOD - Specific types
from myapp.models import DataModel, Config

def process_data(data: DataModel) -> TransformedData:
    return data.transform()

config: Config = load_config()
```

### Legacy Generic Type Parameters

```python
# BAD - Old TypeVar syntax
from typing import TypeVar, Sequence

T = TypeVar("T")

def first(items: Sequence[T]) -> T | None:
    return items[0] if items else None
```

```python
# GOOD - PEP 695 syntax (Python 3.12+)
from collections.abc import Sequence

def first[T](items: Sequence[T]) -> T | None:
    return items[0] if items else None
```

---

## Exception Handling

### Broad Try Blocks

```python
# BAD - Too much in try block
try:
    user_id = parse_user_id(request)
    user = fetch_user(user_id)
    permissions = get_permissions(user)
    data = process_request(user, permissions)
    return format_response(data)
except ValueError:
    return error_response("Invalid user")
```

```python
# GOOD - Tight try block
user_id = parse_user_id(request)

try:
    user = fetch_user(user_id)
except UserNotFoundError:
    return error_response("User not found")

permissions = get_permissions(user)
data = process_request(user, permissions)
return format_response(data)
```

### Bare Except

```python
# BAD - Catches everything including KeyboardInterrupt
try:
    process_data(data)
except:
    log_error("Something went wrong")
    return None
```

```python
# GOOD - Specific exception
try:
    process_data(data)
except ProcessingError as e:
    logger.exception("Processing failed", extra={"data_id": data.id})
    raise
```

### Swallowing Exceptions

```python
# BAD - Exception silently ignored
try:
    send_notification(user)
except Exception:
    pass
```

```python
# GOOD - Log and handle appropriately
try:
    send_notification(user)
except NotificationError:
    logger.warning(
        "Failed to send notification",
        extra={"user_id": user.id},
    )
    # Continue execution - notification is not critical
```

### Not Chaining Exceptions

```python
# BAD - Original traceback lost
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    raise ConfigError("Invalid configuration")
```

```python
# GOOD - Chain with 'from'
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    raise ConfigError(f"Invalid configuration: {e}") from e
```

---

## Logging

### Using Print

```python
# BAD - Print statements
def process_order(order):
    print(f"Processing order {order.id}")
    # ...
    print(f"Order {order.id} completed")
```

```python
# GOOD - Proper logging
import logging

logger = logging.getLogger(__name__)

def process_order(order: Order) -> None:
    logger.info("Processing order", extra={"order_id": order.id})
    # ...
    logger.info("Order completed", extra={"order_id": order.id})
```

### Logger in Function

```python
# BAD - Creating logger inside function
def process_data(data):
    logger = logging.getLogger(__name__)  # Created on every call
    logger.info("Processing")
```

```python
# GOOD - Module-level logger
import logging

logger = logging.getLogger(__name__)

def process_data(data: Data) -> None:
    logger.info("Processing", extra={"data_id": data.id})
```

### Wrong Log Level

```python
# BAD - Using wrong levels
logger.info("User not found")  # Should be warning or debug
logger.error("Starting server")  # Should be info
logger.warning("Request processed successfully")  # Should be info/debug
```

```python
# GOOD - Correct levels
logger.warning("User not found", extra={"user_id": user_id})
logger.info("Starting server", extra={"port": 8080})
logger.debug("Request processed", extra={"request_id": req.id})
```

### Missing Context

```python
# BAD - No context
logger.error("Database error occurred")
logger.info("User created")
```

```python
# GOOD - Rich context
logger.error(
    "Database error occurred",
    extra={"query": query, "params": params, "error_code": e.code},
)
logger.info("User created", extra={"user_id": user.id, "email": user.email})
```

---

## Imports

### Star Imports

```python
# BAD - Pollutes namespace
from os.path import *
from myapp.utils import *
```

```python
# GOOD - Explicit imports
from pathlib import Path

from myapp.utils import format_date, parse_config
```

### Wrong Import Order

```python
# BAD - Mixed order
from myapp.models import User
import json
from pydantic import BaseModel
import os
from myapp.utils import helper
```

```python
# GOOD - Correct order with blank lines
import json
import os

from pydantic import BaseModel

from myapp.models import User
from myapp.utils import helper
```

### Relative Imports in Applications

```python
# BAD - Relative imports in app code
from .models import User
from ..utils import helper
```

```python
# GOOD - Absolute imports
from myapp.models import User
from myapp.utils import helper
```

---

## String Formatting

### Old-Style Formatting

```python
# BAD - % formatting
message = "Hello %s, you have %d messages" % (name, count)

# BAD - .format()
message = "Hello {}, you have {} messages".format(name, count)
```

```python
# GOOD - f-strings
message = f"Hello {name}, you have {count} messages"
```

### String Concatenation

```python
# BAD - Concatenation for building strings
query = "SELECT * FROM " + table + " WHERE id = " + str(id)
```

```python
# GOOD - f-string (but use parameterized queries for SQL!)
query = f"SELECT * FROM {table} WHERE id = ?"
cursor.execute(query, (id,))
```

---

## Function Design

### Too Many Parameters

```python
# BAD - Too many parameters
def create_user(
    name, email, password, age, address, city, country, phone, role, active
):
    ...
```

```python
# GOOD - Use dataclass or Pydantic model
from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    age: int | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    role: str = "user"
    active: bool = True

def create_user(request: CreateUserRequest) -> User:
    ...
```

### Deep Nesting

```python
# BAD - Deep nesting
def process(data):
    if data:
        if data.is_valid:
            if data.user:
                if data.user.is_active:
                    return do_something(data)
    return None
```

```python
# GOOD - Early returns
def process(data: Data | None) -> Result | None:
    if data is None:
        return None
    if not data.is_valid:
        return None
    if data.user is None:
        return None
    if not data.user.is_active:
        return None

    return do_something(data)
```

### Long Functions

```python
# BAD - 50+ line function doing many things
def process_order(order):
    # validate order (10 lines)
    # calculate totals (15 lines)
    # apply discounts (10 lines)
    # send notifications (10 lines)
    # update database (10 lines)
    ...
```

```python
# GOOD - Small, focused functions
def process_order(order: Order) -> ProcessedOrder:
    validate_order(order)
    totals = calculate_totals(order)
    final_totals = apply_discounts(totals, order.customer)
    processed = save_order(order, final_totals)
    schedule_notifications(processed)
    return processed
```

---

## Data Classes

### Regular Class for Data

```python
# BAD - Boilerplate
class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

    def __eq__(self, other):
        return (self.id, self.name, self.email) == (other.id, other.name, other.email)

    def __hash__(self):
        return hash((self.id, self.name, self.email))

    def __repr__(self):
        return f"User(id={self.id}, name={self.name}, email={self.email})"
```

```python
# GOOD - Dataclass
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str
    email: str
```

### Mutable Default Arguments

```python
# BAD - Mutable default
@dataclass
class Config:
    items: list[str] = []  # Shared between instances!
```

```python
# GOOD - Use field with default_factory
from dataclasses import dataclass, field

@dataclass
class Config:
    items: list[str] = field(default_factory=list)
```

---

## Project Structure

### No src/ Layout

```python
# BAD - Flat structure
myproject/
├── mypackage/
│   └── __init__.py
├── tests/
└── setup.py
```

```python
# GOOD - src/ layout
myproject/
├── src/
│   └── mypackage/
│       └── __init__.py
├── tests/
└── pyproject.toml
```

### setup.py Instead of pyproject.toml

```python
# BAD - Legacy setup.py
from setuptools import setup, find_packages

setup(
    name="my-package",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["requests"],
)
```

```toml
# GOOD - pyproject.toml
[project]
name = "my-package"
version = "0.1.0"
dependencies = ["httpx"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Context Managers

### Manual Resource Management

```python
# BAD - Manual file handling
f = open("data.txt")
try:
    data = f.read()
finally:
    f.close()
```

```python
# GOOD - Context manager
from pathlib import Path

with Path("data.txt").open() as f:
    data = f.read()

# Or even simpler for reading:
data = Path("data.txt").read_text()
```

### Not Using pathlib

```python
# BAD - os.path
import os

path = os.path.join(base_dir, "data", "file.txt")
if os.path.exists(path):
    with open(path) as f:
        content = f.read()
```

```python
# GOOD - pathlib
from pathlib import Path

path = Path(base_dir) / "data" / "file.txt"
if path.exists():
    content = path.read_text()
```
