"""
MCP server that exposes typhon-stress-test commands as callable tools
for Hermes (or any MCP-compatible LLM client).

Usage:
  python -m iacriolla.typhon_mcp.server
  # or via entry point:
  typhon-mcp

Client config:
  {
    "mcpServers": {
      "typhon": {
        "command": "typhon-mcp"
      }
    }
  }
"""

import asyncio
import subprocess
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("typhon-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="typhon_scan",
            description=(
                "Detect and save the hardware and software profile of this machine. "
                "Scans GPU (name, VRAM, driver), CPU, RAM, and any running LLM servers "
                "(llama.cpp, Ollama, LM Studio, vLLM, Jan, text-generation-webui) on their "
                "default ports. Saves results to data/hardware_profile.json."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="typhon_run",
            description=(
                "Run the full benchmark pipeline: scan (if needed) → benchmarks → chronicle → "
                "dashboard. Tests baseline TPS, context sweep, stress, and (in full mode) memory "
                "wall detection. Saves results to data/last_run.json and generates an HTML dashboard."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["quick", "full"],
                        "description": (
                            "'quick': reduced suite, ~3-5 min. "
                            "'full': complete suite with memory wall detection, ~15-20 min. Default."
                        ),
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="typhon_dashboard",
            description=(
                "Regenerate the interactive HTML dashboard from the latest benchmark run. "
                "Outputs a self-contained typhon-dashboard.html file."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "no_open": {
                        "type": "boolean",
                        "description": "If true, generates the file without opening the browser.",
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="typhon_train",
            description=(
                "Train two XGBoost Oracle models on data/chronicle.jsonl. "
                "Requires ≥10 records. Produces oracle_tps.pkl and oracle_vram.pkl."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="typhon_recommend",
            description=(
                "Query the trained Oracle models for optimization recommendations. "
                "Predicts TPS and VRAM across context sizes and flags OOM risks. "
                "Requires prior typhon_train and typhon_scan."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ctx": {
                        "type": "integer",
                        "description": "Extra context size in tokens to include. E.g. 49152.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name as in chronicle. E.g. 'hermes-3-llama-3.1-8b-q8_0'.",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="typhon_export",
            description=(
                "Export anonymized benchmark data for community contribution. "
                "Strips paths, usernames, IPs. Keeps GPU/CPU specs and benchmark metrics."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


def _run_typhon(cmd: list[str], timeout: int = 1800) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    output = result.stdout.strip()
    if result.returncode != 0 and result.stderr.strip():
        stderr = result.stderr.strip()
        output = f"{output}\n[stderr]: {stderr}" if output else f"[stderr]: {stderr}"
    return output or f"Command exited with code {result.returncode}"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    loop = asyncio.get_event_loop()

    if name == "typhon_scan":
        cmd = ["typhon-scan"]
    elif name == "typhon_run":
        cmd = ["typhon-run"]
        if arguments.get("mode") == "quick":
            cmd.append("--quick")
    elif name == "typhon_dashboard":
        cmd = ["typhon-dashboard"]
        if arguments.get("no_open"):
            cmd.append("--no-open")
    elif name == "typhon_train":
        cmd = ["typhon-train"]
    elif name == "typhon_recommend":
        cmd = ["typhon-recommend"]
        if arguments.get("ctx"):
            cmd.extend(["--ctx", str(arguments["ctx"])])
        if arguments.get("model"):
            cmd.extend(["--model", arguments["model"]])
    elif name == "typhon_export":
        cmd = ["typhon-export"]
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    output = await loop.run_in_executor(None, _run_typhon, cmd)
    return [types.TextContent(type="text", text=output)]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="typhon-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())