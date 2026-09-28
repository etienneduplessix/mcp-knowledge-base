#!/usr/bin/env python3
"""
End-to-end test for MCP Knowledge Base Server.

Starts a real MCP stdio server (mcp_kb_server.py) and calls tools over the
MCP protocol to verify path resolution, reading, searching, and querying work
correctly. Run on Windows with:
    $env:PYTHONIOENCODING='utf-8'; python test_mcp_e2e.py
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).parent.resolve()
SERVER_SCRIPT = HERE / "mcp_kb_server.py"

PASS = 0
FAIL = 0


def report(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    mark = "✓" if ok else "✗"
    print(f"{mark} {name}" + (f" — {detail}" if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        env={
            **os.environ,
            "KB_PATHS": ",".join(
                str(HERE / p) for p in ("specs", "knowledge", "docs", "config")
            ),
            "KB_EXTENSIONS": ".md,.json",
            "KB_MAX_SIZE_MB": "10",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # --- list tools ---
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            report("list_tools", len(names) >= 17, f"{len(names)} tools: {', '.join(names[:5])}...")

            # --- read markdown (root-prefixed relative path) ---
            res = await session.call_tool(
                "kb_read_file",
                {"file_path": "knowledge/coding-standards.md"},
            )
            ok = "coding-standards" in str(res.content[0].text)
            report("kb_read_file (knowledge/...)", ok)

            # --- read JSON with config/ prefix (previous bug case) ---
            res = await session.call_tool(
                "kb_read_file",
                {"file_path": "config/app-config.json"},
            )
            ok = '"name"' in str(res.content[0].text) and "Error" not in str(res.content[0].text)
            report("kb_read_file (config/app-config.json)", ok)

            # --- query_json with JSONPath ---
            res = await session.call_tool(
                "kb_query_json",
                {"file_path": "config/app-config.json", "expression": "$.project.name"},
            )
            txt = str(res.content[0].text)
            ok = "Matches:" in txt and "Matches: 0" not in txt
            report("kb_query_json ($.project.name)", ok, txt[:120])

            # --- search ---
            res = await session.call_tool("kb_search", {"query": "MCP"})
            txt = str(res.content[0].text)
            report("kb_search ('MCP')", "Found matches in" in txt)

            # --- list_files with extension filter ---
            res = await session.call_tool("kb_list_files", {"extension": ".json"})
            txt = str(res.content[0].text)
            report("kb_list_files (.json)", "app-config.json" in txt)

            # --- get_file_info ---
            res = await session.call_tool(
                "kb_get_file_info", {"file_path": "docs/api-reference.md"}
            )
            txt = str(res.content[0].text)
            report("kb_get_file_info (docs/api-reference.md)", "api-reference.md" in txt)

    print(f"\nTotal: {PASS}/{PASS + FAIL} tests passed")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
