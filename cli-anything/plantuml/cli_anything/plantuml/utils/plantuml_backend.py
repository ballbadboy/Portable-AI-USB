"""
plantuml_backend.py
~~~~~~~~~~~~~~~~~~~
Backend utilities for discovering and invoking PlantUML.

Supports two invocation strategies:
  1. Native binary:  plantuml -tsvg input.puml
  2. JAR via Java:   java -jar /path/to/plantuml.jar -tsvg input.puml

Public API
----------
find_plantuml() -> tuple[str, ...] | None
    Returns the command prefix to invoke PlantUML, or None if unavailable.

render(source_text, format="svg") -> bytes
    Renders PlantUML source to the requested format and returns raw bytes.

validate(source_text) -> bool
    Returns True if PlantUML considers the source syntactically valid.

TEMPLATES : dict[str, str]
    Mapping of template name -> PlantUML source text.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class PlantUMLNotFoundError(RuntimeError):
    """Raised when no PlantUML installation can be located."""

    def __init__(self) -> None:
        super().__init__(
            "PlantUML not found. Install it with:\n"
            "  brew install plantuml          (macOS)\n"
            "  sudo apt install plantuml      (Debian/Ubuntu)\n"
            "  choco install plantuml         (Windows)\n"
            "Or place plantuml.jar in one of the search paths and ensure Java is available."
        )


class PlantUMLRenderError(RuntimeError):
    """Raised when PlantUML reports an error during rendering."""


# ---------------------------------------------------------------------------
# JAR search paths (ordered by priority)
# ---------------------------------------------------------------------------

_JAR_SEARCH_PATHS: list[Path] = [
    Path.home() / "plantuml.jar",
    Path.home() / ".local" / "lib" / "plantuml.jar",
    Path("/usr/local/lib/plantuml.jar"),
    Path("/usr/lib/plantuml/plantuml.jar"),
    Path("/opt/plantuml/plantuml.jar"),
    # Common Homebrew Cellar path (version-agnostic glob handled at runtime)
]


def _find_jar() -> Optional[Path]:
    """Search common locations for plantuml.jar. Returns path or None."""
    for p in _JAR_SEARCH_PATHS:
        if p.is_file():
            return p

    # Try Homebrew Cellar glob: /usr/local/Cellar/plantuml/*/libexec/plantuml.jar
    cellar_roots = [
        Path("/usr/local/Cellar/plantuml"),
        Path("/opt/homebrew/Cellar/plantuml"),
    ]
    for root in cellar_roots:
        if root.is_dir():
            candidates = sorted(root.glob("*/libexec/plantuml.jar"), reverse=True)
            if candidates:
                return candidates[0]

    return None


# ---------------------------------------------------------------------------
# find_plantuml
# ---------------------------------------------------------------------------


def find_plantuml() -> Optional[tuple[str, ...]]:
    """
    Locate a working PlantUML installation.

    Returns a command tuple suitable for use with subprocess, e.g.::

        ("plantuml",)               # native binary on PATH
        ("java", "-jar", "/p/t/plantuml.jar")  # JAR invocation

    Returns None if PlantUML cannot be found.
    """
    # 1. Native binary on PATH
    if shutil.which("plantuml"):
        return ("plantuml",)

    # 2. JAR + java
    jar = _find_jar()
    if jar and shutil.which("java"):
        return ("java", "-jar", str(jar))

    # 3. PLANTUML_JAR environment variable override
    env_jar = os.environ.get("PLANTUML_JAR")
    if env_jar and Path(env_jar).is_file() and shutil.which("java"):
        return ("java", "-jar", env_jar)

    return None


# ---------------------------------------------------------------------------
# Format mapping
# ---------------------------------------------------------------------------

_FORMAT_FLAG: dict[str, str] = {
    "svg": "-tsvg",
    "png": "-tpng",
    "pdf": "-tpdf",
    "txt": "-ttxt",
    "eps": "-teps",
    "latex": "-tlatex",
}

_FORMAT_EXT: dict[str, str] = {
    "svg": ".svg",
    "png": ".png",
    "pdf": ".pdf",
    "txt": ".txt",
    "eps": ".eps",
    "latex": ".latex",
}


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render(source_text: str, format: str = "svg") -> bytes:
    """
    Render *source_text* as a PlantUML diagram.

    Parameters
    ----------
    source_text:
        Raw PlantUML source (e.g. ``@startuml\\n...\\n@enduml``).
    format:
        Output format: ``"svg"``, ``"png"``, ``"pdf"``, ``"txt"``.

    Returns
    -------
    bytes
        The rendered diagram as raw bytes.

    Raises
    ------
    PlantUMLNotFoundError
        If PlantUML is not installed.
    PlantUMLRenderError
        If PlantUML reports a syntax/rendering error.
    ValueError
        If *format* is not supported.
    """
    fmt = format.lower()
    if fmt not in _FORMAT_FLAG:
        raise ValueError(
            f"Unsupported format {format!r}. Choose from: {', '.join(_FORMAT_FLAG)}"
        )

    cmd_prefix = find_plantuml()
    if cmd_prefix is None:
        raise PlantUMLNotFoundError()

    flag = _FORMAT_FLAG[fmt]
    ext = _FORMAT_EXT[fmt]

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "diagram.puml"
        output_path = Path(tmpdir) / f"diagram{ext}"

        input_path.write_text(source_text, encoding="utf-8")

        cmd = [*cmd_prefix, flag, "-o", tmpdir, str(input_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # PlantUML uses exit code 0 even on parse errors sometimes;
        # check stderr for "ERROR" or "Exception" patterns.
        stderr_combined = result.stderr + result.stdout
        if result.returncode != 0 or _has_error(stderr_combined):
            raise PlantUMLRenderError(
                f"PlantUML render failed:\n{stderr_combined.strip()}"
            )

        if not output_path.exists():
            raise PlantUMLRenderError(
                f"PlantUML ran but produced no output file at {output_path}.\n"
                f"stdout: {result.stdout.strip()}\n"
                f"stderr: {result.stderr.strip()}"
            )

        return output_path.read_bytes()


def _has_error(text: str) -> bool:
    """Heuristically detect PlantUML error output."""
    patterns = [
        r"\bERROR\b",
        r"Exception",
        r"Syntax Error",
        r"cannot find",
    ]
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def validate(source_text: str) -> bool:
    """
    Check whether *source_text* is valid PlantUML syntax.

    Returns True on success, False on any parse/render error.
    Does NOT raise PlantUMLRenderError.
    Raises PlantUMLNotFoundError if PlantUML is not installed.
    """
    try:
        render(source_text, format="svg")
        return True
    except PlantUMLRenderError:
        return False


# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, str] = {
    "sequence": """\
@startuml
title Sequence Diagram

actor User
participant "Frontend" as FE
participant "Backend" as BE
database "Database" as DB

User -> FE : Request
activate FE
FE -> BE : API Call
activate BE
BE -> DB : Query
activate DB
DB --> BE : Result
deactivate DB
BE --> FE : Response
deactivate BE
FE --> User : Display
deactivate FE

@enduml
""",
    "class": """\
@startuml
title Class Diagram

abstract class Animal {
    - name : String
    - age : int
    + getName() : String
    + getAge() : int
    + {abstract} speak() : String
}

class Dog extends Animal {
    - breed : String
    + getBreed() : String
    + speak() : String
}

class Cat extends Animal {
    - indoor : boolean
    + isIndoor() : boolean
    + speak() : String
}

Animal <|-- Dog
Animal <|-- Cat

@enduml
""",
    "activity": """\
@startuml
title Activity Diagram

start
:Receive Request;
if (Authenticated?) then (yes)
  :Process Request;
  if (Valid Data?) then (yes)
    :Save to Database;
    :Send Confirmation;
  else (no)
    :Return Validation Error;
  endif
else (no)
  :Return 401 Unauthorized;
endif
stop

@enduml
""",
    "usecase": """\
@startuml
title Use Case Diagram

left to right direction

actor "Customer" as customer
actor "Admin" as admin

rectangle "E-Commerce System" {
  usecase "Browse Products" as UC1
  usecase "Add to Cart" as UC2
  usecase "Checkout" as UC3
  usecase "Manage Products" as UC4
  usecase "View Reports" as UC5
}

customer --> UC1
customer --> UC2
customer --> UC3
admin --> UC4
admin --> UC5
UC3 .> UC2 : <<include>>

@enduml
""",
    "component": """\
@startuml
title Component Diagram

package "Frontend" {
  [Web App] as webapp
  [Mobile App] as mobile
}

package "Backend" {
  [API Gateway] as gateway
  [Auth Service] as auth
  [Business Logic] as logic
  [Notification Service] as notify
}

database "PostgreSQL" as db
database "Redis Cache" as cache
queue "Message Queue" as mq

webapp --> gateway : HTTPS
mobile --> gateway : HTTPS
gateway --> auth : validates
gateway --> logic : routes
logic --> db : reads/writes
logic --> cache : caches
logic --> mq : publishes
mq --> notify : subscribes

@enduml
""",
    "state": """\
@startuml
title State Diagram - Order Lifecycle

[*] --> Pending : Order Placed

Pending --> Processing : Payment Confirmed
Pending --> Cancelled : User Cancels
Pending --> Cancelled : Payment Failed

Processing --> Shipped : Items Dispatched
Processing --> Cancelled : Out of Stock

Shipped --> Delivered : Delivery Confirmed
Shipped --> Returned : Customer Refuses

Delivered --> Returned : Return Request

Returned --> Refunded : Refund Processed

Cancelled --> [*]
Refunded --> [*]
Delivered --> [*]

@enduml
""",
    "er": """\
@startuml
title Entity-Relationship Diagram

entity "User" as user {
  * id : INTEGER <<PK>>
  --
  * email : VARCHAR(255) <<UNIQUE>>
  * password_hash : VARCHAR(255)
  * created_at : TIMESTAMP
  updated_at : TIMESTAMP
}

entity "Product" as product {
  * id : INTEGER <<PK>>
  --
  * name : VARCHAR(255)
  * price : DECIMAL(10,2)
  * stock : INTEGER
  category_id : INTEGER <<FK>>
}

entity "Order" as order {
  * id : INTEGER <<PK>>
  --
  * user_id : INTEGER <<FK>>
  * status : VARCHAR(50)
  * total : DECIMAL(10,2)
  * created_at : TIMESTAMP
}

entity "OrderItem" as item {
  * id : INTEGER <<PK>>
  --
  * order_id : INTEGER <<FK>>
  * product_id : INTEGER <<FK>>
  * quantity : INTEGER
  * unit_price : DECIMAL(10,2)
}

entity "Category" as category {
  * id : INTEGER <<PK>>
  --
  * name : VARCHAR(100)
  parent_id : INTEGER <<FK>>
}

user ||--o{ order : "places"
order ||--|{ item : "contains"
product ||--o{ item : "included in"
category ||--o{ product : "groups"
category ||--o{ category : "sub-category of"

@enduml
""",
    "mindmap": """\
@startmindmap
title Software Architecture Mindmap

* System Architecture
** Frontend
*** React / Vue / Angular
*** Mobile (iOS / Android)
*** Progressive Web App
** Backend
*** REST API
*** GraphQL
*** gRPC Services
** Data Layer
*** Relational DB
**** PostgreSQL
**** MySQL
*** NoSQL
**** MongoDB
**** Redis
** Infrastructure
*** Cloud Provider
**** AWS
**** GCP
**** Azure
*** CI/CD
*** Monitoring & Logging

@endmindmap
""",
}
