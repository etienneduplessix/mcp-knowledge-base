# Path Resolution Guide - IMPORTANT!

## The Issue (FIXED ✅)

**Before:** When you used a relative path like `docs/test.md`, it was resolved from the current working directory where OpenCode runs, which could be anywhere.

**After:** Relative paths are now correctly resolved against your knowledge base root directories.

## How Path Resolution Works Now

### Relative Paths (Recommended)

When you specify a relative path, the MCP server will resolve it against your configured knowledge base directories:

```
If your KB_PATHS = "/Users/you/knowledge-base/knowledge,/Users/you/knowledge-base/docs"

And you use: "docs/meeting-notes.md"
It resolves to: "/Users/you/knowledge-base/docs/meeting-notes.md"

And you use: "knowledge/standards.md"
It resolves to: "/Users/you/knowledge-base/knowledge/standards.md"
```

### Absolute Paths (Also Works)

You can still use absolute paths if you prefer:

```
"/Users/you/knowledge-base/docs/meeting-notes.md"
```

## Usage Examples

### ✅ CORRECT - Using Relative Paths

```
"Use personal-kb kb_create_file with:"
- file_path: "docs/meeting-notes.md"
- content: "# Meeting Notes"

"Use work-kb kb_edit_file with:"
- file_path: "knowledge/standards.md"
- old_text: "old"
- new_text: "new"
```

### ✅ ALSO CORRECT - Using Absolute Paths

```
"Use personal-kb kb_create_file with:"
- file_path: "/Users/etienneduplessix/knowledge-base/docs/meeting-notes.md"
- content: "# Meeting Notes"
```

### ❌ AVOID - Paths Outside Knowledge Base

```
"Use personal-kb kb_create_file with:"
- file_path: "../../some/other/folder/file.md"  # ❌ Will be rejected
```

## Path Priority

When using relative paths, the MCP server checks each configured KB directory in order:

1. First, it tries to resolve against each KB path
2. It uses the first KB path where the file would be valid
3. If no match, it defaults to the first KB path

## Configuration

Your `~/.config/opencode/opencode.json` defines the base paths:

```json
{
  "mcp": {
    "personal-kb": {
      "environment": {
        "KB_PATHS": "/Users/you/knowledge-base/knowledge,/Users/you/knowledge-base/docs,/Users/you/knowledge-base/config"
      }
    }
  }
}
```

With this config:
- `"docs/file.md"` → `/Users/you/knowledge-base/docs/file.md`
- `"knowledge/file.md"` → `/Users/you/knowledge-base/knowledge/file.md`
- `"config/file.json"` → `/Users/you/knowledge-base/config/file.json`

## Troubleshooting

### "Access denied" Error

This means the resolved path is outside your configured KB directories. Make sure:
1. You're using the correct KB server (personal-kb vs work-kb)
2. Your path is within one of the configured directories
3. You're not using `..` or absolute paths outside the KB

### File Not Found

If reading a file and it's not found:
1. Check which KB server you're using
2. Verify the file exists: `"Use personal-kb kb_list_files"`
3. Use the correct relative or absolute path

### Wrong Location

If files are being created in the wrong place:
1. **Update the MCP server** - Make sure you have the latest version with the fix
2. **Restart OpenCode** - The MCP server needs to reload
3. **Use relative paths** - They're more reliable than absolute paths

## Testing

To verify the fix works, try creating a test file:

```
"Use personal-kb kb_create_file with:"
- file_path: "docs/test-path-resolution.md"
- content: "# Test\nThis file should be in knowledge-base/docs/"
```

Then check:
```bash
ls -la ~/knowledge-base/docs/test-path-resolution.md
```

If the file is there, the fix is working! ✅

## Security

The path resolution includes security checks:
- ✅ Paths must be within configured KB directories
- ✅ Cannot use `..` to escape the KB
- ✅ File extensions are validated
- ✅ File size limits are enforced
