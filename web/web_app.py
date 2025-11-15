"""
D&D Dungeon Manager - Web Application

A Flask-based web interface for managing dungeons, rooms, and items
with a D&D-themed graphical interface.
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from core.db import ensure_indexes, db, utcnow
from web.auth import create_user, verify_user, get_current_user_id, require_auth, ensure_users_index
from dungeon import dungeon_manager as dm
from character.dnd_character_agent import create_agent, character_data, _generate_character_sheet
from langchain_core.messages import HumanMessage, AIMessage
from bson import ObjectId
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app, supports_credentials=True)

# Ensure MongoDB indexes on startup
def setup_indexes():
    """
    Initialize MongoDB indexes when the application starts.
    
    Creates indexes for dungeons, rooms, items, characters, and users
    to ensure uniqueness constraints and improve query performance.
    """
    try:
        ensure_indexes()
        ensure_users_index()
        print("✓ MongoDB indexes ensured.")
    except Exception as e:
        print(f"⚠ Warning: Could not ensure MongoDB indexes: {e}")

# Setup indexes when module is imported (runs on server startup)
setup_indexes()


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password are required"}), 400
        
        result = create_user(username, password)
        if result["status"] == "error":
            return jsonify(result), 400
        
        # Auto-login after registration
        session["user_id"] = result["user_id"]
        session["username"] = username
        return jsonify({"status": "ok", "user_id": result["user_id"], "username": username})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login a user."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password are required"}), 400
        
        result = verify_user(username, password)
        if result["status"] == "error":
            return jsonify(result), 401
        
        session["user_id"] = result["user_id"]
        session["username"] = result["username"]
        return jsonify({"status": "ok", "user_id": result["user_id"], "username": result["username"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout the current user."""
    session.clear()
    return jsonify({"status": "ok", "message": "Logged out"})


@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Check if user is authenticated."""
    user_id = get_current_user_id()
    if user_id:
        from auth import get_current_username
        return jsonify({
            "status": "ok",
            "authenticated": True,
            "user_id": user_id,
            "username": get_current_username()
        })
    return jsonify({"status": "ok", "authenticated": False})


# ============================================================================
# API Routes
# ============================================================================

@app.route('/')
def index():
    """Render the main page."""
    # Check if user is authenticated
    user_id = get_current_user_id()
    if not user_id:
        # Redirect to login page if not authenticated
        return render_template('login.html')
    return render_template('index.html')


@app.route('/login')
def login_page():
    """Render the login page."""
    # If already authenticated, redirect to main page
    user_id = get_current_user_id()
    if user_id:
        return render_template('index.html')
    return render_template('login.html')


# Dungeon operations
@app.route('/api/dungeons', methods=['GET'])
@require_auth
def list_dungeons():
    """List all dungeons."""
    try:
        user_id = get_current_user_id()
        dungeons = dm.list_dungeons(user_id=user_id)
        return jsonify({"status": "ok", "dungeons": dungeons})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons', methods=['POST'])
@require_auth
def create_dungeon():
    """Create a new dungeon."""
    try:
        user_id = get_current_user_id()
        data = request.json
        name = data.get('name')
        summary = data.get('summary')
        exists_ok = data.get('exists_ok', False)
        
        if not name:
            return jsonify({"status": "error", "message": "Dungeon name is required"}), 400
        
        result = dm.create_dungeon(name=name, summary=summary, exists_ok=exists_ok, user_id=user_id)
        return jsonify({"status": "ok", "dungeon": result})
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rename', methods=['POST'])
@require_auth
def rename_dungeon(dungeon):
    """Rename a dungeon."""
    try:
        user_id = get_current_user_id()
        data = request.json
        new_name = data.get('new_name')
        
        if not new_name:
            return jsonify({"status": "error", "message": "New name is required"}), 400
        
        result = dm.rename_dungeon(dungeon=dungeon, new_name=new_name, user_id=user_id)
        return jsonify({"status": "ok", "dungeon": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>', methods=['PATCH'])
@require_auth
def update_dungeon(dungeon):
    """Update a dungeon."""
    try:
        user_id = get_current_user_id()
        data = request.json
        patch = data.get('patch', {})
        
        if not patch:
            return jsonify({"status": "error", "message": "Patch data is required"}), 400
        
        result = dm.update_dungeon(dungeon=dungeon, patch=patch, user_id=user_id)
        return jsonify({"status": "ok", "dungeon": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>', methods=['DELETE'])
@require_auth
def delete_dungeon(dungeon):
    """Delete a dungeon."""
    try:
        user_id = get_current_user_id()
        confirm_token = request.args.get('token')
        
        dm.delete_dungeon(dungeon=dungeon, confirm_token=confirm_token, user_id=user_id)
        return jsonify({"status": "ok", "message": "Dungeon deleted"})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.UnsafeOperationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Room operations
@app.route('/api/dungeons/<dungeon>/rooms', methods=['GET'])
@require_auth
def list_rooms(dungeon):
    """List all rooms in a dungeon."""
    try:
        user_id = get_current_user_id()
        rooms = dm.list_rooms(dungeon=dungeon, user_id=user_id)
        return jsonify({"status": "ok", "rooms": rooms})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms', methods=['POST'])
@require_auth
def create_room(dungeon):
    """Create a new room."""
    try:
        user_id = get_current_user_id()
        data = request.json
        name = data.get('name')
        summary = data.get('summary')
        exists_ok = data.get('exists_ok', False)
        
        if not name:
            return jsonify({"status": "error", "message": "Room name is required"}), 400
        
        result = dm.create_room(dungeon=dungeon, name=name, summary=summary, exists_ok=exists_ok, user_id=user_id)
        return jsonify({"status": "ok", "room": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/rename', methods=['POST'])
@require_auth
def rename_room(dungeon, room):
    """Rename a room."""
    try:
        user_id = get_current_user_id()
        data = request.json
        new_name = data.get('new_name')
        
        if not new_name:
            return jsonify({"status": "error", "message": "New name is required"}), 400
        
        result = dm.rename_room(dungeon=dungeon, room=room, new_name=new_name, user_id=user_id)
        return jsonify({"status": "ok", "room": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>', methods=['PATCH'])
@require_auth
def update_room(dungeon, room):
    """Update a room."""
    try:
        user_id = get_current_user_id()
        data = request.json
        patch = data.get('patch', {})
        
        if not patch:
            return jsonify({"status": "error", "message": "Patch data is required"}), 400
        
        result = dm.update_room(dungeon=dungeon, room=room, patch=patch, user_id=user_id)
        return jsonify({"status": "ok", "room": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>', methods=['DELETE'])
@require_auth
def delete_room(dungeon, room):
    """Delete a room."""
    try:
        user_id = get_current_user_id()
        confirm_token = request.args.get('token')
        
        dm.delete_room(dungeon=dungeon, room=room, confirm_token=confirm_token, user_id=user_id)
        return jsonify({"status": "ok", "message": "Room deleted"})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.UnsafeOperationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Category operations
@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>', methods=['GET'])
@require_auth
def list_category_items(dungeon, room, category):
    """List items in a category."""
    try:
        user_id = get_current_user_id()
        items = dm.list_category_items(dungeon=dungeon, room=room, category=category, user_id=user_id)
        return jsonify({"status": "ok", "items": items})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>', methods=['POST'])
@require_auth
def ensure_category(dungeon, room, category):
    """Ensure a category exists."""
    try:
        user_id = get_current_user_id()
        result = dm.ensure_category(dungeon=dungeon, room=room, category=category, user_id=user_id)
        return jsonify({"status": "ok", "category": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Item operations
@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items', methods=['POST'])
@require_auth
def create_item(dungeon, room, category):
    """Create a new item."""
    try:
        user_id = get_current_user_id()
        data = request.json
        payload = data.get('payload', {})
        exists_ok = data.get('exists_ok', False)
        
        if not payload.get('name'):
            return jsonify({"status": "error", "message": "Item name is required"}), 400
        
        result = dm.create_item(dungeon=dungeon, room=room, category=category, payload=payload, exists_ok=exists_ok, user_id=user_id)
        return jsonify({"status": "ok", "item": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items/<item>', methods=['GET'])
@require_auth
def read_item(dungeon, room, category, item):
    """Read an item."""
    try:
        user_id = get_current_user_id()
        result = dm.read_item(dungeon=dungeon, room=room, category=category, item=item, user_id=user_id)
        return jsonify({"status": "ok", "item": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items/<item>', methods=['PATCH'])
@require_auth
def update_item(dungeon, room, category, item):
    """Update an item."""
    try:
        user_id = get_current_user_id()
        data = request.json
        patch = data.get('patch', {})
        
        if not patch:
            return jsonify({"status": "error", "message": "Patch data is required"}), 400
        
        result = dm.update_item(dungeon=dungeon, room=room, category=category, item=item, patch=patch, user_id=user_id)
        return jsonify({"status": "ok", "item": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items/<item>/rename', methods=['POST'])
@require_auth
def rename_item(dungeon, room, category, item):
    """Rename an item."""
    try:
        user_id = get_current_user_id()
        data = request.json
        new_name = data.get('new_name')
        
        if not new_name:
            return jsonify({"status": "error", "message": "New name is required"}), 400
        
        result = dm.rename_item(dungeon=dungeon, room=room, category=category, item=item, new_name=new_name, user_id=user_id)
        return jsonify({"status": "ok", "item": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items/<item>', methods=['DELETE'])
@require_auth
def delete_item(dungeon, room, category, item):
    """Delete an item."""
    try:
        user_id = get_current_user_id()
        confirm_token = request.args.get('token')
        
        dm.delete_item(dungeon=dungeon, room=room, category=category, item=item, confirm_token=confirm_token, user_id=user_id)
        return jsonify({"status": "ok", "message": "Item deleted"})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.UnsafeOperationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items/<item>/move', methods=['POST'])
@require_auth
def move_item(dungeon, room, category, item):
    """Move an item."""
    try:
        user_id = get_current_user_id()
        data = request.json
        dst_dungeon = data.get('dst_dungeon')
        dst_room = data.get('dst_room')
        dst_category = data.get('dst_category')
        overwrite = data.get('overwrite', False)
        
        if not all([dst_dungeon, dst_room, dst_category]):
            return jsonify({"status": "error", "message": "Destination dungeon, room, and category are required"}), 400
        
        result = dm.move_item(
            src_dungeon=dungeon, src_room=room, src_category=category, item=item,
            dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
            overwrite=overwrite, user_id=user_id
        )
        return jsonify({"status": "ok", "item": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/rooms/<room>/categories/<category>/items/<item>/copy', methods=['POST'])
@require_auth
def copy_item(dungeon, room, category, item):
    """Copy an item."""
    try:
        user_id = get_current_user_id()
        data = request.json
        dst_dungeon = data.get('dst_dungeon')
        dst_room = data.get('dst_room')
        dst_category = data.get('dst_category')
        new_name = data.get('new_name')
        overwrite = data.get('overwrite', False)
        
        if not all([dst_dungeon, dst_room, dst_category]):
            return jsonify({"status": "error", "message": "Destination dungeon, room, and category are required"}), 400
        
        result = dm.copy_item(
            src_dungeon=dungeon, src_room=room, src_category=category, item=item,
            dst_dungeon=dst_dungeon, dst_room=dst_room, dst_category=dst_category,
            new_name=new_name, overwrite=overwrite, user_id=user_id
        )
        return jsonify({"status": "ok", "item": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except dm.ConflictError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Utility operations
@app.route('/api/search', methods=['GET'])
@require_auth
def search():
    """Search for items."""
    try:
        user_id = get_current_user_id()
        query = request.args.get('query', '')
        dungeon = request.args.get('dungeon')
        tags = request.args.get('tags')
        
        tags_any = tags.split(',') if tags else None
        
        results = dm.search(query=query, dungeon=dungeon, tags_any=tags_any, user_id=user_id)
        return jsonify({"status": "ok", "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/stat', methods=['GET'])
@require_auth
def stat_dungeon(dungeon):
    """Get stat info for a dungeon, room, category, or item."""
    try:
        user_id = get_current_user_id()
        room = request.args.get('room')
        category = request.args.get('category')
        item = request.args.get('item')
        
        result = dm.stat(dungeon=dungeon, room=room, category=category, item=item, user_id=user_id)
        return jsonify({"status": "ok", "stat": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/list', methods=['GET'])
@require_auth
def list_children(dungeon):
    """List children of a dungeon, room, or category."""
    try:
        user_id = get_current_user_id()
        room = request.args.get('room')
        category = request.args.get('category')
        
        result = dm.list_children(dungeon=dungeon, room=room, category=category, user_id=user_id)
        return jsonify({"status": "ok", "children": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/<dungeon>/export', methods=['GET'])
@require_auth
def export_dungeon(dungeon):
    """Export a dungeon."""
    try:
        user_id = get_current_user_id()
        result = dm.export_dungeon(dungeon=dungeon, user_id=user_id)
        return jsonify({"status": "ok", "dungeon": result})
    except dm.NotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dungeons/import', methods=['POST'])
@require_auth
def import_dungeon():
    """Import a dungeon."""
    try:
        user_id = get_current_user_id()
        data = request.json
        dungeon_data = data.get('dungeon')
        strategy = data.get('strategy', 'skip')
        
        if not dungeon_data:
            return jsonify({"status": "error", "message": "Dungeon data is required"}), 400
        
        result = dm.import_dungeon(data=dungeon_data, strategy=strategy, user_id=user_id)
        return jsonify({"status": "ok", "dungeon": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# Character Management Routes
# ============================================================================

# Store agent sessions per user/character (in-memory, not persistent)
# Each session maintains its own LangChain agent and chat history
_agent_sessions = {}

def get_agent_session(session_id: str, user_id: str):
    """
    Get or create an agent session for character creation.
    
    Sessions are stored in memory and allow multiple users to create
    characters simultaneously. Each session has its own character data
    and conversation history.
    """
    if session_id not in _agent_sessions:
        # Create a new agent executor
        agent_executor = create_agent()
        # Initialize character data for this session
        # character_data is already imported at the top of the file
        session_character_data = {
            "name": None,
            "class": None,
            "level": 1,
            "species": None,
            "subspecies": None,
            "background": None,
            "alignment": None,
            "experience_points": 0,
            "ability_scores": {
                "Strength": None,
                "Dexterity": None,
                "Constitution": None,
                "Intelligence": None,
                "Wisdom": None,
                "Charisma": None
            },
            "ability_modifiers": {
                "Strength": None,
                "Dexterity": None,
                "Constitution": None,
                "Intelligence": None,
                "Wisdom": None,
                "Charisma": None
            },
            "saving_throw_proficiencies": [],
            "skill_proficiencies": [],
            "armor_proficiencies": [],
            "weapon_proficiencies": [],
            "tool_proficiencies": [],
            "language_proficiencies": [],
            "passive_perception": None,
            "passive_investigation": None,
            "passive_insight": None,
            "armor_class": None,
            "initiative": None,
            "speed": None,
            "hit_points": None,
            "hit_dice": None,
            "equipment": [],
            "personality_trait": None,
            "ideal": None,
            "bond": None,
            "flaw": None,
            "background_feature": None,
            "class_features": [],
            "subclass": None,
            "species_traits": [],
            "age": None,
            "height": None,
            "weight": None,
            "eyes": None,
            "skin": None,
            "hair": None,
            "backstory": None,
            "generation_method": None
        }
        _agent_sessions[session_id] = {
            "agent_executor": agent_executor,
            "chat_history": [],
            "character_data": session_character_data,
            "user_id": user_id
        }
    return _agent_sessions[session_id]


@app.route('/api/characters', methods=['GET'])
@require_auth
def list_characters():
    """List all characters for the current user."""
    try:
        user_id = get_current_user_id()
        characters = list(db().characters.find(
            {"user_id": user_id, "deleted": False},
            {"user_id": 0, "deleted": 0}
        ).sort("created_at", -1))
        
        # Convert ObjectId to string for JSON serialization
        for char in characters:
            if "_id" in char:
                char["_id"] = str(char["_id"])
            # Convert datetime to ISO string if present
            if "created_at" in char and hasattr(char["created_at"], "isoformat"):
                char["created_at"] = char["created_at"].isoformat()
            if "updated_at" in char and hasattr(char["updated_at"], "isoformat"):
                char["updated_at"] = char["updated_at"].isoformat()
        
        return jsonify({"status": "ok", "characters": characters})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/characters', methods=['POST'])
@require_auth
def create_character():
    """Create a new character creation session."""
    try:
        user_id = get_current_user_id()
        session_id = str(uuid.uuid4())
        
        # Initialize session
        get_agent_session(session_id, user_id)
        
        return jsonify({"status": "ok", "session_id": session_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/characters/<character_id>', methods=['GET'])
@require_auth
def get_character(character_id):
    """Get a character by ID."""
    try:
        user_id = get_current_user_id()
        try:
            obj_id = ObjectId(character_id)
        except:
            return jsonify({"status": "error", "message": "Invalid character ID"}), 400
        
        character = db().characters.find_one(
            {"_id": obj_id, "user_id": user_id, "deleted": False},
            {"user_id": 0, "deleted": 0}
        )
        
        if not character:
            return jsonify({"status": "error", "message": "Character not found"}), 404
        
        # Convert ObjectId to string
        character["_id"] = str(character["_id"])
        
        return jsonify({"status": "ok", "character": character})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/characters/<character_id>', methods=['DELETE'])
@require_auth
def delete_character(character_id):
    """Delete a character (soft delete)."""
    try:
        user_id = get_current_user_id()
        try:
            obj_id = ObjectId(character_id)
        except:
            return jsonify({"status": "error", "message": "Invalid character ID"}), 400
        
        result = db().characters.update_one(
            {"_id": obj_id, "user_id": user_id, "deleted": False},
            {"$set": {"deleted": True, "deleted_at": utcnow()}}
        )
        
        if result.matched_count == 0:
            return jsonify({"status": "error", "message": "Character not found"}), 404
        
        return jsonify({"status": "ok", "message": "Character deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/characters/agent/chat', methods=['POST'])
@require_auth
def agent_chat():
    """
    Interact with the character creation agent.
    
    Sends a message to the LangChain agent and returns the response.
    Maintains conversation history within the session.
    """
    try:
        user_id = get_current_user_id()
        data = request.json
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message:
            return jsonify({"status": "error", "message": "session_id and message are required"}), 400
        
        # Get or create session
        session = get_agent_session(session_id, user_id)
        
        # Temporarily set the global character_data to this session's data
        # This is needed because the agent tools use the global character_data
        original_character_data = character_data.copy()
        character_data.clear()
        character_data.update(session["character_data"])
        
        try:
            # Invoke the agent
            response = session["agent_executor"].invoke({
                "input": message,
                "chat_history": session["chat_history"]
            })
            
            # Update session character data
            session["character_data"] = character_data.copy()
            
            # Update chat history
            session["chat_history"].append(HumanMessage(content=message))
            session["chat_history"].append(AIMessage(content=response['output']))
            
            return jsonify({
                "status": "ok",
                "response": response['output'],
                "character_data": session["character_data"]
            })
        finally:
            # Restore original character_data
            character_data.clear()
            character_data.update(original_character_data)
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/characters/agent/save', methods=['POST'])
@require_auth
def save_character():
    """
    Save the current character from a session to the database.
    
    Validates that the character has a name and doesn't already exist,
    then saves both the character data and formatted character sheet.
    Cleans up the session after saving.
    """
    try:
        user_id = get_current_user_id()
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"status": "error", "message": "session_id is required"}), 400
        
        if session_id not in _agent_sessions:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        session = _agent_sessions[session_id]
        if session["user_id"] != user_id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        char_data = session["character_data"]
        
        if not char_data.get("name"):
            return jsonify({"status": "error", "message": "Character must have a name"}), 400
        
        # Check if character with this name already exists
        existing = db().characters.find_one(
            {"user_id": user_id, "name": char_data["name"], "deleted": False}
        )
        
        if existing:
            return jsonify({"status": "error", "message": f"Character '{char_data['name']}' already exists"}), 409
        
        # Get character sheet
        original_character_data = character_data.copy()
        character_data.clear()
        character_data.update(char_data)
        
        try:
            character_sheet = _generate_character_sheet()
        finally:
            character_data.clear()
            character_data.update(original_character_data)
        
        # Save to database
        character_doc = {
            "user_id": user_id,
            "name": char_data["name"],
            "character_data": char_data,
            "character_sheet": character_sheet,
            "created_at": utcnow(),
            "updated_at": utcnow(),
            "deleted": False
        }
        
        result = db().characters.insert_one(character_doc)
        
        # Clean up session
        del _agent_sessions[session_id]
        
        return jsonify({
            "status": "ok",
            "character_id": str(result.inserted_id),
            "message": "Character saved successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

