"""EXECUTE step: run a test case through the real MCP protocol (stdio),
exactly the path an actual AI client (OpenClaw/Nemotron)
uses -- not a direct call into oc_service/server internals. This is what
makes the loop test the thing users actually experience, not just "does
the Python function work".
"""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_SERVER_SH = os.path.abspath(os.path.join(HERE, "..", "run_server.sh"))


class ExecutionError(Exception):
    """Raised when the MCP call itself fails (crash, timeout, transport
    error) -- distinct from a tool call that completes but returns a
    result VERIFY later judges to be wrong."""


async def _call_tool_async(tool_name, arguments, timeout_s):
    params = StdioServerParameters(command=RUN_SERVER_SH, args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout_s)
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments=arguments), timeout=timeout_s
            )
            text_blocks = [c.text for c in result.content if c.type == "text"]
            images = [c.data for c in result.content if c.type == "image"]
            if not text_blocks:
                raise ExecutionError(f"Tool '{tool_name}' returned no text content.")
            try:
                data = json.loads(text_blocks[0])
            except json.JSONDecodeError as exc:
                raise ExecutionError(
                    f"Tool '{tool_name}' returned non-JSON text: {text_blocks[0][:500]}"
                ) from exc
            data["_had_image_content"] = bool(images)
            # Keep the chart itself, not just the fact that there was one:
            # Layer C reviews the rendered image, and the rendering layer is
            # where several real defects in this project actually lived (a
            # gap across the phase transition, a y-axis that started at 0.2,
            # a duplicated legend entry) -- none of which the numbers alone
            # would reveal. Underscore-prefixed so it stays clearly apart
            # from the tool's own result fields.
            if images:
                data["_chart_png_base64"] = images[0]
            return data


def execute(case, timeout_s=180):
    """Run one test case's tool call through the real MCP server.

    Returns the tool's parsed JSON result dict on success. Raises
    ExecutionError on transport/crash/timeout failures -- a case whose
    tool call didn't even complete is always a hard EXECUTE failure, never
    something VERIFY has to reason about.
    """
    try:
        return asyncio.run(
            _call_tool_async(case["tool"], case["arguments"], timeout_s)
        )
    except asyncio.TimeoutError as exc:
        raise ExecutionError(
            f"Tool '{case['tool']}' timed out after {timeout_s}s."
        ) from exc
    except ExecutionError:
        raise
    except Exception as exc:  # transport errors, server crash, etc.
        raise ExecutionError(f"MCP call failed: {exc}") from exc
