#!/usr/bin/env python3
"""
Test script for MCP servers
Tests both FastMCP and Node.js MCP servers for basic functionality
"""

import json
import subprocess
import sys
from pathlib import Path


def test_server(server_command, server_name):
    """Test an MCP server with basic commands."""
    print(f"\nTesting {server_name}")
    print("=" * 50)

    # Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    # Tools list request
    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    # Search tool call request
    search_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_vault",
            "arguments": {"query": "test_value", "limit": 3},
        },
    }

    try:
        # Start server process
        process = subprocess.Popen(
            server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent / "mcp-servers",
        )

        # Send requests
        requests = [init_request, tools_request, search_request]
        outputs = []

        for i, request in enumerate(requests, 1):
            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json)
            process.stdin.flush()

            # Read response
            response_line = process.stdout.readline()
            if response_line.strip():
                try:
                    response = json.loads(response_line.strip())
                    outputs.append((f"Request {i}", response))
                    print(f"Request {i} ({request['method']}): Success")
                except json.JSONDecodeError:
                    print(f"Request {i}: Invalid JSON response")
                    outputs.append((f"Request {i}", response_line.strip()))

        # Clean shutdown
        process.stdin.close()
        process.terminate()
        process.wait(timeout=5)

        # Print detailed results
        print(f"\n{server_name} Results:")
        for label, output in outputs:
            print(f"\n{label}:")
            if isinstance(output, dict):
                print(
                    json.dumps(output, indent=2)[:500]
                    + ("..." if len(json.dumps(output, indent=2)) > 500 else ""),
                )
            else:
                print(str(output)[:500] + ("..." if len(str(output)) > 500 else ""))

        return True

    except subprocess.TimeoutExpired:
        print(f"{server_name}: Timeout")
        process.kill()
        return False
    except Exception as e:
        print(f"{server_name}: Error - {e}")
        return False


def main():
    """Run tests on all MCP servers."""
    print("PAKE MCP Server Testing Suite")
    print("Testing MCP servers for basic functionality")

    # Test FastMCP server
    fastmcp_command = [
        str(Path(__file__).parent / "mcp-env" / ".venv" / "Scripts" / "python.exe"),
        "pake_fastmcp_server.py",
    ]

    # Test Node.js server
    node_command = ["node", "pake_node_mcp_server.js"]

    results = []

    # Run tests
    results.append(("FastMCP Server", test_server(fastmcp_command, "FastMCP Server")))
    results.append(("Node.js Server", test_server(node_command, "Node.js Server")))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"{name}: {status}")

    print(f"\nResults: {passed}/{total} servers passed")

    if passed == total:
        print("All servers are working correctly!")
        print("\nNext steps:")
        print("1. Restart your Gemini CLI")
        print("2. Run: /mcp desc")
        print('3. Test with: @pake-knowledge-vault search_vault query="test"')
    else:
        print("Some servers failed. Check error messages above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
