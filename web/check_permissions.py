#!/usr/bin/env python3
"""
Script to check MongoDB user permissions.
Run this to verify what operations your MongoDB user can perform.
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv

load_dotenv()

# Get connection details
MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME", "dnd_dungeon")

if not MONGO_URI:
    print("❌ ERROR: MONGODB_URI not found in environment variables")
    print("   Make sure you have a .env file with MONGODB_URI set")
    sys.exit(1)

print(f"🔗 Connecting to MongoDB...")
print(f"   Database: {DB_NAME}")
print()

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Test connection
    client.admin.command('ping')
    print("✅ Successfully connected to MongoDB")
    print()
    
    # Get current user info
    try:
        user_info = client.admin.command('connectionStatus')
        print("📋 Connection Info:")
        auth_info = user_info.get('authInfo', {})
        authenticated_users = auth_info.get('authenticatedUsers', [])
        if authenticated_users:
            for user in authenticated_users:
                print(f"   User: {user.get('user', 'unknown')}")
                print(f"   Database: {user.get('db', 'unknown')}")
        else:
            print("   No authenticated user info available")
            print(db.getUsers())
        print()
    except Exception as e:
        print(f"⚠ Could not get user info: {e}")
        print()
    
    # Test permissions by attempting various operations
    print("🔍 Testing Permissions:")
    print("-" * 50)
    
    # Test 1: Read permission
    print("1. Testing READ permission...", end=" ")
    try:
        db.dungeons.find_one()
        print("✅ PASS")
    except OperationFailure as e:
        print(f"❌ FAIL: {e}")
    except Exception as e:
        print(f"⚠ ERROR: {e}")
    
    # Test 2: Write permission (insert)
    print("2. Testing INSERT permission...", end=" ")
    try:
        test_doc = {"_permission_test": True, "timestamp": "test"}
        result = db.dungeons.insert_one(test_doc)
        # Clean up test document
        db.dungeons.delete_one({"_id": result.inserted_id})
        print("✅ PASS")
    except OperationFailure as e:
        print(f"❌ FAIL: {e}")
    except Exception as e:
        print(f"⚠ ERROR: {e}")
    
    # Test 3: Update permission
    print("3. Testing UPDATE permission...", end=" ")
    try:
        # Try to update a non-existent document (won't actually update anything)
        db.dungeons.update_one({"_nonexistent": True}, {"$set": {"test": True}})
        print("✅ PASS")
    except OperationFailure as e:
        print(f"❌ FAIL: {e}")
    except Exception as e:
        print(f"⚠ ERROR: {e}")
    
    # Test 4: Delete permission
    print("4. Testing DELETE permission...", end=" ")
    try:
        # Try to delete a non-existent document (won't actually delete anything)
        db.dungeons.delete_one({"_nonexistent": True})
        print("✅ PASS")
    except OperationFailure as e:
        print(f"❌ FAIL: {e}")
    except Exception as e:
        print(f"⚠ ERROR: {e}")
    
    # Test 5: Create Index permission
    print("5. Testing CREATE INDEX permission...", end=" ")
    try:
        db.dungeons.create_index([("_permission_test_field", 1)], name="permission_test_idx")
        # Clean up test index
        db.dungeons.drop_index("permission_test_idx")
        print("✅ PASS")
    except OperationFailure as e:
        error_msg = str(e)
        if "createIndex" in error_msg.lower() or "not authorized" in error_msg.lower():
            print(f"❌ FAIL: {e}")
            print("   ⚠ This is why ensure_indexes() might fail!")
        else:
            print(f"⚠ ERROR: {e}")
    except Exception as e:
        print(f"⚠ ERROR: {e}")
    
    # Test 6: List collections
    print("6. Testing LIST COLLECTIONS permission...", end=" ")
    try:
        collections = db.list_collection_names()
        print(f"✅ PASS (Found {len(collections)} collections)")
        if collections:
            print(f"   Collections: {', '.join(collections)}")
    except OperationFailure as e:
        print(f"❌ FAIL: {e}")
    except Exception as e:
        print(f"⚠ ERROR: {e}")
    
    # Test 7: Check if collections exist
    print()
    print("📊 Current Collections Status:")
    print("-" * 50)
    for coll_name in ["dungeons", "rooms", "items"]:
        try:
            coll = db[coll_name]
            count = coll.count_documents({})
            indexes = list(coll.list_indexes())
            print(f"   {coll_name}:")
            print(f"      Documents: {count}")
            print(f"      Indexes: {len(indexes)}")
        except Exception as e:
            print(f"   {coll_name}: ⚠ Error accessing: {e}")
    
    print()
    print("=" * 50)
    print("✅ Permission check complete!")
    print()
    print("💡 Tips:")
    print("   - If CREATE INDEX failed, you'll need to create indexes manually")
    print("   - If other operations failed, check your MongoDB user roles")
    print("   - For Atlas: Go to Database Access → Select user → Edit → Roles")
    
except ConnectionFailure:
    print("❌ ERROR: Could not connect to MongoDB")
    print(f"   URI: {MONGO_URI[:50]}...")
    print("   Check your MONGODB_URI and network connection")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

