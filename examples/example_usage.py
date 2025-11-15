"""
Example usage of the D&D Dungeon Organizer file manager.

This demonstrates basic operations for managing dungeons, rooms, and items.
"""

import sys
import os
# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from dungeon.dungeon_manager import (
    create_dungeon, create_room, create_item,
    list_dungeons, list_rooms, list_category_items,
    read_item, search, stat, list_children,
    export_dungeon, import_dungeon,
    delete_item, delete_room, delete_dungeon
)


def main():
    """
    Run example usage demonstrations.
    
    Shows how to use the dungeon manager API to create dungeons, rooms,
    items, search, export/import, and perform other operations.
    """
    print("=" * 60)
    print("D&D Dungeon Organizer - Example Usage")
    print("=" * 60)
    print()

    # Clear any existing data (for clean demo)
    # Note: In production, you'd want a proper reset function
    from dungeon_manager import STORE
    STORE.clear()

    # 1. Create a dungeon
    print("1. Creating dungeon 'Crown Vault'...")
    create_dungeon(name="Crown Vault")
    print("   ✓ Created\n")

    # 2. Create rooms
    print("2. Creating rooms...")
    create_room(dungeon="Crown Vault", name="Treasury", summary="Steel door; faint hum.")
    create_room(dungeon="Crown Vault", name="Guard Post", summary="Narrow corridor with arrow slits.")
    print("   ✓ Created rooms\n")

    # 3. Create items (traps, treasures, enemies, puzzles)
    print("3. Creating items...")
    
    # Trap in Treasury
    create_item(
        dungeon="Crown Vault",
        room="Treasury",
        category="traps",
        payload={
            "name": "Poison Needle",
            "summary": "Chest lock trap",
            "notes_md": "Hidden needle in the lock mechanism.",
            "tags": ["poison", "dc15", "mechanical"],
            "metadata": {"dc_disable": 15, "damage": "1d10", "type": "poison"}
        }
    )
    
    # Treasure in Treasury
    create_item(
        dungeon="Crown Vault",
        room="Treasury",
        category="treasures",
        payload={
            "name": "Golden Crown",
            "summary": "Ornate crown with gems",
            "tags": ["valuable", "artifact"],
            "metadata": {"value": "5000gp", "weight": "2lbs"}
        }
    )
    
    # Enemy in Guard Post
    create_item(
        dungeon="Crown Vault",
        room="Guard Post",
        category="enemies",
        payload={
            "name": "Skeleton Guard",
            "summary": "Undead warrior with rusted armor",
            "tags": ["undead", "melee"],
            "metadata": {"hp": 45, "ac": 15, "attack": "1d8+3"}
        }
    )
    
    # Puzzle in Treasury
    create_item(
        dungeon="Crown Vault",
        room="Treasury",
        category="puzzles",
        payload={
            "name": "Rune Lock",
            "summary": "Ancient runic combination lock",
            "notes_md": "Requires three correct symbols: Moon, Star, Sun",
            "tags": ["magical", "dc20"],
            "metadata": {"dc_solve": 20, "hint": "Look to the constellations"}
        }
    )
    
    print("   ✓ Created items\n")

    # 4. List operations
    print("4. Listing dungeons...")
    dungeons = list_dungeons()
    for d in dungeons:
        print(f"   - {d['name']} (deleted: {d['deleted']})")
    print()

    print("5. Listing rooms in 'Crown Vault'...")
    rooms = list_rooms(dungeon="Crown Vault")
    for r in rooms:
        print(f"   - {r['name']}")
    print()

    print("6. Listing traps in Treasury...")
    traps = list_category_items(dungeon="Crown Vault", room="Treasury", category="traps")
    for t in traps:
        print(f"   - {t['name']}")
    print()

    # 5. Read item details
    print("7. Reading item details...")
    item = read_item(dungeon="Crown Vault", room="Treasury", category="traps", item="Poison Needle")
    print(f"   Item: {item['name']}")
    print(f"   Summary: {item['summary']}")
    print(f"   Tags: {', '.join(item['tags'])}")
    print(f"   Metadata: {item['metadata']}")
    print()

    # 6. Search
    print("8. Searching for 'poison'...")
    results = search(query="poison")
    for r in results:
        print(f"   - {r['name']} ({r['category']}) in {r['room']}")
    print()

    print("9. Searching for items with 'undead' tag...")
    results = search(query="", tags_any=["undead"])
    for r in results:
        print(f"   - {r['name']} ({r['category']}) in {r['room']}")
    print()

    # 7. Stat and list_children
    print("10. Getting dungeon stat...")
    d_stat = stat(dungeon="Crown Vault")
    print(f"   {d_stat}")
    print()

    print("11. Listing children of Treasury room...")
    children = list_children(dungeon="Crown Vault", room="Treasury")
    for c in children:
        print(f"   - {c['name']} ({c['type']})")
    print()

    # 8. Export/Import
    print("12. Exporting dungeon...")
    exported = export_dungeon(dungeon="Crown Vault")
    print(f"   Exported dungeon with {len(exported['rooms'])} rooms")
    print()

    print("13. Importing as new dungeon 'Crown Vault Copy'...")
    exported["name"] = "Crown Vault Copy"
    import_dungeon(data=exported, strategy="skip")
    print("   ✓ Imported\n")

    # 9. Cleanup demonstration (soft delete)
    print("14. Soft deleting an item...")
    delete_item(dungeon="Crown Vault", room="Treasury", category="traps", item="Poison Needle")
    print("   ✓ Deleted (soft)")
    
    # Verify it's deleted
    traps_after = list_category_items(dungeon="Crown Vault", room="Treasury", category="traps")
    print(f"   Remaining traps: {len(traps_after)}")
    print()

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

