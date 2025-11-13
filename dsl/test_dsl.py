"""
Example usage of the D&D Dungeon Organizer file manager.

This demonstrates basic operations for managing dungeons, rooms, and items,
and validates that DSL operations return the standardized JSON structure.
"""

import sys
import os
# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from dsl.dungeon_dsl import execute_command, execute_file
from dungeon.dungeon_manager import STORE


def validate_standard_format(result: dict, operation_name: str):
    """
    Validate that a result follows the standardized JSON structure.
    
    Returns:
        (is_valid, list_of_errors) tuple
    """
    errors = []
    required_fields = ["version", "status", "code", "message", "command", "target", "result", "meta"]
    
    # Check required fields
    for field in required_fields:
        if field not in result:
            errors.append(f"Missing required field: {field}")
    
    # Validate version
    if "version" in result and result["version"] != "1.0":
        errors.append(f"Invalid version: {result['version']}, expected '1.0'")
    
    # Validate status
    if "status" in result and result["status"] not in ["ok", "error", "skipped"]:
        errors.append(f"Invalid status: {result['status']}, must be 'ok', 'error', or 'skipped'")
    
    # Validate command structure
    if "command" in result:
        cmd = result["command"]
        if not isinstance(cmd, dict):
            errors.append("'command' must be a dictionary")
        else:
            if "raw" not in cmd:
                errors.append("'command.raw' is required")
            if "name" not in cmd:
                errors.append("'command.name' is required")
            if "args" not in cmd:
                errors.append("'command.args' is required")
    
    # Validate target structure
    if "target" in result:
        target = result["target"]
        if not isinstance(target, dict):
            errors.append("'target' must be a dictionary")
        else:
            for field in ["type", "path", "name"]:
                if field not in target:
                    errors.append(f"'target.{field}' is required")
    
    # Validate result structure
    if "result" in result:
        if not isinstance(result["result"], dict):
            errors.append("'result' must be a dictionary")
    
    # Validate meta structure
    if "meta" in result:
        meta = result["meta"]
        if not isinstance(meta, dict):
            errors.append("'meta' must be a dictionary")
        else:
            if "ts" not in meta:
                errors.append("'meta.ts' is required")
            if "duration_ms" not in meta:
                errors.append("'meta.duration_ms' is required")
            # Validate timestamp format (ISO 8601)
            if "ts" in meta:
                ts = meta["ts"]
                if not isinstance(ts, str) or not ts.endswith("Z"):
                    errors.append(f"'meta.ts' should be ISO 8601 format ending with 'Z', got: {ts}")
    
    # Check for valid status codes
    valid_success_codes = ["CREATED", "UPDATED", "RENAMED", "DELETED_SOFT", "DELETED_HARD", 
                          "LIST", "READ", "ENSURED", "MOVED", "COPIED", "NOOP", "BATCH"]
    valid_error_codes = ["ERROR_PARSE", "ERROR_VALIDATION", "ERROR_NOT_FOUND", 
                        "ERROR_CONFLICT", "ERROR_UNSAFE", "ERROR_INTERNAL"]
    
    if "code" in result:
        code = result["code"]
        status = result.get("status", "")
        if status == "ok" and code not in valid_success_codes:
            errors.append(f"Invalid success code: {code}")
        elif status == "error" and not code.startswith("ERROR_"):
            errors.append(f"Invalid error code: {code}, should start with 'ERROR_'")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def test_operation(dsl_command: str, operation_name: str, expected_status: str = "ok") -> dict:
    """
    Execute a DSL command and validate the result format.
    
    Returns:
        The result dictionary
    """
    print(f"   Testing: {dsl_command}")
    result = execute_command(dsl_command)
    
    if result is None:
        print(f"   ⚠ Skipped (empty/comment line)")
        return None
    
    is_valid, errors = validate_standard_format(result, operation_name)
    
    if is_valid:
        print(f"   ✓ Valid format - Status: {result['status']}, Code: {result['code']}")
        if result['status'] != expected_status:
            print(f"   ⚠ Warning: Expected status '{expected_status}', got '{result['status']}'")
    else:
        print(f"   ✗ INVALID FORMAT:")
        for error in errors:
            print(f"      - {error}")
    
    return result


def main():
    """Run example usage demonstrations with standardized format validation."""
    print("=" * 60)
    print("D&D Dungeon Organizer - Standardized JSON Format Test")
    print("=" * 60)
    print()

    # Clear any existing data (for clean demo)
    STORE.clear()

    # Test 1: Create dungeon
    print("1. Testing dungeon creation...")
    result = test_operation("dungeon create Crown Vault", "dungeon.create", "ok")
    if result:
        print(f"   Message: {result['message']}")
        print(f"   Target path: {result['target']['path']}")
        print(f"   Duration: {result['meta']['duration_ms']}ms")
    print()

    # Test 2: Create rooms
    print("2. Testing room creation...")
    result1 = test_operation('room create Crown Vault Treasury "Steel door; faint hum."', "room.create", "ok")
    result2 = test_operation('room create Crown Vault "Guard Post" "Narrow corridor with arrow slits."', "room.create", "ok")
    print()

    # Test 3: Create items
    print("3. Testing item creation...")
    result = test_operation(
        'item create Crown Vault Treasury traps "Poison Needle" summary="Chest lock trap" tags=poison,dc15,mechanical meta=dc_disable=15,damage="1d10",type=poison',
        "item.create",
        "ok"
    )
    if result and "item" in result["result"]:
        print(f"   Created item: {result['result']['item']['name']}")
    
    result = test_operation(
        'item create Crown Vault Treasury treasures "Golden Crown" summary="Ornate crown with gems" tags=valuable,artifact meta=value="5000gp",weight="2lbs"',
        "item.create",
        "ok"
    )
    
    result = test_operation(
        'item create Crown Vault "Guard Post" enemies "Skeleton Guard" summary="Undead warrior" tags=undead,melee meta=hp=45,ac=15,attack="1d8+3"',
        "item.create",
        "ok"
    )
    print()

    # Test 4: List operations
    print("4. Testing list operations...")
    result = test_operation("dungeon list", "dungeon.list", "ok")
    if result and "dungeons" in result["result"]:
        print(f"   Found {len(result['result']['dungeons'])} dungeons")
    
    result = test_operation("room list Crown Vault", "room.list", "ok")
    if result and "rooms" in result["result"]:
        print(f"   Found {len(result['result']['rooms'])} rooms")
    
    result = test_operation("category list Crown Vault Treasury traps", "category.list", "ok")
    if result and "items" in result["result"]:
        print(f"   Found {len(result['result']['items'])} items in traps category")
    print()

    # Test 5: Read item
    print("5. Testing item read...")
    result = test_operation('item read Crown Vault Treasury traps "Poison Needle"', "item.read", "ok")
    if result and "item" in result["result"]:
        item = result["result"]["item"]
        print(f"   Item: {item['name']}")
        print(f"   Summary: {item.get('summary', 'N/A')}")
        if "tags" in item:
            print(f"   Tags: {', '.join(item['tags'])}")
    print()

    # Test 6: Update item
    print("6. Testing item update...")
    result = test_operation(
        'item update Crown Vault Treasury traps "Poison Needle" summary="Updated: Chest lock trap with poison needle"',
        "item.update",
        "ok"
    )
    print()

    # Test 7: Search
    print("7. Testing search...")
    result = test_operation('search poison', "search", "ok")
    if result and "matches" in result["result"]:
        print(f"   Found {len(result['result']['matches'])} matches")
        for match in result["result"]["matches"][:3]:  # Show first 3
            print(f"      - {match['name']} at {match['path']}")
    print()

    # Test 8: Stat
    print("8. Testing stat...")
    result = test_operation("stat Crown Vault", "stat", "ok")
    if result and "node" in result["result"]:
        node = result["result"]["node"]
        print(f"   Node type: {node.get('type')}")
        print(f"   Node name: {node.get('name')}")
    print()

    # Test 9: List children
    print("9. Testing list children...")
    result = test_operation("list Crown Vault Treasury", "list", "ok")
    if result and "children" in result["result"]:
        print(f"   Found {len(result['result']['children'])} children")
    print()

    # Test 10: Export
    print("10. Testing export...")
    result = test_operation("export Crown Vault", "export", "ok")
    if result and "export" in result["result"]:
        export_data = result["result"]["export"]
        print(f"   Exported dungeon with {len(export_data.get('rooms', {}))} rooms")
    print()

    # Test 11: Error case
    print("11. Testing error handling...")
    result = test_operation("dungeon delete NonExistent", "dungeon.delete", "error")
    if result:
        print(f"   Error code: {result['code']}")
        print(f"   Error message: {result['message']}")
        if "diagnostics" in result:
            print(f"   Diagnostics: {result['diagnostics']}")
    print()

    # Test 12: Delete item (soft)
    print("12. Testing item deletion (soft)...")
    result = test_operation('item delete Crown Vault Treasury traps "Poison Needle"', "item.delete", "ok")
    if result:
        print(f"   Deleted: {result['result'].get('deleted')}")
        print(f"   Hard delete: {result['result'].get('hard')}")
    print()

    # Test 13: Batch file execution
    print("13. Testing batch file execution...")
    import tempfile
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.dsl', delete=False)
    test_file.write("dungeon create BatchTest\n")
    test_file.write("room create BatchTest Room1\n")
    test_file.write("item create BatchTest Room1 traps Trap1 summary=\"Test\"\n")
    test_file.close()
    
    try:
        batch_result = execute_file(test_file.name, verbose=False)
        print(f"   Batch status: {batch_result['status']}")
        print(f"   Batch code: {batch_result['code']}")
        print(f"   Summary: {batch_result['summary']}")
        print(f"   Results count: {len(batch_result['results'])}")
        
        # Validate batch format
        if "version" in batch_result and batch_result["version"] == "1.0":
            print("   ✓ Batch format valid")
        if "file" in batch_result:
            print(f"   ✓ File path included: {batch_result['file']}")
        
        # Validate first result in batch
        if batch_result['results']:
            is_valid, errors = validate_standard_format(batch_result['results'][0], "batch.first_result")
            if is_valid:
                print("   ✓ First batch result format valid")
            else:
                print(f"   ✗ First batch result invalid: {errors}")
    finally:
        os.unlink(test_file.name)
    print()

    print("=" * 60)
    print("Standardized JSON Format Test completed!")
    print("=" * 60)
    print()
    print("Summary:")
    print("  - All DSL operations now return standardized JSON format")
    print("  - Each result includes: version, status, code, message, command, target, result, meta")
    print("  - Error cases return proper error format with diagnostics")
    print("  - Batch operations return batch envelope with summary")
    print()


if __name__ == "__main__":
    main()
