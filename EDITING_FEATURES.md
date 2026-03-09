# MCP Knowledge Base Server - With Editing Capabilities

## What's New - Editing Features Added! 🎉

Your MCP Knowledge Base Server now supports **full CRUD operations**:

### NEW: Write Operations

| Tool | Description | Use Case |
|------|-------------|----------|
| `kb_create_file` | Create new files | Add new documentation |
| `kb_write_file` | Write/overwrite files | Update entire files |
| `kb_edit_file` | Edit by find & replace | Fix specific text |
| `kb_append_file` | Append to files | Add to logs/notes |
| `kb_delete_file` | Delete files | Clean up old files |

### Existing: Read Operations

| Tool | Description |
|------|-------------|
| `kb_list_files` | List all files |
| `kb_read_file` | Read file content |
| `kb_search` | Search across files |
| `kb_get_file_info` | Get file metadata |
| `kb_query_json` | Query JSON files |

## Dual Knowledge Base Setup

You now have **TWO separate knowledge bases**:

### 1. Personal Knowledge Base
**Location:** `~/knowledge-base/`
- Personal projects
- Learning notes
- Hobbies
- Non-confidential content

### 2. Work Knowledge Base  
**Location:** `~/knowledge-base-work/`
- Professional work
- Company projects
- Work procedures
- Confidential work info

## OpenCode Configuration

Your `~/.config/opencode/opencode.json` now includes both:

```json
{
  "mcp": {
    "personal-kb": {
      // Personal knowledge base
      "environment": {
        "KB_PATHS": "/Users/etienneduplessix/knowledge-base/..."
      }
    },
    "work-kb": {
      // Work knowledge base
      "environment": {
        "KB_PATHS": "/Users/etienneduplessix/knowledge-base-work/..."
      }
    }
  }
}
```

## Usage Examples

### Reading (Works with both KBs)

```
"Use personal-kb to list all files"
"Search work-kb for 'deployment'"
"Read the coding standards from personal-kb"
"Query work-kb config for API endpoints"
```

### Writing (NEW!)

```
"Use personal-kb kb_create_file to create docs/new-project.md with content..."
"Use work-kb kb_edit_file to fix the typo in standards.md"
"Use personal-kb kb_append_file to add to my notes"
"Use work-kb kb_delete_file to remove old-file.md"
```

## Practical Examples

### Example 1: Create Meeting Notes

```
Use work-kb kb_create_file with:
- file_path: "docs/meetings/2024-01-15-sprint-planning.md"
- content: |
    # Sprint Planning - Jan 15, 2024
    
    ## Attendees
    - John, Sarah, Mike
    
    ## Goals
    - Complete authentication module
    - Fix critical bugs
```

### Example 2: Update Documentation

```
Use personal-kb kb_edit_file with:
- file_path: "knowledge/python-tips.md"
- old_text: "Use list comprehensions for simple loops"
- new_text: "Use list comprehensions for simple loops (but avoid complex ones)"
```

### Example 3: Add to Daily Log

```
Use work-kb kb_append_file with:
- file_path: "docs/daily-log.md"
- content: |
    
    ## 2024-01-15
    - Completed user authentication
    - Started working on payment integration
    - Blocked: waiting for API keys
```

## Security Notes

⚠️ **Important:** The editing tools have these protections:

1. **Path validation** - Can only edit files within configured KB paths
2. **Extension validation** - Only `.md` and `.json` files
3. **Size limits** - Max file size (default 10MB)
4. **No directory traversal** - Cannot access files outside KB

## Project Structure

```
~/
├── knowledge-base/              # Personal KB
│   ├── knowledge/
│   ├── docs/
│   ├── config/
│   └── README.md
│
└── knowledge-base-work/        # Work KB
    ├── knowledge/
    ├── docs/
    ├── config/
    └── README.md
```

## Files Created

✅ **mcp_kb_server.py** - Updated with editing tools  
✅ **~/.config/opencode/opencode.json** - Dual KB configuration  
✅ **~/knowledge-base-work/** - Work KB directory structure  
✅ **README files** - Documentation for both KBs  

## Next Steps

1. **Restart OpenCode** to load the new configuration
2. **Test both KBs**:
   ```
   "Use personal-kb to list files"
   "Use work-kb to list files"
   ```
3. **Try editing**:
   ```
   "Use personal-kb kb_create_file to create test.md with content Hello World"
   ```

## Migration from Single KB

If you were using the single KB before:
- Your original `~/knowledge-base/` still works as **personal-kb**
- New `~/knowledge-base-work/` is available as **work-kb**
- Both are independent and accessible from any project

---

**All tests passing! ✅**
- 6 original tests pass
- 5 new editing operations work
- Dual KB configuration ready
