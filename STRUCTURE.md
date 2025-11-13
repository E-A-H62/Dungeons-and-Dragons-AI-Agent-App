# Application Structure

This document describes the reorganized file structure of the D&D Dungeon Manager application.

## Directory Organization

### `core/`
Core database and utility modules:
- `db.py` - MongoDB connection and index management
- `mongo_fs.py` - Low-level MongoDB file system operations
- `result_format.py` - Result formatting utilities

### `dungeon/`
Dungeon management modules:
- `dungeon_manager.py` - High-level dungeon management API
- `interactive_dungeon_manager.py` - Interactive CLI for dungeon management

### `character/`
Character management modules:
- `dnd_character_agent.py` - D&D 5e character creation agent

### `web/`
Web application modules and assets:
- `web_app.py` - Flask web application
- `app_start.py` - Application startup script
- `auth.py` - Authentication and user management
- `check_permissions.py` - MongoDB permission checking utility
- `static/` - Web assets (CSS, JavaScript)
- `templates/` - HTML templates

### `dsl/`
Domain-Specific Language for dungeons:
- `dungeon_dsl.py` - DSL executor
- `test_dsl.py` - DSL tests
- `*.dsl` - DSL example files

### `examples/`
Example usage scripts:
- `example_usage.py` - Example demonstrations

### Root Level
- `requirements.txt` - Python dependencies
- `WEB_APP_README.md` - Web application documentation
- `venv/` - Virtual environment (not tracked in git)

## Import Paths

All imports have been updated to use the new structure:

- `from core.db import ...` - Database utilities
- `from core import mongo_fs as mf` - MongoDB file system
- `from dungeon import dungeon_manager as dm` - Dungeon management
- `from character.dnd_character_agent import ...` - Character agent
- `from web.auth import ...` - Authentication

## Running the Application

### Web Application
```bash
python web/web_app.py
```

### Interactive Dungeon Manager
```bash
python dungeon/interactive_dungeon_manager.py
```

### Example Usage
```bash
python examples/example_usage.py
```

### Check Permissions
```bash
python web/check_permissions.py
```

### Start App (Index Setup)
```bash
python web/app_start.py
```

