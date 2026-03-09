# Dockerfile for MCP Knowledge Base Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_kb_server.py .
COPY mcp-config.json .

# Create directories for knowledge base
RUN mkdir -p /app/knowledge /app/docs /app/config

# Set environment variables
ENV KB_PATHS=/app/knowledge,/app/docs,/app/config
ENV KB_EXTENSIONS=.md,.json
ENV KB_MAX_SIZE_MB=10
ENV PYTHONUNBUFFERED=1

# Run as non-root user for security
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose port for SSE transport (optional)
EXPOSE 8000

# Default command runs with stdio transport
# Use ENTRYPOINT for easy overriding, CMD for default args
ENTRYPOINT ["python", "mcp_kb_server.py"]
CMD ["--transport", "stdio"]

# Alternative: Use CMD only for full flexibility
# CMD ["python", "mcp_kb_server.py", "--transport", "stdio"]
