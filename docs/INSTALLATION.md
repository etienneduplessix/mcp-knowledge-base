# Installation Guide

Complete installation and configuration guide for MCP Knowledge Base Server.

## Table of Contents

1. [Quick Setup (Recommended)](#quick-setup-recommended)
2. [Manual Installation](#manual-installation)
3. [AI Tool Configuration](#ai-tool-configuration)
4. [Troubleshooting](#troubleshooting)

## Quick Setup (Recommended)

The easiest way to get started is using the interactive setup wizard:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the setup wizard
python setup.py
```

### What the Wizard Does

1. **Asks for MCP server location** (auto-detects if in current directory)
2. **Configures knowledge bases**:
   - Personal knowledge base path
   - Optional work knowledge base path
3. **Asks which AI tools** you want to configure:
   - Claude Desktop
   - Claude Code
   - Cursor
   - OpenCode
4. **Creates knowledge base directories** with proper structure
5. **Generates all configuration files** automatically

### Example Setup Session

```
======================================================================
MCP Knowledge Base Server - Setup Wizard
======================================================================

Step 1: MCP Server Location
----------------------------------------------------------------------
Where is the MCP server located? [/Users/you/projects/mcp-kb/mcp_kb_server.py]: 

Step 2: Knowledge Base Configuration
----------------------------------------------------------------------
Personal knowledge base path? [~/knowledge-base]: 

Set up a separate work knowledge base? [y/N]: y
Work knowledge base path? [~/knowledge-base-work]: 

Step 3: File Settings
----------------------------------------------------------------------
File extensions to index? [.md,.json]: 
Maximum file size (MB)? [10]: 

Step 4: AI Tools Configuration
----------------------------------------------------------------------
Which AI tools do you want to configure?

Configure for Claude Desktop? [Y/n]: y
Configure for Claude Code? [y/N]: n
Configure for Cursor? [y/N]: y
Configure for OpenCode? [y/N]: y

Configuration Preview
======================================================================

MCP Server Path:     /Users/you/projects/mcp-kb/mcp_kb_server.py
Personal KB Path:    /Users/you/knowledge-base
Work KB Path:        /Users/you/knowledge-base-work
File Extensions:     .md, .json
Max File Size:       10 MB

AI Tools to Configure:
  [✓] Claude Desktop
  [✗] Claude Code
  [✓] Cursor
  [✓] OpenCode

Apply this configuration? [Y/n]: y
```

## Manual Installation

If you prefer manual configuration or the wizard doesn't work for your setup:

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Create Knowledge Base Directories

Create your knowledge base structure:

```bash
# Personal knowledge base
mkdir -p ~/knowledge-base/{docs,knowledge,config}

# Optional: Work knowledge base
mkdir -p ~/knowledge-base-work/{docs,knowledge,config}
```

### Step 3: Configure AI Tools

Choose your preferred AI tool(s) and follow the configuration guide below.

## AI Tool Configuration

### Claude Desktop

**Config Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration:**

1. Copy the template:
   ```bash
   cp config/claude-desktop-config.json.template ~/claude_desktop_config.json
   ```

2. Edit the file and replace placeholders:
   - `{{MCP_SERVER_PATH}}` - Full path to `mcp_kb_server.py`
   - `{{PERSONAL_KB_PATH}}` - Path to your personal knowledge base
   - `{{WORK_KB_PATH}}` - Path to your work knowledge base (optional)

3. Move to the correct location:
   ```bash
   # macOS
   mkdir -p ~/Library/Application\ Support/Claude
   mv ~/claude_desktop_config.json ~/Library/Application\ Support/Claude/
   ```

4. Restart Claude Desktop

### Claude Code

Claude Code uses project-specific MCP configuration.

**Option 1: Project-specific config**

1. In your project directory:
   ```bash
   mkdir -p .claude
   cp config/claude-code-mcp.json.template .claude/mcp.json
   ```

2. Edit `.claude/mcp.json` and replace placeholders

3. Run Claude Code in the project directory

**Option 2: Global config via environment variable**

```bash
export MCP_CONFIG_PATH=/path/to/your/claude-code-mcp.json
claude
```

### Cursor

Cursor uses workspace-specific MCP configuration in `.cursor/mcp.json`.

**Configuration:**

1. In your project root:
   ```bash
   mkdir -p .cursor
   cp config/cursor-mcp.json.template .cursor/mcp.json
   ```

2. Edit `.cursor/mcp.json` and replace placeholders

3. Restart Cursor or reload the window

**Note:** Cursor requires the `.cursor` directory to be in your project root, not globally.

### OpenCode

**Config Location:** `~/.config/opencode/opencode.json`

**Configuration:**

1. Create the config directory:
   ```bash
   mkdir -p ~/.config/opencode
   ```

2. Copy and edit the template:
   ```bash
   cp config/opencode.json.template ~/.config/opencode/opencode.json
   ```

3. Replace placeholders in the file

4. Restart OpenCode

**Using Dual Knowledge Bases with OpenCode:**

OpenCode supports multiple MCP servers. Configure both:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "personal-kb": {
      "type": "local",
      "command": ["python", "/path/to/mcp_kb_server.py"],
      "enabled": true,
      "environment": {
        "KB_PATHS": "/path/to/personal/knowledge,/path/to/personal/docs"
      }
    },
    "work-kb": {
      "type": "local",
      "command": ["python", "/path/to/mcp_kb_server.py"],
      "enabled": true,
      "environment": {
        "KB_PATHS": "/path/to/work/knowledge,/path/to/work/docs"
      }
    }
  }
}
```

Then use:
- `"Use personal-kb to list files"`
- `"Search work-kb for deployment procedures"`

## Environment Variables

The MCP server uses these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `KB_PATHS` | Comma-separated list of knowledge base directories | `./knowledge,./docs` |
| `KB_EXTENSIONS` | Comma-separated list of file extensions | `.md,.json` |
| `KB_MAX_SIZE_MB` | Maximum file size in MB | `10` |

## Troubleshooting

### "File not found" errors

**Problem:** The MCP server can't find your knowledge base files.

**Solution:**
- Check that `KB_PATHS` points to existing directories
- Verify paths are absolute (not relative) in the config
- Ensure the directories contain `.md` or `.json` files

### "Access denied" errors

**Problem:** The MCP server rejects file access.

**Solution:**
- Files must be within the configured `KB_PATHS`
- Check that paths don't contain `..` or try to escape the knowledge base
- Verify file extensions are in `KB_EXTENSIONS`

### Claude Desktop not showing tools

**Problem:** Tools don't appear in Claude Desktop.

**Solution:**
1. Check the config file location is correct
2. Verify JSON syntax (use a JSON validator)
3. Check Claude Desktop logs for errors
4. Restart Claude Desktop completely

### Cursor not loading MCP

**Problem:** Cursor doesn't recognize the MCP configuration.

**Solution:**
- Ensure `.cursor/mcp.json` is in the project root
- Restart Cursor or use "Developer: Reload Window"
- Check the Output panel for MCP errors

### OpenCode can't find tools

**Problem:** OpenCode doesn't show knowledge base tools.

**Solution:**
- Verify config is at `~/.config/opencode/opencode.json`
- Check that the `mcp` section is properly formatted
- Restart OpenCode

## Manual Testing

Test the MCP server directly:

```bash
# List files
python mcp_kb_server.py --path ~/knowledge-base --list

# Read a file
echo '{"file_path": "test.md"}' | python mcp_kb_server.py --path ~/knowledge-base
```

## Getting Help

- Check the [main README](../README.md)
- Review [OPENCODE.md](../OPENCODE.md) for OpenCode-specific details
- See [EDITING_FEATURES.md](../EDITING_FEATURES.md) for write operations
- Open an issue on GitHub

## Tips for Best Results

1. **Use absolute paths** in configuration files to avoid confusion
2. **Organize your knowledge base**:
   ```
   ~/knowledge-base/
   ├── docs/           # Documentation
   ├── knowledge/      # Knowledge articles
   └── config/         # Configuration files
   ```
3. **Keep files under 10MB** for best performance
4. **Use consistent naming** with lowercase and hyphens
5. **Back up your knowledge base** regularly
