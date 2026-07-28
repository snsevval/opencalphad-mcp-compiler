import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))


async def main():
    params = StdioServerParameters(
        command="/root/projects/oc-mcp/run_server.sh",
        args=[],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])

            result = await session.call_tool(
                "list_databases", arguments={}
            )
            print("list_databases ->", result.content[0].text[:300])

            result2 = await session.call_tool(
                "calculate_equilibrium",
                arguments={
                    "database": "AlFe-4SLBF.TDB",
                    "elements_composition": {"AL": 0.2, "FE": 0.8},
                    "temperature_K": 1000,
                },
            )
            print("calculate_equilibrium ->", result2.content[0].text)

            result3 = await session.call_tool(
                "inspect_database", arguments={"database": "steel7.TDB"}
            )
            print("inspect_database ->", result3.content[0].text[:200])

            result4 = await session.call_tool(
                "compare_alloys",
                arguments={
                    "database": "AlFe-4SLBF.TDB",
                    "composition_a": {"AL": 0.25, "FE": 0.75},
                    "composition_b": {"AL": 0.35, "FE": 0.65},
                    "temperature_K": 1000,
                    "label_a": "low_Al",
                    "label_b": "high_Al",
                },
            )
            print("compare_alloys ->", result4.content[0].text[-600:])

            result5 = await session.call_tool(
                "calculate_property_diagram",
                arguments={
                    "database": "AlFe-4SLBF.TDB",
                    "elements_composition": {"AL": 0.3, "FE": 0.7},
                    "temperature_min_K": 900,
                    "temperature_max_K": 1300,
                    "n_points": 5,
                },
            )
            print("calculate_property_diagram content blocks:", [c.type for c in result5.content])
            for c in result5.content:
                if c.type == "text":
                    print("  text ->", c.text[:300])
                elif c.type == "image":
                    print("  image bytes (base64 len) ->", len(c.data))


if __name__ == "__main__":
    asyncio.run(main())
