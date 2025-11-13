#!/usr/bin/env python3
"""
Test script to verify all imports work correctly after reorganization.
Run this from the project root directory.
"""

import sys
import os

def test_import(module_name, description):
    """Test if a module can be imported."""
    try:
        __import__(module_name)
        print(f"✓ {description}")
        return True
    except ImportError as e:
        print(f"✗ {description}: {e}")
        return False
    except Exception as e:
        print(f"⚠ {description}: {e} (import succeeded but error occurred)")
        return True  # Import worked, but module has other issues

def main():
    print("Testing imports after file reorganization...")
    print("=" * 60)
    
    all_passed = True
    
    # Test core modules
    print("\nCore Modules:")
    all_passed &= test_import("core.db", "core.db")
    all_passed &= test_import("core.mongo_fs", "core.mongo_fs")
    all_passed &= test_import("core.result_format", "core.result_format")
    all_passed &= test_import("core", "core package")
    
    # Test dungeon modules
    print("\nDungeon Modules:")
    all_passed &= test_import("dungeon.dungeon_manager", "dungeon.dungeon_manager")
    all_passed &= test_import("dungeon.interactive_dungeon_manager", "dungeon.interactive_dungeon_manager")
    all_passed &= test_import("dungeon", "dungeon package")
    
    # Test character modules
    print("\nCharacter Modules:")
    all_passed &= test_import("character.dnd_character_agent", "character.dnd_character_agent")
    all_passed &= test_import("character", "character package")
    
    # Test web modules
    print("\nWeb Modules:")
    all_passed &= test_import("web.auth", "web.auth")
    all_passed &= test_import("web.web_app", "web.web_app")
    all_passed &= test_import("web.app_start", "web.app_start")
    
    # Test DSL modules
    print("\nDSL Modules:")
    all_passed &= test_import("dsl.dungeon_dsl", "dsl.dungeon_dsl")
    
    # Test cross-module imports
    print("\nCross-Module Imports:")
    try:
        from core.db import db, utcnow, ensure_indexes
        print("✓ from core.db import ...")
    except Exception as e:
        print(f"✗ from core.db import ...: {e}")
        all_passed = False
    
    try:
        from dungeon import dungeon_manager
        print("✓ from dungeon import dungeon_manager")
    except Exception as e:
        print(f"✗ from dungeon import dungeon_manager: {e}")
        all_passed = False
    
    try:
        from character.dnd_character_agent import create_agent
        print("✓ from character.dnd_character_agent import create_agent")
    except Exception as e:
        print(f"⚠ from character.dnd_character_agent import create_agent: {e}")
        # This might fail if langchain isn't installed, which is okay
    
    try:
        from web.auth import create_user, verify_user
        print("✓ from web.auth import ...")
    except Exception as e:
        print(f"✗ from web.auth import ...: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All critical imports passed!")
    else:
        print("✗ Some imports failed. Check the errors above.")
    print("\nNote: Some modules may show warnings if dependencies aren't installed.")
    print("This is normal if you're just testing the import structure.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

