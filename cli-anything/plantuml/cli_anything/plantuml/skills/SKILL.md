# cli-anything-plantuml SKILL

## What This Tool Does
`cli-anything-plantuml` is a CLI harness that wraps PlantUML to generate diagrams
from text-based DSL source files. It supports SVG, PNG, PDF, and TXT output formats,
provides built-in diagram templates, and includes an interactive REPL.

## Installation
```bash
pip install cli-anything-plantuml
# OR from source:
cd /path/to/cli-anything/plantuml && pip install -e .
```

PlantUML must also be available:
```bash
brew install plantuml          # macOS
sudo apt install plantuml      # Debian/Ubuntu
choco install plantuml         # Windows
# Or set PLANTUML_JAR=/path/to/plantuml.jar (requires Java)
```

## CLI Reference

### Global Flags
| Flag     | Description                        |
|----------|------------------------------------|
| `--json` | Emit all output as JSON (machine-readable) |

---

### `diagram render`
Render a PlantUML diagram to SVG, PNG, PDF, or TXT.

```bash
# Render inline source to SVG on stdout
cli-anything-plantuml diagram render --source "@startuml
A -> B : Hello
@enduml"

# Render a .puml file to PNG, save to disk
cli-anything-plantuml diagram render --file diagram.puml --format png --output out.png

# Pipe source from stdin
cat diagram.puml | cli-anything-plantuml diagram render --format svg --output out.svg

# Machine-readable JSON output
cli-anything-plantuml --json diagram render --file diagram.puml --format svg
```

**Options:**
| Option       | Short | Default | Description                             |
|--------------|-------|---------|-----------------------------------------|
| `--source`   | `-s`  |         | PlantUML source text                    |
| `--file`     | `-f`  |         | Path to .puml source file               |
| `--format`   | `-F`  | `svg`   | Output format: svg, png, pdf, txt       |
| `--output`   | `-o`  |         | Output file path (default: stdout)      |

---

### `diagram validate`
Check if PlantUML source is syntactically valid. Exits with code 1 if invalid.

```bash
cli-anything-plantuml diagram validate --file my.puml
cli-anything-plantuml diagram validate --source "@startuml
A -> B
@enduml"
echo "@startuml
A->B
@enduml" | cli-anything-plantuml diagram validate
```

---

### `diagram preview`
Render a diagram and open it in the system's default SVG viewer.

```bash
cli-anything-plantuml diagram preview --file my.puml
cli-anything-plantuml diagram preview --source "@startuml
A->B
@enduml"
```

---

### `template list`
List all available built-in templates.

```bash
cli-anything-plantuml template list
cli-anything-plantuml --json template list
```

**Available templates:** `sequence`, `class`, `activity`, `usecase`, `component`, `state`, `er`, `mindmap`

---

### `template show`
Display the PlantUML source for a template.

```bash
cli-anything-plantuml template show sequence
cli-anything-plantuml template show er
```

---

### `template use`
Output a template to a file or stdout.

```bash
# Print to stdout
cli-anything-plantuml template use sequence

# Save to file, then edit and render
cli-anything-plantuml template use class --output class_diagram.puml
cli-anything-plantuml diagram render --file class_diagram.puml --format svg --output class.svg
```

---

### `server status`
Check whether PlantUML is available and run a smoke-test render.

```bash
cli-anything-plantuml server status
cli-anything-plantuml --json server status
```

---

### `repl`
Start an interactive REPL with tab-completion and command history.

```bash
cli-anything-plantuml repl
```

Inside the REPL, type commands without the `cli-anything-plantuml` prefix:
```
plantuml> server status
plantuml> template list
plantuml> template use sequence
plantuml> diagram render --source "@startuml
...
@enduml"
plantuml> exit
```

---

## Python API

```python
from cli_anything.plantuml.utils import find_plantuml, render, validate, TEMPLATES

# Check availability
cmd = find_plantuml()  # returns tuple or None
print(cmd)             # ('plantuml',) or ('java', '-jar', '/path/to/plantuml.jar')

# Render diagram
svg_bytes = render("@startuml\nA -> B\n@enduml", format="svg")

# Validate syntax
is_valid = validate("@startuml\nA -> B\n@enduml")  # True

# Use a template
src = TEMPLATES["sequence"]
png_bytes = render(src, format="png")
```

## Supported Formats
| Format | Flag     | Notes                        |
|--------|----------|------------------------------|
| SVG    | `-tsvg`  | Scalable vector, default     |
| PNG    | `-tpng`  | Raster image                 |
| PDF    | `-tpdf`  | Requires PlantUML PDF plugin |
| TXT    | `-ttxt`  | ASCII art output             |

## Environment Variables
| Variable       | Description                                          |
|----------------|------------------------------------------------------|
| `PLANTUML_JAR` | Override path to `plantuml.jar` (requires Java)      |

## Error Handling
- `PlantUMLNotFoundError` — raised when no PlantUML installation is found
- `PlantUMLRenderError` — raised when PlantUML reports a syntax or rendering error

Both are importable from `cli_anything.plantuml.utils`.

## Architecture
```
cli_anything/plantuml/
├── __init__.py              # Package metadata
├── __main__.py              # python -m cli_anything.plantuml entry point
├── plantuml_cli.py          # Click CLI: diagram, template, server groups + REPL
├── core/
│   └── __init__.py
├── skills/
│   └── SKILL.md             # This file
└── utils/
    ├── __init__.py
    └── plantuml_backend.py  # find_plantuml, render, validate, TEMPLATES
```
