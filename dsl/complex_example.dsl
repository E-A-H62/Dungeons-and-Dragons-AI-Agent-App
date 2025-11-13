# Complex Example: Building a Complete Dungeon
# This demonstrates more advanced features

# Create main dungeon
dungeon create "Dragon's Lair"

# Create multiple rooms
room create "Dragon's Lair" Entrance "Main entrance with large stone doors"
room create "Dragon's Lair" "Treasure Chamber" "Massive room filled with gold"
room create "Dragon's Lair" "Dragon's Den" "Final chamber with the dragon"
room create "Dragon's Lair" Corridor "Narrow passage between rooms"

# Create traps throughout
item create "Dragon's Lair" Entrance traps "Pit Trap" summary="10-foot deep pit" tags=mechanical,dc15 meta=dc_detect=15,damage="1d6",depth=10
item create "Dragon's Lair" Corridor traps "Poison Dart" summary="Hidden dart launcher" tags=poison,dc18 meta=dc_disable=18,damage="1d4+2",type=poison
item create "Dragon's Lair" "Treasure Chamber" traps "Fire Trap" summary="Magical fire trap protecting treasure" tags=magical,fire,dc20 meta=dc_disable=20,damage="4d6",type=fire

# Create treasures
item create "Dragon's Lair" "Treasure Chamber" treasures "Dragon's Hoard" summary="Pile of gold coins" tags=valuable,gold meta=value="10000gp",weight="500lbs"
item create "Dragon's Lair" "Treasure Chamber" treasures "Dragon Scale Armor" summary="Armor made from dragon scales" tags=magical,armor meta=ac=18,rarity=legendary
item create "Dragon's Lair" "Treasure Chamber" treasures "Ancient Scroll" summary="Spell scroll with unknown magic" tags=magical,scroll meta=level=9,spell="Wish"

# Create enemies
item create "Dragon's Lair" Entrance enemies "Goblin Guards" summary="Two goblin guards at entrance" tags=goblin,melee meta=hp=7,ac=15,count=2
item create "Dragon's Lair" Corridor enemies "Kobold Ambush" summary="Group of kobolds hiding" tags=kobold,ambush meta=hp=5,ac=12,count=4
item create "Dragon's Lair" "Dragon's Den" enemies "Ancient Red Dragon" summary="Massive red dragon" tags=dragon,fire,legendary meta=hp=546,ac=22,breath="12d6",cr=24

# Create puzzles
item create "Dragon's Lair" Entrance puzzles "Riddle Door" summary="Door with riddle inscription" notes="Answer the riddle to pass" tags=riddle,dc18 meta=dc_solve=18,hint="What has keys but no locks?"
item create "Dragon's Lair" Corridor puzzles "Pressure Plate Sequence" summary="Must step on plates in correct order" notes="Sequence: Moon, Star, Sun, Moon" tags=mechanical,dc20 meta=dc_solve=20,sequence="Moon,Star,Sun,Moon"

# List everything
dungeon list
room list "Dragon's Lair"

# Search for specific items
search dragon
search "" tags=fire
search treasure dungeon="Dragon's Lair"

# Get detailed information
item read "Dragon's Lair" "Dragon's Den" enemies "Ancient Red Dragon"
item read "Dragon's Lair" "Treasure Chamber" treasures "Dragon Scale Armor"

# Move an item
item move "Dragon's Lair" Entrance traps "Pit Trap" "Dragon's Lair" Corridor traps

# Copy an item
item copy "Dragon's Lair" "Treasure Chamber" treasures "Dragon Scale Armor" "Dragon's Lair" Entrance treasures "Dragon Scale Armor Copy"

# Update item
item update "Dragon's Lair" "Dragon's Den" enemies "Ancient Red Dragon" meta=hp=600,ac=24

# List all items in categories
category list "Dragon's Lair" Entrance traps
category list "Dragon's Lair" "Treasure Chamber" treasures
category list "Dragon's Lair" "Dragon's Den" enemies

# Export the complete dungeon
export "Dragon's Lair"

