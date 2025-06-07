# VEX Tournament Manager Bridge

An unofficial Python bridge for interacting with VEX Tournament Manager software. This package provides a high-level API to control and monitor VEX Tournament Manager through its UI using pywinauto.

## Installation

Using uv (recommended):
```bash
uv add vex-tm-bridge
```

Using pip:
```bash
pip install vex-tm-bridge
```

## Quick Start

```python
from vex_tm_bridge import get_bridge_engine
from vex_tm_bridge.base import Competition

# Create a bridge engine instance
engine = get_bridge_engine(low_cpu_usage=True)
engine.start()

# Get a fieldset instance
fieldset = engine.get_fieldset(Competition.V5RC, "Match Field Set #1")

# Get current overview
overview = fieldset.get_overview()
print(overview)

# Subscribe to overview updates
def on_overview_updated(self, overview):
    print(f"Overview updated: {overview}")

fieldset.overview_event.on(on_overview_updated)
```

## Features

- Monitor and control VEX Tournament Manager Match Field Sets
- Event-based updates for field state changes
- Support for both VRC and VIQRC competitions
- Low CPU usage mode for better performance

## Requirements

- Python 3.10 or higher
- Windows OS
- VEX Tournament Manager software

## Development

### Setting Up Development Environment

1. Install uv (package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   or on Windows:
   ```powershell
   powershell -c "(irm https://astral.sh/uv/install.ps1) | iex"
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/jerrylum/vex-tm-bridge.git
   cd vex-tm-bridge
   ```

3. Install venv:
   ```bash
   uv venv
   ```

4. Install dependencies:
   ```bash
   # Install from uv.lock for reproducible environment
   uv pip sync requirements.txt
   
   # Install in editable mode with dev dependencies
   uv pip install -e ".[dev]"
   ```

### Development Dependencies

The project uses uv for dependency management with the following key files:
- `pyproject.toml`: Defines project metadata and dependencies
- `uv.lock`: Ensures reproducible builds by locking all dependency versions

Development tools:
- `black`: Code formatting (version 25.1.0 or higher)
- `pytest`: Testing (version 8.4.0 or higher)
- `build`: Package building (version 1.0.3 or higher)

### Building and Testing

To run the project in development mode:
```bash
uv run dev/playground.py
```

To build the package:

```bash
uv build
```

This will create distribution files in the `dist/` directory.

To run tests:

```bash
uv run pytest
```

### Code Formatting

Format code using black:
```bash
uv run black .
```

### Development Tips

- The virtual environment is created in `.venv/` directory
- `uv` advantages:
- Managing dependencies:
  - Use `uv add PACKAGE` to add new runtime dependencies
  - Use `uv add --dev PACKAGE` to add new development dependencies
  - Use `uv pip sync requirements.txt` for initial setup or after pulling changes (uses uv.lock)
  - Use `uv pip install -e ".[dev]"` when working on the package locally
  - Use `uv pip compile pyproject.toml` to update `uv.lock` when dependencies change
