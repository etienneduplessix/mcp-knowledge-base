#!/usr/bin/env python3
"""
Regression tests: stdout is reserved for JSON-RPC.

In stdio mode the MCP client reads the server's stdout and expects every
line to be a JSON-RPC message. Any diagnostic text written to stdout is
parsed as a malformed response and breaks the handshake, e.g.:

    Warning: Path does not exist: /some/missing/path

These tests launch the real server as a subprocess and assert that all
diagnostics go to stderr while stdout stays parseable.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

SERVER_SCRIPT = Path(__file__).parent / "mcp_kb_server.py"

# A KB root that is guaranteed not to exist, used to trigger the warning.
MISSING_KB_PATH = str(Path(__file__).parent / "does-not-exist-kb-root")

INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "stdio-purity-test", "version": "1.0"},
    },
}


def run_server(args, kb_paths, timeout=60):
    """Run the server with a scripted stdin and capture stdout/stderr separately."""
    env = dict(os.environ)
    env["KB_PATHS"] = kb_paths
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    return subprocess.run(
        [sys.executable, str(SERVER_SCRIPT)] + args,
        input=json.dumps(INITIALIZE_REQUEST) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


def non_json_lines(stream_text):
    """Return the lines of a stream that are not valid JSON."""
    bad = []
    for line in stream_text.splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            bad.append(line)
    return bad


def test_missing_path_warning_does_not_pollute_stdout():
    """A warning about a missing KB root must be written to stderr, not stdout."""
    result = run_server(["--transport", "stdio"], MISSING_KB_PATH)

    bad = non_json_lines(result.stdout)
    if bad:
        print(f"  Found {len(bad)} non-JSON line(s) on stdout:")
        for line in bad:
            print(f"    {line}")
        return False

    warnings = [line for line in result.stderr.splitlines() if "Warning:" in line]
    if not warnings:
        print("  stdout is clean, but no 'Warning:' line was found on stderr.")
        return False

    json_lines = [line for line in result.stdout.splitlines() if line.strip()]
    print(f"  Warning routed to stderr; stdout holds {len(json_lines)} JSON line(s).")
    return True


def test_unimplemented_sse_notice_does_not_pollute_stdout():
    """The 'SSE not implemented' notice must also go to stderr."""
    result = run_server(["--transport", "sse"], MISSING_KB_PATH)

    bad = non_json_lines(result.stdout)
    if bad:
        print(f"  Found {len(bad)} non-JSON line(s) on stdout:")
        for line in bad:
            print(f"    {line}")
        return False

    if "not yet implemented" not in result.stderr:
        print("  stdout is clean, but the SSE notice was not found on stderr.")
        return False

    print("  SSE notice routed to stderr; stdout is empty.")
    return True


def test_stdout_purity_with_existing_paths():
    """A normal run keeps stdout free of diagnostics as well."""
    result = run_server(["--transport", "stdio"], str(Path(__file__).parent / "knowledge"))

    bad = non_json_lines(result.stdout)
    if bad:
        print(f"  Found {len(bad)} non-JSON line(s) on stdout:")
        for line in bad:
            print(f"    {line}")
        return False

    print("  stdout contains only JSON-RPC traffic.")
    return True


def main():
    """Run all tests."""
    tests = [
        ("missing path warning goes to stderr", test_missing_path_warning_does_not_pollute_stdout),
        ("SSE notice goes to stderr", test_unimplemented_sse_notice_does_not_pollute_stdout),
        ("stdout purity with existing paths", test_stdout_purity_with_existing_paths),
    ]

    print("Testing stdio stdout purity...")
    print("=" * 50)

    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\nFAIL: {test_name} raised {type(e).__name__}: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}]: {test_name}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
