"""
D&D Dungeon Organizer - MongoDB-Backed File-System Manager

A Python implementation for managing dungeons, rooms, and items
(puzzles, traps, treasures, enemies) using MongoDB.

This module provides a high-level API that wraps the low-level mongo_fs
operations and converts MongoDB result envelopes into simple return values
or raises appropriate exceptions.
"""

from typing import Optional, List, Dict
from core import mongo_fs as mf


# ============================================================================
# 1) Custom Errors (maintained for backward compatibility)
# ============================================================================

class NotFoundError(Exception):
    """Raised when a requested resource is not found in the database."""
    pass


class ConflictError(Exception):
    """Raised when an operation conflicts with existing data (e.g., duplicate name)."""
    pass


class UnsafeOperationError(Exception):
    """Raised when a destructive operation lacks proper confirmation token."""
    pass


# ============================================================================
# 2) Helper: Extract data from MongoDB result envelopes
# ============================================================================

def _extract_result(mongo_result: dict) -> dict:
    """
    Extract the actual result data from MongoDB result envelope.
    
    Converts MongoDB error codes into appropriate Python exceptions
    for cleaner error handling in the high-level API.
    """
    if mongo_result["status"] == "error":
        code = mongo_result.get("code", "ERROR")
        message = mongo_result.get("message", "Unknown error")
        
        if code == "ERROR_NOT_FOUND":
            raise NotFoundError(message)
        elif code == "ERROR_CONFLICT":
            raise ConflictError(message)
        elif code == "ERROR_UNSAFE":
            raise UnsafeOperationError(message)
        else:
            raise ValueError(message)
    
    return mongo_result.get("result", {})


def _extract_dungeon_info(mongo_result: dict) -> dict:
    """Extract dungeon info from MongoDB result."""
    result = _extract_result(mongo_result)
    dungeon_data = result.get("dungeon", {})
    return {
        "type": "dungeon",
        "name": dungeon_data.get("name", ""),
        "summary": dungeon_data.get("summary"),
        "deleted": dungeon_data.get("deleted", False)
    }


def _extract_room_info(mongo_result: dict) -> dict:
    """Extract room info from MongoDB result."""
    result = _extract_result(mongo_result)
    room_data = result.get("room", {})
    return {
        "type": "room",
        "dungeon": room_data.get("dungeon", ""),
        "name": room_data.get("name", ""),
        "summary": room_data.get("summary"),
        "deleted": room_data.get("deleted", False)
    }


def _extract_item_info(mongo_result: dict) -> dict:
    """Extract item info from MongoDB result."""
    result = _extract_result(mongo_result)
    item_data = result.get("item", {})
    return {
        "type": "item",
        "dungeon": item_data.get("dungeon", ""),
        "room": item_data.get("room", ""),
        "category": item_data.get("category", ""),
        "name": item_data.get("name", ""),
        "deleted": item_data.get("deleted", False)
    }


# ============================================================================
# 3) Functions — One per Task (MongoDB-backed)
# ============================================================================

# --- Dungeons ---

def create_dungeon(*, name: str, summary: Optional[str] = None, exists_ok: bool = False, user_id: Optional[str] = None) -> dict:
    """
    Create a new dungeon.
    
    Returns a dictionary with dungeon info (name, summary, deleted status).
    Raises ConflictError if dungeon already exists (unless exists_ok=True).
    """
    result = mf.create_dungeon(name=name, summary=summary, exists_ok=exists_ok, user_id=user_id, raw="")
    return _extract_dungeon_info(result)


def list_dungeons(*, user_id: Optional[str] = None) -> List[dict]:
    """List all non-deleted dungeons."""
    result = mf.list_dungeons(user_id=user_id, raw="")
    data = _extract_result(result)
    dungeons = data.get("dungeons", [])
    return [{"type": "dungeon", "name": d["name"], "summary": d.get("summary"), "deleted": d.get("deleted", False)} for d in dungeons]


def rename_dungeon(*, dungeon: str, new_name: str, user_id: Optional[str] = None) -> dict:
    """Rename a dungeon."""
    result = mf.rename_dungeon(dungeon=dungeon, new_name=new_name, user_id=user_id, raw="")
    return _extract_dungeon_info(result)


def update_dungeon(*, dungeon: str, patch: dict, user_id: Optional[str] = None) -> dict:
    """Update a dungeon."""
    result = mf.update_dungeon(dungeon=dungeon, patch=patch, user_id=user_id, raw="")
    return _extract_dungeon_info(result)


def delete_dungeon(*, dungeon: str, confirm_token: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """
    Delete a dungeon (permanent deletion with confirmation required).
    
    This is a hard delete - permanently removes the dungeon and all
    associated rooms and items. Requires confirmation token to prevent accidents.
    """
    result = mf.delete_dungeon(dungeon=dungeon, token=confirm_token, user_id=user_id, raw="")
    if result["status"] == "error":
        code = result.get("code", "ERROR")
        message = result.get("message", "Unknown error")
        if code == "ERROR_NOT_FOUND":
            raise NotFoundError(message)
        elif code == "ERROR_UNSAFE":
            raise UnsafeOperationError(message)
        else:
            raise ValueError(message)
    # Success - no return value for delete operations


# --- Rooms ---

def create_room(*, dungeon: str, name: str, exists_ok: bool = False, summary: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """Create a new room in a dungeon."""
    result = mf.create_room(dungeon=dungeon, name=name, summary=summary, exists_ok=exists_ok, user_id=user_id, raw="")
    return _extract_room_info(result)


def list_rooms(*, dungeon: str, user_id: Optional[str] = None) -> List[dict]:
    """List all non-deleted rooms in a dungeon."""
    result = mf.list_rooms(dungeon=dungeon, user_id=user_id, raw="")
    data = _extract_result(result)
    rooms = data.get("rooms", [])
    return [
        {"type": "room", "dungeon": r.get("dungeon", dungeon), "name": r["name"], "summary": r.get("summary"), "deleted": r.get("deleted", False)}
        for r in rooms
    ]


def rename_room(*, dungeon: str, room: str, new_name: str, user_id: Optional[str] = None) -> dict:
    """Rename a room."""
    result = mf.rename_room(dungeon=dungeon, room=room, new_name=new_name, user_id=user_id, raw="")
    return _extract_room_info(result)


def update_room(*, dungeon: str, room: str, patch: dict, user_id: Optional[str] = None) -> dict:
    """Update a room."""
    result = mf.update_room(dungeon=dungeon, room=room, patch=patch, user_id=user_id, raw="")
    return _extract_room_info(result)


def delete_room(*, dungeon: str, room: str, confirm_token: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """Delete a room (permanent deletion with confirmation required)."""
    result = mf.delete_room(dungeon=dungeon, room=room, token=confirm_token, user_id=user_id, raw="")
    if result["status"] == "error":
        code = result.get("code", "ERROR")
        message = result.get("message", "Unknown error")
        if code == "ERROR_NOT_FOUND":
            raise NotFoundError(message)
        elif code == "ERROR_UNSAFE":
            raise UnsafeOperationError(message)
        else:
            raise ValueError(message)
    # Success - no return value for delete operations


# --- Categories (fixed) ---

def ensure_category(*, dungeon: str, room: str, category: str, user_id: Optional[str] = None) -> dict:
    """Ensure a category exists in a room."""
    result = mf.ensure_category(dungeon=dungeon, room=room, category=category, user_id=user_id, raw="")
    data = _extract_result(result)
    cat_data = data.get("category", {})
    return {
        "type": "category",
        "dungeon": cat_data.get("dungeon", dungeon),
        "room": cat_data.get("room", room),
        "name": cat_data.get("name", category)
    }


def list_category_items(*, dungeon: str, room: str, category: str, user_id: Optional[str] = None) -> List[dict]:
    """List all non-deleted items in a category."""
    result = mf.list_category_items(dungeon=dungeon, room=room, category=category, user_id=user_id, raw="")
    data = _extract_result(result)
    items = data.get("items", [])
    return [
        {
            "type": "item",
            "dungeon": i.get("dungeon", dungeon),
            "room": i.get("room", room),
            "category": i.get("category", category),
            "name": i["name"],
            "deleted": i.get("deleted", False)
        }
        for i in items
    ]


# --- Items ---

def create_item(*, dungeon: str, room: str, category: str, payload: dict, exists_ok: bool = False, user_id: Optional[str] = None) -> dict:
    """Create a new item in a category."""
    result = mf.create_item(dungeon=dungeon, room=room, category=category, payload=payload, exists_ok=exists_ok, user_id=user_id, raw="")
    data = _extract_result(result)
    item_data = data.get("item", {})
    return {
        "type": "item",
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "name": item_data.get("name", ""),
        "deleted": item_data.get("deleted", False)
    }


def read_item(*, dungeon: str, room: str, category: str, item: str, user_id: Optional[str] = None) -> dict:
    """Read an item's full data."""
    result = mf.read_item(dungeon=dungeon, room=room, category=category, item=item, user_id=user_id, raw="")
    data = _extract_result(result)
    item_data = data.get("item", {})
    # Convert timestamps to floats for backward compatibility
    return {
        "name": item_data.get("name", ""),
        "summary": item_data.get("summary"),
        "notes_md": item_data.get("notes_md"),
        "tags": item_data.get("tags", []),
        "metadata": item_data.get("metadata", {}),
        "created_at": item_data.get("created_at", 0.0),
        "updated_at": item_data.get("updated_at", 0.0)
    }


def update_item(*, dungeon: str, room: str, category: str, item: str, patch: dict, user_id: Optional[str] = None) -> dict:
    """Update an item with a patch dictionary."""
    result = mf.update_item(dungeon=dungeon, room=room, category=category, item=item, patch=patch, user_id=user_id, raw="")
    # Return the updated item data in the same format as read_item
    return read_item(dungeon=dungeon, room=room, category=category, item=result["result"]["item"]["name"], user_id=user_id)


def rename_item(*, dungeon: str, room: str, category: str, item: str, new_name: str, user_id: Optional[str] = None) -> dict:
    """Rename an item."""
    return update_item(dungeon=dungeon, room=room, category=category, item=item, patch={"name": new_name}, user_id=user_id)


def delete_item(*, dungeon: str, room: str, category: str, item: str, confirm_token: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """Delete an item (permanent deletion with confirmation required)."""
    result = mf.delete_item(dungeon=dungeon, room=room, category=category, item=item, token=confirm_token, user_id=user_id, raw="")
    if result["status"] == "error":
        code = result.get("code", "ERROR")
        message = result.get("message", "Unknown error")
        if code == "ERROR_NOT_FOUND":
            raise NotFoundError(message)
        elif code == "ERROR_UNSAFE":
            raise UnsafeOperationError(message)
        else:
            raise ValueError(message)
    # Success - no return value for delete operations


def move_item(
    *,
    src_dungeon: str, src_room: str, src_category: str, item: str,
    dst_dungeon: str, dst_room: str, dst_category: str,
    overwrite: bool = False, user_id: Optional[str] = None
) -> dict:
    """
    Move an item from one location to another (copies then deletes source).
    
    If overwrite=False and destination exists, raises ConflictError.
    """
    result = mf.move_item(
        src_dungeon=src_dungeon, src_room=src_room, src_category=src_category, item=item,
        dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
        overwrite=overwrite, user_id=user_id, raw=""
    )
    data = _extract_result(result)
    return {"moved": True, "name": data.get("name", item)}


def copy_item(
    *,
    src_dungeon: str, src_room: str, src_category: str, item: str,
    dst_dungeon: str, dst_room: str, dst_category: str,
    new_name: Optional[str] = None, overwrite: bool = False, user_id: Optional[str] = None
) -> dict:
    """
    Copy an item from one location to another.
    
    If new_name is provided, the copy will have that name.
    Otherwise, uses the original item name.
    """
    result = mf.copy_item(
        src_dungeon=src_dungeon, src_room=src_room, src_category=src_category, item=item,
        dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
        new_name=new_name, overwrite=overwrite, user_id=user_id, raw=""
    )
    data = _extract_result(result)
    item_data = data.get("item", {}) if "item" in data else {}
    return {
        "type": "item",
        "dungeon": dst_dungeon,
        "room": dst_room,
        "category": dst_category,
        "name": item_data.get("name", data.get("name", item)),
        "deleted": False
    }


# --- Generic utilities ---

def stat(*, dungeon: str, room: Optional[str] = None, category: Optional[str] = None, item: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """Get stat info for a dungeon, room, category, or item."""
    result = mf.stat(dungeon=dungeon, room=room, category=category, item=item, user_id=user_id, raw="")
    data = _extract_result(result)
    
    if "dungeon" in data:
        return {"type": "dungeon", "name": data["dungeon"]["name"], "deleted": data["dungeon"].get("deleted", False)}
    elif "room" in data:
        return {"type": "room", "dungeon": data["room"].get("dungeon", dungeon), "name": data["room"]["name"], "deleted": data["room"].get("deleted", False)}
    elif "category" in data:
        return {"type": "category", "dungeon": data["category"].get("dungeon", dungeon), "room": data["category"].get("room", room or ""), "name": data["category"]["name"]}
    elif "item" in data:
        return {"type": "item", "dungeon": data["item"].get("dungeon", dungeon), "room": data["item"].get("room", room or ""), "category": data["item"].get("category", category or ""), "name": data["item"]["name"], "deleted": data["item"].get("deleted", False)}
    raise NotFoundError("Not found")


def list_children(*, dungeon: str, room: Optional[str] = None, category: Optional[str] = None, user_id: Optional[str] = None) -> List[dict]:
    """List children of a dungeon, room, or category."""
    result = mf.list_children(dungeon=dungeon, room=room, category=category, user_id=user_id, raw="")
    data = _extract_result(result)
    
    if "rooms" in data:
        rooms = data["rooms"]
        return [
            {"type": "room", "dungeon": r.get("dungeon", dungeon), "name": r["name"], "deleted": r.get("deleted", False)}
            for r in rooms
        ]
    elif "categories" in data:
        cats = data["categories"]
        return [
            {"type": "category", "dungeon": c.get("dungeon", dungeon), "room": c.get("room", room or ""), "name": c["name"]}
            for c in cats
        ]
    elif "items" in data:
        items = data["items"]
        return [
            {"type": "item", "dungeon": i.get("dungeon", dungeon), "room": i.get("room", room or ""), "category": i.get("category", category or ""), "name": i["name"], "deleted": i.get("deleted", False)}
            for i in items
        ]
    return []


def search(*, query: str, dungeon: Optional[str] = None, tags_any: Optional[List[str]] = None, user_id: Optional[str] = None) -> List[dict]:
    """Search for items matching query and optional tags."""
    result = mf.search(query=query, dungeon=dungeon, tags_any=tags_any, user_id=user_id, raw="")
    data = _extract_result(result)
    matches = data.get("matches", [])
    return [
        {
            "type": "item",
            "dungeon": m.get("dungeon", ""),
            "room": m.get("room", ""),
            "category": m.get("category", ""),
            "name": m["name"],
            "deleted": m.get("deleted", False)
        }
        for m in matches
    ]


def export_dungeon(*, dungeon: str, user_id: Optional[str] = None) -> dict:
    """
    Export a dungeon as a deep copy dictionary (JSON-serializable).
    
    Includes all rooms and items organized hierarchically.
    Useful for backup or sharing between users.
    """
    result = mf.export_dungeon(dungeon=dungeon, user_id=user_id, raw="")
    data = _extract_result(result)
    return data.get("dungeon", {})


def import_dungeon(*, data: dict, strategy: str = "skip", user_id: Optional[str] = None) -> dict:
    """
    Import a dungeon from a dictionary (from export_dungeon).
    
    Strategy options:
    - "skip": Don't import if dungeon name already exists
    - "rename": Import with a new name (adds -2, -3, etc. suffix)
    """
    result = mf.import_dungeon(data=data, strategy=strategy, user_id=user_id, raw="")
    dungeon_data = _extract_result(result)
    dungeon_info = dungeon_data.get("dungeon", {})
    return {
        "type": "dungeon",
        "name": dungeon_info.get("name", ""),
        "deleted": dungeon_info.get("deleted", False),
        "import_action": dungeon_data.get("import_action", "imported"),
        "original_name": dungeon_data.get("original_name", dungeon_info.get("name", ""))
    }


# Maintain backward compatibility: STORE is no longer used but kept for compatibility
STORE: Dict[str, dict] = {}
