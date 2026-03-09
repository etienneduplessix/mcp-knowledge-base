# OpenCode Integration Guide

This guide explains how to add the MCP Knowledge Base Server to OpenCode.

## Configuration File Location

OpenCode looks for configuration files in these locations (in order of priority):

1. **Project-level**: `./opencode.json` or `./opencode.jsonc` (in your working directory)
2. **Global**: `~/.config/opencode/opencode.json` (applies to all projects)

## Option 1: Project-Level Configuration (Recommended)

Place the `opencode.json` file in your project's root directory:

```bash
cp /Users/etienneduplessix/Developement/mcp-test/opencode.json /path/to/your/project/opencode.json
```

Edit the paths in the file to match your project's knowledge base locations:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "knowledge-base": {
      "type": "local",
      "command": ["python", "/absolute/path/to/mcp_kb_server.py"],
      "enabled": true,
      "environment": {
        "KB_PATHS": "/path/to/your/project/knowledge,/path/to/your/project/docs",
        "KB_EXTENSIONS": ".md,.json",
        "KB_MAX_SIZE_MB": "10"
      }
    }
  }
}
```

## Option 2: Global Configuration

Add to your global OpenCode config:

```bash
mkdir -p ~/.config/opencode
cp /Users/etienneduplessix/Developement/mcp-test/opencode.json ~/.config/opencode/opencode.json
```

## Option 3: Docker Configuration

If you prefer using Docker:

```bash
cp /Users/etienneduplessix/Developement/mcp-test/opencode-docker.json /path/to/your/project/opencode.json
```

Or use this configuration directly:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "knowledge-base": {
      "type": "local",
      "command": [
        "docker",
        "run",
        "-i",
        "--rm",
        "-v", "/path/to/your/knowledge:/app/knowledge:ro",
        "-v", "/path/to/your/docs:/app/docs:ro",
        "mcp-kb-server"
      ],
      "enabled": true
    }
  }
}
```

## Verification

After adding the configuration:

1. **Restart OpenCode** if it's already running
2. The MCP tools should be automatically available
3. You can reference the server by name: `knowledge-base`

## Usage in OpenCode

Once configured, you can ask OpenCode to:

```
Use the knowledge-base MCP to list all available files
```

```
Search the knowledge-base for "authentication"
```

```
Read the coding standards from the knowledge-base
```

```
Query the knowledge-base JSON config for database settings
```

## Available Tools

Your OpenCode agent will have access to these tools:

| Tool | Description |
|------|-------------|
| `kb_list_files` | List all knowledge base files |
| `kb_read_file` | Read content of a specific file |
| `kb_search` | Search text across all files |
| `kb_get_file_info` | Get file metadata |
| `kb_query_json` | Query JSON with JSONPath |

## Troubleshooting

### MCP Server Not Found

1. Check that the configuration file is in the correct location
2. Verify the paths in the configuration are absolute paths
3. Ensure the server script is executable: `chmod +x mcp_kb_server.py`

### Permission Denied

For local Python:
```bash
chmod +x /path/to/mcp_kb_server.py
```

For Docker:
```bash
# Ensure Docker daemon is running
docker ps
```

### Environment Variables Not Working

Make sure to use `"environment"` key in the MCP config, not `"env"`:

```json
{
  "mcp": {
    "knowledge-base": {
      "environment": {
        "KB_PATHS": "/path/to/files"
      }
    }
  }
}
```

## Configuration Reference

### Required Fields

- `type`: Must be `"local"` for local servers
- `command`: Array with command and arguments
- `enabled`: Boolean to enable/disable the server

### Optional Fields

- `environment`: Object with environment variables
- `timeout`: Timeout in milliseconds (default: varies)

## Example Configurations

### Minimal Configuration

```json
{
  "mcp": {
    "kb": {
      "type": "local",
      "command": ["python", "/path/to/mcp_kb_server.py"],
      "enabled": true
    }
  }
}
```

### Full Configuration

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "knowledge-base": {
      "type": "local",
      "command": ["python", "/Users/etienneduplessix/Developement/mcp-test/mcp_kb_server.py"],
      "enabled": true,
      "environment": {
        "KB_PATHS": "/Users/etienneduplessix/Developement/mcp-test/knowledge,/Users/etienneduplessix/Developement/mcp-test/docs,/Users/etienneduplessix/Developement/mcp-test/config",
        "KB_EXTENSIONS": ".md,.json",
        "KB_MAX_SIZE_MB": "10",
        "PYTHONUNBUFFERED": "1"
      },
      "timeout": 30000
    }
  }
}
```

## Multiple Knowledge Bases

You can configure multiple knowledge base servers:

```json
{
  "mcp": {
    "project-kb": {
      "type": "local",
      "command": ["python", "/path/to/mcp_kb_server.py"],
      "environment": {
        "KB_PATHS": "/path/to/project/docs"
      },
      "enabled": true
    },
    "company-kb": {
      "type": "local",
      "command": ["python", "/path/to/mcp_kb_server.py"],
      "environment": {
        "KB_PATHS": "/path/to/company/standards"
      },
      "enabled": true
    }
  }
}
```

## Next Steps

1. Create your `opencode.json` configuration
2. Add your knowledge base files to the configured directories
3. Start OpenCode in your project directory
4. Ask OpenCode to use the knowledge base!

## Links

- [OpenCode MCP Documentation](https://opencode.ai/docs/mcp-servers/)
- [MCP Configuration Guide](https://opencodeguide.com/en/mcp-configuration)
