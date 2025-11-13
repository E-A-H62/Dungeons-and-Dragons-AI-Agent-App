# Example D&D Dungeon DSL Script
# This demonstrates the basic syntax of the Dungeon DSL

# Create a dungeon
dungeon create "Crown Vault"

# Create rooms in the dungeon
room create "Crown Vault" Treasury "Steel door; faint hum"
room create "Crown Vault" "Guard Post" "Narrow corridor with arrow slits"
room create "Crown Vault" Armory "Weapon storage room"

# Create items (traps, treasures, enemies, puzzles)
item create "Crown Vault" Treasury traps "Poison Needle" summary="Chest lock trap" notes="Hidden needle in the lock mechanism" tags=poison,dc15,mechanical meta=dc_disable=15,damage="1d10",type=poison

item create "Crown Vault" Treasury treasures "Golden Crown" summary="Ornate crown with gems" tags=valuable,artifact meta=value="5000gp",weight="2lbs"

item create "Crown Vault" "Guard Post" enemies "Skeleton Guard" summary="Undead warrior with rusted armor" tags=undead,melee meta=hp=45,ac=15,attack="1d8+3"

item create "Crown Vault" Treasury puzzles "Rune Lock" summary="Ancient runic combination lock" notes="Requires three correct symbols: Moon, Star, Sun" tags=magical,dc20 meta=dc_solve=20,hint="Look to the constellations"

# List all dungeons
dungeon list

# List rooms in a dungeon
room list "Crown Vault"

# List items in a category
category list "Crown Vault" Treasury traps
category list "Crown Vault" Treasury treasures

# Search for items
search poison
search "" tags=undead

# Get stat information
stat "Crown Vault"
stat "Crown Vault" Treasury

# List children
list "Crown Vault"
list "Crown Vault" Treasury

# Read an item
item read "Crown Vault" Treasury traps "Poison Needle"

# Update an item
item update "Crown Vault" Treasury traps "Poison Needle" meta=dc_disable=18,damage="2d6"

# Export dungeon
export "Crown Vault"

