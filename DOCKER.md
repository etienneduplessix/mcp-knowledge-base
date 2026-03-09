# Docker Setup Guide

This guide explains how to containerize and run the MCP Knowledge Base Server using Docker.

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t mcp-kb-server .
```

### 2. Run with Docker Compose

```bash
# Start the server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KB_PATHS` | Comma-separated list of knowledge base directories | `/app/knowledge,/app/docs,/app/config` |
| `KB_EXTENSIONS` | File extensions to index | `.md,.json` |
| `KB_MAX_SIZE_MB` | Maximum file size in MB | `10` |

### Volume Mounts

The Docker container expects these directories:

- `/app/knowledge` - Coding standards, guidelines
- `/app/docs` - API documentation, READMEs
- `/app/config` - Configuration files

Mount your local directories:

```bash
docker run -v $(pwd)/knowledge:/app/knowledge:ro \
           -v $(pwd)/docs:/app/docs:ro \
           -v $(pwd)/config:/app/config:ro \
           mcp-kb-server
```

## Usage Scenarios

### 1. Claude Desktop with Docker

Update your Claude Desktop config:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "/path/to/knowledge:/app/knowledge:ro",
        "-v", "/path/to/docs:/app/docs:ro",
        "-v", "/path/to/config:/app/config:ro",
        "mcp-kb-server"
      ]
    }
  }
}
```

### 2. Development Mode

```bash
# Use development compose file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run tests
docker-compose --profile testing run --rm test
```

### 3. Production Deployment

```bash
# Build for production
docker build -t mcp-kb-server:prod --target production .

# Run with resource limits
docker run -d \
  --name mcp-kb-prod \
  --memory=256m \
  --cpus=0.5 \
  -v /host/knowledge:/app/knowledge:ro \
  -v /host/docs:/app/docs:ro \
  mcp-kb-server:prod
```

## Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f mcp-kb-server

# Restart service
docker-compose restart mcp-kb-server

# Scale (if using SSE mode)
docker-compose up -d --scale mcp-kb-server=3

# Clean up
docker-compose down -v
```

## Building Custom Images

### Multi-stage Build

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY mcp_kb_server.py .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "mcp_kb_server.py"]
```

Build:
```bash
docker build --target production -t mcp-kb-server:slim .
```

## Troubleshooting

### Permission Issues

If you encounter permission errors:

```bash
# Fix permissions on knowledge base directories
chmod -R 755 knowledge/ docs/ config/

# Run with specific user
docker run -u $(id -u):$(id -g) -v ... mcp-kb-server
```

### File Not Found

Ensure your knowledge base files are mounted correctly:

```bash
# Check mounted files
docker exec mcp-knowledge-base ls -la /app/knowledge

# Test file reading
docker exec mcp-knowledge-base python -c \
  "from mcp_kb_server import KnowledgeBase, KnowledgeBaseConfig; \
   kb = KnowledgeBase(KnowledgeBaseConfig(paths=[Path('/app/knowledge')])); \
   print(kb.list_files())"
```

### Container Won't Start

Check logs:
```bash
docker-compose logs mcp-kb-server
```

Common issues:
- Missing volume mounts
- Incorrect file permissions
- Invalid JSON configuration

## Performance Tips

1. **Use read-only mounts** (`:ro`) for security and performance
2. **Limit container resources** (memory/CPU)
3. **Use .dockerignore** to reduce build context
4. **Cache dependencies** by copying requirements.txt first

## Security Considerations

- Container runs as non-root user (`mcpuser`)
- Knowledge base files are mounted read-only
- File size limits prevent DoS
- Path validation prevents directory traversal

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t mcp-kb-server .
      
      - name: Run tests
        run: docker-compose --profile testing run --rm test
      
      - name: Push to registry
        if: github.ref == 'refs/heads/main'
        run: |
          docker tag mcp-kb-server:latest ghcr.io/${{ github.repository }}:latest
          docker push ghcr.io/${{ github.repository }}:latest
```
