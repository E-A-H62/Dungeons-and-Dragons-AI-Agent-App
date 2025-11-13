"""
Interactive Terminal-Based Dungeon Manager

This program provides a menu-driven interface for managing dungeons using OpenAI
to generate DSL code that is then executed.
"""

import os
from dotenv import load_dotenv
import sys
import json
from typing import Optional, Dict, Any, List
import inspect
from openai import OpenAI

load_dotenv()

# Add parent directory to path for dsl
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from dsl.dungeon_dsl import execute_command
from dungeon import dungeon_manager as dm
from core.db import ensure_indexes


# DSL Specifications
DSL_SPEC = """
# Dungeon DSL (Domain-Specific Language)

A simple, concise language for managing D&D dungeons through text commands.

## Commands

### Dungeon Commands
- dungeon create <name> [exists_ok]
- dungeon list
- dungeon rename <old_name> <new_name>
- dungeon delete <name> [hard] [token=<token>]

### Room Commands
- room create <dungeon> <name> [summary] [summary=<text>]
- room list <dungeon>
- room rename <dungeon> <old_name> <new_name>
- room delete <dungeon> <name> [hard] [token=<token>]

### Item Commands
- item create <dungeon> <room> <category> <name> [summary=<text>] [notes=<text>] [tags=<tag1,tag2,...>] [meta=<key1=value1,key2=value2,...>] [exists_ok]
- item read <dungeon> <room> <category> <name>
- item update <dungeon> <room> <category> <name> [summary=<text>] [notes=<text>] [tags=<tag1,tag2,...>] [meta=<key1=value1,...>]
- item rename <dungeon> <room> <category> <old_name> <new_name>
- item delete <dungeon> <room> <category> <name> [hard] [token=<token>]
- item move <src_dungeon> <src_room> <src_category> <item> <dst_dungeon> <dst_room> <dst_category> [overwrite]
- item copy <src_dungeon> <src_room> <src_category> <item> <dst_dungeon> <dst_room> <dst_category> [new_name=<name>] [overwrite]

Categories: puzzles, traps, treasures, enemies

### Category Commands
- category list <dungeon> <room> <category>
- category ensure <dungeon> <room> <category>

### Utility Commands
- search <query> [dungeon=<name>] [tags=<tag1,tag2,...>]
- stat <dungeon> [room] [category] [item]
- list <dungeon> [room] [category]
- export <dungeon>
"""


# Available actions mapping
ACTIONS = {
    # Dungeon operations
    "1": ("create_dungeon", "Create a new dungeon", ["name"]),
    "2": ("list_dungeons", "List all dungeons", []),
    "3": ("rename_dungeon", "Rename a dungeon", ["dungeon", "new_name"]),
    "4": ("delete_dungeon", "Delete a dungeon", ["dungeon", "hard"]),
    
    # Room operations
    "5": ("create_room", "Create a new room", ["dungeon", "name", "summary"]),
    "6": ("list_rooms", "List rooms in a dungeon", ["dungeon"]),
    "7": ("rename_room", "Rename a room", ["dungeon", "room", "new_name"]),
    "8": ("delete_room", "Delete a room", ["dungeon", "room"]),
    
    # Item operations
    "9": ("create_item", "Create a new item", ["dungeon", "room", "category", "payload"]),
    "10": ("read_item", "Read an item", ["dungeon", "room", "category", "item"]),
    "11": ("update_item", "Update an item", ["dungeon", "room", "category", "item", "patch"]),
    "12": ("rename_item", "Rename an item", ["dungeon", "room", "category", "item", "new_name"]),
    "13": ("delete_item", "Delete an item", ["dungeon", "room", "category", "item"]),
    "14": ("move_item", "Move an item", ["src_dungeon", "src_room", "src_category", "item", "dst_dungeon", "dst_room", "dst_category", "overwrite"]),
    "15": ("copy_item", "Copy an item", ["src_dungeon", "src_room", "src_category", "item", "dst_dungeon", "dst_room", "dst_category", "new_name", "overwrite"]),
    
    # Category operations
    "16": ("list_category_items", "List items in a category", ["dungeon", "room", "category"]),
    "17": ("ensure_category", "Ensure a category exists", ["dungeon", "room", "category"]),
    
    # Utility operations
    "18": ("search", "Search for items", ["query", "dungeon", "tags_any"]),
    "19": ("stat", "Get stat info", ["dungeon", "room", "category", "item"]),
    "20": ("list_children", "List children", ["dungeon", "room", "category"]),
    "21": ("export_dungeon", "Export a dungeon", ["dungeon"]),
    "22": ("import_dungeon", "Import a dungeon", ["data", "strategy"]),
}


def get_openai_client() -> OpenAI:
    """Get OpenAI client, checking for API key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\nOPENAI_API_KEY environment variable not found.")
        return None
    return OpenAI(api_key=api_key)


def get_dsl_spec() -> str:
    """Get the DSL specification text."""
    return DSL_SPEC


def prompt_for_parameter(param_name: str, param_type: Any = str, required: bool = True) -> Any:
    """Prompt user for a parameter value."""
    while True:
        prompt_text = f"Enter {param_name}"
        
        # Add type hints and examples
        if param_name == "category" or param_name == "src_category" or param_name == "dst_category":
            prompt_text += " (puzzles, traps, treasures, or enemies)"
        elif param_name == "hard":
            prompt_text += " (true/false, default: false)"
        elif param_name == "overwrite":
            prompt_text += " (true/false, default: false)"
        elif param_name == "tags" or param_name == "tags_any":
            prompt_text += " (comma-separated, e.g., 'poison,dc15')"
        elif param_name == "metadata":
            prompt_text += " (key=value pairs, comma-separated, e.g., 'dc_disable=15,damage=1d10')"
        elif param_name == "notes_md":
            prompt_text += " (markdown notes)"
        elif param_name == "strategy":
            prompt_text += " (skip, overwrite, or rename)"
        elif param_name == "data":
            prompt_text += " (JSON string or file path)"
        
        if not required:
            prompt_text += " (optional)"
        
        prompt_text += ": "
        
        value = input(prompt_text).strip()
        
        # Handle optional parameters
        if not value and not required:
            return None
        
        if not value and required:
            print(f"{param_name} is required. Please enter a value.")
            continue
        
        # Type conversion
        if param_type == bool:
            if value.lower() in ("true", "yes", "on", "1"):
                return True
            elif value.lower() in ("false", "no", "off", "0", ""):
                return False
            else:
                print(f"Invalid boolean value. Use 'true' or 'false'.")
                continue
        
        if param_name == "tags" or param_name == "tags_any":
            return [t.strip() for t in value.split(",") if t.strip()] if value else []
        
        if param_name == "metadata" and value:
            metadata = {}
            for pair in value.split(","):
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    metadata[key.strip()] = val.strip()
            return metadata
        
        if param_name == "data" and value:
            # Try to parse as JSON, or read from file
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Try as file path
                if os.path.exists(value):
                    with open(value, 'r') as f:
                        return json.load(f)
                else:
                    print(f"Invalid JSON or file not found: {value}")
                    continue
        
        return value


def get_function_signature(func_name: str):
    """Get function signature and parameter info."""
    func = getattr(dm, func_name, None)
    if not func:
        return None
    
    sig = inspect.signature(func)
    params = {}
    for param_name, param in sig.parameters.items():
        params[param_name] = {
            "type": param.annotation if param.annotation != inspect.Parameter.empty else str,
            "default": param.default if param.default != inspect.Parameter.empty else None,
            "required": param.default == inspect.Parameter.empty
        }
    return params


def collect_parameters(func_name: str, param_list: List[str]) -> Dict[str, Any]:
    """Collect parameters from user for a function."""
    params = {}
    func_params = get_function_signature(func_name)
    
    for param_name in param_list:
        # Skip special parameters that need custom handling
        if param_name in ["payload", "data", "patch"]:
            continue
        
        param_info = func_params.get(param_name, {}) if func_params else {}
        param_type = param_info.get("type", str)
        required = param_info.get("required", True)
        default = param_info.get("default", None)
        
        # Special handling for certain parameters
        if param_name in ["hard", "overwrite"]:
            param_type = bool
            required = False
        
        value = prompt_for_parameter(param_name, param_type, required)
        if value is not None:
            params[param_name] = value
    
    # Handle special parameters
    if "payload" in param_list:
        # For create_item - collect payload components
        print("\n📦 Item Details (for payload):")
        name = prompt_for_parameter("name", str, required=True)
        summary = prompt_for_parameter("summary", str, required=False)
        notes_md = prompt_for_parameter("notes_md", str, required=False)
        tags = prompt_for_parameter("tags", list, required=False)
        metadata = prompt_for_parameter("metadata", dict, required=False)
        
        payload = {"name": name}
        if summary:
            payload["summary"] = summary
        if notes_md:
            payload["notes_md"] = notes_md
        if tags:
            payload["tags"] = tags
        if metadata:
            payload["metadata"] = metadata
        params["payload"] = payload
    
    if "patch" in param_list:
        # For update_item - collect patch components
        print("\nUpdate Fields (for patch):")
        summary = prompt_for_parameter("summary", str, required=False)
        notes_md = prompt_for_parameter("notes_md", str, required=False)
        tags = prompt_for_parameter("tags", list, required=False)
        metadata = prompt_for_parameter("metadata", dict, required=False)
        
        patch = {}
        if summary:
            patch["summary"] = summary
        if notes_md:
            patch["notes_md"] = notes_md
        if tags:
            patch["tags"] = tags
        if metadata:
            patch["metadata"] = metadata
        
        # Validate that at least one field is provided
        if not patch:
            print("\n⚠️  Warning: No fields provided for update. At least one field must be specified.")
            raise ValueError("At least one patch field must be provided")
        
        params["patch"] = patch
    
    if "data" in param_list:
        # For import_dungeon
        data = prompt_for_parameter("data", dict, required=True)
        params["data"] = data
    
    # Automatically set exists_ok=False for create operations (managed by program)
    if func_name in ["create_dungeon", "create_room", "create_item"]:
        params["exists_ok"] = False
    
    # Handle delete confirmation (always required for permanent deletion)
    if func_name in ["delete_dungeon", "delete_room", "delete_item"]:
        # Prompt user to type "delete" to confirm deletion
        print("\n⚠️  WARNING: This will permanently remove this item and cannot be undone!")
        confirmation = input("Type 'delete' to confirm deletion: ").strip()
        
        if confirmation.lower() != "delete":
            print("Deletion cancelled. Operation aborted.")
            raise ValueError("Deletion not confirmed")
        
        # Generate the appropriate confirmation token
        if func_name == "delete_dungeon":
            dungeon = params.get("dungeon", "")
            confirm_token = f"DELETE:/{dungeon}"
        elif func_name == "delete_room":
            dungeon = params.get("dungeon", "")
            room = params.get("room", "")
            confirm_token = f"DELETE:/{dungeon}/{room}"
        elif func_name == "delete_item":
            dungeon = params.get("dungeon", "")
            room = params.get("room", "")
            category = params.get("category", "")
            item = params.get("item", "")
            confirm_token = f"DELETE:/{dungeon}/{room}/{category}/{item}"
        else:
            confirm_token = None
        
        if confirm_token:
            params["confirm_token"] = confirm_token
    
    return params


def call_openai_for_dsl(client: OpenAI, action: str, params: Dict[str, Any]) -> Optional[str]:
    """Call OpenAI API to generate DSL code."""
    prompt = f"""You are a DSL code generator for a D&D dungeon management system.

Given the following DSL specifications:

{DSL_SPEC}

Generate a single DSL command line that performs the following action:
- Action: {action}
- Parameters: {json.dumps(params, indent=2)}

Rules:
1. Generate ONLY the DSL command line, nothing else
2. Use proper DSL syntax as shown in the specifications
3. Handle all parameters correctly - ALWAYS quote field values that contain spaces (e.g., notes_md="text with spaces", summary="summary with spaces")
4. Use appropriate field assignments (e.g., summary="...", notes_md="...", tags=..., meta=...)
5. For field assignments like notes_md= or summary=, if the value contains ANY spaces, it MUST be quoted: notes_md="value with spaces"
6. For delete operations with confirm_token, include it as token=<value> (quote the value if it contains special characters like : or /)
7. Do not include any explanations or comments in your response
8. Return only the command line

DSL Command:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a cost-effective model
            messages=[
                {"role": "system", "content": "You are a DSL code generator. Generate only DSL command lines."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        dsl_code = response.choices[0].message.content.strip()
        
        # Clean up the response (remove code blocks if present)
        if dsl_code.startswith("```"):
            lines = dsl_code.split("\n")
            # Remove first and last lines if they are code block markers
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            dsl_code = "\n".join(lines).strip()
        
        return dsl_code
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


def execute_dsl_code(dsl_code: str) -> Optional[Dict[str, Any]]:
    """Execute generated DSL code."""
    print(f"\nGenerated DSL Code: {dsl_code}")
    print("\nExecuting DSL code...\n")
    
    try:
        result = execute_command(dsl_code)
        if result:
            if result.get("status") == "ok":
                print(f"{result.get('message', 'Operation completed successfully')}")
                if result.get("result"):
                    print(f"\n📊 Result: {json.dumps(result.get('result'), indent=2)}")
            else:
                print(f"❌ Error: {result.get('message', 'Unknown error')}")
                if result.get("code"):
                    print(f"   Error Code: {result.get('code')}")
                if result.get("diagnostics"):
                    print(f"   Diagnostics: {json.dumps(result.get('diagnostics'), indent=2)}")
        else:
            print("No result returned (command may have been a comment or empty line)")
        return result
    except Exception as e:
        print(f"❌ Error executing DSL code: {e}")
        import traceback
        print("\nFull error traceback:")
        traceback.print_exc()
        return None


def display_menu():
    """Display the main menu."""
    print("\n" + "=" * 70)
    print("D&D Dungeon Manager - Interactive Terminal")
    print("=" * 70)
    print("\nAvailable Actions:\n")
    
    print("DUNGEON OPERATIONS:")
    print("  1. Create dungeon")
    print("  2. List dungeons")
    print("  3. Rename dungeon")
    print("  4. Delete dungeon")
    
    print("\nROOM OPERATIONS:")
    print("  5. Create room")
    print("  6. List rooms")
    print("  7. Rename room")
    print("  8. Delete room")
    
    print("\nITEM OPERATIONS:")
    print("  9. Create item")
    print(" 10. Read item")
    print(" 11. Update item")
    print(" 12. Rename item")
    print(" 13. Delete item")
    print(" 14. Move item")
    print(" 15. Copy item")
    
    print("\nCATEGORY OPERATIONS:")
    print(" 16. List category items")
    print(" 17. Ensure category")
    
    print("\nUTILITY OPERATIONS:")
    print(" 18. Search")
    print(" 19. Stat")
    print(" 20. List children")
    print(" 21. Export dungeon")
    print(" 22. Import dungeon")
    
    print("\n  0. Exit")
    print("=" * 70)


def main():
    """Main program loop."""
    print("\n\nWelcome to the Interactive Dungeon Manager!")
    print("This program uses OpenAI to generate DSL code for dungeon management.")
    
    # Ensure MongoDB indexes are set up
    print("\nSetting up MongoDB indexes...")
    try:
        success = ensure_indexes()
        if success:
            print("✓ MongoDB indexes ensured.")
        else:
            print("⚠ Index creation skipped (permissions issue).")
            print("   Application will continue, but you may want to create indexes manually via Atlas UI.")
    except Exception as e:
        print(f"⚠ Warning: Could not ensure MongoDB indexes: {e}")
        print("   Continuing anyway, but operations may fail if indexes are missing.")
    
    client = get_openai_client()
    if not client:
        print("\nOpenAI API not available. You can still use the program,")
        print("   but DSL generation will be skipped.")
        print("   Set OPENAI_API_KEY environment variable or enter it when prompted.")
        client = None
    
    while True:
        display_menu()
        choice = input("\nSelect an action (0-22): ").strip()
        
        if choice == "0":
            print("\nGoodbye!")
            break
        
        if choice not in ACTIONS:
            print(f"\nInvalid choice: {choice}. Please select a number between 0-22.")
            continue
        
        func_name, description, param_list = ACTIONS[choice]
        print(f"\nAction: {description}")
        print("-" * 70)
        
        # Collect parameters
        try:
            params = collect_parameters(func_name, param_list)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            continue
        except ValueError as e:
            # Handle hard delete cancellation gracefully
            if "Hard delete not confirmed" in str(e):
                print("\nOperation cancelled.")
            elif "patch field must be provided" in str(e):
                print("\nOperation cancelled - no fields to update.")
            else:
                print(f"\nError collecting parameters: {e}")
            continue
        except Exception as e:
            print(f"\nError collecting parameters: {e}")
            continue
        
        # Special handling for import_dungeon (no direct DSL command)
        if func_name == "import_dungeon":
            print("\nExecuting import_dungeon directly (no DSL equivalent)...")
            try:
                result_data = dm.import_dungeon(**params)
                print(f"Dungeon imported successfully: {json.dumps(result_data, indent=2)}")
            except Exception as e:
                print(f"Error importing dungeon: {e}")
            continue
        
        # Generate DSL code using OpenAI
        if client:
            print("\nCalling OpenAI to generate DSL code...")
            dsl_code = call_openai_for_dsl(client, func_name, params)
            
            if not dsl_code:
                print("Failed to generate DSL code. Please try again.")
                continue
        else:
            # Fallback: construct DSL manually (basic implementation)
            print("\nOpenAI not available. Attempting to construct DSL manually...")
            dsl_code = construct_dsl_manually(func_name, params)
            if not dsl_code:
                print("Could not construct DSL code. Please set up OpenAI API.")
                continue
        
        # Execute the DSL code
        result = execute_dsl_code(dsl_code)
        
        # Ask if user wants to continue
        print("\n" + "-" * 70)
        continue_choice = input("\nContinue? (y/n): ").strip().lower()
        if continue_choice != 'y':
            print("\nGoodbye!")
            break


def construct_dsl_manually(func_name: str, params: Dict[str, Any]) -> Optional[str]:
    """Fallback: manually construct DSL code when OpenAI is not available."""
    # This is a basic implementation - only handles simple cases
    try:
        if func_name == "create_dungeon":
            name = params.get("name", "")
            return f"dungeon create {name}"
        
        elif func_name == "list_dungeons":
            return "dungeon list"
        
        elif func_name == "rename_dungeon":
            dungeon = params.get("dungeon", "")
            new_name = params.get("new_name", "")
            return f"dungeon rename {dungeon} {new_name}"
        
        elif func_name == "delete_dungeon":
            dungeon = params.get("dungeon", "")
            confirm_token = params.get("confirm_token")
            cmd = f"dungeon delete {dungeon}"
            if confirm_token:
                # Quote token if it contains special characters
                if any(c in confirm_token for c in [' ', ':', '/']):
                    cmd += f' token="{confirm_token}"'
                else:
                    cmd += f" token={confirm_token}"
            return cmd
        
        elif func_name == "create_room":
            dungeon = params.get("dungeon", "")
            name = params.get("name", "")
            summary = params.get("summary")
            cmd = f"room create {dungeon} {name}"
            if summary:
                if " " in summary:
                    cmd += f' "{summary}"'
                else:
                    cmd += f" {summary}"
            return cmd
        
        elif func_name == "list_rooms":
            dungeon = params.get("dungeon", "")
            return f"room list {dungeon}"
        
        elif func_name == "update_item":
            dungeon = params.get("dungeon", "")
            room = params.get("room", "")
            category = params.get("category", "")
            item = params.get("item", "")
            patch = params.get("patch", {})
            
            if not patch:
                return None  # Empty patch - should be caught earlier but handle gracefully
            
            cmd = f"item update {dungeon} {room} {category} {item}"
            
            # Add patch fields to the command
            if "summary" in patch:
                summary = patch["summary"]
                if " " in summary:
                    cmd += f' summary="{summary}"'
                else:
                    cmd += f" summary={summary}"
            
            if "notes_md" in patch:
                notes_md = patch["notes_md"]
                # Use "notes" in DSL (maps to notes_md internally)
                if " " in notes_md:
                    cmd += f' notes="{notes_md}"'
                else:
                    cmd += f" notes={notes_md}"
            
            if "tags" in patch:
                tags = patch["tags"]
                if isinstance(tags, list):
                    tags_str = ",".join(str(t) for t in tags)
                    cmd += f" tags={tags_str}"
                else:
                    cmd += f" tags={tags}"
            
            if "metadata" in patch:
                metadata = patch["metadata"]
                if isinstance(metadata, dict):
                    meta_parts = []
                    for k, v in metadata.items():
                        if " " in str(v):
                            meta_parts.append(f'{k}="{v}"')
                        else:
                            meta_parts.append(f"{k}={v}")
                    meta_str = ",".join(meta_parts)
                    cmd += f" meta={meta_str}"
                else:
                    cmd += f" meta={metadata}"
            
            return cmd
        
        # Add more manual constructions as needed...
        # For now, return None for complex cases
        return None
    except Exception as e:
        print(f"Error constructing DSL manually: {e}")
        return None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()

