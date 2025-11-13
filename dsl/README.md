# Dungeon DSL (Domain-Specific Language)

A simple, concise language for managing D&D dungeons through text commands.

## Syntax Overview

Each line is a single command. Lines starting with `#` are comments and are ignored.

## Commands

### Dungeon Commands

```
dungeon create <name> [exists_ok]
dungeon list
dungeon rename <old_name> <new_name>
dungeon delete <name> [hard] [token=<token>]
```

**Examples:**
```
dungeon create Crown Vault
dungeon create My Dungeon exists_ok
dungeon list
dungeon rename Crown Vault New Crown Vault
dungeon delete Old Dungeon
```

### Room Commands

```
room create <dungeon> <name> [summary] [summary=<text>]
room list <dungeon>
room rename <dungeon> <old_name> <new_name>
room delete <dungeon> <name> [hard] [token=<token>]
```

**Examples:**
```
room create Crown Vault Treasury "Steel door; faint hum"
room create Crown Vault Armory summary="Weapon storage"
room list Crown Vault
room rename Crown Vault Treasury New Treasury
room delete Crown Vault Old Room
```

### Item Commands

#### Create Item
```
item create <dungeon> <room> <category> <name> [summary=<text>] [notes=<text>] [tags=<tag1,tag2,...>] [meta=<key1=value1,key2=value2,...>] [exists_ok]
```

Categories: `puzzles`, `traps`, `treasures`, `enemies`

**Examples:**
```
item create Crown Vault Treasury traps Poison Needle summary="Chest lock trap" tags=poison,dc15 meta=dc_disable=15,damage="1d10"

item create Crown Vault Treasury treasures Golden Crown summary="Ornate crown" tags=valuable,artifact meta=value="5000gp",weight="2lbs"
```

#### Read Item
```
item read <dungeon> <room> <category> <name>
```

#### Update Item
```
item update <dungeon> <room> <category> <name> [summary=<text>] [notes=<text>] [tags=<tag1,tag2,...>] [meta=<key1=value1,...>]
```

#### Rename Item
```
item rename <dungeon> <room> <category> <old_name> <new_name>
```

#### Delete Item
```
item delete <dungeon> <room> <category> <name> [hard] [token=<token>]
```

#### Move Item
```
item move <src_dungeon> <src_room> <src_category> <item> <dst_dungeon> <dst_room> <dst_category> [overwrite]
```

#### Copy Item
```
item copy <src_dungeon> <src_room> <src_category> <item> <dst_dungeon> <dst_room> <dst_category> [new_name=<name>] [overwrite]
```

**Examples:**
```
item read Crown Vault Treasury traps Poison Needle
item update Crown Vault Treasury traps Poison Needle meta=dc_disable=18
item rename Crown Vault Treasury traps Poison Needle Deadly Needle
item move Crown Vault Treasury traps Poison Needle Crown Vault Armory traps
item copy Crown Vault Treasury treasures Golden Crown Crown Vault Armory treasures new_name=Crown Copy
item delete Crown Vault Treasury traps Old Trap
```

### Category Commands

```
category list <dungeon> <room> <category>
category ensure <dungeon> <room> <category>
```

**Examples:**
```
category list Crown Vault Treasury traps
category ensure Crown Vault Treasury puzzles
```

### Utility Commands

#### Search
```
search <query> [dungeon=<name>] [tags=<tag1,tag2,...>]
```

**Examples:**
```
search poison
search treasure dungeon=Crown Vault
search "" tags=undead,fire
```

#### Stat
```
stat <dungeon> [room] [category] [item]
```

**Examples:**
```
stat Crown Vault
stat Crown Vault Treasury
stat Crown Vault Treasury traps
stat Crown Vault Treasury traps Poison Needle
```

#### List Children
```
list <dungeon> [room] [category]
```

**Examples:**
```
list Crown Vault
list Crown Vault Treasury
list Crown Vault Treasury traps
```

#### Export
```
export <dungeon>
```

**Example:**
```
export Crown Vault
```

## Value Types

- **Strings**: Plain text, or use quotes for text with spaces: `"My Room Name"`
- **Booleans**: `true`, `false`, `yes`, `no`, `on`, `off`
- **None**: `none`, `null`
- **Numbers**: Automatically parsed as integers or floats
- **Lists**: Use `tags=tag1,tag2,tag3` for comma-separated lists
- **Metadata**: Use `meta=key1=value1,key2=value2` for key-value pairs

## Special Arguments

- `exists_ok` or `--exists-ok`: Allow creating resources that already exist (upsert)
- `hard` or `--hard`: Perform hard deletion (permanent)
- `token=<token>`: Confirmation token for hard deletions (format: `DELETE:<path>`)
- `overwrite` or `--overwrite`: Allow overwriting existing items when moving/copying

## Usage

### Command Line
```bash
python dsl/dungeon_dsl.py example.dsl
```

### Python API
```python
from dsl.dungeon_dsl import execute_file, execute_command

# Execute a script file
output = execute_file("example.dsl", verbose=True)

# Execute a single command
result = execute_command("dungeon create My Dungeon")
```

## Example Script

See `example.dsl` and `complex_example.dsl` for complete examples.

## Notes

- Commands are case-insensitive
- Whitespace is flexible (multiple spaces are treated as one)
- Comments start with `#` and extend to end of line
- Empty lines are ignored
- Errors on one line don't stop execution of subsequent lines

