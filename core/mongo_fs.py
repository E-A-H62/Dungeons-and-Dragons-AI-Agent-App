"""
MongoDB-backed file system operations for dungeon management.

This module provides low-level database operations for dungeons, rooms, and items.
All functions return standardized result dictionaries with status, code, and data.
"""

import time
from datetime import datetime
from typing import Optional, List, Dict, Union
from pymongo.errors import DuplicateKeyError
from .db import db, utcnow
from .result_format import make_result, start_timer

# Valid item categories (fixed set)
CATEGORIES = ("puzzles", "traps", "treasures", "enemies")


# ---------- DUNGEONS ----------

def create_dungeon(*, name: str, summary: Optional[str] = None, exists_ok: bool = False, user_id: Optional[str] = None, raw: str = "") -> dict:
    """
    Create a new dungeon in the database.
    
    Args:
        name: Unique dungeon name (per user)
        summary: Optional description
        exists_ok: If True, return existing dungeon instead of error
        user_id: Owner of the dungeon (required)
        raw: Original command string (for tracking)
    
    Returns:
        Standardized result dictionary with dungeon data
    """
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION",
            message="User ID is required.",
            command={"raw": raw, "name": "dungeon.create", "args": {"name": name, "summary": summary, "exists_ok": exists_ok}},
            target={"type": "dungeon", "path": f"/{name}", "name": name},
            started=t0
        )
    coll = db().dungeons
    doc = {
        "name": name,
        "summary": summary,
        "user_id": user_id,
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "deleted": False,
    }
    try:
        coll.insert_one(doc)
        code, msg = "CREATED", "Dungeon created."
    except DuplicateKeyError:
        if not exists_ok:
            return make_result(
                status="error", code="ERROR_CONFLICT",
                message=f"Dungeon '{name}' already exists.",
                command={"raw": raw, "name": "dungeon.create", "args": {"name": name, "summary": summary, "exists_ok": exists_ok}},
                target={"type": "dungeon", "path": f"/{name}", "name": name},
                started=t0
            )
        doc = coll.find_one({"name": name, "user_id": user_id, "deleted": False})
        if not doc:
            return make_result(
                status="error", code="ERROR_CONFLICT",
                message=f"Dungeon '{name}' already exists.",
                command={"raw": raw, "name": "dungeon.create", "args": {"name": name, "summary": summary, "exists_ok": exists_ok}},
                target={"type": "dungeon", "path": f"/{name}", "name": name},
                started=t0
            )
        code, msg = "NOOP", "Dungeon exists; no change."

    return make_result(
        status="ok", code=code, message=msg,
        command={"raw": raw, "name": "dungeon.create", "args": {"name": name, "summary": summary, "exists_ok": exists_ok}},
        target={"type": "dungeon", "path": f"/{name}", "name": name},
        result={"dungeon": {"name": doc["name"], "summary": doc.get("summary"), "deleted": doc["deleted"],
                            "created_at": doc["created_at"].timestamp(),
                            "updated_at": doc["updated_at"].timestamp()}},
        diff={"applied": code == "CREATED", "changes": (
            [{"op": "add", "path": "/", "node_type": "dungeon", "name": name}] if code == "CREATED" else []
        )},
        started=t0
    )


def list_dungeons(*, user_id: Optional[str] = None, raw: str = "") -> dict:
    """List all non-deleted dungeons for a user."""
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "dungeon.list", "args": {}},
            target={"type": "dungeon", "path": "/", "name": ""},
            started=t0
        )
    docs = list(db().dungeons.find({"user_id": user_id, "deleted": False}))
    dungeons = [{"name": d["name"], "summary": d.get("summary"), "deleted": d.get("deleted", False)} for d in docs]
    return make_result(
        status="ok", code="LIST", message=f"{len(dungeons)} dungeons.",
        command={"raw": raw, "name": "dungeon.list", "args": {}},
        target={"type": "dungeon", "path": "/", "name": ""},
        result={"dungeons": dungeons}, started=t0
    )


def rename_dungeon(*, dungeon: str, new_name: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    """
    Rename a dungeon and cascade the change to all related rooms and items.
    
    Note: This updates the dungeon name in rooms and items collections
    since they store dungeon name as a string field.
    """
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "dungeon.rename", "args": {"old_name": dungeon, "new_name": new_name}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    coll = db().dungeons
    old = coll.find_one({"name": dungeon, "user_id": user_id, "deleted": False})
    if not old:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "dungeon.rename", "args": {"old_name": dungeon, "new_name": new_name}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    # Check conflict on new_name (partial unique index also enforces it)
    conflict = coll.find_one({"name": new_name, "user_id": user_id, "deleted": False})
    if conflict:
        return make_result(
            status="error", code="ERROR_CONFLICT", message=f"Dungeon '{new_name}' exists.",
            command={"raw": raw, "name": "dungeon.rename", "args": {"old_name": dungeon, "new_name": new_name}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    coll.update_one({"_id": old["_id"]}, {"$set": {"name": new_name, "updated_at": utcnow()}})
    # Cascade rename in rooms/items (stored as strings)
    db().rooms.update_many({"dungeon": dungeon, "user_id": user_id}, {"$set": {"dungeon": new_name}})
    db().items.update_many({"dungeon": dungeon, "user_id": user_id}, {"$set": {"dungeon": new_name}})
    return make_result(
        status="ok", code="RENAMED", message="Dungeon renamed.",
        command={"raw": raw, "name": "dungeon.rename", "args": {"old_name": dungeon, "new_name": new_name}},
        target={"type": "dungeon", "path": f"/{new_name}", "name": new_name},
        diff={"applied": True, "changes": [
            {"op": "update", "path": "/", "node_type": "dungeon", "name": dungeon, "to": new_name}
        ]},
        result={"dungeon": {"name": new_name, "deleted": False}},
        started=t0
    )


def update_dungeon(*, dungeon: str, patch: dict, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "dungeon.update", "args": {"name": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    coll = db().dungeons
    doc = coll.find_one({
        "name": dungeon,
        "user_id": user_id,
        "deleted": False
    })
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Dungeon '{dungeon}' not found.",
            command={"raw": raw, "name": "dungeon.update", "args": {"name": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    
    update_fields = {"updated_at": utcnow()}
    changes = []
    
    # Handle name change (rename)
    if "name" in patch and patch["name"] != dungeon:
        new_name = patch["name"]
        conflict = coll.find_one({
            "name": new_name,
            "user_id": user_id,
            "deleted": False
        })
        if conflict:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Dungeon '{new_name}' already exists.",
                command={"raw": raw, "name": "dungeon.update", "args": {"name": dungeon}},
                target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
                started=t0
            )
        # Update the name field
        update_fields["name"] = new_name
        changes.append({"op": "update", "path": "/", "node_type": "dungeon", "name": dungeon, "to": new_name})
        # Cascade rename in rooms/items
        db().rooms.update_many({"dungeon": dungeon, "user_id": user_id}, {"$set": {"dungeon": new_name}})
        db().items.update_many({"dungeon": dungeon, "user_id": user_id}, {"$set": {"dungeon": new_name}})
    
    # Handle summary field
    if "summary" in patch:
        update_fields["summary"] = patch["summary"]
        result_name = update_fields.get("name", dungeon)
        changes.append({"op": "update", "path": f"/{result_name}", "field": "summary"})
    
    coll.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    
    # Read updated dungeon
    updated_doc = coll.find_one({"_id": doc["_id"]})
    result_name = updated_doc["name"]
    
    return make_result(
        status="ok", code="UPDATED", message="Dungeon updated.",
        command={"raw": raw, "name": "dungeon.update", "args": {"name": dungeon}},
        target={"type": "dungeon", "path": f"/{result_name}", "name": result_name},
        result={"dungeon": {
            "name": updated_doc["name"],
            "summary": updated_doc.get("summary"),
            "deleted": updated_doc.get("deleted", False)
        }},
        diff={"applied": True, "changes": changes},
        started=t0
    )


def delete_dungeon(*, dungeon: str, token: Optional[str] = None, user_id: Optional[str] = None, raw: str = "") -> dict:
    """
    Permanently delete a dungeon and all its rooms and items (hard delete).
    
    Requires confirmation token to prevent accidental deletion.
    This is a cascading delete - removes dungeon, rooms, and items.
    """
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "dungeon.delete", "args": {"name": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon}, started=t0
        )
    coll = db().dungeons
    doc = coll.find_one({"name": dungeon, "user_id": user_id})
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "dungeon.delete", "args": {"name": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon}, started=t0
        )
    expected = f"DELETE:/{dungeon}"
    if token != expected:
        return make_result(
            status="error", code="ERROR_UNSAFE", message="Confirmation token required.",
            command={"raw": raw, "name": "dungeon.delete", "args": {"name": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            result={"confirm_required": True, "token_hint": expected},
            started=t0
        )
    # Hard delete: remove dungeon, rooms, items
    coll.delete_one({"_id": doc["_id"]})
    db().rooms.delete_many({"dungeon": dungeon, "user_id": user_id})
    db().items.delete_many({"dungeon": dungeon, "user_id": user_id})
    return make_result(
        status="ok", code="DELETED_HARD", message="Dungeon permanently deleted.",
        command={"raw": raw, "name": "dungeon.delete", "args": {"name": dungeon}},
        target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
        result={"deleted": True, "hard": True},
        diff={"applied": True, "changes": [{"op": "remove", "path": "/", "node_type": "dungeon", "name": dungeon}]},
        started=t0
    )


# ---------- ROOMS ----------

def create_room(*, dungeon: str, name: str, summary: Optional[str] = None, exists_ok: bool = False, user_id: Optional[str] = None, raw: str = "") -> dict:
    """Create a new room within a dungeon."""
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "room.create", "args": {"dungeon": dungeon, "name": name, "summary": summary}},
            target={"type": "room", "path": f"/{dungeon}/{name}", "name": name}, started=t0
        )
    if not db().dungeons.find_one({"name": dungeon, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "room.create", "args": {"dungeon": dungeon, "name": name, "summary": summary}},
            target={"type": "room", "path": f"/{dungeon}/{name}", "name": name}, started=t0
        )
    doc = {
        "dungeon": dungeon,
        "name": name,
        "summary": summary,
        "user_id": user_id,
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "deleted": False,
    }
    try:
        db().rooms.insert_one(doc)
        code, msg = "CREATED", "Room created."
    except DuplicateKeyError:
        if not exists_ok:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Room '{name}' exists in '{dungeon}'.",
                command={"raw": raw, "name": "room.create", "args": {"dungeon": dungeon, "name": name}},
                target={"type": "room", "path": f"/{dungeon}/{name}", "name": name}, started=t0
            )
        code, msg = "NOOP", "Room exists; no change."
    return make_result(
        status="ok", code=code, message=msg,
        command={"raw": raw, "name": "room.create", "args": {"dungeon": dungeon, "name": name, "summary": summary}},
        target={"type": "room", "path": f"/{dungeon}/{name}", "name": name},
        result={"room": {"name": name, "summary": summary, "deleted": False}},
        diff={"applied": code == "CREATED", "changes": (
            [{"op": "add", "path": f"/{dungeon}", "node_type": "room", "name": name}] if code == "CREATED" else []
        )},
        started=t0
    )


def list_rooms(*, dungeon: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "room.list", "args": {"dungeon": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    if not db().dungeons.find_one({"name": dungeon, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "room.list", "args": {"dungeon": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    docs = list(db().rooms.find({"dungeon": dungeon, "user_id": user_id, "deleted": False}))
    rooms = [{"name": d["name"], "dungeon": d["dungeon"], "summary": d.get("summary"), "deleted": d.get("deleted", False)} for d in docs]
    return make_result(
        status="ok", code="LIST", message=f"{len(rooms)} rooms.",
        command={"raw": raw, "name": "room.list", "args": {"dungeon": dungeon}},
        target={"type": "room", "path": f"/{dungeon}", "name": ""},
        result={"rooms": rooms}, started=t0
    )


def rename_room(*, dungeon: str, room: str, new_name: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "room.rename", "args": {"dungeon": dungeon, "old_name": room, "new_name": new_name}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    if not db().dungeons.find_one({"name": dungeon, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "room.rename", "args": {"dungeon": dungeon, "old_name": room, "new_name": new_name}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    coll = db().rooms
    old = coll.find_one({"dungeon": dungeon, "name": room, "user_id": user_id, "deleted": False})
    if not old:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No room '{room}' in '{dungeon}'.",
            command={"raw": raw, "name": "room.rename", "args": {"dungeon": dungeon, "old_name": room, "new_name": new_name}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    conflict = coll.find_one({"dungeon": dungeon, "name": new_name, "user_id": user_id, "deleted": False})
    if conflict:
        return make_result(
            status="error", code="ERROR_CONFLICT", message=f"Room '{new_name}' exists in '{dungeon}'.",
            command={"raw": raw, "name": "room.rename", "args": {"dungeon": dungeon, "old_name": room, "new_name": new_name}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    coll.update_one({"_id": old["_id"]}, {"$set": {"name": new_name, "updated_at": utcnow()}})
    # Cascade rename in items
    db().items.update_many({"dungeon": dungeon, "room": room, "user_id": user_id}, {"$set": {"room": new_name}})
    return make_result(
        status="ok", code="RENAMED", message="Room renamed.",
        command={"raw": raw, "name": "room.rename", "args": {"dungeon": dungeon, "old_name": room, "new_name": new_name}},
        target={"type": "room", "path": f"/{dungeon}/{new_name}", "name": new_name},
        diff={"applied": True, "changes": [
            {"op": "update", "path": f"/{dungeon}", "node_type": "room", "name": room, "to": new_name}
        ]},
        result={"room": {"name": new_name, "dungeon": dungeon, "deleted": False}},
        started=t0
    )


def update_room(*, dungeon: str, room: str, patch: dict, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "room.update", "args": {"dungeon": dungeon, "name": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    coll = db().rooms
    doc = coll.find_one({
        "dungeon": dungeon,
        "name": room,
        "user_id": user_id,
        "deleted": False
    })
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Room '{room}' not found.",
            command={"raw": raw, "name": "room.update", "args": {"dungeon": dungeon, "name": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    
    update_fields = {"updated_at": utcnow()}
    changes = []
    
    # Handle name change (rename)
    if "name" in patch and patch["name"] != room:
        new_name = patch["name"]
        conflict = coll.find_one({
            "dungeon": dungeon,
            "name": new_name,
            "user_id": user_id,
            "deleted": False
        })
        if conflict:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Room '{new_name}' already exists.",
                command={"raw": raw, "name": "room.update", "args": {"dungeon": dungeon, "name": room}},
                target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
                started=t0
            )
        # Update the name field
        update_fields["name"] = new_name
        changes.append({"op": "update", "path": f"/{dungeon}", "node_type": "room", "name": room, "to": new_name})
        # Cascade rename in items
        db().items.update_many({"dungeon": dungeon, "room": room, "user_id": user_id}, {"$set": {"room": new_name}})
    
    # Handle summary field
    if "summary" in patch:
        update_fields["summary"] = patch["summary"]
        result_name = update_fields.get("name", room)
        changes.append({"op": "update", "path": f"/{dungeon}/{result_name}", "field": "summary"})
    
    coll.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    
    # Read updated room
    updated_doc = coll.find_one({"_id": doc["_id"]})
    result_name = updated_doc["name"]
    
    return make_result(
        status="ok", code="UPDATED", message="Room updated.",
        command={"raw": raw, "name": "room.update", "args": {"dungeon": dungeon, "name": room}},
        target={"type": "room", "path": f"/{dungeon}/{result_name}", "name": result_name},
        result={"room": {
            "name": updated_doc["name"],
            "summary": updated_doc.get("summary"),
            "deleted": updated_doc.get("deleted", False)
        }},
        diff={"applied": True, "changes": changes},
        started=t0
    )


def delete_room(*, dungeon: str, room: str, token: Optional[str] = None, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "room.delete", "args": {"dungeon": dungeon, "name": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    coll = db().rooms
    doc = coll.find_one({"dungeon": dungeon, "name": room, "user_id": user_id})
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Room '{room}' not found in '{dungeon}'.",
            command={"raw": raw, "name": "room.delete", "args": {"dungeon": dungeon, "name": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    expected = f"DELETE:/{dungeon}/{room}"
    if token != expected:
        return make_result(
            status="error", code="ERROR_UNSAFE", message="Confirmation token required.",
            command={"raw": raw, "name": "room.delete", "args": {"dungeon": dungeon, "name": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            result={"confirm_required": True, "token_hint": expected},
            started=t0
        )
    coll.delete_one({"_id": doc["_id"]})
    db().items.delete_many({"dungeon": dungeon, "room": room, "user_id": user_id})
    return make_result(
        status="ok", code="DELETED_HARD", message="Room permanently deleted.",
        command={"raw": raw, "name": "room.delete", "args": {"dungeon": dungeon, "name": room}},
        target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
        result={"deleted": True, "hard": True},
        diff={"applied": True, "changes": [{"op": "remove", "path": f"/{dungeon}", "node_type": "room", "name": room}]},
        started=t0
    )


# ---------- ITEMS ----------

def create_item(
    *, dungeon: str, room: str, category: str, payload: dict, exists_ok: bool = False, user_id: Optional[str] = None, raw: str = ""
) -> dict:
    """
    Create a new item (puzzle, trap, treasure, or enemy) in a room.
    
    Args:
        payload: Dictionary containing item data (name, summary, notes_md, tags, metadata)
        category: Must be one of: puzzles, traps, treasures, enemies
    """
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "item.create", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category}, started=t0
        )
    if category not in CATEGORIES:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="Invalid category.",
            command={"raw": raw, "name": "item.create", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category}, started=t0
        )
    if not db().rooms.find_one({"dungeon": dungeon, "name": room, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Room '{room}' not found in '{dungeon}'.",
            command={"raw": raw, "name": "item.create", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room}, started=t0
        )
    name = payload.get("name")
    if not name:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="Item name required.",
            command={"raw": raw, "name": "item.create", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/", "name": ""}, started=t0
        )
    doc = {
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "name": name,
        "user_id": user_id,
        "summary": payload.get("summary"),
        "notes_md": payload.get("notes_md"),
        "tags": list(payload.get("tags", [])),
        "metadata": dict(payload.get("metadata", {})),
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "deleted": False,
    }
    coll = db().items
    try:
        coll.insert_one(doc)
        code, msg, applied = "CREATED", "Item created.", True
    except DuplicateKeyError:
        if not exists_ok:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Item '{name}' exists.",
                command={"raw": raw, "name": "item.create", "args": {"dungeon": dungeon, "room": room, "category": category, "name": name}},
                target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{name}", "name": name}, started=t0
            )
        # upsert-like merge (basic)
        coll.update_one(
            {"dungeon": dungeon, "room": room, "category": category, "name": name, "user_id": user_id, "deleted": False},
            {"$set": {k: v for k, v in doc.items() if k not in ("created_at", "_id")}, "$setOnInsert": {"created_at": doc["created_at"]}}
        )
        code, msg, applied = "NOOP", "Item existed; metadata updated.", False
    return make_result(
        status="ok", code=code, message=msg,
        command={"raw": raw, "name": "item.create", "args": {"dungeon": dungeon, "room": room, "category": category, "name": name, "exists_ok": exists_ok}},
        target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{name}", "name": name},
        result={"item": {
            "name": name,
            "summary": doc.get("summary"),
            "notes_md": doc.get("notes_md"),
            "tags": doc.get("tags"),
            "metadata": doc.get("metadata"),
            "deleted": False
        }},
        diff={"applied": applied, "changes": (
            [{"op": "add", "path": f"/{dungeon}/{room}/{category}", "node_type": "item", "name": name}] if applied else []
        )},
        started=t0
    )


def read_item(*, dungeon: str, room: str, category: str, item: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "item.read", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    doc = db().items.find_one({
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "name": item,
        "user_id": user_id,
        "deleted": False
    })
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Item '{item}' not found.",
            command={"raw": raw, "name": "item.read", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    return make_result(
        status="ok", code="READ", message="Item read.",
        command={"raw": raw, "name": "item.read", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
        target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
        result={"item": {
            "name": doc["name"],
            "summary": doc.get("summary"),
            "notes_md": doc.get("notes_md"),
            "tags": doc.get("tags", []),
            "metadata": doc.get("metadata", {}),
            "created_at": doc["created_at"].timestamp(),
            "updated_at": doc["updated_at"].timestamp()
        }},
        started=t0
    )


def update_item(*, dungeon: str, room: str, category: str, item: str, patch: dict, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "item.update", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    coll = db().items
    doc = coll.find_one({
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "name": item,
        "user_id": user_id,
        "deleted": False
    })
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Item '{item}' not found.",
            command={"raw": raw, "name": "item.update", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    
    update_fields = {"updated_at": utcnow()}
    changes = []
    
    # Handle name change (rename)
    if "name" in patch and patch["name"] != item:
        new_name = patch["name"]
        conflict = coll.find_one({
            "dungeon": dungeon,
            "room": room,
            "category": category,
            "name": new_name,
            "user_id": user_id,
            "deleted": False
        })
        if conflict:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Item '{new_name}' already exists.",
                command={"raw": raw, "name": "item.update", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
                target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
                started=t0
            )
        # Update the name field
        update_fields["name"] = new_name
        changes.append({"op": "update", "path": f"/{dungeon}/{room}/{category}", "node_type": "item", "name": item, "to": new_name})
    
    # Handle other fields
    for field in ("summary", "notes_md"):
        if field in patch:
            update_fields[field] = patch[field]
            changes.append({"op": "update", "path": f"/{dungeon}/{room}/{category}/{item}", "field": field})
    
    if "tags" in patch:
        update_fields["tags"] = list(patch["tags"])
        changes.append({"op": "update", "path": f"/{dungeon}/{room}/{category}/{item}", "field": "tags"})
    
    if "metadata" in patch:
        if not isinstance(patch["metadata"], dict):
            return make_result(
                status="error", code="ERROR_VALIDATION", message="metadata must be dict",
                command={"raw": raw, "name": "item.update", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
                target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
                started=t0
            )
        # Merge metadata
        current_metadata = doc.get("metadata", {})
        current_metadata.update(patch["metadata"])
        update_fields["metadata"] = current_metadata
        changes.append({"op": "update", "path": f"/{dungeon}/{room}/{category}/{item}", "field": "metadata"})
    
    coll.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    
    # Read updated item
    updated_doc = coll.find_one({"_id": doc["_id"]})
    result_name = updated_doc["name"]
    
    return make_result(
        status="ok", code="UPDATED", message="Item updated.",
        command={"raw": raw, "name": "item.update", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
        target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{result_name}", "name": result_name},
        result={"item": {
            "name": updated_doc["name"],
            "summary": updated_doc.get("summary"),
            "notes_md": updated_doc.get("notes_md"),
            "tags": updated_doc.get("tags", []),
            "metadata": updated_doc.get("metadata", {})
        }},
        diff={"applied": True, "changes": changes},
        started=t0
    )


def rename_item(*, dungeon: str, room: str, category: str, item: str, new_name: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    return update_item(dungeon=dungeon, room=room, category=category, item=item, patch={"name": new_name}, user_id=user_id, raw=raw)


def delete_item(*, dungeon: str, room: str, category: str, item: str, token: Optional[str] = None, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "item.delete", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    coll = db().items
    doc = coll.find_one({
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "name": item,
        "user_id": user_id
    })
    if not doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Item '{item}' not found.",
            command={"raw": raw, "name": "item.delete", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    expected = f"DELETE:/{dungeon}/{room}/{category}/{item}"
    if token != expected:
        return make_result(
            status="error", code="ERROR_UNSAFE", message="Confirmation token required.",
            command={"raw": raw, "name": "item.delete", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            result={"confirm_required": True, "token_hint": expected},
            started=t0
        )
    coll.delete_one({"_id": doc["_id"]})
    return make_result(
        status="ok", code="DELETED_HARD", message="Item permanently deleted.",
        command={"raw": raw, "name": "item.delete", "args": {"dungeon": dungeon, "room": room, "category": category, "name": item}},
        target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
        result={"deleted": True, "hard": True},
        diff={"applied": True, "changes": [{"op": "remove", "path": f"/{dungeon}/{room}/{category}", "node_type": "item", "name": item}]},
        started=t0
    )


def move_item(
    *, src_dungeon: str, src_room: str, src_category: str, item: str,
    dst_dungeon: str, dst_room: str, dst_category: str,
    overwrite: bool = False, user_id: Optional[str] = None, raw: str = ""
) -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "item.move", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category}},
            target={"type": "item", "path": f"/{src_dungeon}/{src_room}/{src_category}/{item}", "name": item},
            started=t0
        )
    # Read source item
    src_result = read_item(dungeon=src_dungeon, room=src_room, category=src_category, item=item, user_id=user_id, raw="")
    if src_result["status"] != "ok":
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Source item '{item}' not found.",
            command={"raw": raw, "name": "item.move", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category}},
            target={"type": "item", "path": f"/{src_dungeon}/{src_room}/{src_category}/{item}", "name": item},
            started=t0
        )
    
    src_data = src_result["result"]["item"]
    name = src_data["name"]
    
    # Check destination (if not overwrite)
    if not overwrite:
        conflict = db().items.find_one({
            "dungeon": dst_dungeon,
            "room": dst_room,
            "category": dst_category,
            "name": name,
            "user_id": user_id,
            "deleted": False
        })
        if conflict:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Destination item '{name}' exists.",
                command={"raw": raw, "name": "item.move", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category}},
                target={"type": "item", "path": f"/{dst_dungeon}/{dst_room}/{dst_category}/{name}", "name": name},
                started=t0
            )
    
    # Copy to destination
    copy_result = copy_item(
        src_dungeon=src_dungeon, src_room=src_room, src_category=src_category, item=item,
        dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
        user_id=user_id,
        new_name=None, overwrite=overwrite, raw=""
    )
    if copy_result["status"] != "ok":
        return copy_result
    
    # Delete source (hard delete)
    delete_result = delete_item(dungeon=src_dungeon, room=src_room, category=src_category, item=item, token=f"DELETE:/{src_dungeon}/{src_room}/{src_category}/{item}", user_id=user_id, raw="")
    
    return make_result(
        status="ok", code="MOVED", message="Item moved.",
        command={"raw": raw, "name": "item.move", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "overwrite": overwrite}},
        target={"type": "item", "path": f"/{dst_dungeon}/{dst_room}/{dst_category}/{name}", "name": name},
        result={"moved": True, "name": name},
        diff={"applied": True, "changes": [
            {"op": "remove", "path": f"/{src_dungeon}/{src_room}/{src_category}", "node_type": "item", "name": item},
            {"op": "add", "path": f"/{dst_dungeon}/{dst_room}/{dst_category}", "node_type": "item", "name": name}
        ]},
        started=t0
    )


def copy_item(
    *, src_dungeon: str, src_room: str, src_category: str, item: str,
    dst_dungeon: str, dst_room: str, dst_category: str,
    new_name: Optional[str] = None, overwrite: bool = False, user_id: Optional[str] = None, raw: str = ""
) -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "item.copy", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "new_name": new_name}},
            target={"type": "item", "path": f"/{src_dungeon}/{src_room}/{src_category}/{item}", "name": item},
            started=t0
        )
    # Read source item
    src_result = read_item(dungeon=src_dungeon, room=src_room, category=src_category, item=item, user_id=user_id, raw="")
    if src_result["status"] != "ok":
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Source item '{item}' not found.",
            command={"raw": raw, "name": "item.copy", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "new_name": new_name}},
            target={"type": "item", "path": f"/{src_dungeon}/{src_room}/{src_category}/{item}", "name": item},
            started=t0
        )
    
    src_data = src_result["result"]["item"]
    name = new_name or src_data["name"]
    
    # Check destination (if not overwrite)
    if not overwrite:
        conflict = db().items.find_one({
            "dungeon": dst_dungeon,
            "room": dst_room,
            "category": dst_category,
            "name": name,
            "user_id": user_id,
            "deleted": False
        })
        if conflict:
            return make_result(
                status="error", code="ERROR_CONFLICT", message=f"Destination item '{name}' exists.",
                command={"raw": raw, "name": "item.copy", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "new_name": new_name}},
                target={"type": "item", "path": f"/{dst_dungeon}/{dst_room}/{dst_category}/{name}", "name": name},
                started=t0
            )
    
    # Create at destination
    payload = {
        "name": name,
        "summary": src_data.get("summary"),
        "notes_md": src_data.get("notes_md"),
        "tags": src_data.get("tags", []),
        "metadata": src_data.get("metadata", {})
    }
    create_result = create_item(
        dungeon=dst_dungeon, room=dst_room, category=dst_category,
        payload=payload, exists_ok=overwrite, user_id=user_id, raw=""
    )
    
    return make_result(
        status="ok", code="COPIED", message="Item copied.",
        command={"raw": raw, "name": "item.copy", "args": {"src_dungeon": src_dungeon, "src_room": src_room, "src_category": src_category, "item": item, "dst_dungeon": dst_dungeon, "dst_room": dst_room, "dst_category": dst_category, "new_name": new_name, "overwrite": overwrite}},
        target={"type": "item", "path": f"/{dst_dungeon}/{dst_room}/{dst_category}/{name}", "name": name},
        result={"copied": True, "name": name},
        diff={"applied": True, "changes": [
            {"op": "add", "path": f"/{dst_dungeon}/{dst_room}/{dst_category}", "node_type": "item", "name": name}
        ]},
        started=t0
    )


# ---------- CATEGORIES ----------

def ensure_category(*, dungeon: str, room: str, category: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if category not in CATEGORIES:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="Invalid category.",
            command={"raw": raw, "name": "category.ensure", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
            started=t0
        )
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "category.ensure", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
            started=t0
        )
    if not db().rooms.find_one({"dungeon": dungeon, "name": room, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Room '{room}' not found in '{dungeon}'.",
            command={"raw": raw, "name": "category.ensure", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    # Categories are implicit in MongoDB (no separate collection)
    return make_result(
        status="ok", code="NOOP", message="Category ensured.",
        command={"raw": raw, "name": "category.ensure", "args": {"dungeon": dungeon, "room": room, "category": category}},
        target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
        result={"category": {"name": category, "dungeon": dungeon, "room": room}},
        started=t0
    )


def list_category_items(*, dungeon: str, room: str, category: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "category.list", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
            started=t0
        )
    if category not in CATEGORIES:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="Invalid category.",
            command={"raw": raw, "name": "category.list", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
            started=t0
        )
    if not db().rooms.find_one({"dungeon": dungeon, "name": room, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"Room '{room}' not found in '{dungeon}'.",
            command={"raw": raw, "name": "category.list", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    docs = list(db().items.find({
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "user_id": user_id,
        "deleted": False
    }))
    items = [{"name": d["name"], "dungeon": d["dungeon"], "room": d["room"], "category": d["category"], "deleted": False} for d in docs]
    return make_result(
        status="ok", code="LIST", message=f"{len(items)} items.",
        command={"raw": raw, "name": "category.list", "args": {"dungeon": dungeon, "room": room, "category": category}},
        target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
        result={"items": items},
        started=t0
    )


# ---------- UTILITIES ----------

def search(*, query: str, dungeon: Optional[str] = None, tags_any: Optional[List[str]] = None, user_id: Optional[str] = None, raw: str = "") -> dict:
    """
    Search for items by text query and optional tag filters.
    
    Searches item names and summaries (case-insensitive substring match).
    If tags_any is provided, only returns items that have at least one matching tag.
    """
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "search", "args": {"query": query, "dungeon": dungeon}},
            target={"type": "item", "path": "/", "name": ""},
            started=t0
        )
    q = query.lower()
    results = []
    
    # Build query filter
    filter_query = {"deleted": False, "user_id": user_id}
    if dungeon:
        filter_query["dungeon"] = dungeon
    
    # Search items
    all_items = list(db().items.find(filter_query))
    
    for item in all_items:
        # Text search
        name_match = q in item["name"].lower()
        summary_match = item.get("summary") and q in item["summary"].lower()
        
        if name_match or summary_match:
            # Tag filter
            if tags_any:
                item_tags = item.get("tags", [])
                if not (set(tags_any) & set(item_tags)):
                    continue
            
            results.append({
                "name": item["name"],
                "dungeon": item["dungeon"],
                "room": item["room"],
                "category": item["category"],
                "deleted": False
            })
    
    return make_result(
        status="ok", code="LIST", message=f"Found {len(results)} matches for '{query}'.",
        command={"raw": raw, "name": "search", "args": {"query": query, "dungeon": dungeon, "tags": tags_any}},
        target={"type": "item", "path": "/", "name": ""},
        result={"query": query, "matches": results},
        started=t0
    )


def stat(*, dungeon: str, room: Optional[str] = None, category: Optional[str] = None, item: Optional[str] = None, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room, "category": category, "item": item}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    # Check dungeon exists
    dungeon_doc = db().dungeons.find_one({"name": dungeon, "user_id": user_id, "deleted": False})
    if not dungeon_doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room, "category": category, "item": item}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    
    if room is None:
        return make_result(
            status="ok", code="STAT", message="Dungeon stat.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            result={"dungeon": {"name": dungeon_doc["name"], "deleted": dungeon_doc.get("deleted", False)}},
            started=t0
        )
    
    # Check room exists
    room_doc = db().rooms.find_one({"dungeon": dungeon, "name": room, "user_id": user_id, "deleted": False})
    if not room_doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No room '{room}'.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            started=t0
        )
    
    if category is None:
        return make_result(
            status="ok", code="STAT", message="Room stat.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            result={"room": {"name": room_doc["name"], "dungeon": room_doc["dungeon"], "deleted": room_doc.get("deleted", False)}},
            started=t0
        )
    
    if item is None:
        return make_result(
            status="ok", code="STAT", message="Category stat.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "category", "path": f"/{dungeon}/{room}/{category}", "name": category},
            result={"category": {"name": category, "dungeon": dungeon, "room": room}},
            started=t0
        )
    
    # Check item exists
    item_doc = db().items.find_one({
        "dungeon": dungeon,
        "room": room,
        "category": category,
        "name": item,
        "user_id": user_id,
        "deleted": False
    })
    if not item_doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No item '{item}'.",
            command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room, "category": category, "item": item}},
            target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
            started=t0
        )
    
    return make_result(
        status="ok", code="STAT", message="Item stat.",
        command={"raw": raw, "name": "stat", "args": {"dungeon": dungeon, "room": room, "category": category, "item": item}},
        target={"type": "item", "path": f"/{dungeon}/{room}/{category}/{item}", "name": item},
        result={"item": {"name": item_doc["name"], "dungeon": item_doc["dungeon"], "room": item_doc["room"], "category": item_doc["category"], "deleted": False}},
        started=t0
    )


def list_children(*, dungeon: str, room: Optional[str] = None, category: Optional[str] = None, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "list", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    if not db().dungeons.find_one({"name": dungeon, "user_id": user_id, "deleted": False}):
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "list", "args": {"dungeon": dungeon, "room": room, "category": category}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    
    if room is None:
        # List rooms
        result = list_rooms(dungeon=dungeon, user_id=user_id, raw=raw)
        result["command"]["name"] = "list"
        return result
    
    if category is None:
        # List categories
        return make_result(
            status="ok", code="LIST", message="Categories listed.",
            command={"raw": raw, "name": "list", "args": {"dungeon": dungeon, "room": room}},
            target={"type": "room", "path": f"/{dungeon}/{room}", "name": room},
            result={"categories": [{"name": c, "dungeon": dungeon, "room": room} for c in CATEGORIES]},
            started=t0
        )
    
    # List items in category
    result = list_category_items(dungeon=dungeon, room=room, category=category, user_id=user_id, raw=raw)
    result["command"]["name"] = "list"
    return result


def export_dungeon(*, dungeon: str, user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "export", "args": {"dungeon": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    dungeon_doc = db().dungeons.find_one({"name": dungeon, "user_id": user_id, "deleted": False})
    if not dungeon_doc:
        return make_result(
            status="error", code="ERROR_NOT_FOUND", message=f"No dungeon '{dungeon}'.",
            command={"raw": raw, "name": "export", "args": {"dungeon": dungeon}},
            target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
            started=t0
        )
    
    # Get all rooms
    room_docs = list(db().rooms.find({"dungeon": dungeon, "user_id": user_id, "deleted": False}))
    
    # Get all items
    item_docs = list(db().items.find({"dungeon": dungeon, "user_id": user_id, "deleted": False}))
    
    # Build export structure
    export_data = {
        "name": dungeon_doc["name"],
        "created_at": dungeon_doc["created_at"].timestamp(),
        "updated_at": dungeon_doc["updated_at"].timestamp(),
        "deleted": dungeon_doc.get("deleted", False),
        "rooms": {}
    }
    
    for room_doc in room_docs:
        room_name = room_doc["name"]
        export_data["rooms"][room_name] = {
            "name": room_doc["name"],
            "summary": room_doc.get("summary"),
            "created_at": room_doc["created_at"].timestamp(),
            "updated_at": room_doc["updated_at"].timestamp(),
            "deleted": room_doc.get("deleted", False),
            "categories": {
                "puzzles": {},
                "traps": {},
                "treasures": {},
                "enemies": {}
            }
        }
    
    # Organize items by room and category
    for item_doc in item_docs:
        room_name = item_doc["room"]
        category = item_doc["category"]
        item_name = item_doc["name"]
        
        if room_name not in export_data["rooms"]:
            continue
        
        export_data["rooms"][room_name]["categories"][category][item_name] = {
            "name": item_doc["name"],
            "summary": item_doc.get("summary"),
            "notes_md": item_doc.get("notes_md"),
            "tags": item_doc.get("tags", []),
            "metadata": item_doc.get("metadata", {}),
            "created_at": item_doc["created_at"].timestamp(),
            "updated_at": item_doc["updated_at"].timestamp(),
            "deleted": item_doc.get("deleted", False)
        }
    
    return make_result(
        status="ok", code="EXPORTED", message="Dungeon exported.",
        command={"raw": raw, "name": "export", "args": {"dungeon": dungeon}},
        target={"type": "dungeon", "path": f"/{dungeon}", "name": dungeon},
        result={"dungeon": export_data},
        started=t0
    )


def import_dungeon(*, data: dict, strategy: str = "skip", user_id: Optional[str] = None, raw: str = "") -> dict:
    t0 = start_timer()
    if not user_id:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="User ID is required.",
            command={"raw": raw, "name": "import", "args": {"strategy": strategy}},
            target={"type": "dungeon", "path": "/", "name": ""},
            started=t0
        )
    name = data.get("name")
    if not name:
        return make_result(
            status="error", code="ERROR_VALIDATION", message="Dungeon data missing 'name'.",
            command={"raw": raw, "name": "import", "args": {"strategy": strategy}},
            target={"type": "dungeon", "path": "/", "name": ""},
            started=t0
        )
    
    coll_dungeons = db().dungeons
    existing = coll_dungeons.find_one({"name": name, "user_id": user_id, "deleted": False})
    
    if existing:
        if strategy == "overwrite":
            # Hard delete existing and recreate
            coll_dungeons.delete_one({"_id": existing["_id"]})
            db().rooms.delete_many({"dungeon": name, "user_id": user_id})
            db().items.delete_many({"dungeon": name, "user_id": user_id})
        elif strategy == "rename":
            i = 2
            new = f"{name}-{i}"
            while coll_dungeons.find_one({"name": new, "user_id": user_id, "deleted": False}):
                i += 1
                new = f"{name}-{i}"
            name = new
            data["name"] = new
        else:  # skip
            return make_result(
                status="ok", code="NOOP", message="Dungeon exists; skipped.",
                command={"raw": raw, "name": "import", "args": {"strategy": strategy}},
                target={"type": "dungeon", "path": f"/{name}", "name": name},
                result={"dungeon": {"name": name, "deleted": False}},
                started=t0
            )
    
    # Import dungeon
    dungeon_doc = {
        "name": name,
        "user_id": user_id,
        "created_at": datetime.fromtimestamp(data.get("created_at", time.time())) if isinstance(data.get("created_at"), (int, float)) else utcnow(),
        "updated_at": utcnow(),
        "deleted": data.get("deleted", False)
    }
    coll_dungeons.insert_one(dungeon_doc)
    
    # Import rooms
    rooms_data = data.get("rooms", {})
    for room_name, room_data in rooms_data.items():
        room_doc = {
            "dungeon": name,
            "name": room_name,
            "user_id": user_id,
            "summary": room_data.get("summary"),
            "created_at": datetime.fromtimestamp(room_data.get("created_at", time.time())) if isinstance(room_data.get("created_at"), (int, float)) else utcnow(),
            "updated_at": utcnow(),
            "deleted": room_data.get("deleted", False)
        }
        db().rooms.insert_one(room_doc)
        
        # Import items
        categories_data = room_data.get("categories", {})
        for category, items_data in categories_data.items():
            for item_name, item_data in items_data.items():
                item_doc = {
                    "dungeon": name,
                    "room": room_name,
                    "category": category,
                    "name": item_name,
                    "user_id": user_id,
                    "summary": item_data.get("summary"),
                    "notes_md": item_data.get("notes_md"),
                    "tags": list(item_data.get("tags", [])),
                    "metadata": dict(item_data.get("metadata", {})),
                    "created_at": datetime.fromtimestamp(item_data.get("created_at", time.time())) if isinstance(item_data.get("created_at"), (int, float)) else utcnow(),
                    "updated_at": utcnow(),
                    "deleted": item_data.get("deleted", False)
                }
                db().items.insert_one(item_doc)
    
    return make_result(
        status="ok", code="IMPORTED", message="Dungeon imported.",
        command={"raw": raw, "name": "import", "args": {"strategy": strategy}},
        target={"type": "dungeon", "path": f"/{name}", "name": name},
        result={"dungeon": {"name": name, "deleted": False}},
        diff={"applied": True, "changes": [{"op": "add", "path": "/", "node_type": "dungeon", "name": name}]},
        started=t0
    )

