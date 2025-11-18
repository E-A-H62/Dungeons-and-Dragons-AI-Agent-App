"""
Database connection and utility functions for MongoDB.

This module provides a centralized database connection and helper functions
for working with MongoDB in the D&D Dungeon Manager application.
"""

import os
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection configuration from environment variables
_MONGO_URI = os.environ["MONGODB_URI"]
_DB_NAME = os.environ.get("DB_NAME", "dnd_dungeon")

# Initialize MongoDB client and database connection (singleton pattern)
_client = MongoClient(_MONGO_URI)
_db = _client[_DB_NAME]


def db():
    """Return the MongoDB database instance."""
    return _db


def utcnow():
    """Get current UTC datetime as a readable string in 24-hour format (YYYY-MM-DD HH:MM:SS)."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def ensure_indexes():
    """
    Create indexes (idempotent). Run once on startup.
    We use partial unique indexes to ensure uniqueness for non-deleted items per user.
    
    Note: On MongoDB Atlas free tier, you may need to create indexes manually
    through the Atlas UI if your database user doesn't have createIndex permission.
    """
    from pymongo.errors import OperationFailure
    
    try:
        # Dungeons: unique name per user when not deleted
        db().dungeons.create_index(
            [("user_id", ASCENDING), ("name", ASCENDING)],
            name="uniq_dungeon_name_per_user_active",
            unique=True,
            partialFilterExpression={"deleted": False}
        )
        db().dungeons.create_index([("user_id", ASCENDING)])

        # Rooms: unique per (user_id, dungeon_name, room_name) when not deleted
        db().rooms.create_index(
            [("user_id", ASCENDING), ("dungeon", ASCENDING), ("name", ASCENDING)],
            name="uniq_room_per_user_dungeon_active",
            unique=True,
            partialFilterExpression={"deleted": False}
        )
        db().rooms.create_index([("user_id", ASCENDING), ("dungeon", ASCENDING)])

        # Items: unique per (user_id, dungeon, room, category, name) when not deleted
        db().items.create_index(
            [("user_id", ASCENDING), ("dungeon", ASCENDING), ("room", ASCENDING), ("category", ASCENDING), ("name", ASCENDING)],
            name="uniq_item_per_user_cat_active",
            unique=True,
            partialFilterExpression={"deleted": False}
        )
        db().items.create_index([("user_id", ASCENDING), ("dungeon", ASCENDING), ("room", ASCENDING), ("category", ASCENDING)])

        # Characters: unique name per user when not deleted
        db().characters.create_index(
            [("user_id", ASCENDING), ("name", ASCENDING)],
            name="uniq_character_name_per_user_active",
            unique=True,
            partialFilterExpression={"deleted": False}
        )
        db().characters.create_index([("user_id", ASCENDING)])
    except OperationFailure as e:
        # If user doesn't have permission to create indexes, that's okay
        # They can create them manually through Atlas UI if needed
        if "createIndex" in str(e):
            print(f"⚠ Warning: Could not create indexes automatically: {e}")
            print("   You may need to create indexes manually through MongoDB Atlas UI.")
            print("   The application will still work, but duplicate checks may be slower.")
            return False
        raise
    return True

