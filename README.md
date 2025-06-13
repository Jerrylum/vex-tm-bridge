# VEX Tournament Manager Bridge

An unofficial Python bridge for interacting with VEX Tournament Manager software. This package provides a high-level API to control and monitor VEX Tournament Manager through its UI using pywinauto and web scraping.

> [!CAUTION]
> **This package is very likely to be considered as unauthorized software.** As an Event Partner, using this package might be treated as a violation of the Commitment to Event Excellence. This package accesses Tournament Manager through UI automation (pywinauto) and web scraping, which might be considered as accessing internal components of Tournament Manager outside of the official open API protocols.
>
> **Read the official [TM Public API guidelines](https://kb.roboticseducation.org/hc/en-us/articles/19238156122135) and [Commitment to Event Excellence](https://kb.roboticseducation.org/hc/en-us/articles/12094736701975-Commitment-to-Event-Excellence) before using this package in any official event.**

## Why Use This Package?

This package provides similar functionality to the TM Public API. One benefit of using this package is that developers do not need to obtain an API key, which expires every year and needs to be re-obtained from the official source.

You might be fine using this package while respecting the spirit of the TM Public API guidelines, which is why this package intentionally does NOT provide some functionality that could compromise event integrity.

## Functionality Available

By using this package, the following functionality is available:

- **Match Control**: Start/resume matches, end matches early, abort matches, reset timers
- **Field Monitoring**: Real-time monitoring of match states, timers, and field conditions
- **Display Control**: Change audience display modes
- **Field Configuration**: Set field IDs, autonomous bonus settings, sound settings
- **Tournament Data**: Access teams, matches, rankings, and skills data through web scraping
- **Event Streaming**: Real-time updates of field state changes

## Functionality NOT Available

This package intentionally does NOT provide:

- **Score Modification**: Cannot edit or submit match scores
- **Team Data Editing**: Cannot modify team information or registration
- **Event Configuration**: Cannot generate match schedules or modify tournament settings
- **Direct Database Access**: Does not bypass Tournament Manager's data validation
- **Real-time Scoring**: Cannot access live scoring data during matches

## Developer Guidelines - Understanding the TM Public API Spirit

As a developer using this package, you should understand and respect the spirit of the TM Public API guidelines:

### 1. Do Not Display Match Time for Live Applications

**NEVER display the match time you obtain from VEX Tournament Manager Bridge in live applications.** Do not use it to create audience displays or real-time match timers.

Even though this package attempts to obtain the most accurate match time possible, it should **never** be considered as the authoritative source of time. You might use it for non-critical applications like timestamping video replays, but **please don't use it for live match displays.**

**The reasoning**: Keeping accurate time and synchronizing it across all devices is a complex challenge intertwined throughout Tournament Manager's codebase. Displaying unofficial match times could confuse teams, volunteers, and spectators about the official match status.

### 2. Do Not Recreate Existing Tournament Manager Functionality

Do not use this package to recreate TM Mobile or create alternative scoring applications.

**However**, you **can** create applications for specific, approved use cases such as:

- A large "start match" button for guest ceremonies (e.g., letting VIPs start the final match)
- Camera control systems that switch views based on active fields
- Video recording systems that automatically start/stop with matches
- Custom displays that enhance (but don't replace) the official audience display

**The reasoning**: Maintaining consistency across events ensures that volunteers can move between events with minimal retraining, and teams have a predictable experience regardless of the event they attend.

## Requirements

- Python 3.11 or higher / uv (package manager)
- Windows OS 10 or higher
- VEX Tournament Manager installed (not necessarily be the host machine)

## Installation

Using uv (recommended):

```bash
uv add "vex-tm-bridge @ git+https://github.com/Jerrylum/vex-tm-bridge.git"
```

Using pip:

```bash
pip install "vex-tm-bridge @ git+https://github.com/Jerrylum/vex-tm-bridge.git"
```

## Quick Start

```python
import time

from vex_tm_bridge import get_bridge_engine
from vex_tm_bridge.base import Competition

# Create a bridge engine instance
engine = get_bridge_engine(Competition.V5RC, low_cpu_usage=True)
engine.start()

# Get a fieldset instance
# The Match Field Set dialog must be open before calling get_fieldset(). After
# this is done, the dialog can be closed, and the fieldset will still be
# available until the Tournament Manager is completely closed.
fieldset = engine.get_fieldset("Match Field Set #1")

# Get current overview
overview = fieldset.get_overview()
print(overview) # FieldsetOverview(audience_display=In-Match, match_timer_content=, ...

# Subscribe to overview updates
def on_overview_updated(self, overview):
    print(f"Overview updated: {overview}")

fieldset.overview_updated_event.on(on_overview_updated)

# Get a web server instance
web_server = engine.get_web_server("localhost")

# Get teams
teams = web_server.get_teams(1) # Get teams for division 1
for team in teams:
    print(team)

while True:
    time.sleep(1) # Keep the program running
```

## API Server

The package includes a FastAPI-based web server that provides a RESTful API and real-time updates.

### Running the API Server

#### Using the CLI command (after installation):

```bash
vex-tm-bridge --tm-host-ip localhost --competition V5RC --port 8000
```

#### Using Python module:

```bash
python -m vex_tm_bridge --tm-host-ip localhost --competition V5RC --port 8000
```

#### Programmatically:

```python
from vex_tm_bridge import get_bridge_engine
from vex_tm_bridge.base import Competition
from vex_tm_bridge.web import create_app

# Create a bridge engine instance
engine = get_bridge_engine(Competition.V5RC, low_cpu_usage=True)

# Create an API application instance
# tm_host_ip is the IP address of the Tournament Manager host machine
# It is not required to enable Local TM API setting in Tournament Manager.
api_server = create_app(tm_host_ip="localhost", bridge_engine=engine)

# Start the application
api_server.start()

# Use uvicorn to serve (api_server.app is the FastAPI instance)
import uvicorn
uvicorn.run(api_server.app, host="0.0.0.0", port=8000)
```

### API Endpoints

#### Tournament Data

- `GET /api/teams/{division_id}` - Get teams for a division
- `GET /api/matches/{division_id}` - Get matches for a division
- `GET /api/rankings/{division_id}` - Get rankings for a division
- `GET /api/skills` - Get skills rankings

#### Fieldset Control

- `GET /api/fieldset/{fieldset_title}` - Get fieldset overview
- `POST /api/fieldset/{fieldset_title}/start` - Start/resume match
- `POST /api/fieldset/{fieldset_title}/end-early` - End match early
- `POST /api/fieldset/{fieldset_title}/abort` - Abort match
- `POST /api/fieldset/{fieldset_title}/reset` - Reset timer

#### Fieldset Settings

- `GET/POST /api/fieldset/{fieldset_title}/display` - Audience display mode
- `GET/POST /api/fieldset/{fieldset_title}/field-id` - Current field ID
- `GET/POST /api/fieldset/{fieldset_title}/autonomous-bonus` - Autonomous bonus (V5RC only)
- `GET/POST /api/fieldset/{fieldset_title}/play-sounds` - Sound settings
- `GET/POST /api/fieldset/{fieldset_title}/auto-results` - Auto results settings

#### Real-time Updates

- `GET /api/fieldset/{fieldset_title}/events` - Server-Sent Events stream for fieldset updates

### API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation.

## Features

- Monitor and control VEX Tournament Manager Match Field Sets
- Event-based updates for field state changes
- Support for both VRC and VIQRC competitions
- Low CPU usage mode for better performance
- RESTful API server with real-time updates via Server-Sent Events
- Command-line interface for running the API server

## Development

### Setting Up Development Environment

1. **Install uv (package manager):**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   or on Windows:

   ```powershell
   powershell -c "(irm https://astral.sh/uv/install.ps1) | iex"
   ```

2. **Clone the repository:**

   ```bash
   git clone https://github.com/jerrylum/vex-tm-bridge.git
   cd vex-tm-bridge
   ```

3. **Create and activate a Python 3.11 virtual environment:**

   ```bash
   uv venv --python 3.11
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install the package in editable mode with all dependencies:**

   ```bash
   uv pip install -e .
   ```

5. **Install development dependencies (optional):**

   ```bash
   uv pip install -e ".[dev]"
   ```

### Dependencies

The project uses the following main dependencies:

- **FastAPI** - Web framework for the API server
- **uvicorn** - ASGI server for FastAPI
- **pywinauto** - Windows UI automation for Tournament Manager integration
- **requests** - HTTP library for Tournament Manager web interface
- **beautifulsoup4** - HTML parsing for web scraping
- **click** - Command-line interface framework
- **sse-starlette** - Server-Sent Events support

Development tools:

- **black** - Code formatting (version 25.1.0 or higher)
- **pytest** - Testing (version 8.4.0 or higher)
- **build** - Package building (version 1.2.2 or higher)

### Development Workflow

1. **Update dependencies:**

   ```bash
   uv pip compile pyproject.toml -o requirements.txt
   ```

2. **Code formatting:**

   ```bash
   black vex_tm_bridge/ --line-length 120
   ```

3. **Testing the basic functionality:**

   ```bash
   python dev/playground.py
   ```

4. **Building the package:**

   ```bash
   uv build
   ```

5. **Running the API server in development:**
   ```bash
   python -m vex_tm_bridge --tm-host-ip localhost --port 8000
   ```

### CLI Options

The API server accepts the following command-line options:

- `--tm-host-ip` (default: localhost) - Tournament Manager host IP address
- `--competition` (default: V5RC) - Competition type (V5RC or VIQRC)
- `--host` (default: 0.0.0.0) - Host to bind the server to
- `--port` (default: 8000) - Port to run the API server on

### Notes

- The bridge requires VEX Tournament Manager to be running and accessible
- Fieldset windows must be opened at least once for pywinauto to find them
- The API server uses low CPU mode by default for efficient monitoring
- Server-Sent Events provide real-time updates for fieldset state changes
- All endpoints include proper error handling and return JSON responses
