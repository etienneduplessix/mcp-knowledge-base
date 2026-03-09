# MCP Knowledge Base Server - Setup Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**
   ```bash
   python mcp_kb_server.py
   ```

## Docker Deployment

### Option 1: Quick Docker Setup

```bash
# Build the Docker image
make docker-build

# Run with Docker Compose
make docker-run

# Test in Docker
make docker-test

# View logs
make docker-logs

# Stop containers
make docker-stop
```

### Option 2: Manual Docker Commands

```bash
# Build image
docker build -t mcp-kb-server .

# Run container
docker run -d \
  --name mcp-knowledge-base \
  -v $(pwd)/knowledge:/app/knowledge:ro \
  -v $(pwd)/docs:/app/docs:ro \
  -v $(pwd)/config:/app/config:ro \
  mcp-kb-server

# Run tests
docker run --rm \
  -v $(pwd)/knowledge:/app/knowledge:ro \
  -v $(pwd)/docs:/app/docs:ro \
  -v $(pwd)/config:/app/config:ro \
  --entrypoint python mcp-kb-server test_kb.py
```

### Option 3: Using docker-compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests
docker-compose --profile testing run --rm test

# Stop
docker-compose down
```

## Docker + Claude Desktop

To use Docker with Claude Desktop, update your config:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "/absolute/path/to/knowledge:/app/knowledge:ro",
        "-v", "/absolute/path/to/docs:/app/docs:ro",
        "-v", "/absolute/path/to/config:/app/config:ro",
        "mcp-kb-server"
      ]
    }
  }
}
```

See [DOCKER.md](DOCKER.md) for comprehensive Docker documentation.

## Integration with Claude Desktop

### macOS

1. Open Claude Desktop
2. Go to Settings → Developer → Edit Config
3. Add the following configuration:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_kb_server.py"],
      "env": {
        "KB_PATHS": "/path/to/knowledge,/path/to/docs,/path/to/config",
        "KB_EXTENSIONS": ".md,.json",
        "KB_MAX_SIZE_MB": "10"
      }
    }
  }
}
```

4. Restart Claude Desktop

### Windows

1. Open Claude Desktop
2. Go to Settings → Developer → Edit Config
3. The config file is at: `%APPDATA%\Claude\settings.json`
4. Add the MCP server configuration (adjust paths for Windows)

## Available Tools

Once connected, you can use these tools:

### 1. kb_list_files
List all available files in the knowledge base.

### 2. kb_read_file
Read the content of a specific file.
Example: "Read the coding standards file"

### 3. kb_search
Search for text across all knowledge base files.
Example: "Search for 'authentication' in all docs"

### 4. kb_get_file_info
Get metadata about a specific file.

### 5. kb_query_json
Query JSON files using JSONPath expressions.
Example: "Query the app config for database settings"

## Example Usage in Claude

```
You: What files are in the knowledge base?
Claude: [Uses kb_list_files to show available files]

You: Read the API documentation
Claude: [Uses kb_read_file to display api-reference.md]

You: Search for error handling guidelines
Claude: [Uses kb_search to find relevant sections]

You: What are the database settings?
Claude: [Uses kb_query_json with expression '$.database']
```

## Environment Variables

- `KB_PATHS`: Comma-separated list of directories or files to include
- `KB_EXTENSIONS`: Comma-separated list of file extensions to index (default: .md,.json)
- `KB_MAX_SIZE_MB`: Maximum file size in MB (default: 10)

## Project Structure

```
.
├── mcp_kb_server.py           # Main MCP server
├── test_kb.py                 # Test suite
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project configuration
├── mcp-config.json           # MCP configuration
├── Makefile                  # Build automation
├── README.md                 # Project readme
├── SETUP.md                  # Setup instructions
├── DOCKER.md                 # Docker documentation
├── claude-desktop-config.json # Example Claude Desktop config
│
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── docker-compose.dev.yml    # Development Docker config
├── .dockerignore             # Docker ignore rules
│
├── install.sh                # Installation script
├── knowledge/                # Knowledge base: coding standards, guidelines
│   └── coding-standards.md
├── docs/                     # Documentation files
│   └── api-reference.md
└── config/                   # Configuration files
    ├── app-config.json
    └── dependencies.json
```

## Customization

To add your own knowledge base files:

1. Create markdown files in `knowledge/` or `docs/`
2. Create JSON files in `config/`
3. Update `KB_PATHS` environment variable if adding new directories
4. Restart the MCP server

## Troubleshooting

### Server not starting
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version (3.10+): `python --version`

### Files not found
- Check that paths in `KB_PATHS` are absolute paths
- Verify file extensions match `KB_EXTENSIONS`
- Ensure files are not larger than `KB_MAX_SIZE_MB`

### Permission errors
- Ensure the server has read access to knowledge base directories
- Check file permissions on knowledge base files

## Advanced Usage

### Custom Paths

You can specify custom paths when running the server:

```bash
python mcp_kb_server.py --path /path/to/custom/docs --path /path/to/config
```

### Multiple File Types

The server supports any text-based files. Add extensions to `KB_EXTENSIONS`:

```bash
export KB_EXTENSIONS=".md,.json,.txt,.yaml,.yml"
```

### Large Knowledge Bases

For large knowledge bases, consider:
- Increasing `KB_MAX_SIZE_MB`
- Organizing files in subdirectories
- Using file patterns when searching
