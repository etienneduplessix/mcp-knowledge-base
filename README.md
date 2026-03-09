# MCP Knowledge Base Server

A custom Model Context Protocol (MCP) server that provides tools for reading, searching, querying **AND EDITING** markdown and JSON files as a knowledge base for coding agents.

## Features

### Read Operations
- **Read Markdown Files**: Extract content from README and documentation files
- **Read JSON Files**: Parse and query JSON configuration and data files
- **Search Knowledge Base**: Full-text search across all indexed files
- **Query by Type**: Filter files by type (markdown or JSON)
- **Get File Info**: Retrieve metadata about files in the knowledge base

### Write Operations (NEW!)
- **Create Files**: Add new documentation and config files
- **Edit Files**: Find and replace text in existing files
- **Write Files**: Overwrite entire files
- **Append Files**: Add content to the end of files
- **Delete Files**: Remove files from the knowledge base

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-knowledge-base.git
cd mcp-knowledge-base

# Install dependencies
pip install -r requirements.txt

# Run interactive setup
python setup.py
```

The setup wizard will:
- Ask for your knowledge base locations (personal + optional work)
- Configure for your AI tools (Claude Desktop, Claude Code, Cursor, OpenCode)
- Create knowledge base directories
- Generate all configuration files automatically

### Manual Installation

If you prefer manual configuration:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Copy config templates** from `config/` directory and customize:
   - `opencode.json.template` → `~/.config/opencode/opencode.json`
   - `claude-desktop-config.json.template` → Claude Desktop config
   - `cursor-mcp.json.template` → Your project's `.cursor/mcp.json`

3. **Update paths** in the configs to point to your MCP server and knowledge bases

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed manual setup instructions.

## 🎯 Dual Knowledge Base Setup

The server supports **TWO separate knowledge bases**:

- **Personal KB** (`~/knowledge-base/`): Personal projects, learning notes, hobbies
- **Work KB** (`~/knowledge-base-work/`): Professional work, company projects

This keeps your personal and work knowledge separate while using the same tools!

## 📖 Documentation

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [docs/INSTALLATION.md](docs/INSTALLATION.md) - AI tool configuration guides
- [OPENCODE.md](OPENCODE.md) - OpenCode integration
- [EDITING_FEATURES.md](EDITING_FEATURES.md) - Write operations guide
- [DOCKER.md](DOCKER.md) - Docker deployment
- [QUICKSTART.md](QUICKSTART.md) - Quick reference
- [PATH_RESOLUTION.md](PATH_RESOLUTION.md) - How paths work

## 🔧 Available Tools

### Read Tools
1. **kb_read_file** - Read the content of a specific file
2. **kb_search** - Search for text across all knowledge base files
3. **kb_list_files** - List all available files in the knowledge base
4. **kb_get_file_info** - Get metadata about a specific file
5. **kb_query_json** - Query JSON files with JSONPath expressions

### Write Tools
6. **kb_create_file** - Create new files in the knowledge base
7. **kb_write_file** - Write/overwrite files
8. **kb_edit_file** - Edit files by find & replace
9. **kb_append_file** - Append content to files
10. **kb_delete_file** - Delete files from the knowledge base

## 🐳 Docker Support

```bash
# Build Docker image
make docker-build

# Run with Docker Compose
make docker-run

# Run tests in Docker
make docker-test
```

See [DOCKER.md](DOCKER.md) for detailed Docker configuration.

## 🛠️ Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linter
ruff check .
black .
```

## 📦 Project Structure

```
mcp-knowledge-base/
├── mcp_kb_server.py          # Main MCP server
├── setup.py                  # Interactive setup wizard
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Package configuration
├── Makefile                 # Build commands
├── Dockerfile               # Container image
├── docker-compose.yml       # Production compose
├── docker-compose.dev.yml   # Development compose
├── config/                  # Configuration templates
│   ├── opencode.json.template
│   ├── claude-desktop-config.json.template
│   ├── claude-code-mcp.json.template
│   └── cursor-mcp.json.template
├── docs/                    # Documentation
├── knowledge/              # Example knowledge base
└── tests/                  # Test files
```

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 💡 Tips

- Run `python setup.py --dry-run` to preview configuration before applying
- Use relative paths in your knowledge base for portability
- Keep file sizes under 10MB for best performance
- Organize knowledge bases with subdirectories (docs/, knowledge/, config/)
