# D&D Dungeon Manager - Web Application

A beautiful, D&D-themed web interface for managing your dungeons, rooms, items, and characters.

## Features

- **Dungeon Management**: Create, rename, update, and delete dungeons
- **Room Management**: Organize rooms within dungeons
- **Item Management**: Manage puzzles, traps, treasures, and enemies
- **Search**: Search across all items with filters and tags
- **Export/Import**: Export dungeons as JSON and import them back
- **User Authentication**: Secure user accounts with session management
- **Character Creation**: AI-powered D&D 5e character creation agent
- **Character Management**: Save and manage your created characters

## Setup

1. **Install Dependencies**

   Make sure you have all required packages installed:
   ```bash
   pip install -r requirements.txt
   ```

   Or if using a virtual environment:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**

   Create a `.env` file in the project root with:
   ```
   MONGODB_URI=your_mongodb_connection_string
   DB_NAME=dnd_dungeon
   OPENAI_API_KEY=your-openai-api-key  # Required for character creation
   ```

3. **Initialize Database Indexes** (Optional but Recommended)

   ```bash
   python web/app_start.py
   ```

   This ensures MongoDB indexes are created for optimal performance.

4. **Run the Application**

   From the project root directory:
   ```bash
   python web/web_app.py
   ```

   Or specify a custom port (useful if port 5000 is in use):
   ```bash
   PORT=5001 python web/web_app.py
   ```

   The application will start on `http://localhost:5000` (or the port you specified).

5. **Open in Browser**

   Navigate to `http://localhost:5000` (or your custom port) in your web browser.

## Usage

### AI-Powered Action Interpretation

The application includes an AI agent system that interprets user actions and converts them into executable DSL (Domain-Specific Language) commands. This system:

- **Parses User Intent**: The AI agent analyzes user actions and natural language inputs to understand what operation they want to perform
- **Generates DSL Commands**: Converts the interpreted actions into structured DSL commands that follow the dungeon management language specification
- **Executes Actions**: The generated DSL commands are then executed to perform the actual database operations

This AI-powered interpretation layer allows for more flexible interaction patterns and ensures that user actions are correctly translated into the underlying dungeon management operations. The DSL provides a standardized way to represent all dungeon management operations (creating dungeons, rooms, items, searching, etc.), and the AI agent bridges the gap between user intent and DSL command execution.

**Note**: The web interface uses direct API calls for most operations, while the interactive terminal manager (`dungeon/interactive_dungeon_manager.py`) demonstrates the full AI-to-DSL conversion workflow.

### User Authentication

1. **Register**: Click "Register" and create a new account
2. **Login**: Use your username and password to log in
3. All your dungeons and characters are private to your account

### Creating a Dungeon

1. Click the "Create Dungeon" button
2. Enter a dungeon name and optional summary
3. Click "Create"

### Managing Dungeons

- **View**: Click on a dungeon card to see its rooms
- **Rename**: Click the edit icon on a dungeon card
- **Delete**: Click the delete icon (requires confirmation)

### Adding Rooms

1. Click on a dungeon card to view its rooms
2. Click "Add Room" or "Create Room" button
3. Enter room name and optional summary
4. Click "Create"

### Adding Items

1. Navigate to a room (click on a dungeon, then a room)
2. Click "Add Item" in any category section (Puzzles, Traps, Treasures, or Enemies)
3. Fill in the item details:
   - **Category**: Choose from Puzzles, Traps, Treasures, or Enemies
   - **Name**: Item name (required)
   - **Summary**: Brief description (optional)
   - **Notes**: Markdown notes (optional)
   - **Tags**: Comma-separated tags (optional)
   - **Metadata**: Key=value pairs, comma-separated (optional)
4. Click "Create"

### Searching

1. Click "Search" in the sidebar
2. Enter a search query
3. Optionally filter by dungeon or tags
4. Click "Search"

### Exporting/Importing

1. Click "Export" in the sidebar
2. Select a dungeon and click "Export" to get JSON
3. Paste JSON in the import section to import a dungeon
4. Choose import strategy: Skip, Overwrite, or Rename

### Character Creation

1. Click "Characters" in the sidebar
2. Click "Create Character" button
3. Start a conversation with the AI agent to create your character
4. The agent will guide you through:
   - Choosing class, species, background
   - Rolling or assigning ability scores
   - Selecting skills, equipment, and more
5. Click "Save Character" when you're done
6. View your saved characters in the Characters view

## Design

The web interface features:
- **Medieval Fantasy Theme**: D&D-inspired colors and styling
- **Intuitive Navigation**: Easy-to-use sidebar and card-based layout
- **Responsive Design**: Works on desktop and mobile devices
- **Dark/Light Theme**: Toggle between themes for comfortable viewing

## Technical Details

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Database**: MongoDB (via `core/db.py` and `core/mongo_fs.py`)
- **Character Agent**: LangChain-powered AI agent for character creation
- **API**: RESTful API endpoints for all operations

## Project Structure

The application is organized into logical modules:

- `web/` - Web application files
  - `web_app.py` - Main Flask application
  - `auth.py` - Authentication module
  - `app_start.py` - Database initialization script
  - `static/` - CSS and JavaScript files
  - `templates/` - HTML templates
- `core/` - Core database and utilities
- `dungeon/` - Dungeon management modules
- `character/` - Character creation agent
- `dsl/` - Domain-specific language for dungeons
- `examples/` - Example usage scripts

See `STRUCTURE.md` for complete project organization details.

## API Endpoints

All API endpoints are under `/api/` and require authentication (except registration/login):

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/status` - Check authentication status

### Dungeons
- `GET /api/dungeons` - List all dungeons
- `POST /api/dungeons` - Create a dungeon
- `POST /api/dungeons/<name>/rename` - Rename a dungeon
- `PUT /api/dungeons/<name>` - Update a dungeon
- `DELETE /api/dungeons/<name>` - Delete a dungeon
- `GET /api/dungeons/<name>/rooms` - List rooms in a dungeon
- `POST /api/dungeons/<name>/rooms` - Create a room
- `POST /api/dungeons/export` - Export a dungeon as JSON
- `POST /api/dungeons/import` - Import a dungeon from JSON

### Rooms
- `POST /api/dungeons/<name>/rooms/<room>/rename` - Rename a room
- `PUT /api/dungeons/<name>/rooms/<room>` - Update a room
- `DELETE /api/dungeons/<name>/rooms/<room>` - Delete a room
- `GET /api/dungeons/<name>/rooms/<room>/items` - List items in a room

### Items
- `POST /api/dungeons/<name>/rooms/<room>/items` - Create an item
- `GET /api/dungeons/<name>/rooms/<room>/items/<item>` - Get an item
- `PUT /api/dungeons/<name>/rooms/<room>/items/<item>` - Update an item
- `DELETE /api/dungeons/<name>/rooms/<room>/items/<item>` - Delete an item

### Search
- `POST /api/search` - Search for items

### Characters
- `GET /api/characters` - List all characters
- `POST /api/characters` - Create a new character session
- `GET /api/characters/<id>` - Get a character
- `DELETE /api/characters/<id>` - Delete a character
- `POST /api/characters/agent/chat` - Chat with character creation agent
- `POST /api/characters/agent/save` - Save a character from session

See `web/web_app.py` for complete API documentation and implementation.

## Troubleshooting

### Port Already in Use
If port 5000 is already in use (common on macOS), run with a different port:
```bash
PORT=5001 python web/web_app.py
```

### MongoDB Connection Issues
- Verify your `MONGODB_URI` in `.env` is correct
- Check network connectivity
- Run `python web/check_permissions.py` to verify MongoDB permissions

### Import Errors
- Make sure you're running from the project root directory
- Ensure virtual environment is activated if using one
- Verify all dependencies are installed: `pip install -r requirements.txt`

### Character Creation Not Working
- Verify `OPENAI_API_KEY` is set in your `.env` file
- Check that you have sufficient OpenAI API credits
- Ensure LangChain dependencies are installed

