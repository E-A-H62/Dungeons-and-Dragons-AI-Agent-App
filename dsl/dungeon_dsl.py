"""
Dungeon DSL Executor

A Domain-Specific Language for managing D&D dungeons through simple commands.
Each line is a single command that maps to a dungeon_manager function.
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add parent directory to path to import dungeon_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dungeon import dungeon_manager as dm


class DSLSyntaxError(Exception):
    """Raised when DSL syntax is invalid."""
    pass


class DSLExecutionError(Exception):
    """Raised when DSL execution fails."""
    pass


def make_result(
    status: str,
    code: str,
    message: str,
    command: Dict[str, Any],
    target: Dict[str, Any],
    result: Dict[str, Any],
    diff: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    duration_ms: float = 0.0
) -> Dict[str, Any]:
    """
    Create a standard result format JSON object.
    
    Args:
        status: "ok", "error", or "skipped"
        code: Operation code (CREATED, UPDATED, ERROR_*, etc.)
        message: Human-readable message
        command: Command object with raw, name, and args
        target: Target object with type, path, and name
        result: Operation-specific result data
        diff: Optional diff object with applied and changes
        diagnostics: Optional diagnostics with warnings and logs
        duration_ms: Execution duration in milliseconds
    
    Returns:
        Standard result format dictionary
    """
    meta = {
        "ts": datetime.now().isoformat() + "Z",
        "duration_ms": round(duration_ms, 2)
    }
    
    response = {
        "version": "1.0",
        "status": status,
        "code": code,
        "message": message,
        "command": command,
        "target": target,
        "result": result,
        "meta": meta
    }
    
    if diff is not None:
        response["diff"] = diff
    
    if diagnostics is not None:
        response["diagnostics"] = diagnostics
    
    return response


def build_path(dungeon: Optional[str] = None, room: Optional[str] = None,
               category: Optional[str] = None, item: Optional[str] = None) -> str:
    """Build a path string from components."""
    parts = []
    if dungeon:
        parts.append(dungeon)
    if room:
        parts.append(room)
    if category:
        parts.append(category)
    if item:
        parts.append(item)
    return "/" + "/".join(parts) if parts else "/"


def build_command_name(entity: str, operation: str) -> str:
    """Build normalized command name like 'dungeon.create'."""
    return f"{entity}.{operation}"


def extract_args_dict(args: List[str], param_names: List[str]) -> Dict[str, Any]:
    """Extract named arguments from args list."""
    result = {}
    for i, param in enumerate(param_names):
        if i < len(args):
            result[param] = args[i]
    return result


def _map_error_to_code(error: Exception) -> str:
    """Map exception to error code."""
    if isinstance(error, dm.NotFoundError):
        return "ERROR_NOT_FOUND"
    elif isinstance(error, dm.ConflictError):
        return "ERROR_CONFLICT"
    elif isinstance(error, dm.UnsafeOperationError):
        return "ERROR_UNSAFE"
    elif isinstance(error, DSLSyntaxError):
        return "ERROR_PARSE"
    elif isinstance(error, ValueError):
        return "ERROR_VALIDATION"
    else:
        return "ERROR_INTERNAL"


def tokenize(line: str) -> list[str]:
    """
    Tokenize a DSL command line, handling quoted strings properly.
    
    Supports both single and double quotes, and preserves spaces within quotes.
    This allows field values with spaces to be properly parsed.
    """
    tokens = []
    current = ""
    in_quotes = False
    quote_char = None
    i = 0
    
    while i < len(line):
        char = line[i]
        
        # Only treat quote as delimiter if it's at word boundary (preceded by whitespace, start, or =)
        # or if we're already in quotes
        is_quote_at_boundary = char in ('"', "'") and (
            i == 0 or 
            line[i-1].isspace() or 
            line[i-1] == '=' or  # Allow quotes after = for field assignments
            (i < len(line) - 1 and line[i+1].isspace())
        )
        
        if is_quote_at_boundary and (i == 0 or line[i-1] != '\\'):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
                # Skip the closing quote
                i += 1
                continue
            else:
                current += char
        elif char in ('"', "'") and in_quotes:
            # Quote inside quoted string (different type)
            current += char
        elif char.isspace() and not in_quotes:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += char
        i += 1
    
    if current:
        tokens.append(current)
    
    # Remove quotes from tokens (they should already be removed, but just in case)
    tokens = [t.strip('"\'') for t in tokens if t.strip()]
    return tokens


def parse_value(value: str):
    """
    Parse a value string, handling booleans, None, and JSON structures.
    
    Converts string representations like "true", "false", "null" to Python types.
    Also attempts JSON parsing for lists and dictionaries.
    """
    value = value.strip()
    
    # Boolean literals
    if value.lower() in ("true", "yes", "on"):
        return True
    if value.lower() in ("false", "no", "off"):
        return False
    
    # None/null
    if value.lower() in ("none", "null"):
        return None
    
    # Try to parse as JSON (for lists, dicts, numbers)
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Return as string
    return value


def parse_tags(tags_str: str) -> list[str]:
    """Parse comma-separated tags."""
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def parse_metadata(meta_str: str) -> dict:
    """Parse metadata string like 'key1=value1,key2=value2'."""
    result = {}
    for pair in meta_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key.strip()] = parse_value(value.strip())
    return result


def parse_field_args(args: list[str]) -> dict:
    """
    Parse field arguments like summary=..., tags=..., meta=...
    
    Handles both positional arguments (for backward compatibility) and
    named field assignments. If any field assignments are found, treats
    remaining unassigned args as part of quoted values that were split.
    """
    fields = {}
    i = 0
    # Track if we've seen any field assignments (with =) to avoid treating unassigned args as positional
    has_field_assignments = False
    
    while i < len(args):
        arg = args[i]
        if "=" in arg:
            has_field_assignments = True
            key, value = arg.split("=", 1)
            key = key.strip()
            # Strip quotes from value if present
            value = value.strip('"\'')
            
            if key == "tags":
                fields["tags"] = parse_tags(value)
            elif key == "meta":
                fields["metadata"] = parse_metadata(value)
            elif key in ("summary", "notes", "notes_md"):
                # Map "notes" to "notes_md" for backward compatibility
                target_key = "notes_md" if key in ("notes", "notes_md") else "summary"
                fields[target_key] = value
            else:
                fields[key] = parse_value(value)
        else:
            # Only treat as positional argument if we haven't seen any field assignments
            # This prevents mis-assignment when field values with spaces are split into multiple tokens
            if not has_field_assignments:
                # Positional argument without key (only for create operations, not update)
                if "summary" not in fields:
                    fields["summary"] = arg
                elif "notes_md" not in fields:
                    fields["notes_md"] = arg
            # If we've seen field assignments, skip unassigned args (they're likely part of a quoted value that was split)
        i += 1
    return fields


def execute_command(line: str, output=None) -> Optional[Dict[str, Any]]:
    """
    Execute a single DSL command line.
    
    Parses the command, calls the appropriate dungeon_manager function,
    and returns a standardized result dictionary.
    
    Returns None for comments or empty lines.
    """
    if output is None:
        output = []
    
    # Strip comments and whitespace
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    
    # Tokenize the line (handling quoted strings)
    parts = tokenize(line)
    if not parts:
        return None
    
    cmd = parts[0].lower()
    args = parts[1:]
    
    start_time = time.time()
    raw_line = line
    
    try:
        # ===== DUNGEON COMMANDS =====
        if cmd == "dungeon" and len(args) >= 1:
            subcmd = args[0].lower()
            
            if subcmd == "create" and len(args) >= 2:
                name = args[1]
                exists_ok = "exists_ok" in args or "--exists-ok" in args
                cmd_args = {"name": name, "exists_ok": exists_ok}
                
                result_data = dm.create_dungeon(name=name, exists_ok=exists_ok)
                duration_ms = (time.time() - start_time) * 1000
                
                # Get created_at from MongoDB if available, otherwise use None
                created_at = None
                try:
                    from db import db
                    dungeon_doc = db().dungeons.find_one({"name": name, "deleted": False})
                    if dungeon_doc and "created_at" in dungeon_doc:
                        created_at = dungeon_doc["created_at"].timestamp()
                except:
                    pass
                
                return make_result(
                    status="ok",
                    code="CREATED",
                    message=f"Dungeon '{name}' created.",
                    command={"raw": raw_line, "name": "dungeon.create", "args": cmd_args},
                    target={"type": "dungeon", "path": build_path(dungeon=name), "name": name},
                    result={"dungeon": {"name": result_data["name"], "deleted": result_data["deleted"], "created_at": created_at}},
                    diff={"applied": True, "changes": [{"op": "add", "path": build_path(dungeon=name), "node_type": "dungeon", "name": name, "from": None, "to": name}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "list":
                result_data = dm.list_dungeons()
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="LIST",
                    message=f"Listed {len(result_data)} dungeons.",
                    command={"raw": raw_line, "name": "dungeon.list", "args": {}},
                    target={"type": "dungeon", "path": "/", "name": ""},
                    result={"dungeons": result_data},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "rename" and len(args) >= 3:
                old_name = args[1]
                new_name = args[2]
                cmd_args = {"dungeon": old_name, "new_name": new_name}
                
                result_data = dm.rename_dungeon(dungeon=old_name, new_name=new_name)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="RENAMED",
                    message=f"Dungeon '{old_name}' renamed to '{new_name}'.",
                    command={"raw": raw_line, "name": "dungeon.rename", "args": cmd_args},
                    target={"type": "dungeon", "path": build_path(dungeon=new_name), "name": new_name},
                    result={"dungeon": {"name": result_data["name"], "deleted": result_data["deleted"]}},
                    diff={"applied": True, "changes": [{"op": "update", "path": build_path(dungeon=new_name), "node_type": "dungeon", "name": new_name, "from": old_name, "to": new_name}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "delete" and len(args) >= 2:
                name = args[1]
                token = None
                if "token=" in " ".join(args):
                    for arg in args:
                        if arg.startswith("token="):
                            token = arg.split("=", 1)[1]
                            # Strip quotes if present (tokenizer might not have removed them from value part)
                            token = token.strip('"\'')
                cmd_args = {"dungeon": name}
                if token:
                    cmd_args["confirm_token"] = token
                
                dm.delete_dungeon(dungeon=name, confirm_token=token)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="DELETED_HARD",
                    message=f"Dungeon '{name}' permanently deleted.",
                    command={"raw": raw_line, "name": "dungeon.delete", "args": cmd_args},
                    target={"type": "dungeon", "path": build_path(dungeon=name), "name": name},
                    result={"deleted": True, "hard": True},
                    diff={"applied": True, "changes": [{"op": "remove", "path": build_path(dungeon=name), "node_type": "dungeon", "name": name, "from": name, "to": None}]},
                    duration_ms=duration_ms
                )
        
        # ===== ROOM COMMANDS =====
        elif cmd == "room" and len(args) >= 1:
            subcmd = args[0].lower()
            
            if subcmd == "create" and len(args) >= 3:
                dungeon = args[1]
                name = args[2]
                summary = args[3] if len(args) > 3 and "=" not in args[3] else None
                exists_ok = "exists_ok" in args or "--exists-ok" in args
                
                # Parse optional fields
                fields = parse_field_args(args[3:])
                if "summary" in fields:
                    summary = fields["summary"]
                
                cmd_args = {"dungeon": dungeon, "name": name, "exists_ok": exists_ok}
                if summary:
                    cmd_args["summary"] = summary
                
                result_data = dm.create_room(dungeon=dungeon, name=name, summary=summary, exists_ok=exists_ok)
                duration_ms = (time.time() - start_time) * 1000
                
                # Use summary from the parameter (already available) instead of accessing STORE
                return make_result(
                    status="ok",
                    code="CREATED",
                    message=f"Room '{name}' created in '{dungeon}'.",
                    command={"raw": raw_line, "name": "room.create", "args": cmd_args},
                    target={"type": "room", "path": build_path(dungeon=dungeon, room=name), "name": name},
                    result={"room": {"name": result_data["name"], "summary": summary, "deleted": result_data["deleted"]}},
                    diff={"applied": True, "changes": [{"op": "add", "path": build_path(dungeon=dungeon, room=name), "node_type": "room", "name": name, "from": None, "to": name}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "list" and len(args) >= 2:
                dungeon = args[1]
                cmd_args = {"dungeon": dungeon}
                
                result_data = dm.list_rooms(dungeon=dungeon)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="LIST",
                    message=f"Listed {len(result_data)} rooms in '{dungeon}'.",
                    command={"raw": raw_line, "name": "room.list", "args": cmd_args},
                    target={"type": "dungeon", "path": build_path(dungeon=dungeon), "name": dungeon},
                    result={"rooms": result_data},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "rename" and len(args) >= 4:
                dungeon = args[1]
                old_name = args[2]
                new_name = args[3]
                cmd_args = {"dungeon": dungeon, "room": old_name, "new_name": new_name}
                
                result_data = dm.rename_room(dungeon=dungeon, room=old_name, new_name=new_name)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="RENAMED",
                    message=f"Room '{old_name}' renamed to '{new_name}' in '{dungeon}'.",
                    command={"raw": raw_line, "name": "room.rename", "args": cmd_args},
                    target={"type": "room", "path": build_path(dungeon=dungeon, room=new_name), "name": new_name},
                    result={"room": {"name": result_data["name"], "deleted": result_data["deleted"]}},
                    diff={"applied": True, "changes": [{"op": "update", "path": build_path(dungeon=dungeon, room=new_name), "node_type": "room", "name": new_name, "from": old_name, "to": new_name}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "delete" and len(args) >= 3:
                dungeon = args[1]
                name = args[2]
                token = None
                if "token=" in " ".join(args):
                    for arg in args:
                        if arg.startswith("token="):
                            token = arg.split("=", 1)[1]
                            # Strip quotes if present (tokenizer might not have removed them from value part)
                            token = token.strip('"\'')
                cmd_args = {"dungeon": dungeon, "room": name}
                if token:
                    cmd_args["confirm_token"] = token
                
                dm.delete_room(dungeon=dungeon, room=name, confirm_token=token)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="DELETED_HARD",
                    message=f"Room '{name}' permanently deleted from '{dungeon}'.",
                    command={"raw": raw_line, "name": "room.delete", "args": cmd_args},
                    target={"type": "room", "path": build_path(dungeon=dungeon, room=name), "name": name},
                    result={"deleted": True, "hard": True},
                    diff={"applied": True, "changes": [{"op": "remove", "path": build_path(dungeon=dungeon, room=name), "node_type": "room", "name": name, "from": name, "to": None}]},
                    duration_ms=duration_ms
                )
        
        # ===== ITEM COMMANDS =====
        elif cmd == "item" and len(args) >= 1:
            subcmd = args[0].lower()
            
            if subcmd == "create" and len(args) >= 5:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                name = args[4]
                
                # Parse optional fields
                fields = parse_field_args(args[5:])
                payload = {"name": name}
                if "summary" in fields:
                    payload["summary"] = fields["summary"]
                if "notes_md" in fields:
                    payload["notes_md"] = fields["notes_md"]
                if "tags" in fields:
                    payload["tags"] = fields["tags"]
                if "metadata" in fields:
                    payload["metadata"] = fields["metadata"]
                
                exists_ok = "exists_ok" in args or "--exists-ok" in args
                cmd_args = {"dungeon": dungeon, "room": room, "category": category, "name": name, "exists_ok": exists_ok}
                cmd_args.update(payload)
                
                result_data = dm.create_item(
                    dungeon=dungeon,
                    room=room,
                    category=category,
                    payload=payload,
                    exists_ok=exists_ok
                )
                duration_ms = (time.time() - start_time) * 1000
                
                item_data = dm.read_item(dungeon=dungeon, room=room, category=category, item=name)
                return make_result(
                    status="ok",
                    code="CREATED",
                    message=f"Item '{name}' created in '{dungeon}/{room}/{category}'.",
                    command={"raw": raw_line, "name": "item.create", "args": cmd_args},
                    target={"type": "item", "path": build_path(dungeon=dungeon, room=room, category=category, item=name), "name": name},
                    result={"item": item_data},
                    diff={"applied": True, "changes": [{"op": "add", "path": build_path(dungeon=dungeon, room=room, category=category, item=name), "node_type": "item", "name": name, "from": None, "to": name}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "read" and len(args) >= 5:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                name = args[4]
                cmd_args = {"dungeon": dungeon, "room": room, "category": category, "item": name}
                
                result_data = dm.read_item(dungeon=dungeon, room=room, category=category, item=name)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="READ",
                    message=f"Item '{name}' read.",
                    command={"raw": raw_line, "name": "item.read", "args": cmd_args},
                    target={"type": "item", "path": build_path(dungeon=dungeon, room=room, category=category, item=name), "name": name},
                    result={"item": result_data},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "update" and len(args) >= 5:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                name = args[4]
                patch = parse_field_args(args[5:])
                cmd_args = {"dungeon": dungeon, "room": room, "category": category, "item": name}
                cmd_args.update(patch)
                
                result_data = dm.update_item(dungeon=dungeon, room=room, category=category, item=name, patch=patch)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="UPDATED",
                    message=f"Item '{name}' updated.",
                    command={"raw": raw_line, "name": "item.update", "args": cmd_args},
                    target={"type": "item", "path": build_path(dungeon=dungeon, room=room, category=category, item=result_data["name"]), "name": result_data["name"]},
                    result={"item": result_data},
                    diff={"applied": True, "changes": [{"op": "update", "path": build_path(dungeon=dungeon, room=room, category=category, item=result_data["name"]), "node_type": "item", "name": result_data["name"], "from": name, "to": result_data["name"]}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "rename" and len(args) >= 6:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                old_name = args[4]
                new_name = args[5]
                cmd_args = {"dungeon": dungeon, "room": room, "category": category, "item": old_name, "new_name": new_name}
                
                result_data = dm.rename_item(dungeon=dungeon, room=room, category=category, item=old_name, new_name=new_name)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="RENAMED",
                    message=f"Item '{old_name}' renamed to '{new_name}'.",
                    command={"raw": raw_line, "name": "item.rename", "args": cmd_args},
                    target={"type": "item", "path": build_path(dungeon=dungeon, room=room, category=category, item=new_name), "name": new_name},
                    result={"item": result_data},
                    diff={"applied": True, "changes": [{"op": "update", "path": build_path(dungeon=dungeon, room=room, category=category, item=new_name), "node_type": "item", "name": new_name, "from": old_name, "to": new_name}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "delete" and len(args) >= 5:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                name = args[4]
                token = None
                if "token=" in " ".join(args):
                    for arg in args:
                        if arg.startswith("token="):
                            token = arg.split("=", 1)[1]
                            # Strip quotes if present (tokenizer might not have removed them from value part)
                            token = token.strip('"\'')
                cmd_args = {"dungeon": dungeon, "room": room, "category": category, "item": name}
                if token:
                    cmd_args["confirm_token"] = token
                
                dm.delete_item(
                    dungeon=dungeon, room=room, category=category, item=name,
                    confirm_token=token
                )
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="DELETED_HARD",
                    message=f"Item '{name}' permanently deleted.",
                    command={"raw": raw_line, "name": "item.delete", "args": cmd_args},
                    target={"type": "item", "path": build_path(dungeon=dungeon, room=room, category=category, item=name), "name": name},
                    result={"deleted": True, "hard": True},
                    diff={"applied": True, "changes": [{"op": "remove", "path": build_path(dungeon=dungeon, room=room, category=category, item=name), "node_type": "item", "name": name, "from": name, "to": None}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "move" and len(args) >= 8:
                src_dungeon = args[1]
                src_room = args[2]
                src_category = args[3]
                item = args[4]
                dst_dungeon = args[5]
                dst_room = args[6]
                dst_category = args[7]
                overwrite = "overwrite" in args or "--overwrite" in args
                cmd_args = {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item,
                           "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "overwrite": overwrite}
                
                result_data = dm.move_item(
                    src_dungeon=src_dungeon, src_room=src_room, src_category=src_category, item=item,
                    dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
                    overwrite=overwrite
                )
                duration_ms = (time.time() - start_time) * 1000
                
                src_path = build_path(dungeon=src_dungeon, room=src_room, category=src_category, item=item)
                dst_path = build_path(dungeon=dst_dungeon, room=dst_room, category=dst_category, item=item)
                return make_result(
                    status="ok",
                    code="MOVED",
                    message=f"Item '{item}' moved to '{dst_dungeon}/{dst_room}/{dst_category}'.",
                    command={"raw": raw_line, "name": "item.move", "args": cmd_args},
                    target={"type": "item", "path": dst_path, "name": item},
                    result={"item": {"name": item}, "source": src_path, "destination": dst_path},
                    diff={"applied": True, "changes": [{"op": "remove", "path": src_path, "node_type": "item", "name": item, "from": item, "to": None},
                                                      {"op": "add", "path": dst_path, "node_type": "item", "name": item, "from": None, "to": item}]},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "copy" and len(args) >= 8:
                src_dungeon = args[1]
                src_room = args[2]
                src_category = args[3]
                item = args[4]
                dst_dungeon = args[5]
                dst_room = args[6]
                dst_category = args[7]
                new_name = None
                overwrite = False
                for arg in args[8:]:
                    if arg.startswith("new_name="):
                        new_name = arg.split("=", 1)[1]
                    elif arg in ("overwrite", "--overwrite"):
                        overwrite = True
                cmd_args = {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item,
                           "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "overwrite": overwrite}
                if new_name:
                    cmd_args["new_name"] = new_name
                
                result_data = dm.copy_item(
                    src_dungeon=src_dungeon, src_room=src_room, src_category=src_category, item=item,
                    dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
                    new_name=new_name, overwrite=overwrite
                )
                duration_ms = (time.time() - start_time) * 1000
                
                final_name = new_name or item
                src_path = build_path(dungeon=src_dungeon, room=src_room, category=src_category, item=item)
                dst_path = build_path(dungeon=dst_dungeon, room=dst_room, category=dst_category, item=final_name)
                return make_result(
                    status="ok",
                    code="COPIED",
                    message=f"Item '{item}' copied to '{dst_dungeon}/{dst_room}/{dst_category}'.",
                    command={"raw": raw_line, "name": "item.copy", "args": cmd_args},
                    target={"type": "item", "path": dst_path, "name": final_name},
                    result={"item": {"name": final_name}, "source": src_path, "destination": dst_path},
                    diff={"applied": True, "changes": [{"op": "add", "path": dst_path, "node_type": "item", "name": final_name, "from": None, "to": final_name}]},
                    duration_ms=duration_ms
                )
        
        # ===== CATEGORY COMMANDS =====
        elif cmd == "category" and len(args) >= 1:
            subcmd = args[0].lower()
            
            if subcmd == "list" and len(args) >= 4:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                cmd_args = {"dungeon": dungeon, "room": room, "category": category}
                
                result_data = dm.list_category_items(dungeon=dungeon, room=room, category=category)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="LIST",
                    message=f"Listed {len(result_data)} items in '{category}'.",
                    command={"raw": raw_line, "name": "category.list", "args": cmd_args},
                    target={"type": "category", "path": build_path(dungeon=dungeon, room=room, category=category), "name": category},
                    result={"category": category, "items": result_data},
                    duration_ms=duration_ms
                )
            
            elif subcmd == "ensure" and len(args) >= 4:
                dungeon = args[1]
                room = args[2]
                category = args[3]
                cmd_args = {"dungeon": dungeon, "room": room, "category": category}
                
                result_data = dm.ensure_category(dungeon=dungeon, room=room, category=category)
                duration_ms = (time.time() - start_time) * 1000
                
                return make_result(
                    status="ok",
                    code="ENSURED",
                    message=f"Category '{category}' ensured in '{dungeon}/{room}'.",
                    command={"raw": raw_line, "name": "category.ensure", "args": cmd_args},
                    target={"type": "category", "path": build_path(dungeon=dungeon, room=room, category=category), "name": category},
                    result={"category": {"name": result_data["name"], "ensured": True}},
                    duration_ms=duration_ms
                )
        
        # ===== UTILITY COMMANDS =====
        elif cmd == "search" and len(args) >= 1:
            query = args[0]
            dungeon = None
            tags = None
            for arg in args[1:]:
                if arg.startswith("dungeon="):
                    dungeon = arg.split("=", 1)[1]
                elif arg.startswith("tags="):
                    tags = parse_tags(arg.split("=", 1)[1])
            cmd_args = {"query": query}
            if dungeon:
                cmd_args["dungeon"] = dungeon
            if tags:
                cmd_args["tags"] = tags
            
            result_data = dm.search(query=query, dungeon=dungeon, tags_any=tags)
            duration_ms = (time.time() - start_time) * 1000
            
            matches = [{"path": build_path(dungeon=r["dungeon"], room=r["room"], category=r["category"], item=r["name"]), "name": r["name"]} for r in result_data]
            return make_result(
                status="ok",
                code="LIST",
                message=f"Found {len(result_data)} matches for '{query}'.",
                command={"raw": raw_line, "name": "search", "args": cmd_args},
                target={"type": "item", "path": "/", "name": ""},
                result={"query": query, "matches": matches},
                duration_ms=duration_ms
            )
        
        elif cmd == "stat" and len(args) >= 1:
            dungeon = args[0]
            room = args[1] if len(args) > 1 else None
            category = args[2] if len(args) > 2 else None
            item = args[3] if len(args) > 3 else None
            cmd_args = {"dungeon": dungeon}
            if room:
                cmd_args["room"] = room
            if category:
                cmd_args["category"] = category
            if item:
                cmd_args["item"] = item
            
            result_data = dm.stat(dungeon=dungeon, room=room, category=category, item=item)
            duration_ms = (time.time() - start_time) * 1000
            
            target_type = result_data.get("type", "dungeon")
            target_path = build_path(dungeon=dungeon, room=room, category=category, item=item)
            target_name = result_data.get("name", dungeon)
            
            return make_result(
                status="ok",
                code="READ",
                message=f"Stat for {target_type} '{target_name}'.",
                command={"raw": raw_line, "name": "stat", "args": cmd_args},
                target={"type": target_type, "path": target_path, "name": target_name},
                result={"node": result_data},
                duration_ms=duration_ms
            )
        
        elif cmd == "list" and len(args) >= 1:
            dungeon = args[0]
            room = args[1] if len(args) > 1 else None
            category = args[2] if len(args) > 2 else None
            cmd_args = {"dungeon": dungeon}
            if room:
                cmd_args["room"] = room
            if category:
                cmd_args["category"] = category
            
            result_data = dm.list_children(dungeon=dungeon, room=room, category=category)
            duration_ms = (time.time() - start_time) * 1000
            
            parent_path = build_path(dungeon=dungeon, room=room, category=category)
            return make_result(
                status="ok",
                code="LIST",
                message=f"Listed {len(result_data)} children.",
                command={"raw": raw_line, "name": "list", "args": cmd_args},
                target={"type": "dungeon" if not room else ("room" if not category else "category"), "path": parent_path, "name": dungeon if not room else (room if not category else category)},
                result={"parent": parent_path, "children": result_data},
                duration_ms=duration_ms
            )
        
        elif cmd == "export" and len(args) >= 1:
            dungeon = args[0]
            cmd_args = {"dungeon": dungeon}
            
            result_data = dm.export_dungeon(dungeon=dungeon)
            duration_ms = (time.time() - start_time) * 1000
            
            return make_result(
                status="ok",
                code="READ",
                message=f"Dungeon '{dungeon}' exported.",
                command={"raw": raw_line, "name": "export", "args": cmd_args},
                target={"type": "dungeon", "path": build_path(dungeon=dungeon), "name": dungeon},
                result={"export": result_data},
                duration_ms=duration_ms
            )
        
        elif cmd == "import" and len(args) >= 1:
            # Import expects JSON data, but for simplicity we'll assume it's passed as a file path
            # or we need to handle JSON inline
            raise DSLSyntaxError("Import command requires JSON data. Use dungeon_manager.import_dungeon() directly.")
        
        else:
            raise DSLSyntaxError(f"Unknown command: {line}")
    
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_code = _map_error_to_code(e)
        
        # Try to extract command info for error response
        try:
            parts = tokenize(raw_line)
            cmd_name = parts[0].lower() if parts else "unknown"
            cmd_args_dict = {}
            if len(parts) > 1:
                # Try to build basic args dict
                if cmd_name == "dungeon" and len(parts) > 1:
                    cmd_args_dict["dungeon"] = parts[1] if len(parts) > 1 else ""
                elif cmd_name == "room" and len(parts) > 2:
                    cmd_args_dict["dungeon"] = parts[1]
                    cmd_args_dict["room"] = parts[2] if len(parts) > 2 else ""
                elif cmd_name == "item" and len(parts) > 4:
                    cmd_args_dict["dungeon"] = parts[1]
                    cmd_args_dict["room"] = parts[2]
                    cmd_args_dict["category"] = parts[3]
                    cmd_args_dict["item"] = parts[4] if len(parts) > 4 else ""
        except:
            cmd_name = "unknown"
            cmd_args_dict = {}
        
        # Build target info
        target_type = "dungeon"
        target_path = "/"
        target_name = ""
        try:
            if cmd_name == "dungeon" and len(parts) > 1:
                target_name = parts[1]
                target_path = build_path(dungeon=target_name)
            elif cmd_name == "room" and len(parts) > 2:
                target_type = "room"
                target_name = parts[2]
                target_path = build_path(dungeon=parts[1], room=target_name)
            elif cmd_name == "item" and len(parts) > 4:
                target_type = "item"
                target_name = parts[4]
                target_path = build_path(dungeon=parts[1], room=parts[2], category=parts[3], item=target_name)
        except:
            pass
        
        return make_result(
            status="error",
            code=error_code,
            message=str(e),
            command={"raw": raw_line, "name": cmd_name, "args": cmd_args_dict},
            target={"type": target_type, "path": target_path, "name": target_name},
            result={},
            diagnostics={"warnings": [], "logs": [f"Error: {str(e)}"]},
            duration_ms=duration_ms
        )


def execute_file(filepath: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Execute a DSL script file line by line.
    
    Processes each line as a command and collects all results.
    Returns a batch result envelope with summary statistics and
    all individual command results.
    """
    start_time = time.time()
    results = []
    output = []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        lines_total = len(lines)
        ok_count = 0
        error_count = 0
        skipped_count = 0
        
        for line_num, line in enumerate(lines, 1):
            try:
                result = execute_command(line, output)
                if result is None:
                    skipped_count += 1
                elif result.get("status") == "ok":
                    ok_count += 1
                    results.append(result)
                elif result.get("status") == "error":
                    error_count += 1
                    results.append(result)
                else:
                    skipped_count += 1
                    results.append(result)
            except (DSLSyntaxError, DSLExecutionError) as e:
                error_count += 1
                error_msg = f"Line {line_num}: {str(e)}"
                output.append(f"ERROR: {error_msg}")
                # Create error result
                error_result = make_result(
                    status="error",
                    code="ERROR_PARSE",
                    message=error_msg,
                    command={"raw": line.strip(), "name": "unknown", "args": {}},
                    target={"type": "dungeon", "path": "/", "name": ""},
                    result={},
                    diagnostics={"warnings": [], "logs": [error_msg]},
                    duration_ms=0.0
                )
                results.append(error_result)
                if verbose:
                    print(f"ERROR: {error_msg}")
            except Exception as e:
                error_count += 1
                error_msg = f"Line {line_num}: Unexpected error - {str(e)}"
                output.append(f"ERROR: {error_msg}")
                error_result = make_result(
                    status="error",
                    code="ERROR_INTERNAL",
                    message=error_msg,
                    command={"raw": line.strip(), "name": "unknown", "args": {}},
                    target={"type": "dungeon", "path": "/", "name": ""},
                    result={},
                    diagnostics={"warnings": [], "logs": [error_msg]},
                    duration_ms=0.0
                )
                results.append(error_result)
                if verbose:
                    print(f"ERROR: {error_msg}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        if verbose:
            for msg in output:
                print(msg)
        
        # Return batch envelope
        return {
            "version": "1.0",
            "status": "ok" if error_count == 0 else "error",
            "code": "BATCH",
            "file": filepath,
            "summary": {
                "lines_total": lines_total,
                "ok": ok_count,
                "error": error_count,
                "skipped": skipped_count,
                "duration_ms": round(duration_ms, 2)
            },
            "results": results,
            "meta": {
                "ts": datetime.now().isoformat() + "Z"
            }
        }
    
    except FileNotFoundError:
        error_msg = f"File not found: {filepath}"
        if verbose:
            print(f"ERROR: {error_msg}")
        raise DSLExecutionError(error_msg)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dungeon_dsl.py <script.dsl>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    execute_file(script_path)

