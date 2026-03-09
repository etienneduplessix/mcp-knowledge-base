# Quick Start Guide - MCP Knowledge Base Server

## 🚀 Get Started in 3 Steps

### Option 1: Local Python (Fastest)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run tests (optional but recommended)
python test_kb.py

# 3. Start the server
python mcp_kb_server.py
```

### Option 2: Docker (Recommended for Production)

```bash
# 1. Build Docker image
make docker-build

# 2. Run with Docker Compose
make docker-run

# 3. Test the container
make docker-test
```

### Option 3: Using Installation Script

```bash
# Run the automated installer
chmod +x install.sh
./install.sh
```

## 🔧 Integration with Claude Desktop

### Local Mode

Add to `~/Library/Application Support/Claude/settings.json` (macOS):

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_kb_server.py"],
      "env": {
        "KB_PATHS": "/absolute/path/to/knowledge,/absolute/path/to/docs,/absolute/path/to/config"
      }
    }
  }
}
```

### Docker Mode

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

## 📚 What's Included

### Tools (5 Available)

1. **`kb_list_files`** - List all knowledge base files
2. **`kb_read_file`** - Read any file's content
3. **`kb_search`** - Full-text search with context
4. **`kb_get_file_info`** - Get file metadata
5. **`kb_query_json`** - Query JSON with JSONPath

### Example Files

- `knowledge/coding-standards.md` - Python coding guidelines
- `docs/api-reference.md` - API documentation example
- `config/app-config.json` - Configuration example
- `config/dependencies.json` - Dependencies tracking

## 💬 Example Queries

Once connected to Claude, try:

- "List all files in the knowledge base"
- "Read the coding standards"
- "Search for 'authentication' in the docs"
- "What are the database settings?"
- "Show me the project dependencies"

## 🛠️ Make Commands

```bash
make install       # Install Python dependencies
make test          # Run all tests
make run           # Start the server
make docker-build  # Build Docker image
make docker-run    # Run with Docker Compose
make docker-test   # Run tests in Docker
make docker-stop   # Stop Docker containers
make clean         # Clean generated files
make fmt           # Format code with black
make lint          # Lint code with ruff
```

## 📁 Add Your Own Files

1. Create markdown files in `knowledge/` or `docs/`
2. Create JSON files in `config/`
3. Files are automatically indexed
4. Restart Claude Desktop to refresh

## ✅ Verification

After setup, verify everything works:

```bash
# Test Python setup
python test_kb.py

# Test Docker setup
make docker-test

# Both should show: "Total: 6/6 tests passed"
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Module not found | Run `pip install -r requirements.txt` |
| Permission denied | Check file permissions: `chmod -R 755 knowledge/ docs/ config/` |
| Files not found | Use absolute paths in `KB_PATHS` |
| Docker fails | Ensure Docker daemon is running |

## 📖 More Documentation

- [SETUP.md](SETUP.md) - Detailed setup guide
- [DOCKER.md](DOCKER.md) - Docker deployment guide
- [README.md](README.md) - Project overview

## 🎯 Next Steps

1. ✅ Install dependencies
2. ✅ Add your knowledge base files
3. ✅ Configure Claude Desktop
4. ✅ Start asking questions!

---

**Status**: ✅ All tests passing | ✅ Docker ready | ✅ Production-ready
